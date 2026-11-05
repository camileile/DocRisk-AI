"""Leitor local com Tesseract (vindo do sprint01). Dono: FRENTE 2.

Opcional: exige Tesseract instalado com o idioma `por`. Útil como segunda
opinião ou sem internet. Classificação por título, então é mais fraco que o Gemini.

Aceite: reaproveitar documents._ocr + documents.classify e devolver AnalisePagina
com origem="TESSERACT" (o rótulo antigo é traduzido por contracts.ROTULOS_SPRINT01).
"""
from __future__ import annotations

from ..contracts import AnalisePagina


class TesseractProvider:
    nome = "tesseract"

    def analisar(self, png: bytes, texto_camada: str | None) -> AnalisePagina:
        raise NotImplementedError("Frente 2: TesseractProvider.analisar")
