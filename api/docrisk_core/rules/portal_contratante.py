"""Consulta da contratante: somente snapshots publicados dos seus contratos.

Não consulta analyses, documents, issues ou workers: alterações internas depois
da publicação não mudam os indicadores apresentados à contratante.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..auth import Usuario


def contratos(conn: sqlite3.Connection, user: Usuario) -> list[dict[str, Any]]:
    # Papel é validado pela rota; a organização também precisa ser contratante.
    if user.org_tipo != "CONTRATANTE":
        return []
    return [dict(r) for r in conn.execute(
        "SELECT c.id, c.nome, c.fornecedora_id, f.nome AS fornecedora_nome "
        "FROM contracts c JOIN organizations f ON f.id=c.fornecedora_id "
        "WHERE c.contratante_id=? ORDER BY f.nome, c.nome, c.id", (user.org_id,))]


def publicados(conn: sqlite3.Connection, scope: list[dict[str, Any]], *,
               fornecedora_id: str | None = None, contract_id: str | None = None,
               competencia: str | None = None) -> list[dict[str, Any]]:
    ids = [c["id"] for c in scope
           if (not fornecedora_id or c["fornecedora_id"] == fornecedora_id)
           and (not contract_id or c["id"] == contract_id)]
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    rows = conn.execute(
        "SELECT id, contract_id, competencia, versao, status, conteudo_json, publicado_em "
        f"FROM reports WHERE contract_id IN ({marks}) AND status='APROVADO_PUBLICADO' "
        "ORDER BY versao DESC, id DESC", ids)
    seen: set[tuple[str, str]] = set()
    result = []
    for row in rows:
        key = (row["contract_id"], row["competencia"])
        if key in seen or (competencia and row["competencia"] != competencia):
            continue
        seen.add(key)
        r = dict(row)
        try:
            content = json.loads(r["conteudo_json"] or "{}")
        except (TypeError, ValueError):
            content = {}
        r["conteudo_json"] = content if isinstance(content, dict) else {}
        result.append(r)
    return sorted(result, key=lambda r: (r["publicado_em"] or "", r["id"]), reverse=True)


def resumo(content: dict[str, Any]) -> dict[str, Any]:
    source = content.get("resumo")
    source = source if isinstance(source, dict) else {}

    def count(key: str) -> int:
        n = source.get(key)
        return n if type(n) is int and n >= 0 else 0

    # DADOS_INSUFICIENTES também pode estar em ANALISADA. Não é análise válida
    # para calcular taxa nem cobertura da comparação de horas extras.
    validos = count("com_divergencia") + count("sem_divergencia")
    total = count("trabalhadores")
    return {
        "trabalhadores": total, "analisados": validos,
        "divergencias": count("com_divergencia"),
        "dados_insuficientes": count("dados_insuficientes"),
        "nao_avaliados": count("bloqueados") + count("em_revisao") + count("aguardando_documentos"),
        "taxa_divergencias": round(count("com_divergencia") / validos, 4) if validos else None,
        "cobertura": round(validos / total, 4) if total else None,
    }


def overview(conn: sqlite3.Connection, user: Usuario, *,
             fornecedora_id: str | None = None, contract_id: str | None = None,
             competencia: str | None = None) -> dict[str, Any]:
    scope = contratos(conn, user)
    suppliers = {c["fornecedora_id"]: c["fornecedora_nome"] for c in scope}
    supplier_scope = [c for c in scope if not fornecedora_id or c["fornecedora_id"] == fornecedora_id]
    selected = [c for c in supplier_scope if not contract_id or c["id"] == contract_id]
    reports = publicados(conn, selected)
    months = sorted({r["competencia"] for r in reports},
                    key=lambda s: (s[3:], s[:2]), reverse=True)
    month = competencia or (months[0] if months else None)
    current = {r["contract_id"]: r for r in reports if r["competencia"] == month}
    totals = dict.fromkeys(("trabalhadores", "analisados", "divergencias",
                           "dados_insuficientes", "nao_avaliados"), 0)
    rows = []
    for c in selected:
        report = current.get(c["id"])
        summary = resumo(report["conteudo_json"]) if report else None
        if summary:
            for key in totals:
                totals[key] += summary[key]
        rows.append({**c, "parecer_id": report["id"] if report else None,
                     "versao": report["versao"] if report else None,
                     "publicado_em": report["publicado_em"] if report else None,
                     "resumo": summary})
    return {
        "filtros": {
            "fornecedoras": [{"id": k, "nome": v} for k, v in suppliers.items()],
            "contratos": [{"id": c["id"], "nome": c["nome"]} for c in supplier_scope],
            "competencias": months, "competencia_selecionada": month,
        },
        "resumo": {
            **totals, "contratos": len(selected), "contratos_com_parecer": len(current),
            "taxa_divergencias": round(totals["divergencias"] / totals["analisados"], 4)
            if totals["analisados"] else None,
            "cobertura": round(totals["analisados"] / totals["trabalhadores"], 4)
            if totals["trabalhadores"] else None,
        },
        "contratos": rows,
        "observacao": "Indicadores dos pareceres publicados na competência selecionada. "
        "Trabalhadores são contados por vínculo contratual. Cobertura = comparações válidas / "
        "vínculos nos pareceres; taxa = divergências / comparações válidas. Dados insuficientes "
        "não contam como comparação válida. Contratos sem parecer não atestam regularidade. "
        "Divergências são indícios a conferir e não comprovam irregularidade trabalhista.",
    }
