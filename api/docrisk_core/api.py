"""API local de prova de conceito. Não habilitar em servidor público."""
from __future__ import annotations
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from .importer import import_bytes, UnsupportedFile
from .aej import AEJError
from .documents import DocumentError

app = FastAPI(title="DocRisk AI | Ingestão POC", version="0.1.0")

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "production_ready": False}

@app.post("/api/v1/inspect")
async def inspect(file: UploadFile = File(...)) -> dict:
    if os.getenv("DOCRISK_DEMO_MODE") != "1":
        raise HTTPException(503, "Endpoint bloqueado: somente modo DEMO local")
    # Limita RAM/carga; versão definitiva usará streaming, auth e jobs persistentes.
    data = await file.read(10 * 1024 * 1024 + 1)
    try:
        return import_bytes(file.filename or "arquivo", data)
    except (UnsupportedFile, DocumentError, AEJError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
