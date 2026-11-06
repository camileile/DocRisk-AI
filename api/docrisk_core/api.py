"""Aplicação FastAPI local para o protótipo DocRisk AI."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .aej import AEJError
from .documents import DocumentError
from .importer import UnsupportedFile, import_bytes
from .pipeline import worker
from .routes import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    try:
        worker.iniciar_worker()
    except NotImplementedError:
        logger.info("Worker F2 ainda não implementado; API iniciada sem processamento assíncrono")
    yield


app = FastAPI(title="DocRisk AI", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router)


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
