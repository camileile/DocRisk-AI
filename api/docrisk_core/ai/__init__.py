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

#: Suba estas versões quando o prompt/schema mudar — invalida o cache antigo.
VERSAO_PROMPT = "p1"
VERSAO_SCHEMA = "s1"


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
    """Chave da tabela ai_cache: separa modelo, prompt, schema e conteúdo."""
    return f"{provedor.nome}:{modelo}:{VERSAO_PROMPT}:{VERSAO_SCHEMA}:{sha256_png}"


def chave_cache_legada(provedor: ProvedorLeitura, sha256_png: str, modelo: str = "") -> str | None:
    """Só p1/s1 é compatível com o contrato anterior à versão explícita do schema.

    O resultado ainda precisa ser validado como AnalisePagina antes da promoção.
    Novos prompts ou schemas não podem reutilizar silenciosamente o cache antigo.
    """
    if (VERSAO_PROMPT, VERSAO_SCHEMA) != ("p1", "s1"):
        return None
    return f"{provedor.nome}:{modelo}:p1:{sha256_png}"


def metadados_basicos(provedor: ProvedorLeitura) -> dict[str, object]:
    gemini = provedor.nome == "gemini"
    return {
        "provider": provedor.nome,
        "model": getattr(provedor, "modelo", ""),
        "prompt_version": VERSAO_PROMPT,
        "schema_version": VERSAO_SCHEMA,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "input_price_usd_per_million": config.GEMINI_INPUT_USD_PER_MILLION if gemini else None,
        "output_price_usd_per_million": config.GEMINI_OUTPUT_USD_PER_MILLION if gemini else None,
        "estimated_cost_usd": None if gemini else 0.0,
        "timeout_ms": config.GEMINI_TIMEOUT_MS if gemini else None,
        "max_output_tokens": config.GEMINI_MAX_OUTPUT_TOKENS if gemini else None,
        "cache_hit": False,
    }


def analisar_com_proveniencia(
    provedor: ProvedorLeitura, png: bytes, texto_camada: str | None,
) -> tuple[AnalisePagina, dict[str, object]]:
    detalhado = getattr(provedor, "analisar_com_proveniencia", None)
    if callable(detalhado):
        analise, metadados = detalhado(png, texto_camada)
        return analise, {**metadados_basicos(provedor), **metadados}
    return provedor.analisar(png, texto_camada), metadados_basicos(provedor)


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
