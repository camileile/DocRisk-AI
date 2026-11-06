"""Gera amostras sintéticas congeladas para cobertura e avaliação cega D1-08.

O comando público só regenera o corpus de desenvolvimento. O holdout é um artefato
versionado; seu hash é verificado pelos testes e não entra no benchmark local.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

import pymupdf as fitz
from PIL import Image, ImageDraw


PERFIS = {
    "dev": {
        "seed": 1808,
        "workers": ["T101", "T102", "T103", "T104", "T105", "T106", "T107"],
        "rotation": 90,
    },
    "holdout": {
        "seed": 8808,
        "workers": ["T201", "T202", "T203", "T204", "T205", "T206", "T207"],
        "rotation": 270,
    },
}


def _digital_page(doc: fitz.Document, lines: list[str], rotation: int = 0) -> None:
    page = doc.new_page(width=595, height=842)
    y = 72
    for i, line in enumerate(lines):
        page.insert_text((48, y), line, fontsize=16 if i == 0 else 12, fontname="helv")
        y += 26
    page.insert_text((48, 805), "DOCUMENTO FICTICIO - corpus D1-08", fontsize=8, color=(0.45, 0.45, 0.45))
    if rotation:
        page.set_rotation(rotation)


def _scanned_page(doc: fitz.Document, lines: list[str], rotation: int = 0) -> None:
    image = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(image)
    y = 120
    for i, line in enumerate(lines):
        draw.text((100, y), line, fill="black", stroke_width=1 if i == 0 else 0)
        y += 72
    draw.text((100, 1650), "DOCUMENTO FICTICIO - corpus D1-08", fill=(90, 90, 90))
    import io

    stream = io.BytesIO()
    image.save(stream, format="PNG")
    page = doc.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=stream.getvalue())
    if rotation:
        page.set_rotation(rotation)


def _point(worker: str, page: int, total: int, hours: int, *, title: bool = True,
           holdout: bool = False) -> list[str]:
    if holdout:
        lines = []
        if title:
            lines.append("REGISTRO DE PONTO")
        lines.extend([
            f"Trabalhador: Pessoa Ficticia {worker}  Matricula: {worker}",
            "Competencia - 11/2026",
            "Batidas do dia  Entrada  Saida",
            "03/11  07:30  16:30",
            f"Total de horas extras {hours} h",
            f"Pagina {page} de {total}",
        ])
        return lines
    lines = []
    if title:
        lines.append("ESPELHO DE PONTO")
    lines.extend([
        f"Trabalhador: Pessoa Ficticia {worker}  Matricula: {worker}",
        "Competencia: 10/2026",
        "Data  Entrada  Saida",
        "01/10  08:00  17:00",
        f"Total de horas extras: {hours},00 h",
        f"Pagina {page} de {total}",
    ])
    return lines


def _holerite(worker: str, *, hours: int | None, money: str = "160,00", holdout: bool = False) -> list[str]:
    if holdout:
        lines = ["CONTRACHEQUE", f"Matricula: {worker}", "Competencia - 11/2026",
                 "Vencimentos e descontos", "Salario base R$ 2.100,00"]
        lines.append(f"Horas extras - Ref.: {hours} h - R$ {money}" if hours is not None
                     else f"Horas extras - R$ {money}")
        lines.extend(["Liquido: R$ 2.000,00", "Pagina 1 de 1"])
        return lines
    lines = ["DEMONSTRATIVO DE PAGAMENTO DE SALARIO", f"Matricula: {worker}",
             "Competencia: 10/2026", "Proventos e descontos", "Salario base R$ 1.800,00"]
    lines.append(f"Horas extras 50% - Ref.: {hours},00 h - R$ {money}" if hours is not None
                 else f"Horas extras 50% - R$ {money}")
    lines.extend(["Liquido a receber: R$ 1.800,00", "Pagina 1 de 1"])
    return lines


def _receipt(worker: str, holdout: bool = False) -> list[str]:
    if holdout:
        return ["COMPROVANTE DE TRANSFERENCIA BANCARIA", f"Favorecido: Pessoa Ficticia {worker}",
                f"Matricula: {worker}", "Competencia: 11/2026", "Valor transferido: R$ 2.000,00",
                "Data de pagamento: 05/12/2026", "Autenticacao ficticia: 9876.5432"]
    return ["COMPROVANTE DE PAGAMENTO", f"Favorecido: Pessoa Ficticia {worker}",
            f"Matricula: {worker}", "Competencia: 10/2026", "Valor pago: R$ 1.800,00",
            "Data do pagamento: 05/11/2026", "Autenticacao ficticia: 0000.1234"]


def _cases(split: str, rotation: int) -> list[dict[str, Any]]:
    w = PERFIS[split]["workers"]
    holdout = split == "holdout"
    return [
        {"id": "multipagina_rotacionada", "kind": "multipagina", "workers": [w[0]],
         "pages": [{"text": _point(w[0], 1, 2, 5 if holdout else 4, holdout=holdout), "rotation": 0},
                   {"text": _point(w[0], 2, 2, 5 if holdout else 4, title=False, holdout=holdout),
                    "rotation": rotation}],
         "documents": [{"local_pages": [1, 2], "tipo": "ESPELHO_PONTO", "worker": w[0],
                        "status": "APTO"}], "ausencias": []},
        {"id": "scan_ilegivel_para_textlayer", "kind": "scan", "workers": [w[1]],
         "pages": [{"scan": _holerite(w[1], hours=6, holdout=holdout),
                    "rotation": rotation if holdout else 0}],
         "documents": [{"local_pages": [1], "tipo": "DESCONHECIDO", "worker": None,
                        "status": "REVISAO_HUMANA"}], "ausencias": []},
        {"id": "rotacao_180", "kind": "rotacao", "workers": [w[2]],
         "pages": [{"text": _receipt(w[2], holdout), "rotation": 180 if not holdout else 90}],
         "documents": [{"local_pages": [1], "tipo": "COMPROVANTE_PAGAMENTO", "worker": w[2],
                        "status": "APTO"}], "ausencias": []},
        {"id": "pagina_faltante", "kind": "ausencia_pagina", "workers": [w[3]],
         "pages": [{"text": _point(w[3], 1, 3 if holdout else 2, 5, holdout=holdout)}],
         "documents": [{"local_pages": [1], "tipo": "ESPELHO_PONTO", "worker": w[3],
                        "status": "PENDENTE_CORRECAO"}], "ausencias": []},
        {"id": "identidade_ambigua_na_continuacao", "kind": "ambiguidade", "workers": [w[4], w[5]],
         "pages": [{"text": _point(w[4], 1, 3 if holdout else 2, 4, holdout=holdout)},
                   {"text": _point(w[5], 2, 3 if holdout else 2, 4, title=False, holdout=holdout)}],
         "documents": [{"local_pages": [1], "tipo": "ESPELHO_PONTO", "worker": w[4],
                        "status": "PENDENTE_CORRECAO"},
                       {"local_pages": [2], "tipo": "DESCONHECIDO", "worker": w[5],
                        "status": "REVISAO_HUMANA"}], "ausencias": []},
        {"id": "holerite_ausente", "kind": "ausencia_documento", "workers": [w[6]],
         "pages": [{"text": _point(w[6], 1, 1, 3, holdout=holdout)}],
         "documents": [{"local_pages": [1], "tipo": "ESPELHO_PONTO", "worker": w[6],
                        "status": "APTO"}], "ausencias": ["HOLERITE"]},
        {"id": "horas_extras_so_em_reais", "kind": "campo_so_em_reais", "workers": [w[1]],
         "pages": [{"text": _holerite(w[1], hours=None, money="275,50" if holdout else "230,00",
                                          holdout=holdout)}],
         "documents": [{"local_pages": [1], "tipo": "HOLERITE", "worker": w[1],
                        "status": "APTO", "horas_extras_h": None, "horas_extras_valor": 230.0}],
         "ausencias": ["ESPELHO_PONTO"]},
    ]


def _generate(split: str, output: Path) -> dict[str, Path]:
    if split not in PERFIS:
        raise ValueError(f"split inválido: {split}")
    profile = PERFIS[split]
    cases = _cases(split, profile["rotation"])
    random.Random(profile["seed"]).shuffle(cases)
    output.mkdir(parents=True, exist_ok=True)
    pdf = fitz.open()
    page_annotations: list[dict[str, Any]] = []
    expected_docs: list[dict[str, Any]] = []
    case_labels: list[dict[str, Any]] = []
    for case in cases:
        first_page = pdf.page_count + 1
        for local_page, page_spec in enumerate(case["pages"], start=1):
            if "scan" in page_spec:
                rotation = int(page_spec.get("rotation", 0))
                _scanned_page(pdf, page_spec["scan"], rotation)
                modality = "scan"
            else:
                rotation = int(page_spec.get("rotation", 0))
                _digital_page(pdf, page_spec["text"], rotation)
                modality = "digital"
            page_annotations.append({"page": pdf.page_count, "case": case["id"], "modality": modality,
                                     "rotation_degrees": rotation})
        case_pages = list(range(first_page, pdf.page_count + 1))
        case_labels.append({"id": case["id"], "kind": case["kind"], "pages": case_pages,
                            "workers": case["workers"], "ausencias_documentais": case["ausencias"]})
        for document in case["documents"]:
            expected_docs.append({
                "case": case["id"],
                "pages": [first_page + index - 1 for index in document["local_pages"]],
                "tipo": document["tipo"],
                "trabalhador_id": document["worker"],
                "status_esperado": document["status"],
                **{key: value for key, value in document.items()
                   if key not in {"local_pages", "tipo", "worker", "status"}},
            })
    pdf_path = output / f"corpus_{split}.pdf"
    pdf.set_metadata({"title": f"D1-08 {split} synthetic corpus", "author": "DocRisk AI",
                      "subject": "Synthetic evaluation fixture", "creator": "D1-08 generator",
                      "producer": "PyMuPDF", "creationDate": "", "modDate": ""})
    pdf.save(pdf_path, garbage=4, deflate=True, no_new_id=True)
    pdf.close()
    distribution: dict[str, int] = {}
    for case in cases:
        distribution[case["kind"]] = distribution.get(case["kind"], 0) + 1
    gold = {
        "schema_version": 1,
        "split": split,
        "seed": profile["seed"],
        "is_evaluation_holdout": split == "holdout",
        "distribution": dict(sorted(distribution.items())),
        "pages": page_annotations,
        "cases": case_labels,
        "documents": expected_docs,
    }
    gold_path = output / f"gabarito_{split}.json"
    gold_path.write_text(json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"pdf": pdf_path, "gabarito": gold_path}


def gerar_corpus_desenvolvimento(output: Path) -> dict[str, Path]:
    """Gera apenas a amostra de desenvolvimento; nunca lê ou grava o holdout congelado."""
    return _generate("dev", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera o corpus sintético de desenvolvimento D1-08.")
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    result = gerar_corpus_desenvolvimento(args.saida)
    for name, path in result.items():
        print(f"{name}: {path} sha256={hashlib.sha256(path.read_bytes()).hexdigest()}")
