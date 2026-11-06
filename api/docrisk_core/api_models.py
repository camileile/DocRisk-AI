from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .contracts import StatusParecer


_COMPETENCIA_PATTERN = r"^(0[1-9]|1[0-2])/\d{4}$"


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_id: str = Field(min_length=1, max_length=80, pattern=r"^CT-[A-Z0-9-]+$")
    competencia: str = Field(pattern=_COMPETENCIA_PATTERN)
    observacoes: str = Field(default="", max_length=2000)

    @field_validator("contract_id", "competencia", mode="before")
    @classmethod
    def trim_required_values(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


class ReportEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: str
    documento: int = Field(gt=0)
    versao: int = Field(gt=0)
    lote: int = Field(gt=0)
    paginas: list[int]
    origem: str | None = None
    vinculo_aej: str | None = None
    linhas_origem: list[int] = Field(default_factory=list)


class ReportItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trabalhador_id: str
    situacao: str
    resultado: str
    detalhe: str
    horas_ponto: float | None
    horas_folha: float | None
    diferenca_h: float | None
    comprovante_presente: bool
    evidencias: list[ReportEvidence]
    analise_id: int | None = None


class ReportContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contrato: dict[str, str]
    contratante: str
    fornecedora: str
    competencia: str = Field(pattern=_COMPETENCIA_PATTERN)
    gerado_em: str
    regra: str
    escopo: str
    limitacoes: list[str]
    resumo: dict[str, int]
    itens: list[ReportItem]


class ReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)
    contract_id: str = Field(min_length=1, max_length=80, pattern=r"^CT-[A-Z0-9-]+$")
    competencia: str = Field(pattern=_COMPETENCIA_PATTERN)
    versao: int = Field(gt=0)
    status: StatusParecer
    conteudo_json: ReportContent | dict[str, Any]
    observacoes: str | None = None
    autor_id: str | None = None
    created_at: str | None = None
    publicado_em: str | None = None
    publicado_por: str | None = None

    @field_validator("conteudo_json", mode="before")
    @classmethod
    def parse_report_content(cls, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = json.loads(value or "{}")
            except json.JSONDecodeError as exc:
                raise ValueError("conteudo_json não contém JSON válido") from exc
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("conteudo_json deve ser um objeto JSON")
        return value
