"""Leitor offline: regras sobre o TEXTO DIGITAL do PDF. Dono: FRENTE 2.

Serve para testes automáticos (determinístico, sem internet) e plano B da demo.
Não é OCR e não deve ser apresentado como IA. Pode reaproveitar os padrões de
título de documents.py (sprint01).

Aceite:
- tipo pelo título nos primeiros ~300 caracteres (evita falsos positivos no corpo)
- "Página X de Y" procurado no texto INTEIRO (numeração costuma estar no rodapé)
- matrícula, competência e horas extras por expressão regular
- página de foco sem os marcadores do corpo (ex.: "Proventos", "Entrada") -> legivel=False
- origem = "TEXTO_PDF"
"""
from __future__ import annotations

from ..contracts import AnalisePagina


class TextLayerProvider:
    nome = "textlayer"

    def analisar(self, png: bytes, texto_camada: str | None) -> AnalisePagina:
        raise NotImplementedError("Frente 2: TextLayerProvider.analisar")
