"""Observabilidade operacional (Dev4 / D4-07, F34).

- Correlação: cada requisição recebe um X-Request-ID (aceita o do cliente se for
  seguro, senão gera) que vai para os logs e volta na resposta.
- Logs estruturados (JSON por linha) com DOCRISK_LOG_JSON=1; nunca registram corpo
  de requisição, tokens ou texto de documentos — só metadados operacionais.
- /health/live: o processo responde. /health/ready: pode receber E executar
  trabalho (banco legível, armazenamento gravável, worker vivo quando assíncrono).
  O /health original permanece inalterado (contrato do front e do CI).
- /api/ops/metrics: métricas reais calculadas do banco, só para ADMIN_PLATAFORMA.
  Nada é estimado: métricas que o sistema não registra aparecem como null.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import re
import sqlite3
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from . import config
from .auth import Usuario, exigir_papel, usuario_atual
from .contracts import Papel

request_id: contextvars.ContextVar[str] = contextvars.ContextVar("docrisk_request_id", default="-")
_ID_SEGURO = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_TOKEN = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")
log = logging.getLogger("docrisk.http")
router = APIRouter(tags=["ops"])


# ------------------------------------------------------------------ logs
class _Contexto(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


class FormatoJSON(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = _TOKEN.sub(r"\1[REDACTED]", record.getMessage())
        item: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"), "level": record.levelname,
            "logger": record.name, "msg": msg, "request_id": getattr(record, "request_id", "-"),
            "pid": record.process, "thread": record.threadName,
        }
        for chave in ("method", "path", "status", "ms"):
            if hasattr(record, chave):
                item[chave] = getattr(record, chave)
        if record.exc_info:
            item["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(item, ensure_ascii=False)


def configurar_logs() -> None:
    """Liga logs da aplicação (docrisk.*) em stderr. Idempotente."""
    raiz = logging.getLogger("docrisk")
    if any(getattr(h, "_docrisk", False) for h in raiz.handlers):
        return
    handler = logging.StreamHandler()
    handler._docrisk = True  # type: ignore[attr-defined]
    handler.addFilter(_Contexto())
    if os.getenv("DOCRISK_LOG_JSON", "0").strip() == "1":
        handler.setFormatter(FormatoJSON())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s [req=%(request_id)s] %(message)s"))
    raiz.addHandler(handler)
    raiz.setLevel(os.getenv("DOCRISK_LOG_LEVEL", "INFO").upper())


async def middleware_correlacao(request: Request, call_next):
    recebido = request.headers.get("x-request-id", "")
    rid = recebido if _ID_SEGURO.match(recebido) else uuid.uuid4().hex[:16]
    token = request_id.set(rid)
    inicio = time.monotonic()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        # Só método, rota (sem query) e status: query pode conter termos de busca.
        log.info("http %s %s %s", request.method, request.url.path, status,
                 extra={"method": request.method, "path": request.url.path, "status": status,
                        "ms": int((time.monotonic() - inicio) * 1000)})
        request_id.reset(token)


# ------------------------------------------------------------------ health
@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


def _verificar_banco() -> tuple[bool, str]:
    try:
        conn = sqlite3.connect(f"file:{config.DB_PATH.as_posix()}?mode=ro", uri=True, timeout=2)
        try:
            conn.execute("SELECT 1 FROM batches LIMIT 1").fetchall()
        finally:
            conn.close()
        return True, "ok"
    except sqlite3.Error as exc:
        return False, type(exc).__name__


def _verificar_armazenamento() -> tuple[bool, str]:
    for pasta in (config.UPLOAD_DIR, config.PAGES_DIR):
        if not pasta.is_dir() or not os.access(pasta, os.W_OK):
            return False, f"{pasta.name} indisponível"
    return True, "ok"


def _verificar_worker() -> tuple[bool, str]:
    from .pipeline import worker
    if config.SYNC:
        return True, "sincrono"
    thread = worker._thread
    if thread is None or not thread.is_alive():
        return False, "thread do worker parada"
    return True, "ok"


@router.get("/health/ready")
def ready() -> JSONResponse:
    checks = {}
    for nome, fn in (("banco", _verificar_banco), ("armazenamento", _verificar_armazenamento),
                     ("worker", _verificar_worker)):
        ok, detalhe = fn()
        checks[nome] = {"ok": ok, "detalhe": detalhe}
    pronto = all(c["ok"] for c in checks.values())
    return JSONResponse({"status": "ready" if pronto else "not_ready", "checks": checks},
                        status_code=200 if pronto else 503)


# ------------------------------------------------------------------ métricas
def _percentil(valores: list[int], p: float) -> int | None:
    if not valores:
        return None
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, int(round(p * (len(ordenados) - 1))))]


@router.get("/api/ops/metrics")
def metrics(user: Usuario = Depends(usuario_atual)) -> dict[str, Any]:
    exigir_papel(user, [Papel.ADMIN_PLATAFORMA])
    from .pipeline import worker
    conn = sqlite3.connect(f"file:{config.DB_PATH.as_posix()}?mode=ro", uri=True, timeout=5)
    try:
        lotes = dict(conn.execute("SELECT status, COUNT(*) FROM batches GROUP BY status").fetchall())
        paginas = dict(conn.execute("SELECT status, COUNT(*) FROM pages GROUP BY status").fetchall())
        ms = [r[0] for r in conn.execute("SELECT ms FROM pages WHERE status='OK' AND ms IS NOT NULL")]
        cache = conn.execute("SELECT COUNT(*) FROM ai_cache").fetchone()[0]
        duracoes = [r[0] for r in conn.execute(
            "SELECT CAST((julianday(finished_at)-julianday(created_at))*86400000 AS INTEGER) "
            "FROM batches WHERE status='CONCLUIDO' AND finished_at IS NOT NULL")]
    finally:
        conn.close()
    concluidos, falhas = lotes.get("CONCLUIDO", 0), lotes.get("FALHA_PROCESSAMENTO", 0)
    vivo = _verificar_worker()[0]
    return {
        "lotes": {"por_status": lotes, "backlog": lotes.get("RECEBIDO", 0),
                  "em_processamento": lotes.get("PROCESSANDO", 0), "concluidos": concluidos,
                  "com_falha": falhas,
                  "taxa_falha": round(falhas / (concluidos + falhas), 4) if concluidos + falhas else None,
                  "duracao_ms_p50": _percentil(duracoes, 0.5), "duracao_ms_p95": _percentil(duracoes, 0.95)},
        "paginas": {"por_status": paginas, "leitura_ms_p50": _percentil(ms, 0.5),
                    "leitura_ms_p95": _percentil(ms, 0.95), "leitura_ms_max": max(ms) if ms else None},
        "fila_memoria": worker._fila.qsize(),
        "worker": {"vivo": vivo, "modo": "sincrono" if config.SYNC else "thread"},
        "ia": {"provedor": config.AI_PROVIDER, "entradas_cache": cache,
               # Não registrados pelo sistema hoje: não estimar.
               "chamadas": None, "retries": None, "custo_estimado_usd": None},
    }
