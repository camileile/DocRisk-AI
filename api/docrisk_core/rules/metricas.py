"""Indicadores do painel Bernhoeft. Dono: FRENTE 3.

Spec 7.1: calcular a partir dos REGISTROS processados (nunca do gabarito) e dizer
a unidade de cada número (documento lógico x versão, par trabalhador+competência...).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from ..contracts import (
    ResultadoConciliacao, StatusConciliacao, StatusDocumento, StatusParecer, StatusPendencia,
)


def _marcas(ids: list[str]) -> str:
    return ",".join("?" * len(ids))


def _contagem(conn: sqlite3.Connection, sql: str, ids: list[str]) -> dict[str, int]:
    return {str(r[0]): int(r[1]) for r in conn.execute(sql, ids).fetchall()}


def _horas_entre(inicio: str | None, fim: str | None) -> float | None:
    try:
        return (datetime.fromisoformat(fim) - datetime.fromisoformat(inicio)).total_seconds() / 3600  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def calcular_metricas(conn: sqlite3.Connection, contratos: list[str]) -> dict[str, Any]:
    """Indicadores dos contratos informados.

    Mínimo: documentos (lógicos e versões) por status e tipo; pares aptos / bloqueados /
    em revisão; divergências sinalizadas (não são passivos); pendências abertas e
    resolvidas; reenvios; tempo médio de regularização (h); taxa de revisão humana;
    páginas processadas e tempo médio por página (ms); pareceres publicados.
    """
    ids = list(contratos)
    if not ids:
        ids = ["__nenhum__"]
    m = _marcas(ids)

    versoes_por_status = _contagem(conn, f"SELECT status, COUNT(*) FROM documents WHERE contract_id IN ({m}) GROUP BY status", ids)
    vigentes_por_tipo = _contagem(
        conn, f"SELECT tipo, COUNT(*) FROM documents WHERE contract_id IN ({m}) AND status<>'{StatusDocumento.SUBSTITUIDO.value}' GROUP BY tipo", ids)
    vigentes_por_status = {k: v for k, v in versoes_por_status.items() if k != StatusDocumento.SUBSTITUIDO.value}
    total_versoes = sum(versoes_por_status.values())
    total_logicos = sum(vigentes_por_status.values())
    # Taxa de revisão humana: documentos lógicos (versões vigentes) que foram ou estão na revisão.
    revisados = conn.execute(
        f"SELECT COUNT(*) FROM documents WHERE contract_id IN ({m}) AND status<>? AND"
        f" (status=? OR revisado_por IS NOT NULL)",
        (*ids, StatusDocumento.SUBSTITUIDO.value, StatusDocumento.REVISAO_HUMANA.value)).fetchone()[0]

    analises = conn.execute(
        f"SELECT status, resultado_json FROM analyses WHERE contract_id IN ({m}) AND atual=1", ids).fetchall()
    pares_status: dict[str, int] = {s.value: 0 for s in StatusConciliacao}
    resultados: dict[str, int] = {r.value: 0 for r in ResultadoConciliacao}
    for a in analises:
        pares_status[a["status"]] = pares_status.get(a["status"], 0) + 1
        try:
            tipo = json.loads(a["resultado_json"]).get("tipo", ResultadoConciliacao.NAO_AVALIADO.value)
        except (TypeError, ValueError):
            tipo = ResultadoConciliacao.NAO_AVALIADO.value
        if a["status"] != StatusConciliacao.ANALISADA.value:
            tipo = ResultadoConciliacao.NAO_AVALIADO.value  # bloqueado nunca conta como regular
        resultados[tipo] = resultados.get(tipo, 0) + 1

    issues = conn.execute(
        f"SELECT status, categoria, created_at, resolved_at FROM issues WHERE contract_id IN ({m})", ids).fetchall()
    pend_status: dict[str, int] = {s.value: 0 for s in StatusPendencia}
    pend_categoria: dict[str, int] = {}
    tempos = []
    for i in issues:
        pend_status[i["status"]] = pend_status.get(i["status"], 0) + 1
        pend_categoria[i["categoria"]] = pend_categoria.get(i["categoria"], 0) + 1
        if i["status"] == StatusPendencia.RESOLVIDA.value:
            horas = _horas_entre(i["created_at"], i["resolved_at"])
            if horas is not None:
                tempos.append(horas)
    em_aberto = sum(pend_status[s.value] for s in (StatusPendencia.ABERTA, StatusPendencia.NOTIFICADA,
                                                    StatusPendencia.REENVIADA, StatusPendencia.REABERTA))

    lotes = _contagem(conn, f"SELECT status, COUNT(*) FROM batches WHERE contract_id IN ({m}) GROUP BY status", ids)
    reenvios = conn.execute(
        f"SELECT COUNT(*) FROM batches WHERE contract_id IN ({m}) AND issue_id IS NOT NULL", ids).fetchone()[0]
    paginas = conn.execute(
        f"SELECT COUNT(*), AVG(p.ms), SUM(CASE WHEN p.status='OK' THEN 1 ELSE 0 END)"
        f" FROM pages p JOIN batches b ON b.id=p.batch_id WHERE b.contract_id IN ({m})", ids).fetchone()
    publicados = conn.execute(
        f"SELECT COUNT(*) FROM reports WHERE contract_id IN ({m}) AND status=?",
        (*ids, StatusParecer.APROVADO_PUBLICADO.value)).fetchone()[0]

    return {
        "contratos": list(contratos),
        "documentos": {
            "unidade": "documento lógico = versão vigente; versões incluem as substituídas",
            "logicos": total_logicos,
            "versoes": total_versoes,
            "por_status": vigentes_por_status,
            "por_tipo": vigentes_por_tipo,
            "substituidos": versoes_por_status.get(StatusDocumento.SUBSTITUIDO.value, 0),
            "taxa_revisao_humana": round(revisados / total_logicos, 4) if total_logicos else None,
        },
        "conciliacao": {
            "unidade": "par trabalhador + competência (análise atual)",
            "pares": len(analises),
            "por_status": pares_status,
            "por_resultado": resultados,
            "aptos": pares_status[StatusConciliacao.ANALISADA.value],
            "bloqueados": pares_status[StatusConciliacao.BLOQUEADA_PENDENCIA.value],
            "em_revisao": pares_status[StatusConciliacao.REVISAO_HUMANA.value],
            "divergencias_a_verificar": resultados[ResultadoConciliacao.DIVERGENCIA_A_VERIFICAR.value],
            "observacao": "Divergência é indício a conferir, não passivo trabalhista. "
                          "Pares bloqueados nunca contam como sem divergência.",
        },
        "pendencias": {
            "unidade": "pendência documental",
            "total": len(issues),
            "em_aberto": em_aberto,
            "resolvidas": pend_status[StatusPendencia.RESOLVIDA.value],
            "por_status": pend_status,
            "por_categoria": pend_categoria,
            "tempo_medio_regularizacao_h": round(sum(tempos) / len(tempos), 2) if tempos else None,
        },
        "lotes": {"unidade": "arquivo enviado", "total": sum(lotes.values()), "por_status": lotes,
                  "reenvios": int(reenvios)},
        "paginas": {"unidade": "página renderizada", "total": int(paginas[0] or 0),
                    "lidas": int(paginas[2] or 0),
                    "tempo_medio_ms": round(paginas[1]) if paginas[1] is not None else None},
        "pareceres_publicados": int(publicados),
    }
