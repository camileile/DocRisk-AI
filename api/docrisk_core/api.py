from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import db, observability
from .aej import AEJError
from .documents import DocumentError
from .routes.platform_management import router as platform_router
from .importer import UnsupportedFile, import_bytes
from .pipeline import worker
from .routes import router
from .routes.supplier_management import router as supplier_management_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    observability.configurar_logs()
    db.init_db()
    worker_started = False
    try:
        worker_started = worker.iniciar_worker()
    except NotImplementedError:
        logger.info("Worker F2 ainda não implementado; API iniciada sem processamento assíncrono")
    try:
        yield
    finally:
        if worker_started:
            worker.parar_worker()


app = FastAPI(title="DocRisk AI", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.middleware("http")(observability.middleware_correlacao)
app.include_router(observability.router)
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
