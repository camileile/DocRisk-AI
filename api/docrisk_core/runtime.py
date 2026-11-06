"""Preparação operacional do processo da API (Dev4 / D4-04).

Executado no início do lifespan, antes de abrir o banco:

1. valida a configuração e reúne TODOS os problemas numa mensagem legível
   (em vez de falhar só no primeiro lote ou com traceback cru);
2. garante uma única instância por DOCRISK_DATA_DIR: a fila do worker é em
   memória, então dois processos sobre o mesmo banco processariam os mesmos
   lotes em duplicidade. A trava é do sistema operacional (liberada mesmo se o
   processo morrer), não um arquivo "pid" que fica órfão;
3. registra um resumo de inicialização sem segredos.

Não altera regras de negócio nem o contrato das rotas.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit

from . import config

log = logging.getLogger("docrisk.runtime")

PROVEDORES = {"gemini", "textlayer", "tesseract"}
LOOPBACK = {"localhost", "127.0.0.1", "[::1]", "::1"}
CORS_PADRAO = "http://localhost:3000,http://127.0.0.1:3000"


class ConfiguracaoInvalida(RuntimeError):
    """Configuração impede a inicialização segura. A mensagem lista cada problema."""

    def __init__(self, problemas: list[str]):
        self.problemas = problemas
        texto = "\n".join(f"  - {p}" for p in problemas)
        super().__init__(f"Configuração inválida do DocRisk AI ({len(problemas)} problema(s)):\n{texto}\n"
                         "Corrija api/.env ou as variáveis de ambiente (modelo: .env.example).")


class InstanciaDuplicada(RuntimeError):
    pass


def origens_cors(valor: str | None = None) -> list[str]:
    bruto = os.getenv("CORS_ORIGINS", CORS_PADRAO) if valor is None else valor
    return [o.strip() for o in bruto.split(",") if o.strip()]


def _problemas_cors(origens: list[str]) -> list[str]:
    problemas = []
    if not origens:
        problemas.append("CORS_ORIGINS está vazio: o frontend não conseguiria chamar a API.")
    for origem in origens:
        if origem in {"*", "null"}:
            problemas.append(f"CORS_ORIGINS não pode conter '{origem}' (credenciais habilitadas).")
            continue
        partes = urlsplit(origem)
        if partes.scheme not in {"http", "https"} or not partes.hostname:
            problemas.append(f"CORS_ORIGINS: '{origem}' não é uma origem http(s)://host[:porta].")
            continue
        if partes.path not in {"", "/"} or partes.query or partes.fragment or partes.username:
            problemas.append(f"CORS_ORIGINS: '{origem}' deve ser só a origem, sem caminho, query ou credenciais.")
            continue
        local = partes.hostname in LOOPBACK
        if partes.scheme == "http" and not local:
            problemas.append(f"CORS_ORIGINS: '{origem}' usa HTTP fora de localhost; use HTTPS.")
        if config.DEMO_MODE and not local:
            problemas.append(f"DOCRISK_DEMO_MODE=1 expõe tokens de teste: origem não local '{origem}' não é permitida.")
    return problemas


def _problemas_diretorio(pasta: Path) -> list[str]:
    try:
        pasta.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return [f"DOCRISK_DATA_DIR '{pasta}' não pode ser criado ({exc.__class__.__name__})."]
    if not pasta.is_dir():
        return [f"DOCRISK_DATA_DIR '{pasta}' existe mas não é um diretório."]
    teste = pasta / f".docrisk-write-test-{os.getpid()}"
    try:
        teste.write_bytes(b"ok")
        teste.unlink()
    except OSError as exc:
        return [f"DOCRISK_DATA_DIR '{pasta}' não permite escrita ({exc.__class__.__name__})."]
    return []


def _problemas_banco(caminho: Path) -> list[str]:
    """Banco existente precisa abrir e responder (leitura barata, sem varredura completa)."""
    if not caminho.exists():
        return []
    import sqlite3
    try:
        conn = sqlite3.connect(f"file:{caminho.as_posix()}?mode=ro", uri=True, timeout=5)
        try:
            conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        return [f"Banco '{caminho.name}' em DOCRISK_DATA_DIR ilegível ({exc}). Restaure o backup "
                "(docs/dev4) ou aponte para outro DATA_DIR; o arquivo não foi alterado."]
    return []


def validar_configuracao() -> list[str]:
    """Devolve a lista de problemas (vazia = ok). Usa os valores já carregados em config."""
    problemas: list[str] = []
    if config.AI_PROVIDER not in PROVEDORES:
        problemas.append(f"AI_PROVIDER='{config.AI_PROVIDER}' inválido; use {', '.join(sorted(PROVEDORES))}.")
    if config.AI_PROVIDER == "gemini" and not config.GEMINI_API_KEY:
        problemas.append("AI_PROVIDER=gemini exige GEMINI_API_KEY. Sem chave, use AI_PROVIDER=textlayer "
                         "(leitor offline, não é IA).")
    for nome, valor in [("GEMINI_RPM", config.GEMINI_RPM), ("MAX_UPLOAD_MB", config.MAX_UPLOAD_MB),
                        ("MAX_PAGINAS", config.MAX_PAGINAS), ("RENDER_DPI", config.RENDER_DPI),
                        ("MAX_LADO_PX", config.MAX_LADO_PX)]:
        if valor <= 0:
            problemas.append(f"{nome} deve ser maior que zero (recebido {valor}).")
    for nome, valor in [("LIMIAR_CONFIANCA", config.LIMIAR_CONFIANCA),
                        ("LIMIAR_LEGIBILIDADE", config.LIMIAR_LEGIBILIDADE)]:
        if not 0.0 <= valor <= 1.0:
            problemas.append(f"{nome} deve estar entre 0 e 1 (recebido {valor}).")
    problemas += _problemas_cors(origens_cors())
    dir_problemas = _problemas_diretorio(config.DATA_DIR)
    problemas += dir_problemas
    if not dir_problemas:
        problemas += _problemas_banco(config.DB_PATH)
    return problemas


# ---------------------------------------------------------------------------
# Instância única por DATA_DIR
# ---------------------------------------------------------------------------
_trava_mem = threading.Lock()
_arquivo = None
_caminho: Path | None = None
_refs = 0


def _travar(fh) -> bool:
    try:
        if sys.platform == "win32":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _destravar(fh) -> None:
    try:
        if sys.platform == "win32":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass


def adquirir_instancia() -> None:
    """Trava DATA_DIR/api.lock. Reentrante no mesmo processo (vários TestClient)."""
    global _arquivo, _caminho, _refs
    if os.getenv("DOCRISK_SINGLE_INSTANCE", "1").strip() == "0":
        return
    caminho = config.DATA_DIR / "api.lock"
    with _trava_mem:
        if _arquivo is not None and _caminho == caminho:
            _refs += 1
            return
        if _arquivo is not None:  # outro DATA_DIR no mesmo processo (testes): troca a trava
            _destravar(_arquivo)
            _arquivo.close()
            _arquivo, _caminho, _refs = None, None, 0
        fh = open(caminho, "a+b")
        if fh.seek(0, os.SEEK_END) == 0:
            fh.write(b"\0")
            fh.flush()
        if not _travar(fh):
            fh.close()
            raise InstanciaDuplicada(
                f"Já existe uma instância da API usando DOCRISK_DATA_DIR='{config.DATA_DIR}'. "
                "A fila do worker é por processo: rode uma única instância (ou outro DATA_DIR).")
        _arquivo, _caminho, _refs = fh, caminho, 1


def liberar_instancia() -> None:
    global _arquivo, _caminho, _refs
    with _trava_mem:
        if _arquivo is None:
            return
        _refs -= 1
        if _refs > 0:
            return
        _destravar(_arquivo)
        _arquivo.close()
        _arquivo, _caminho, _refs = None, None, 0


def preparar_inicio() -> None:
    """Valida, trava a instância e registra o resumo. Levanta erro claro se não puder subir."""
    problemas = validar_configuracao()
    if problemas:
        log.error("inicialização recusada: %d problema(s) de configuração", len(problemas))
        raise ConfiguracaoInvalida(problemas)
    adquirir_instancia()
    log.info(
        "docrisk iniciando pid=%d data_dir=%s provedor=%s modelo=%s gemini_chave=%s sync=%s demo=%s cors=%s",
        os.getpid(), config.DATA_DIR, config.AI_PROVIDER,
        config.GEMINI_MODEL if config.AI_PROVIDER == "gemini" else "-",
        "presente" if config.GEMINI_API_KEY else "ausente", config.SYNC, config.DEMO_MODE,
        ",".join(origens_cors()))
