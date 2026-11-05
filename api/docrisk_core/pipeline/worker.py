"""Fila, processamento em segundo plano e retomada. Dono: FRENTE 2.

O upload só valida e registra (criar_lote); o worker renderiza, lê página por
página e grava o estado de cada uma, para que uma queda nunca obrigue a
recomeçar ("retomada após falha"). Páginas já lidas não voltam à IA (status OK +
cache em ai_cache).

Limitação conhecida: a fila é em memória, uma thread por PROCESSO. Com vários
processos (ex.: uvicorn --workers 2) cada um teria sua fila; para o MVP rode um
único processo. Lotes interrompidos são recolocados na fila por iniciar_worker().
"""
from __future__ import annotations

import hashlib
import json
import logging
import queue
import sqlite3
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .. import config, db
from ..ai import ErroIA, ProvedorLeitura, chave_cache, get_provider
from ..contracts import (
    TIPOS_FOCO, AnalisePagina, CategoriaPendencia, StatusDocumento, StatusLote, StatusPagina,
)
from . import integracao_f3 as f3
from .render import EXTENSAO_POR_TIPO, ArquivoInvalido, inspecionar_arquivo, iterar_paginas
from .routing import rotear
from .segmentation import segmentar

if TYPE_CHECKING:
    from ..auth import Usuario

log = logging.getLogger("docrisk.pipeline.worker")


class LoteNaoEncontrado(LookupError):
    pass


class ConsolidacaoImpossivel(RuntimeError):
    """Consolidação pedida com páginas ainda não lidas."""


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------
def criar_lote(usuario: "Usuario", contract_id: str, filename: str, data: bytes,
               issue_id: int | None = None) -> int:
    """Valida, guarda o ORIGINAL em DATA_DIR/uploads e grava `batches` (RECEBIDO).

    A autorização é da F1 (rota). Aqui: arquivo inválido -> render.ArquivoInvalido;
    o nome enviado pelo usuário é guardado só para exibição — o arquivo em disco
    recebe nome gerado (lote-000123.pdf), nunca um caminho vindo do cliente.
    As páginas são renderizadas depois, no worker.
    """
    info = inspecionar_arquivo(data, filename)
    nome_exibicao = Path((filename or "arquivo").replace("\\", "/")).name[:200] or "arquivo"
    sha = hashlib.sha256(data).hexdigest()
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destino: Path | None = None
    try:
        with db.tx() as conn:
            cur = conn.execute(
                "INSERT INTO batches (contract_id, uploaded_by, filename, arquivo, sha256, tipo_arquivo,"
                " status, total_pages, issue_id, created_at) VALUES (?, ?, ?, '', ?, ?, ?, ?, ?, ?)",
                (contract_id, usuario.id, nome_exibicao, sha, info.tipo, StatusLote.RECEBIDO.value,
                 info.paginas, issue_id, db.agora()))
            batch_id = int(cur.lastrowid)
            destino = config.UPLOAD_DIR / f"lote-{batch_id:06d}{EXTENSAO_POR_TIPO[info.tipo]}"
            destino.write_bytes(data)
            conn.execute("UPDATE batches SET arquivo = ? WHERE id = ?", (str(destino), batch_id))
    except BaseException:
        if destino is not None:
            destino.unlink(missing_ok=True)
        raise
    log.info("lote criado id=%d contrato=%s tipo=%s paginas=%d reenvio=%s",
             batch_id, contract_id, info.tipo, info.paginas, issue_id is not None)
    return batch_id


# ---------------------------------------------------------------------------
# Fila e thread
# ---------------------------------------------------------------------------
_fila: "queue.Queue[int | None]" = queue.Queue()
_na_fila: set[int] = set()
_trava = threading.Lock()
_parar = threading.Event()
_thread: threading.Thread | None = None


def enfileirar(batch_id: int) -> None:
    """Coloca o lote na fila. Com config.SYNC=1 processa na hora (testes e demo)."""
    if config.SYNC:
        processar_lote(batch_id)
        return
    with _trava:
        if batch_id in _na_fila:
            return
        _na_fila.add(batch_id)
    _fila.put(batch_id)


def lotes_para_retomar() -> list[int]:
    with db.tx() as conn:
        linhas = conn.execute(
            "SELECT id FROM batches WHERE status IN (?, ?) ORDER BY id",
            (StatusLote.RECEBIDO.value, StatusLote.PROCESSANDO.value)).fetchall()
    return [int(r[0]) for r in linhas]


def _laco() -> None:
    while not _parar.is_set():
        try:
            batch_id = _fila.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            if batch_id is None:
                break
            with _trava:
                _na_fila.discard(batch_id)
            processar_lote(batch_id)
        except Exception:  # a thread não pode morrer por causa de um lote
            log.exception("falha inesperada no lote id=%s", batch_id)
            if batch_id is not None:
                _marcar_falha(batch_id, "Falha inesperada no processamento; reprocessar o lote.")
        finally:
            _fila.task_done()


def iniciar_worker() -> bool:
    """Sobe a thread do worker (uma por processo) e recoloca na fila os lotes
    RECEBIDO/PROCESSANDO. Chamado pela F1 no lifespan do FastAPI; nunca no import.

    Com config.SYNC=1 não sobe thread (o processamento já ocorre em enfileirar).
    Devolve True se iniciou agora.
    """
    global _thread
    if config.SYNC:
        log.info("DOCRISK_SYNC=1: worker em segundo plano desativado")
        return False
    with _trava:
        if _thread is not None and _thread.is_alive():
            return False
        _parar.clear()
        _thread = threading.Thread(target=_laco, name="docrisk-worker", daemon=True)
        _thread.start()
    retomar = lotes_para_retomar()
    for batch_id in retomar:
        enfileirar(batch_id)
    log.info("worker iniciado; lotes retomados=%d", len(retomar))
    return True


def parar_worker(timeout: float = 10.0) -> None:
    """Encerramento ordenado (F1 pode chamar no fim do lifespan)."""
    global _thread
    _parar.set()
    _fila.put(None)
    if _thread is not None:
        _thread.join(timeout)
    _thread = None
    with _trava:
        _na_fila.clear()


# ---------------------------------------------------------------------------
# Processamento
# ---------------------------------------------------------------------------
def _marcar_falha(batch_id: int, mensagem: str) -> None:
    with db.tx() as conn:
        conn.execute("UPDATE batches SET status = ?, erro = ? WHERE id = ?",
                     (StatusLote.FALHA_PROCESSAMENTO.value, mensagem[:500], batch_id))


def _registrar_paginas(lote: sqlite3.Row) -> None:
    """Renderiza e grava as páginas que ainda não existem (ordem preservada)."""
    batch_id = int(lote["id"])
    with db.tx() as conn:
        existentes = {int(r[0]) for r in conn.execute(
            "SELECT ordem FROM pages WHERE batch_id = ?", (batch_id,))}
    if existentes and len(existentes) >= int(lote["total_pages"]):
        return
    data = Path(lote["arquivo"]).read_bytes()
    pasta = config.PAGES_DIR / f"lote-{batch_id:06d}"
    pasta.mkdir(parents=True, exist_ok=True)
    for pagina in iterar_paginas(data, lote["tipo_arquivo"]):
        if pagina.ordem in existentes:
            continue
        caminho = pasta / f"p{pagina.ordem:04d}.png"
        caminho.write_bytes(pagina.png)
        with db.tx() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO pages (batch_id, ordem, image_path, sha256, texto_camada, status)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (batch_id, pagina.ordem, str(caminho), hashlib.sha256(pagina.png).hexdigest(),
                 pagina.texto_camada, StatusPagina.PENDENTE.value))


def _chave(provedor: ProvedorLeitura, pagina: sqlite3.Row) -> str:
    """Muda se mudar a imagem, o texto digital, o provedor, o modelo ou a versão do prompt."""
    texto = (pagina["texto_camada"] or "").encode("utf-8")
    entrada = f"{pagina['sha256']}:{hashlib.sha256(texto).hexdigest()[:16]}"
    return chave_cache(provedor, entrada, getattr(provedor, "modelo", ""))


def _analisar_pagina(pagina: sqlite3.Row, contract_id: str, provedor: ProvedorLeitura) -> bool:
    chave = _chave(provedor, pagina)
    inicio = time.monotonic()
    do_cache = False
    try:
        with db.tx() as conn:
            linha = conn.execute("SELECT resultado_json FROM ai_cache WHERE chave = ?", (chave,)).fetchone()
        if linha is not None:
            analise = AnalisePagina.model_validate_json(linha[0])
            do_cache = True
        else:
            png = Path(pagina["image_path"]).read_bytes()
            analise = provedor.analisar(png, pagina["texto_camada"] or "")
            if not isinstance(analise, AnalisePagina):
                analise = AnalisePagina.model_validate(analise)
    except Exception as exc:
        ms = int((time.monotonic() - inicio) * 1000)
        if isinstance(exc, ErroIA):
            motivo = str(exc)
        else:
            log.exception("erro inesperado lendo página id=%s", pagina["id"])
            motivo = f"Falha inesperada na leitura ({type(exc).__name__})."
        with db.tx() as conn:
            conn.execute("UPDATE pages SET status = ?, erro = ?, ms = ? WHERE id = ?",
                         (StatusPagina.ERRO.value, motivo[:500], ms, pagina["id"]))
        log.warning("página falhou id=%s ordem=%s provedor=%s erro=%s",
                    pagina["id"], pagina["ordem"], provedor.nome, type(exc).__name__)
        return False

    ms = int((time.monotonic() - inicio) * 1000)
    resultado = analise.model_dump_json()
    with db.tx() as conn:
        if not do_cache:
            conn.execute("INSERT OR REPLACE INTO ai_cache (chave, resultado_json, created_at) VALUES (?, ?, ?)",
                         (chave, resultado, db.agora()))
        conn.execute("UPDATE pages SET status = ?, texto = ?, analise_json = ?, ms = ?, erro = NULL WHERE id = ?",
                     (StatusPagina.OK.value, analise.texto, resultado, ms, pagina["id"]))
        conn.execute("DELETE FROM page_fts WHERE page_id = ?", (pagina["id"],))
        conn.execute("INSERT INTO page_fts (texto, page_id, contract_id) VALUES (?, ?, ?)",
                     (analise.texto, pagina["id"], contract_id))
    log.info("página lida id=%s ordem=%s provedor=%s cache=%s ms=%d tipo=%s",
             pagina["id"], pagina["ordem"], provedor.nome, do_cache, ms, analise.tipo.value)
    return True


def processar_lote(batch_id: int, provedor: ProvedorLeitura | None = None) -> None:
    """Renderiza (se preciso), lê cada página ainda não OK (com cache), indexa em
    page_fts e grava ms. Alguma página com ERRO -> lote FALHA_PROCESSAMENTO (as
    páginas OK ficam; reprocessar lê só as que faltam). Todas OK -> consolidar_lote
    + CONCLUIDO. Lote já CONCLUIDO: nada a fazer (idempotente).
    """
    with db.tx() as conn:
        lote = conn.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)).fetchone()
        if lote is None:
            raise LoteNaoEncontrado(f"Lote {batch_id} não existe.")
        if lote["status"] == StatusLote.CONCLUIDO.value:
            return
        conn.execute("UPDATE batches SET status = ?, erro = NULL WHERE id = ?",
                     (StatusLote.PROCESSANDO.value, batch_id))

    try:
        _registrar_paginas(lote)
    except ArquivoInvalido as exc:
        _marcar_falha(batch_id, str(exc))
        return
    except OSError:
        log.exception("arquivo original indisponível lote=%d", batch_id)
        _marcar_falha(batch_id, "Arquivo original do lote indisponível.")
        return

    try:
        leitor = provedor or get_provider()
    except ErroIA as exc:
        _marcar_falha(batch_id, str(exc))
        return

    with db.tx() as conn:
        paginas = conn.execute(
            "SELECT id, ordem, image_path, sha256, texto_camada, status FROM pages"
            " WHERE batch_id = ? ORDER BY ordem", (batch_id,)).fetchall()
    falhas = sum(
        1 for p in paginas
        if p["status"] != StatusPagina.OK.value and not _analisar_pagina(p, lote["contract_id"], leitor)
    )
    if falhas:
        _marcar_falha(batch_id, f"{falhas} página(s) não puderam ser lidas; reprocessar o lote "
                                "reaproveita as páginas já lidas.")
        return

    try:
        with db.tx() as conn:
            consolidar_lote(conn, batch_id)
            conn.execute("UPDATE batches SET status = ?, erro = NULL, finished_at = ? WHERE id = ?",
                         (StatusLote.CONCLUIDO.value, db.agora(), batch_id))
    except Exception:
        _marcar_falha(batch_id, "Falha ao consolidar os documentos do lote; ver log do servidor.")
        raise
    log.info("lote concluído id=%d paginas=%d", batch_id, len(paginas))


# ---------------------------------------------------------------------------
# Consolidação
# ---------------------------------------------------------------------------
def _pares_do_lote(conn: sqlite3.Connection, batch_id: int) -> set[tuple[str, str]]:
    focos = tuple(t.value for t in TIPOS_FOCO)
    linhas = conn.execute(
        f"SELECT DISTINCT worker_id, competencia FROM documents WHERE batch_id = ? AND tipo IN ({','.join('?' * len(focos))})"
        " AND worker_id IS NOT NULL AND competencia IS NOT NULL", (batch_id, *focos)).fetchall()
    return {(r[0], r[1]) for r in linhas}


def consolidar_lote(conn: sqlite3.Connection, batch_id: int) -> set[tuple[str, str]]:
    """segmentar + rotear + gravar documents/doc_pages, de forma IDEMPOTENTE.

    Roda dentro da transação do chamador (tudo ou nada). Já consolidado -> devolve
    os pares existentes sem gravar nada nem chamar a F3 de novo.

    Para cada documento de foco com trabalhador+competência:
    - versão vigente anterior (de OUTRO lote) do mesmo tipo/trabalhador/competência
      vira SUBSTITUIDO; a nova recebe versao+1 e substitui_id
      (F3: rules.pendencias.atualizar_por_nova_versao);
    - PENDENTE_CORRECAO -> F3: rules.pendencias.criar_pendencia.
    Depois chama F3: rules.conciliacao.conciliar para cada par afetado e devolve esses pares.
    """
    if conn.execute("SELECT 1 FROM documents WHERE batch_id = ? LIMIT 1", (batch_id,)).fetchone():
        return _pares_do_lote(conn, batch_id)

    lote = conn.execute("SELECT id, contract_id FROM batches WHERE id = ?", (batch_id,)).fetchone()
    if lote is None:
        raise LoteNaoEncontrado(f"Lote {batch_id} não existe.")
    contract_id = lote["contract_id"]
    paginas = conn.execute("SELECT id, ordem, status, analise_json FROM pages WHERE batch_id = ? ORDER BY ordem",
                           (batch_id,)).fetchall()
    if not paginas or any(p["status"] != StatusPagina.OK.value for p in paginas):
        raise ConsolidacaoImpossivel(f"Lote {batch_id} tem páginas ainda não lidas.")

    analises = [AnalisePagina.model_validate_json(p["analise_json"]) for p in paginas]
    ordens = [int(p["ordem"]) for p in paginas]
    pagina_id = {int(p["ordem"]): int(p["id"]) for p in paginas}
    trabalhadores = {r[0] for r in conn.execute("SELECT id FROM workers WHERE contract_id = ?", (contract_id,))}

    agora = db.agora()
    pares: set[tuple[str, str]] = set()
    for seg in segmentar(analises, ordens):
        rota = rotear(seg, trabalhadores, config.LIMIAR_CONFIANCA)
        cur = conn.execute(
            "INSERT INTO documents (batch_id, contract_id, tipo, worker_id, competencia, status, confianca,"
            " motivos_pendencia, motivos_revisao, campos_json, versao, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (batch_id, contract_id, seg.tipo.value, seg.trabalhador_id, seg.competencia, rota.status.value,
             seg.confianca, json.dumps(rota.motivos_pendencia, ensure_ascii=False),
             json.dumps(rota.motivos_revisao, ensure_ascii=False), seg.campos.model_dump_json(), agora, agora))
        doc_id = int(cur.lastrowid)
        conn.executemany("INSERT INTO doc_pages (document_id, page_id, posicao) VALUES (?, ?, ?)",
                         [(doc_id, pagina_id[o], pos) for pos, o in enumerate(seg.paginas, start=1)])

        if seg.tipo in TIPOS_FOCO and seg.trabalhador_id and seg.competencia:
            anterior = conn.execute(
                "SELECT id, versao FROM documents WHERE contract_id = ? AND tipo = ? AND worker_id = ?"
                " AND competencia = ? AND status != ? AND batch_id != ? ORDER BY id DESC LIMIT 1",
                (contract_id, seg.tipo.value, seg.trabalhador_id, seg.competencia,
                 StatusDocumento.SUBSTITUIDO.value, batch_id)).fetchone()
            if anterior is not None:
                conn.execute("UPDATE documents SET status = ?, updated_at = ? WHERE id = ?",
                             (StatusDocumento.SUBSTITUIDO.value, agora, anterior["id"]))
                conn.execute("UPDATE documents SET versao = ?, substitui_id = ? WHERE id = ?",
                             (int(anterior["versao"]) + 1, anterior["id"], doc_id))
                f3.atualizar_por_nova_versao(conn, int(anterior["id"]), rota.status)
            pares.add((seg.trabalhador_id, seg.competencia))

        if rota.status is StatusDocumento.PENDENTE_CORRECAO:
            f3.criar_pendencia(
                conn, contract_id=contract_id, document_id=doc_id, worker_id=seg.trabalhador_id,
                competencia=seg.competencia, tipo_documento=seg.tipo.value,
                categoria=(CategoriaPendencia.PAGINA_FALTANTE if seg.paginas_faltantes
                           else CategoriaPendencia.ILEGIVEL),
                motivo="; ".join(rota.motivos_pendencia),
                evidencia=f"Lote {batch_id}, página(s) {', '.join(map(str, seg.paginas))}",
                acao="Reenviar o documento completo e legível.")

    for worker_id, competencia in sorted(pares):
        f3.conciliar(conn, contract_id, worker_id, competencia)
    log.info("lote consolidado id=%d documentos=%d pares=%d", batch_id,
             conn.execute("SELECT COUNT(*) FROM documents WHERE batch_id = ?", (batch_id,)).fetchone()[0],
             len(pares))
    return pares


__all__: list[Any] = [
    "criar_lote", "enfileirar", "iniciar_worker", "parar_worker", "processar_lote",
    "consolidar_lote", "lotes_para_retomar", "LoteNaoEncontrado", "ConsolidacaoImpossivel",
]
