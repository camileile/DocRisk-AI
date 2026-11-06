from __future__ import annotations

from collections import Counter
from enum import StrEnum
from typing import Any, Iterable


class EstadoComprovante(StrEnum):
    NAO_RECEBIDO = "NAO_RECEBIDO"
    RECEBIDO = "RECEBIDO"
    EM_REVISAO = "EM_REVISAO"
    CONFERIDO = "CONFERIDO"
    INSUFICIENTE = "INSUFICIENTE"
    REJEITADO = "REJEITADO"


_SUBSTITUIDO = "SUBSTITUIDO"
_AVALIADOS = {EstadoComprovante.CONFERIDO, EstadoComprovante.INSUFICIENTE, EstadoComprovante.REJEITADO}
_RECEBIDOS = {
    EstadoComprovante.RECEBIDO,
    EstadoComprovante.EM_REVISAO,
    EstadoComprovante.CONFERIDO,
    EstadoComprovante.INSUFICIENTE,
}


def classificar_comprovante(documentos: Iterable[dict[str, Any]]) -> EstadoComprovante:
    vigentes = [doc for doc in documentos if doc.get("status") != _SUBSTITUIDO]
    if not vigentes:
        return EstadoComprovante.NAO_RECEBIDO
    atual = max(vigentes, key=lambda doc: (int(doc.get("versao") or 1), int(doc.get("id") or 0)))
    status = atual.get("status")
    if status == EstadoComprovante.REJEITADO.value:
        return EstadoComprovante.REJEITADO
    if status == "REVISAO_HUMANA":
        return EstadoComprovante.EM_REVISAO
    if status == "PENDENTE_CORRECAO":
        return EstadoComprovante.INSUFICIENTE
    if status == "APTO" and atual.get("revisado_por"):
        return EstadoComprovante.CONFERIDO
    return EstadoComprovante.RECEBIDO


def calcular_metricas_comprovante(obrigacoes: Iterable[dict[str, Any]]) -> dict[str, Any]:
    elegiveis = [obrigacao for obrigacao in obrigacoes if obrigacao.get("exigivel", True)]
    estados: list[EstadoComprovante] = []
    reenvios = 0
    for obrigacao in elegiveis:
        estados.append(classificar_comprovante(obrigacao.get("documentos", [])))
        reenvios += max(0, int(obrigacao.get("reenvios", 0)))
    contagem = Counter(estados)
    for estado in EstadoComprovante:
        contagem.setdefault(estado, 0)
    total = len(elegiveis)
    recebidos = sum(contagem[estado] for estado in _RECEBIDOS)
    avaliados = sum(contagem[estado] for estado in _AVALIADOS)
    conferidos = contagem[EstadoComprovante.CONFERIDO]
    insuficientes = contagem[EstadoComprovante.INSUFICIENTE]
    return {
        "unidade": "obrigação exigível por trabalhador, competência e tipo documental",
        "populacao_exigivel": total,
        "por_estado": {estado.value: contagem[estado] for estado in EstadoComprovante},
        "taxa_recebimento": round(recebidos / total, 4) if total else None,
        "taxa_conferencia": round(conferidos / total, 4) if total else None,
        "taxa_insuficiencia": round(insuficientes / avaliados, 4) if avaliados else None,
        "pendencias": total - conferidos,
        "reenvios": reenvios,
    }
