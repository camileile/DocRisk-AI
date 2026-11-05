"""Leitor local com Tesseract (OCR do sprint01). Dono: FRENTE 2. Prioridade baixa.

Opcional: exige o Tesseract instalado com o idioma `por`. Útil como segunda
opinião ou sem internet. Faz OCR com documents._ocr (sprint01) e aplica as
mesmas regras do TextLayerProvider ao texto reconhecido.
"""
from __future__ import annotations

import io
import shutil

from PIL import Image

from ..contracts import AnalisePagina
from . import ErroConfiguracaoIA, ErroIAPermanente
from .textlayer import VERSAO_REGRAS, analisar_texto


class TesseractProvider:
    nome = "tesseract"
    modelo = f"tesseract-{VERSAO_REGRAS}"

    def __init__(self) -> None:
        if shutil.which("tesseract") is None:
            raise ErroConfiguracaoIA("AI_PROVIDER=tesseract, mas o Tesseract não está instalado no PATH.")

    def analisar(self, png: bytes, texto_camada: str | None = None) -> AnalisePagina:
        from ..documents import DocumentError, _ocr

        try:
            with Image.open(io.BytesIO(png)) as img:
                texto = _ocr(img.convert("RGB"))
        except DocumentError as exc:
            raise ErroIAPermanente("Tesseract indisponível ou sem o idioma 'por'.") from exc
        analise = analisar_texto(texto, origem="TESSERACT")
        # OCR local é menos confiável que o texto digital: limita a confiança.
        return analise.model_copy(update={"confianca_tipo": min(analise.confianca_tipo, 0.7)})
