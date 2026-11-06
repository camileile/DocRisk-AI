"""Correções humanas e evidências de campos, somente no escopo autorizado do documento."""
from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any

from fastapi import HTTPException


FIELDS = {"horas_extras_h", "horas_extras_valor", "valor_liquido", "valor_pago", "data_pagamento"}


def corrigir(conn, doc, payload: dict[str, Any], user_id: str) -> None:
    changes = payload.get("campos")
    sources = payload.get("fontes")
    reason = payload.get("motivo")
    if not isinstance(changes, dict) or not changes or not set(changes) <= FIELDS:
        raise HTTPException(422, "Informe somente campos documentais editáveis")
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 500:
        raise HTTPException(422, "Informe justificativa com até 500 caracteres")
    if not isinstance(sources, dict) or set(sources) != set(changes):
        raise HTTPException(422, "Indique a página conferida para cada campo alterado")
    if payload.get("esperado_em") != doc["updated_at"]:
        raise HTTPException(409, "Documento atualizado por outra operação; recarregue antes de editar")
    pages = {r[0] for r in conn.execute("SELECT page_id FROM doc_pages WHERE document_id=?", (doc["id"],))}
    for name, value in changes.items():
        if isinstance(sources[name], bool) or not isinstance(sources[name], int) or sources[name] not in pages:
            raise HTTPException(422, "A fonte deve ser uma página deste documento")
        if value is None:
            continue  # Ausência de valor permanece explícita; não vira zero.
        if name == "data_pagamento":
            if not isinstance(value, str) or len(value) != 10:
                raise HTTPException(422, "Data deve estar no formato DD/MM/AAAA")
            try:
                datetime.strptime(value, "%d/%m/%Y")
            except ValueError as exc:
                raise HTTPException(422, "Data de pagamento inválida") from exc
        else:
            try:
                valid = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0
            except OverflowError:
                valid = False
            if not valid:
                raise HTTPException(422, "Horas e valores devem ser números finitos não negativos, ou nulos")
    fields = json.loads(doc["campos_json"] or "{}")
    actual = {name: value for name, value in changes.items() if fields.get(name) != value}
    if not actual:
        raise HTTPException(422, "Nenhum campo foi alterado")
    before = {name: fields.get(name) for name in actual}
    fields.update(actual)
    now = datetime.now().isoformat(timespec="microseconds")
    updated = conn.execute(
        "UPDATE documents SET campos_json=?,revisado_por=?,updated_at=? WHERE id=? AND updated_at=? AND status=?",
        (json.dumps(fields), user_id, now, doc["id"], doc["updated_at"], doc["status"]))
    if updated.rowcount != 1:
        raise HTTPException(409, "Documento atualizado por outra operação; recarregue antes de editar")
    revision = conn.execute("SELECT COALESCE(MAX(revision_number),0)+1 FROM document_field_reviews WHERE document_id=?", (doc["id"],)).fetchone()[0]
    for name, value in actual.items():
        conn.execute(
            "INSERT INTO document_field_reviews (document_id,field_name,original_value_json,corrected_value_json,author_id,reason,source,document_version,revision_number,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (doc["id"],name,json.dumps(before[name]),json.dumps(value),user_id,reason.strip(),
             f"Página #{sources[name]}",doc["versao"],revision,now))
        revision += 1



def evidencias(conn, document_id: int) -> dict[str, list[dict[str, Any]]]:
    result = {name: [] for name in sorted(FIELDS)}
    rows = conn.execute(
        "SELECT p.id,p.ordem,p.analise_json FROM doc_pages dp JOIN pages p ON p.id=dp.page_id "
        "WHERE dp.document_id=? ORDER BY dp.posicao", (document_id,))
    for row in rows:
        try:
            analysis = json.loads(row["analise_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(analysis, dict) or not isinstance(analysis.get("campos"), dict):
            continue
        for name, value in analysis["campos"].items():
            if name in result and value is not None:
                result[name].append({"page_id": row["id"], "ordem": row["ordem"], "valor": value,
                                     "origem": analysis.get("origem", "Não informada"),
                                     "confianca_classificacao": analysis.get("confianca_tipo")})
    return result
