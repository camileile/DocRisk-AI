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

from pydantic import ValidationError

from .. import config, db
from ..aej import parse_aej_detalhado
from ..ai import (
    ErroIA, ProvedorLeitura, analisar_com_proveniencia, chave_cache, chave_cache_legada, get_provider,
    metadados_basicos,
)
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


def _meses(inicio: str, fim: str) -> list[str]:
    from datetime import date
    a, b = date.fromisoformat(inicio), date.fromisoformat(fim)
    resultado = []
    ano, mes = a.year, a.month
    while (ano, mes) <= (b.year, b.month):
        resultado.append(f"{mes:02d}/{ano:04d}")
        mes += 1
        if mes == 13:
            mes, ano = 1, ano + 1
    return resultado


def _processar_lote_aej(batch_id: int) -> None:
    """Persiste AEJ original + registros e cria espelhos derivados sem leitor de IA."""
    with db.tx() as conn:
        lote = conn.execute("SELECT * FROM batches WHERE id=?", (batch_id,)).fetchone()
        if lote is None:
            raise LoteNaoEncontrado(f"Lote {batch_id} não existe.")
        if conn.execute("SELECT 1 FROM documents WHERE batch_id=? LIMIT 1", (batch_id,)).fetchone():
            conn.execute("UPDATE batches SET status=?, erro=NULL, finished_at=? WHERE id=?",
                         (StatusLote.CONCLUIDO.value, db.agora(), batch_id))
            return
    arquivo = Path(lote["arquivo"])
    conteudo = arquivo.read_bytes()
    if hashlib.sha256(conteudo).hexdigest() != lote["sha256"]:
        raise ArquivoInvalido("O arquivo AEJ original não corresponde ao hash registrado no recebimento.")
    detalhe = parse_aej_detalhado(conteudo)
    resumo = detalhe["summary"]
    agora = db.agora()
    periodos = _meses(resumo["period_start"], resumo["period_end"])
    pares: set[tuple[str, str]] = set()

    with db.tx() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO aej_imports (batch_id, schema_version, period_start, period_end, "
            "validation_json, p7s_present, parser_version, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (batch_id, resumo["schema_version"], resumo["period_start"], resumo["period_end"],
             json.dumps({k: v for k, v in resumo.items() if k not in {"workers"}}, ensure_ascii=False),
             int(any(r["record_type"] == "P7S_MARKER" for r in detalhe["records"])), "aej-parser-v2", agora),
        )
        conn.executemany(
            "INSERT OR IGNORE INTO aej_records (batch_id, line_number, record_type, worker_link_id, raw_line) "
            "VALUES (?, ?, ?, ?, ?)",
            [(batch_id, r["line_number"], r["record_type"], r["worker_link_id"], r["raw_line"])
             for r in detalhe["records"]],
        )
        for link_id, calculation in detalhe["calculations"].items():
            mapping = conn.execute(
                "SELECT worker_id FROM aej_worker_mappings WHERE contract_id=? AND worker_link_id=?",
                (lote["contract_id"], link_id),
            ).fetchone()
            worker_id = str(mapping[0]) if mapping else None
            for competencia in periodos:
                mm, yyyy = competencia.split("/")
                dias = [d for d in calculation["days"] if d["date"].startswith(f"{yyyy}-{mm}-")]
                warnings = list(calculation["warnings"])
                if not worker_id:
                    warnings.append("Vínculo AEJ sem mapeamento explícito para trabalhador do contrato.")
                if not dias:
                    warnings.append("Nenhuma marcação encontrada para esta competência.")
                horas = None
                if worker_id and dias and calculation["calculation_status"] == "CALCULATED":
                    mins = sum(int(d["observed_daily_excess_minutes"] or 0) for d in dias)
                    horas = round(mins / 60, 2)
                status = (StatusDocumento.APTO if horas is not None else StatusDocumento.REVISAO_HUMANA)
                confianca = 1.0 if horas is not None else 0.0
                compensacoes = [item for item in calculation.get("compensations", [])
                                if str(item.get("date", "")).startswith(f"{yyyy}-{mm}-")]
                calculo_doc = {
                    "origem": "AEJ", "worker_link_id": link_id, "worker_id": worker_id,
                    "competencia": competencia, "calculation_status": calculation["calculation_status"],
                    "hours": horas, "method": calculation["method"], "warnings": list(dict.fromkeys(warnings)),
                    "validation_warnings": calculation["validation_warnings"],
                    "days": dias, "compensations": compensacoes,
                    "worker_record_line": calculation["worker_record_line"],
                    "p7s_validated": False,
                }
                cur = conn.execute(
                    "INSERT INTO documents (batch_id, contract_id, tipo, worker_id, competencia, status, "
                    "confianca, motivos_revisao, campos_json, versao, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
                    (batch_id, lote["contract_id"], "ESPELHO_PONTO", worker_id, competencia, status.value,
                     confianca, json.dumps(calculo_doc["warnings"], ensure_ascii=False),
                     json.dumps({"horas_extras_h": horas}, ensure_ascii=False), agora, agora),
                )
                document_id = int(cur.lastrowid)
                conn.execute(
                    "INSERT INTO aej_documents (document_id, batch_id, worker_link_id, competencia, "
                    "calculation_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (document_id, batch_id, link_id, competencia,
                     json.dumps(calculo_doc, ensure_ascii=False), agora),
                )
                if worker_id:
                    anterior = conn.execute(
                        "SELECT id, versao FROM documents WHERE contract_id=? AND tipo='ESPELHO_PONTO' "
                        "AND worker_id=? AND competencia=? AND status<>? AND batch_id<>? ORDER BY id DESC LIMIT 1",
                        (lote["contract_id"], worker_id, competencia, StatusDocumento.SUBSTITUIDO.value,
                         batch_id),
                    ).fetchone()
                    if anterior:
                        conn.execute("UPDATE documents SET status=?,updated_at=? WHERE id=?",
                                     (StatusDocumento.SUBSTITUIDO.value, agora, anterior["id"]))
                        conn.execute("UPDATE documents SET versao=?,substitui_id=? WHERE id=?",
                                     (int(anterior["versao"]) + 1, anterior["id"], document_id))
                        f3.atualizar_por_nova_versao(conn, int(anterior["id"]), status)
                    pares.add((worker_id, competencia))
        for worker_id, competencia in sorted(pares):
            f3.conciliar(conn, lote["contract_id"], worker_id, competencia)
        conn.execute("UPDATE batches SET status=?, erro=NULL, finished_at=? WHERE id=?",
                     (StatusLote.CONCLUIDO.value, db.agora(), batch_id))
    log.info("lote AEJ concluído id=%d vínculos=%d documentos=%d p7s_validado=false",
             batch_id, resumo["workers_count"], len(periodos) * resumo["workers_count"])


def _entrada_cache(pagina: sqlite3.Row) -> str:
    """Identifica a imagem e o texto digital, igualmente nas duas versões da chave."""
    texto = (pagina["texto_camada"] or "").encode("utf-8")
    entrada = f"{pagina['sha256']}:{hashlib.sha256(texto).hexdigest()[:16]}"
    return entrada


def _chave(provedor: ProvedorLeitura, pagina: sqlite3.Row) -> str:
    return chave_cache(provedor, _entrada_cache(pagina), getattr(provedor, "modelo", ""))


def _analisar_pagina(pagina: sqlite3.Row, contract_id: str, provedor: ProvedorLeitura) -> bool:
    chave = _chave(provedor, pagina)
    inicio = time.monotonic()
    do_cache = False
    cache_legado = False
    metadados = metadados_basicos(provedor)
    try:
        with db.tx() as conn:
            linha = conn.execute("SELECT resultado_json FROM ai_cache WHERE chave = ?", (chave,)).fetchone()
        if linha is not None:
            analise = AnalisePagina.model_validate_json(linha[0])
            do_cache = True
        else:
            antiga = chave_cache_legada(provedor, _entrada_cache(pagina), getattr(provedor, "modelo", ""))
            if antiga is not None:
                with db.tx() as conn:
                    legada = conn.execute("SELECT resultado_json FROM ai_cache WHERE chave = ?", (antiga,)).fetchone()
                if legada is not None:
                    try:
                        analise = AnalisePagina.model_validate_json(legada[0])
                    except ValidationError:
                        log.warning("cache legado inválido ignorado página id=%s", pagina["id"])
                    else:
                        do_cache = cache_legado = True
        if do_cache:
            metadados.update({
                "input_tokens": 0 if provedor.nome == "gemini" else None,
                "output_tokens": 0 if provedor.nome == "gemini" else None,
                "total_tokens": 0 if provedor.nome == "gemini" else None,
                "estimated_cost_usd": 0.0,
                "cache_hit": True,
            })
        else:
            png = Path(pagina["image_path"]).read_bytes()
            analise, metadados = analisar_com_proveniencia(provedor, png, pagina["texto_camada"] or "")
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
            _registrar_telemetria(conn, int(pagina["id"]), metadados, "ERRO", ms, type(exc).__name__)
        log.warning("página falhou id=%s ordem=%s provedor=%s erro=%s",
                    pagina["id"], pagina["ordem"], provedor.nome, type(exc).__name__)
        return False

    ms = int((time.monotonic() - inicio) * 1000)
    resultado = analise.model_dump_json()
    with db.tx() as conn:
        if not do_cache or cache_legado:
            conn.execute("INSERT OR REPLACE INTO ai_cache (chave, resultado_json, created_at) VALUES (?, ?, ?)",
                         (chave, resultado, db.agora()))
        conn.execute("UPDATE pages SET status = ?, texto = ?, analise_json = ?, ms = ?, erro = NULL WHERE id = ?",
                     (StatusPagina.OK.value, analise.texto, resultado, ms, pagina["id"]))
        _registrar_telemetria(conn, int(pagina["id"]), metadados, "OK", ms, None)
        conn.execute("DELETE FROM page_fts WHERE page_id = ?", (pagina["id"],))
        conn.execute("INSERT INTO page_fts (texto, page_id, contract_id) VALUES (?, ?, ?)",
                     (analise.texto, pagina["id"], contract_id))
    log.info("página lida id=%s ordem=%s provedor=%s cache=%s ms=%d tipo=%s",
             pagina["id"], pagina["ordem"], provedor.nome, do_cache, ms, analise.tipo.value)
    return True


def _registrar_telemetria(conn: sqlite3.Connection, page_id: int, metadados: dict[str, object],
                          status: str, duration_ms: int, error_type: str | None) -> None:
    campos = (
        "provider", "model", "prompt_version", "schema_version", "input_tokens", "output_tokens",
        "total_tokens", "input_price_usd_per_million", "output_price_usd_per_million",
        "estimated_cost_usd", "timeout_ms", "max_output_tokens",
    )
    valores = [metadados.get(campo) for campo in campos]
    conn.execute(
        "INSERT OR REPLACE INTO ai_telemetry (page_id, provider, model, prompt_version, schema_version, "
        "input_tokens, output_tokens, total_tokens, input_price_usd_per_million, "
        "output_price_usd_per_million, estimated_cost_usd, timeout_ms, max_output_tokens, cache_hit, "
        "status, duration_ms, error_type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (page_id, *valores, int(bool(metadados.get("cache_hit"))), status, duration_ms, error_type, db.agora()),
    )


def processar_lote(batch_id: int, provedor: ProvedorLeitura | None = None) -> None:
    """Renderiza (se preciso), lê cada página ainda não OK (com cache), indexa em
    page_fts e grava ms. Alguma página com ERRO -> lote FALHA_PROCESSAMENTO (as
    páginas OK ficam; reprocessar lê só as que faltam). Todas OK -> consolidar_lote
    + CONCLUIDO. Lote já CONCLUIDO: nada a fazer (idempotente).
    """
    with db.tx() as conn:
        # Reservar escrita antes de ler evita reabrir um lote concluído por outro chamador.
        conn.execute("BEGIN IMMEDIATE")
        lote = conn.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)).fetchone()
        if lote is None:
            raise LoteNaoEncontrado(f"Lote {batch_id} não existe.")
        if lote["status"] == StatusLote.CONCLUIDO.value:
            return
        conn.execute("UPDATE batches SET status = ?, erro = NULL WHERE id = ?",
                     (StatusLote.PROCESSANDO.value, batch_id))

    if lote["tipo_arquivo"] == "AEJ":
        try:
            _processar_lote_aej(batch_id)
        except Exception:
            _marcar_falha(batch_id, "Falha ao validar ou consolidar o AEJ; o arquivo original foi preservado.")
            raise
        return

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
    - duplicata sem vínculo a uma pendência reenviada vai para revisão; documento anterior preservado;
    - reenvio ligado à pendência aberta do documento vigente cria nova versão
      (F3: rules.pendencias.atualizar_por_nova_versao);
    - PENDENTE_CORRECAO -> F3: rules.pendencias.criar_pendencia.
    Depois chama F3: rules.conciliacao.conciliar para cada par afetado e devolve esses pares.
    """
    # A leitura de idempotência e os INSERTs precisam da mesma reserva de escrita.
    # SELECT sozinho não abre transação no modo padrão do sqlite3.
    if not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")
    if conn.execute("SELECT 1 FROM documents WHERE batch_id = ? LIMIT 1", (batch_id,)).fetchone():
        return _pares_do_lote(conn, batch_id)

    lote = conn.execute("SELECT id, contract_id, issue_id FROM batches WHERE id = ?", (batch_id,)).fetchone()
    if lote is None:
        raise LoteNaoEncontrado(f"Lote {batch_id} não existe.")
    contract_id = lote["contract_id"]
    paginas = conn.execute(
        "SELECT id, ordem, status, analise_json, sha256 FROM pages WHERE batch_id = ? ORDER BY ordem",
        (batch_id,)).fetchall()
    if not paginas or any(p["status"] != StatusPagina.OK.value for p in paginas):
        raise ConsolidacaoImpossivel(f"Lote {batch_id} tem páginas ainda não lidas.")

    analises = [AnalisePagina.model_validate_json(p["analise_json"]) for p in paginas]
    ordens = [int(p["ordem"]) for p in paginas]
    pagina_id = {int(p["ordem"]): int(p["id"]) for p in paginas}
    pagina_hash = {int(p["ordem"]): p["sha256"] for p in paginas}
    trabalhadores = {r[0] for r in conn.execute("SELECT id FROM workers WHERE contract_id = ?", (contract_id,))}

    agora = db.agora()
    pares: set[tuple[str, str]] = set()
    for seg in segmentar(analises, ordens):
        rota = rotear(seg, trabalhadores, config.LIMIAR_CONFIANCA)
        anterior = None
        reenvio_autorizado = False
        if seg.tipo in TIPOS_FOCO and seg.trabalhador_id and seg.competencia:
            vigentes = conn.execute(
                "SELECT id, versao FROM documents WHERE contract_id = ? AND tipo = ? AND worker_id = ?"
                " AND competencia = ? AND status != ? AND batch_id != ? ORDER BY id DESC",
                (contract_id, seg.tipo.value, seg.trabalhador_id, seg.competencia,
                 StatusDocumento.SUBSTITUIDO.value, batch_id)).fetchall()
            if len(vigentes) == 1:
                anterior = vigentes[0]
                if lote["issue_id"] is not None:
                    issue = conn.execute(
                        "SELECT id FROM issues WHERE id = ? AND contract_id = ? AND document_id = ?"
                        " AND worker_id = ? AND competencia = ? AND tipo_documento = ? AND status = 'REENVIADA'",
                        (lote["issue_id"], contract_id, anterior["id"], seg.trabalhador_id,
                         seg.competencia, seg.tipo.value)).fetchone()
                    reenvio_autorizado = issue is not None
                if not reenvio_autorizado:
                    # Mesmo conteúdo (mesmas imagens de página, na mesma ordem) = o mesmo documento
                    # enviado de novo, não ambiguidade: vira nova versão, como antes.
                    hashes_anterior = [r[0] for r in conn.execute(
                        "SELECT p.sha256 FROM doc_pages dp JOIN pages p ON p.id = dp.page_id"
                        " WHERE dp.document_id = ? ORDER BY dp.posicao", (anterior["id"],))]
                    reenvio_autorizado = hashes_anterior == [pagina_hash[o] for o in seg.paginas]
            if vigentes and not reenvio_autorizado:
                detalhes = (f"{len(vigentes)} documentos vigentes" if len(vigentes) != 1
                            else f"documento vigente #{vigentes[0]['id']}")
                rota.motivos_revisao.append(
                    f"Possível duplicidade para {seg.tipo.value}, trabalhador {seg.trabalhador_id}, "
                    f"competência {seg.competencia}: {detalhes}; revisar antes de substituir."
                )
                rota.motivos_revisao = list(dict.fromkeys(rota.motivos_revisao))
                rota.status = StatusDocumento.REVISAO_HUMANA
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
            if anterior is not None and reenvio_autorizado:
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
