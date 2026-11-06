"""Base sintética de 100 trabalhadores: o gerador roda, é reproduzível e o motor bate com o gabarito."""
import json

import pymupdf as fitz
import pytest

from docrisk_core.ai.textlayer import analisar_texto
from docrisk_core.pipeline.routing import rotear
from docrisk_core.pipeline.segmentation import segmentar
from test_f3_regras import _gerador

TRABALHADORES = {f"T{i:03d}" for i in range(1, 101)}


@pytest.fixture(scope="module")
def lote_100(tmp_path_factory):
    arquivos = _gerador().gerar_parametrizado(100, tmp_path_factory.mktemp("lote_100"))
    gabarito = json.loads(arquivos["gabarito.json"].read_text(encoding="utf-8"))
    with fitz.open(arquivos["lote_100.pdf"]) as doc:
        textos = [p.get_text() for p in doc]
    return gabarito, textos


def test_gera_300_paginas_com_a_distribuicao_planejada(lote_100):
    gabarito, textos = lote_100
    assert len(textos) == 300 and gabarito["paginas"] == 300
    assert gabarito["distribuicao"] == {"normal": 70, "divergencia": 15, "ilegivel": 5,
                                        "faltante": 5, "reais": 5}
    assert set(gabarito["conciliacao"]) == TRABALHADORES
    # Trabalhadores além do T005 recebem nome genérico em todos os documentos (inclusive comprovante).
    assert "Favorecido: Trabalhador Fictício 100" in "".join(textos)


def test_mesma_semente_mesmo_gabarito(lote_100, tmp_path):
    gabarito, _ = lote_100
    outro = _gerador().gerar_parametrizado(100, tmp_path)
    assert json.loads(outro["gabarito.json"].read_text(encoding="utf-8")) == gabarito


def test_so_100_trabalhadores():
    with pytest.raises(ValueError):
        _gerador().gerar_parametrizado(50, None)


def test_motor_separa_e_classifica_conforme_gabarito(lote_100):
    gabarito, textos = lote_100
    segmentos = segmentar([analisar_texto(t) for t in textos])
    obtido = [(s.paginas, s.tipo.value, rotear(s, TRABALHADORES, 0.75).status.value) for s in segmentos]
    esperado = [(d["paginas"], d["tipo"], d["status_esperado"]) for d in gabarito["documentos"]]
    assert obtido == esperado
