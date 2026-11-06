"""Indicadores do Analista Bernhoeft, sempre restritos aos contratos autorizados.

Unidade principal: par (contrato, trabalhador, competência).
A cobertura usa o cadastro de trabalhadores como denominador.
Indício de divergência não é comprovação de irregularidade.
"""
from __future__ import annotations

import json
import math
import sqlite3
from collections import defaultdict
from typing import Any

from ..contracts import ResultadoConciliacao, StatusConciliacao, StatusPendencia

_VALIDOS = {
    ResultadoConciliacao.DIVERGENCIA_A_VERIFICAR.value,
    ResultadoConciliacao.SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS.value,
}
_ABERTAS = {s.value for s in (
    StatusPendencia.ABERTA, StatusPendencia.NOTIFICADA,
    StatusPendencia.REENVIADA, StatusPendencia.REABERTA,
)}


def _lista_contratos(conn: sqlite3.Connection, ids: list[str]) -> list[dict[str, str]]:
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    rows = conn.execute(
        "SELECT c.id, c.nome, c.contratante_id, c.fornecedora_id, "
        "contr.nome AS contratante_nome, forn.nome AS fornecedora_nome "
        "FROM contracts c "
        "JOIN organizations contr ON contr.id=c.contratante_id "
        "JOIN organizations forn ON forn.id=c.fornecedora_id "
        f"WHERE c.id IN ({marks}) ORDER BY c.nome, c.id", ids,
    ).fetchall()
    return [dict(row) for row in rows]


def _analises(conn: sqlite3.Connection, ids: list[str]) -> list[dict[str, Any]]:
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    rows = conn.execute(
        "SELECT contract_id, worker_id, competencia, status, resultado_json "
        f"FROM analyses WHERE atual=1 AND contract_id IN ({marks})", ids,
    ).fetchall()
    parsed = []
    for row in rows:
        try:
            resultado = json.loads(row["resultado_json"])
            if not isinstance(resultado, dict):
                resultado = {}
        except (ValueError, TypeError):
            resultado = {}
        parsed.append({**dict(row), "resultado": resultado})
    return parsed


def _mes(competencia: str) -> tuple[int, int]:
    try:
        mes, ano = competencia.split("/")
        return int(ano), int(mes)
    except (ValueError, AttributeError):
        return 0, 0


def _contagem(analises: list[dict[str, Any]], roster: set[tuple[str, str]]) -> dict[str, Any]:
    # Cada trabalhador é contado uma vez por contrato na competência escolhida.
    validas = [a for a in analises if (
        (a["contract_id"], a["worker_id"]) in roster
        and a["status"] == StatusConciliacao.ANALISADA.value
        and a["resultado"].get("tipo") in _VALIDOS
    )]
    divergentes = [a for a in validas if a["resultado"]["tipo"] ==
                   ResultadoConciliacao.DIVERGENCIA_A_VERIFICAR.value]
    horas = 0.0
    sem_horas = 0
    for a in divergentes:
        diferenca = a["resultado"].get("diferenca_h")
        if isinstance(diferenca, (int, float)) and not isinstance(diferenca, bool) and math.isfinite(diferenca):
            horas += abs(float(diferenca))
        else:
            sem_horas += 1
    bloqueadas = sum(a["status"] in (
        StatusConciliacao.BLOQUEADA_PENDENCIA.value,
        StatusConciliacao.REVISAO_HUMANA.value,
    ) for a in analises if (a["contract_id"], a["worker_id"]) in roster)
    total = len(roster)
    avaliados = len(validas)
    return {
        "cadastrados": total,
        "avaliados": avaliados,
        "divergencias": len(divergentes),
        "taxa_divergencias": round(len(divergentes) / avaliados, 4) if avaliados else None,
        "cobertura": round(avaliados / total, 4) if total else None,
        "horas_divergentes": round(horas, 2),
        "divergencias_sem_horas": sem_horas,
        "pendencias_criticas": bloqueadas,
    }


def montar_dashboard(
    conn: sqlite3.Connection,
    ids_autorizados: list[str],
    *,
    contratante_id: str | None = None,
    fornecedora_id: str | None = None,
    contrato_id: str | None = None,
    competencia: str | None = None,
) -> dict[str, Any]:
    """Combina somente os contratos autorizados pela sessão.

    Por padrão, os cartões apresentam a competência mais recente. A evolução
    apresenta até 12 competências (histórico) para o mesmo escopo empresarial.
    """
    permitidos = _lista_contratos(conn, ids_autorizados)
    contratantes = sorted(
        {c["contratante_id"]: c["contratante_nome"] for c in permitidos}.items(),
        key=lambda item: item[1],
    )
    fornecedoras_base = [c for c in permitidos if not contratante_id or c["contratante_id"] == contratante_id]
    fornecedoras = sorted(
        {c["fornecedora_id"]: c["fornecedora_nome"] for c in fornecedoras_base}.items(),
        key=lambda item: item[1],
    )
    scope = [
        c for c in permitidos
        if (not contratante_id or c["contratante_id"] == contratante_id)
        and (not fornecedora_id or c["fornecedora_id"] == fornecedora_id)
        and (not contrato_id or c["id"] == contrato_id)
    ]
    ids = [c["id"] for c in scope]
    todas_analises = _analises(conn, ids)
    meses = sorted({a["competencia"] for a in todas_analises if _mes(a["competencia"]) != (0, 0)}, key=_mes)
    selecionada = competencia or (meses[-1] if meses else None)
    analises_mes = [a for a in todas_analises if a["competencia"] == selecionada]

    roster_por_contrato: dict[str, set[tuple[str, str]]] = defaultdict(set)
    if ids:
        marks = ",".join("?" for _ in ids)
        for row in conn.execute(
            f"SELECT contract_id, id FROM workers WHERE contract_id IN ({marks})", ids,
        ).fetchall():
            roster_por_contrato[row["contract_id"]].add((row["contract_id"], row["id"]))
    roster = set().union(*(roster_por_contrato.values())) if roster_por_contrato else set()
    resumo = _contagem(analises_mes, roster)

    abertas = 0
    if ids and selecionada:
        marks = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT status FROM issues WHERE contract_id IN ({marks}) AND competencia=?",
            (*ids, selecionada),
        ).fetchall()
        abertas = sum(row["status"] in _ABERTAS for row in rows)
    resumo["pendencias_abertas"] = abertas

    evolucao = []
    for mes in meses[-12:]:
        metricas = _contagem([a for a in todas_analises if a["competencia"] == mes], roster)
        evolucao.append({
            "competencia": mes,
            "avaliados": metricas["avaliados"],
            "divergencias": metricas["divergencias"],
            "taxa_divergencias": metricas["taxa_divergencias"],
            "cobertura": metricas["cobertura"],
        })

    comparacao = []
    for fornecedora, nome in fornecedoras:
        contratos_fornecedora = {c["id"] for c in scope if c["fornecedora_id"] == fornecedora}
        if not contratos_fornecedora:
            continue
        roster_fornecedora = set().union(
            *(roster_por_contrato.get(i, set()) for i in contratos_fornecedora)
        )
        metricas = _contagem(
            [a for a in analises_mes if a["contract_id"] in contratos_fornecedora],
            roster_fornecedora,
        )
        comparacao.append({
            "id": fornecedora,
            "nome": nome,
            "avaliados": metricas["avaliados"],
            "divergencias": metricas["divergencias"],
            "taxa_divergencias": metricas["taxa_divergencias"],
            "cobertura": metricas["cobertura"],
        })

    return {
        "filtros": {
            "contratantes": [{"id": id_, "nome": nome} for id_, nome in contratantes],
            "fornecedoras": [{"id": id_, "nome": nome} for id_, nome in fornecedoras],
            "contratos": [{"id": c["id"], "nome": c["nome"]} for c in scope],
            "competencias": meses[::-1],
            "competencia_selecionada": selecionada,
        },
        "resumo": resumo,
        "evolucao": evolucao,
        "comparacao": comparacao,
        "observacao": (
            "Taxa de divergências: trabalhadores com divergência / trabalhadores com análise válida. "
            "Cobertura: trabalhadores com análise válida / trabalhadores cadastrados nos contratos selecionados. "
            "Pendências críticas: análises bloqueadas ou em revisão humana. "
            "Divergência é indício a verificar, nunca irregularidade comprovada."
        ),
    }
