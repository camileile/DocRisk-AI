from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import db, runtime
from .aej import AEJError
from .documents import DocumentError
from .routes.platform_management import router as platform_router
from .importer import UnsupportedFile, import_bytes
from .pipeline import worker
from .routes import router
from .routes.supplier_management import router as supplier_management_router

logger = logging.getLogger(__name__)


def _configured_cors_origins() -> list[str]:
    # Padrão local: o `npm run dev` sobe em 127.0.0.1:3000 (ver README); localhost:3000 também.
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins or "*" in origins:
        raise RuntimeError("CORS_ORIGINS deve conter uma allowlist explícita, sem wildcard.")
    for origin in origins:
        parsed = urlsplit(origin)
        if (parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path or
                parsed.query or parsed.fragment or parsed.username or parsed.password):
            raise RuntimeError(f"Origem inválida em CORS_ORIGINS: {origin}")
    return origins


@asynccontextmanager
async def lifespan(_: FastAPI):
    # D4-04: configuração validada e instância única por DATA_DIR antes do banco.
    runtime.preparar_inicio()
    worker_started = False
    try:
        db.init_db()
        try:
            worker_started = worker.iniciar_worker()
        except NotImplementedError:
            logger.info("Worker F2 ainda não implementado; API iniciada sem processamento assíncrono")
        yield
    finally:
        if worker_started:
            worker.parar_worker()
        runtime.liberar_instancia()
        logger.info("docrisk encerrado")


app = FastAPI(title="DocRisk AI", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_configured_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router)
app.include_router(supplier_management_router)


@app.get("/health")
def health() -> dict[str, bool | str]:
    return {"status": "ok", "production_ready": False}


@app.post("/api/v1/inspect")
async def inspect(file: UploadFile = File(...)) -> dict:
    if os.getenv("DOCRISK_DEMO_MODE") != "1":
        raise HTTPException(503, "Endpoint bloqueado: somente modo DEMO local")
    data = await file.read(10 * 1024 * 1024 + 1)
    try:
        return import_bytes(file.filename or "arquivo", data)
    except (UnsupportedFile, DocumentError, AEJError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


app.include_router(platform_router)
