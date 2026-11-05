"""Detecção de formato por conteúdo, hash e entrada unificada do núcleo."""
from __future__ import annotations
import hashlib
from typing import Any
from .aej import parse_aej
from .documents import inspect_document

class UnsupportedFile(ValueError):
    pass

def detect_type(filename: str, data: bytes) -> str:
    name = filename.lower()
    if data.startswith(b"%PDF-"):
        return "PDF"
    if data.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")):
        return "IMAGE"
    if name.endswith((".aej", ".txt")) and data.lstrip().startswith(b"01|"):
        return "AEJ"
    raise UnsupportedFile("Arquivo inválido ou formato não reconhecido (PDF, PNG, JPEG, AEJ)")

def import_bytes(filename: str, data: bytes) -> dict[str, Any]:
    if not data or len(data) > 10 * 1024 * 1024:
        raise UnsupportedFile("Tamanho deve ser entre 1 byte e 10 MB na prova de conceito")
    kind = detect_type(filename, data)
    result = parse_aej(data) if kind == "AEJ" else inspect_document(data, kind)
    # Não persiste documentos, nomes, CPF nem OCR nesta versão.
    return {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data), **result}
