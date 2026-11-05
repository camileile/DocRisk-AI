"""Leitores de página (IA e alternativas). Dono: FRENTE 2 (motor documental e IA).

Todo provedor recebe a imagem PNG da página (e o texto digital do PDF, se houver)
e devolve um `contracts.AnalisePagina`. O resto do sistema não sabe qual
provedor está ativo: trocar Gemini por outro modelo = trocar uma classe.
"""
from __future__ import annotations

from typing import Protocol

from ..contracts import AnalisePagina

#: Suba este número sempre que o prompt mudar — invalida o cache antigo.
VERSAO_PROMPT = "p1"


class ProvedorLeitura(Protocol):
    nome: str  # "gemini" | "textlayer" | "tesseract"

    def analisar(self, png: bytes, texto_camada: str | None) -> AnalisePagina:
        """Lê UMA página. Não inventa: campo ausente = None."""
        ...


def chave_cache(provedor: ProvedorLeitura, sha256_png: str, modelo: str = "") -> str:
    """Chave da tabela ai_cache: a mesma página nunca é enviada duas vezes."""
    return f"{provedor.nome}:{modelo}:{VERSAO_PROMPT}:{sha256_png}"


def get_provider() -> ProvedorLeitura:
    """Instância única conforme config.AI_PROVIDER (gemini | textlayer | tesseract).

    Aceite: AI_PROVIDER=gemini sem GEMINI_API_KEY -> erro claro, não silencioso.
    """
    raise NotImplementedError("Frente 2: get_provider")
