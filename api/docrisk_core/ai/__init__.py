"""Leitores de página (IA e alternativas). Dono: FRENTE 2 (motor documental e IA).

Todo provedor recebe a imagem PNG da página (e o texto digital do PDF, se houver)
e devolve um `contracts.AnalisePagina`. O resto do sistema não sabe qual
provedor está ativo: trocar Gemini por outro modelo = trocar uma classe.
"""
from __future__ import annotations

import threading
from typing import Protocol

from .. import config
from ..contracts import AnalisePagina

#: Suba este número sempre que o prompt ou a instrução de sistema mudar — invalida o cache antigo.
VERSAO_PROMPT = "p1"


class ErroIA(Exception):
    """Base dos erros de leitura. A mensagem nunca traz conteúdo do documento nem a chave."""


class ErroConfiguracaoIA(ErroIA):
    """Configuração impossível (ex.: AI_PROVIDER=gemini sem GEMINI_API_KEY)."""


class ErroIATransitorio(ErroIA):
    """Indisponibilidade temporária (429, 5xx, rede) que persistiu após as tentativas."""


class ErroIAPermanente(ErroIA):
    """Falha que não melhora repetindo (chave inválida, requisição recusada...)."""


class RespostaIAInvalida(ErroIAPermanente):
    """O modelo respondeu, mas fora do contrato (JSON inválido, campos obrigatórios ausentes)."""


class ProvedorLeitura(Protocol):
    nome: str  # "gemini" | "textlayer" | "tesseract"
    modelo: str  # identifica a versão do leitor na chave de cache

    def analisar(self, png: bytes, texto_camada: str | None) -> AnalisePagina:
        """Lê UMA página. Não inventa: campo ausente = None."""
        ...


def chave_cache(provedor: ProvedorLeitura, sha256_png: str, modelo: str = "") -> str:
    """Chave da tabela ai_cache: a mesma página nunca é enviada duas vezes."""
    return f"{provedor.nome}:{modelo}:{VERSAO_PROMPT}:{sha256_png}"


_PROVEDORES: dict[str, ProvedorLeitura] = {}
_TRAVA = threading.Lock()


def _criar(nome: str) -> ProvedorLeitura:
    if nome == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider()
    if nome == "textlayer":
        from .textlayer import TextLayerProvider
        return TextLayerProvider()
    if nome == "tesseract":
        from .tesseract import TesseractProvider
        return TesseractProvider()
    raise ErroConfiguracaoIA(f"AI_PROVIDER desconhecido: {nome!r}. Use gemini, textlayer ou tesseract.")


def get_provider(nome: str | None = None) -> ProvedorLeitura:
    """Instância única por provedor, conforme config.AI_PROVIDER (gemini | textlayer | tesseract).

    Nunca troca de provedor sozinho: AI_PROVIDER=gemini sem chave -> ErroConfiguracaoIA.
    """
    escolhido = (nome or config.AI_PROVIDER or "").strip().lower()
    with _TRAVA:
        if escolhido not in _PROVEDORES:
            _PROVEDORES[escolhido] = _criar(escolhido)
        return _PROVEDORES[escolhido]


def redefinir_provider() -> None:
    """Esquece as instâncias criadas (usado em testes e ao trocar a configuração)."""
    with _TRAVA:
        _PROVEDORES.clear()
