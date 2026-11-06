import hashlib
import json
from pathlib import Path

import pymupdf as fitz

from docrisk_core.ai.textlayer import analisar_texto
from docrisk_core.pipeline.routing import rotear
from docrisk_core.pipeline.segmentation import segmentar
from scripts.gerar_corpus_d1_08 import gerar_corpus_desenvolvimento


FIXTURES = Path(__file__).parent / "fixtures" / "d1_08"
TRABALHADORES = {f"T{i:03d}" for i in range(101, 108)}


def test_corpus_dev_e_reproduzivel_e_cobre_os_cenarios_planejados(tmp_path):
    first = gerar_corpus_desenvolvimento(tmp_path / "one")
    second = gerar_corpus_desenvolvimento(tmp_path / "two")
    first_gold = json.loads(first["gabarito"].read_text(encoding="utf-8"))
    second_gold = json.loads(second["gabarito"].read_text(encoding="utf-8"))

    assert first_gold == second_gold
    assert hashlib.sha256(first["pdf"].read_bytes()).digest() == hashlib.sha256(second["pdf"].read_bytes()).digest()
    assert first_gold["split"] == "dev" and first_gold["is_evaluation_holdout"] is False
    assert first_gold["distribution"] == {
        "ambiguidade": 1, "ausencia_documento": 1, "ausencia_pagina": 1,
        "campo_so_em_reais": 1, "multipagina": 1, "rotacao": 1, "scan": 1,
    }
    assert len(first_gold["pages"]) == 9

    with fitz.open(first["pdf"]) as pdf:
        assert pdf.page_count == 9
        for page_data in first_gold["pages"]:
            page = pdf[page_data["page"] - 1]
            if page_data["modality"] == "scan":
                assert not page.get_text().strip()
                assert page.get_images()
            if page_data["rotation_degrees"]:
                assert page.rotation == page_data["rotation_degrees"]


def test_corpus_dev_gabarito_confere_com_segmentacao_e_roteamento(tmp_path):
    generated = gerar_corpus_desenvolvimento(tmp_path)
    gold = json.loads(generated["gabarito"].read_text(encoding="utf-8"))
    with fitz.open(generated["pdf"]) as pdf:
        analyses = [analisar_texto(page.get_text()) for page in pdf]
    actual = [
        {"pages": segment.paginas, "tipo": segment.tipo.value, "trabalhador_id": segment.trabalhador_id,
         "status_esperado": rotear(segment, TRABALHADORES, 0.75).status.value}
        for segment in segmentar(analyses)
    ]
    expected = [{key: doc[key] for key in ("pages", "tipo", "trabalhador_id", "status_esperado")}
                for doc in gold["documents"]]

    assert actual == expected
    absence_case = next(case for case in gold["cases"] if case["kind"] == "ausencia_documento")
    assert absence_case["ausencias_documentais"] == ["HOLERITE"]
    money_only = next(doc for doc in gold["documents"] if doc.get("horas_extras_valor") is not None)
    assert money_only["horas_extras_h"] is None and money_only["horas_extras_valor"] == 230.0


def test_holdout_congelado_permanece_intacto():
    hashes = {}
    for line in (FIXTURES / "holdout.sha256").read_text(encoding="ascii").splitlines():
        expected, filename = line.split("  ", 1)
        hashes[filename] = expected
    assert set(hashes) == {"corpus_holdout.pdf", "gabarito_holdout.json"}
    for filename, expected in hashes.items():
        actual = hashlib.sha256((FIXTURES / filename).read_bytes()).hexdigest()
        assert actual.lower() == expected.lower(), f"holdout alterado: {filename}"
