"""Contratos compartilhados entre as três frentes do back-end.

Este arquivo é o ponto de encontro da equipe: tipos documentais, estados e o
JSON que o leitor de páginas (IA, camada de texto ou Tesseract) devolve.
Mudou algo aqui? Avise as outras duas frentes antes do commit.

Dono: as três frentes juntas (mudanças combinadas).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Vocabulário
# ---------------------------------------------------------------------------
class TipoDocumento(StrEnum):
    ESPELHO_PONTO = "ESPELHO_PONTO"
    HOLERITE = "HOLERITE"
    COMPROVANTE_PAGAMENTO = "COMPROVANTE_PAGAMENTO"
    CONTRATO = "CONTRATO"
    DOCUMENTO_IDENTIFICACAO = "DOCUMENTO_IDENTIFICACAO"
    NOTA_FISCAL = "NOTA_FISCAL"
    OUTRO = "OUTRO"
    DESCONHECIDO = "DESCONHECIDO"


#: Tipos que recebem extração de campos, prazos e análise especializada (spec 3.1).
TIPOS_FOCO: frozenset[TipoDocumento] = frozenset(
    {TipoDocumento.ESPELHO_PONTO, TipoDocumento.HOLERITE, TipoDocumento.COMPROVANTE_PAGAMENTO}
)

#: Tradução dos rótulos usados no sprint01 (documents.py) para o vocabulário oficial.
ROTULOS_SPRINT01: dict[str, TipoDocumento] = {
    "ESPELHO_PONTO": TipoDocumento.ESPELHO_PONTO,
    "FOLHA_PAGAMENTO": TipoDocumento.HOLERITE,
    "COMPROVANTE": TipoDocumento.COMPROVANTE_PAGAMENTO,
    "CONTRATO": TipoDocumento.CONTRATO,
    "IDENTIFICACAO": TipoDocumento.DOCUMENTO_IDENTIFICACAO,
    "NAO_IDENTIFICADO": TipoDocumento.DESCONHECIDO,
}


class Papel(StrEnum):
    ADMIN_BH = "ADMIN_BH"
    ANALISTA_BH = "ANALISTA_BH"
    GESTOR_FORN = "GESTOR_FORN"
    OPERADOR_FORN = "OPERADOR_FORN"
    GESTOR_CONTR = "GESTOR_CONTR"


PAPEIS_BERNHOEFT = frozenset({Papel.ADMIN_BH, Papel.ANALISTA_BH})
PAPEIS_FORNECEDORA = frozenset({Papel.GESTOR_FORN, Papel.OPERADOR_FORN})
PAPEIS_CONTRATANTE = frozenset({Papel.GESTOR_CONTR})


class StatusLote(StrEnum):
    RECEBIDO = "RECEBIDO"
    PROCESSANDO = "PROCESSANDO"
    CONCLUIDO = "CONCLUIDO"
    FALHA_PROCESSAMENTO = "FALHA_PROCESSAMENTO"  # falha técnica: retomar, nunca culpa da fornecedora


class StatusPagina(StrEnum):
    PENDENTE = "PENDENTE"
    OK = "OK"
    ERRO = "ERRO"


class StatusDocumento(StrEnum):
    APTO = "APTO"
    PENDENTE_CORRECAO = "PENDENTE_CORRECAO"
    REVISAO_HUMANA = "REVISAO_HUMANA"
    SUBSTITUIDO = "SUBSTITUIDO"


class StatusConciliacao(StrEnum):
    AGUARDANDO_DOCUMENTOS = "AGUARDANDO_DOCUMENTOS"
    BLOQUEADA_PENDENCIA = "BLOQUEADA_PENDENCIA"
    REVISAO_HUMANA = "REVISAO_HUMANA"
    ANALISADA = "ANALISADA"


class ResultadoConciliacao(StrEnum):
    NAO_AVALIADO = "NAO_AVALIADO"
    DADOS_INSUFICIENTES = "DADOS_INSUFICIENTES"
    DIVERGENCIA_A_VERIFICAR = "DIVERGENCIA_A_VERIFICAR"
    SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS = "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS"


class StatusPendencia(StrEnum):
    ABERTA = "ABERTA"
    NOTIFICADA = "NOTIFICADA"
    REENVIADA = "REENVIADA"
    RESOLVIDA = "RESOLVIDA"
    REABERTA = "REABERTA"


class CategoriaPendencia(StrEnum):
    ILEGIVEL = "ILEGIVEL"
    PAGINA_FALTANTE = "PAGINA_FALTANTE"
    DOCUMENTO_AUSENTE = "DOCUMENTO_AUSENTE"
    ARQUIVO_INVALIDO = "ARQUIVO_INVALIDO"
    SOLICITADA_NA_REVISAO = "SOLICITADA_NA_REVISAO"


class StatusParecer(StrEnum):
    RASCUNHO = "RASCUNHO"
    EM_REVISAO = "EM_REVISAO"
    APROVADO_PUBLICADO = "APROVADO_PUBLICADO"
    SUBSTITUIDO_POR_VERSAO = "SUBSTITUIDO_POR_VERSAO"


#: Versão da regra de conciliação gravada em cada análise (spec 5.2, item 5).
REGRA_CONCILIACAO = "HE-CMP-v1"

OrigemLeitura = Literal["GEMINI", "TEXTO_PDF", "TESSERACT", "AEJ"]


# ---------------------------------------------------------------------------
# JSON de saída por página — o que TODO provedor de leitura devolve
# ---------------------------------------------------------------------------
_COMPETENCIA = re.compile(r"(\d{1,2})\s*/\s*(\d{4})")


def numero_br(valor: Any) -> float | None:
    """Converte '1.234,56', 'R$ 160,00', 12 ou '8,00 h' em float. None se não der."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = re.sub(r"[^\d,.\-]", "", str(valor))
    if not texto:
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


class CamposPagina(BaseModel):
    """Campos extraídos. Horas e reais NUNCA se convertem um no outro."""

    horas_extras_h: float | None = None
    horas_extras_valor: float | None = None  # R$
    valor_liquido: float | None = None  # R$
    valor_pago: float | None = None  # R$ (comprovante)
    data_pagamento: str | None = None  # DD/MM/AAAA

    @field_validator("horas_extras_h", "horas_extras_valor", "valor_liquido", "valor_pago", mode="before")
    @classmethod
    def _numero(cls, v: Any) -> float | None:
        n = numero_br(v)
        return n if n is None or n >= 0 else None


class AnalisePagina(BaseModel):
    """Leitura de UMA página. Gravado em pages.analise_json.

    `confianca_tipo` é sinal para a fila de revisão, não probabilidade calibrada.
    """

    texto: str = ""
    tipo: TipoDocumento = TipoDocumento.DESCONHECIDO
    inicio_documento: bool = False
    pagina_x: int | None = Field(default=None, description="'Página X de Y' impresso no documento")
    pagina_de: int | None = None
    trabalhador_id: str | None = Field(default=None, description="Matrícula/ID sintético, ex.: T001")
    trabalhador_nome: str | None = None
    competencia: str | None = Field(default=None, description="MM/AAAA")
    legivel: bool = True
    qualidade: float = Field(default=0.5, ge=0, le=1)
    confianca_tipo: float = Field(default=0.5, ge=0, le=1)
    campos: CamposPagina = Field(default_factory=CamposPagina)
    origem: OrigemLeitura = "GEMINI"

    @field_validator("tipo", mode="before")
    @classmethod
    def _tipo(cls, v: Any) -> TipoDocumento:
        rotulo = str(v or "").strip().upper()
        if rotulo in ROTULOS_SPRINT01:
            return ROTULOS_SPRINT01[rotulo]
        try:
            return TipoDocumento(rotulo)
        except ValueError:
            return TipoDocumento.DESCONHECIDO

    @field_validator("pagina_x", "pagina_de", mode="before")
    @classmethod
    def _inteiro_positivo(cls, v: Any) -> int | None:
        try:
            n = int(v)
        except (TypeError, ValueError):
            return None
        return n if n > 0 else None

    @field_validator("trabalhador_id", mode="before")
    @classmethod
    def _trabalhador(cls, v: Any) -> str | None:
        if v is None:
            return None
        s = re.sub(r"\s+", "", str(v)).upper()
        return s or None

    @field_validator("competencia", mode="before")
    @classmethod
    def _competencia(cls, v: Any) -> str | None:
        m = _COMPETENCIA.search(str(v or ""))
        if not m or not 1 <= int(m.group(1)) <= 12:
            return None
        return f"{int(m.group(1)):02d}/{m.group(2)}"

    @field_validator("qualidade", "confianca_tipo", mode="before")
    @classmethod
    def _zero_a_um(cls, v: Any) -> float:
        n = numero_br(v)
        return 0.5 if n is None else min(1.0, max(0.0, n))

    @field_validator("legivel", "inicio_documento", mode="before")
    @classmethod
    def _booleano(cls, v: Any) -> bool:
        if isinstance(v, str):
            return v.strip().lower() in {"true", "sim", "1", "yes"}
        return bool(v)

    @model_validator(mode="after")
    def _numeracao_coerente(self) -> "AnalisePagina":
        if self.pagina_x and self.pagina_de and self.pagina_x > self.pagina_de:
            self.pagina_x = self.pagina_de = None
        return self


# ---------------------------------------------------------------------------
# Saídas do motor documental (frente 2) consumidas por regras (frente 3) e API (frente 1)
# ---------------------------------------------------------------------------
@dataclass
class PaginaRenderizada:
    ordem: int  # 1..N, ordem original no lote
    png: bytes
    texto_camada: str  # texto digital do PDF ("" em imagem/escaneado)


@dataclass
class SegmentoDocumento:
    """Um documento lógico separado do lote (páginas consecutivas)."""

    paginas: list[int]  # ordens das páginas no lote
    tipo: TipoDocumento
    trabalhador_id: str | None
    competencia: str | None
    confianca: float
    campos: CamposPagina
    paginas_ilegiveis: list[int] = field(default_factory=list)
    paginas_faltantes: list[int] = field(default_factory=list)  # pelo "x de y" impresso
    alertas: list[str] = field(default_factory=list)  # fronteira incerta, numeração quebrada...


@dataclass
class Roteamento:
    status: StatusDocumento
    motivos_pendencia: list[str] = field(default_factory=list)  # objetivos -> vão à fornecedora
    motivos_revisao: list[str] = field(default_factory=list)  # internos -> só Bernhoeft vê
