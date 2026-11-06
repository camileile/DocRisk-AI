"""Gabarito manual do pequeno corpus visual Gemini; não chama a API."""
import importlib.util
import json
from pathlib import Path

import pymupdf as fitz

REPO = Path(__file__).resolve().parents[2]
GABARITO = REPO / "docs" / "GABARITO_AVALIACAO_GEMINI.json"


def _gerador():
    caminho = REPO / "api" / "scripts" / "gerar_lote_demo.py"
    spec = importlib.util.spec_from_file_location("gerar_lote_demo_visual", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_gabarito_visual_manual_cobre_e_confere_com_as_16_paginas(tmp_path):
    gabarito_visual = json.loads(GABARITO.read_text(encoding="utf-8"))
    assert "manualmente" in gabarito_visual["origem"].lower()
    rotulos = gabarito_visual["pages"]
    assert [item["page"] for item in rotulos] == list(range(1, 17))

    arquivos = _gerador().gerar(tmp_path / "lote")
    pdf = fitz.open(arquivos["lote_demo.pdf"])
    try:
        assert pdf.page_count == len(rotulos)
    finally:
        pdf.close()

    gerado = json.loads(arquivos["gabarito.json"].read_text(encoding="utf-8"))
    por_pagina = {pagina: documento for documento in gerado["documentos"]
                  for pagina in documento["paginas"]}
    for item in rotulos:
        doc = por_pagina[item["page"]]
        esperado = item["expected"]
        assert esperado["tipo"] == doc["tipo"], item["page"]
        assert esperado["trabalhador_id"] == doc["trabalhador_id"], item["page"]
        assert esperado["competencia"] == doc["competencia"], item["page"]

    assert rotulos[6]["expected"]["legivel"] is False  # corpo borrado
    assert rotulos[12]["expected"]["campos"]["horas_extras_h"] is None
    assert rotulos[12]["expected"]["campos"]["horas_extras_valor"] == 230.0
