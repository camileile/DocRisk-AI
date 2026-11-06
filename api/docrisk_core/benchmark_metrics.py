"""Métricas determinísticas para avaliar saídas do motor contra um gabarito fixo."""
from __future__ import annotations

import math
from collections import Counter
from typing import Any

NUMERIC_FIELDS = ("horas_extras_h", "horas_extras_valor", "valor_liquido", "valor_pago")
STATUSES_REVIEW = {"REVISAO_HUMANA", "PENDENTE_CORRECAO"}


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _pr(tp: int, fp: int, fn: int) -> dict[str, float | int]:
    return {"tp": tp, "fp": fp, "fn": fn, "precision": _ratio(tp, tp + fp),
            "recall": _ratio(tp, tp + fn)}


def calcular_metricas(gold_docs: list[dict[str, Any]], predicted_docs: list[dict[str, Any]],
                      *, tolerancia: float = 0.01) -> dict[str, Any]:
    """Calcula fronteiras, classificação, campos, associação e escalonamento.

    Documentos são alinhados pelo número da primeira página; uma fronteira é correta
    somente quando a lista inteira de páginas coincide com o rótulo.
    """
    def pages(doc: dict[str, Any]) -> list[int]:
        return list(map(int, doc.get("pages", doc.get("paginas", []))))

    gold_by_start = {pages(doc)[0]: doc for doc in gold_docs if pages(doc)}
    pred_by_start = {int(doc["pages"][0]): doc for doc in predicted_docs if doc.get("pages")}
    gold_spans = {tuple(pages(doc)) for doc in gold_docs if pages(doc)}
    pred_spans = {tuple(pages(doc)) for doc in predicted_docs if pages(doc)}
    boundary_tp = len(gold_spans & pred_spans)
    boundaries = {**_pr(boundary_tp, len(pred_spans) - boundary_tp, len(gold_spans) - boundary_tp),
                  "exact": boundary_tp, "predicted": len(pred_spans), "expected": len(gold_spans)}

    types = Counter()
    type_names = {str(doc.get("tipo", "DESCONHECIDO")) for doc in gold_docs + predicted_docs}
    for start, gold in gold_by_start.items():
        pred = pred_by_start.get(start)
        expected_type = str(gold.get("tipo", "DESCONHECIDO"))
        if pred is None:
            types[(expected_type, "fn")] += 1
        else:
            predicted_type = str(pred.get("tipo", "DESCONHECIDO"))
            if predicted_type == expected_type:
                types[(expected_type, "tp")] += 1
            else:
                types[(expected_type, "fn")] += 1
                types[(predicted_type, "fp")] += 1
    for start, pred in pred_by_start.items():
        if start not in gold_by_start:
            types[(str(pred.get("tipo", "DESCONHECIDO")), "fp")] += 1
    per_type = {name: _pr(types[(name, "tp")], types[(name, "fp")], types[(name, "fn")])
                for name in sorted(type_names)}

    fields: dict[str, dict[str, Any]] = {}
    for field in NUMERIC_FIELDS:
        tp = fp = fn = 0
        errors: list[float] = []
        for start, gold in gold_by_start.items():
            expected = gold.get("campos_esperados", {}).get(field)
            pred_doc = pred_by_start.get(start)
            predicted = pred_doc.get("campos", {}).get(field) if pred_doc else None
            if expected is None and predicted is None:
                continue
            if expected is None:
                fp += 1
                continue
            if predicted is None:
                fn += 1
                continue
            try:
                error = abs(float(predicted) - float(expected))
            except (TypeError, ValueError, OverflowError):
                fn += 1
                continue
            if not math.isfinite(error):
                fn += 1
                continue
            errors.append(error)
            if error <= tolerancia:
                tp += 1
            else:
                fp += 1
                fn += 1
        for start, pred in pred_by_start.items():
            if start not in gold_by_start and pred.get("campos", {}).get(field) is not None:
                fp += 1
        fields[field] = {
            **_pr(tp, fp, fn),
            "expected_non_null": sum(doc.get("campos_esperados", {}).get(field) is not None
                                     for doc in gold_docs),
            "predicted_non_null": sum(doc.get("campos", {}).get(field) is not None
                                      for doc in predicted_docs),
            "mae": sum(errors) / len(errors) if errors else None,
            "mae_count": len(errors),
            "tolerance": tolerancia,
        }

    association_tp = association_fp = association_fn = 0
    review_tp = review_fp = review_fn = review_tn = 0
    for start, gold in gold_by_start.items():
        pred = pred_by_start.get(start)
        expected_worker = gold.get("trabalhador_id")
        predicted_worker = pred.get("trabalhador_id") if pred else None
        if expected_worker is not None:
            if predicted_worker == expected_worker:
                association_tp += 1
            else:
                association_fn += 1
                if predicted_worker is not None:
                    association_fp += 1
        elif predicted_worker is not None:
            association_fp += 1

        expected_review = gold.get("status_esperado", gold.get("status")) in STATUSES_REVIEW
        predicted_review = pred is not None and pred.get("status") in STATUSES_REVIEW
        if expected_review and predicted_review:
            review_tp += 1
        elif expected_review:
            review_fn += 1
        elif predicted_review:
            review_fp += 1
        elif pred is not None:
            review_tn += 1
    for start, pred in pred_by_start.items():
        if start not in gold_by_start:
            if pred.get("trabalhador_id") is not None:
                association_fp += 1
            if pred.get("status") in STATUSES_REVIEW:
                review_fp += 1

    escalations = review_tp + review_fp
    review = {
        **_pr(review_tp, review_fp, review_fn),
        "true_negative": review_tn,
        "rate": _ratio(escalations, len(predicted_docs)),
        "false_alert_rate": _ratio(review_fp, review_fp + review_tn),
        "false_negatives": review_fn,
    }
    return {
        "document_counts": {"expected": len(gold_docs), "predicted": len(predicted_docs)},
        "boundaries": boundaries,
        "types": per_type,
        "association": _pr(association_tp, association_fp, association_fn),
        "fields": fields,
        "review": review,
    }
