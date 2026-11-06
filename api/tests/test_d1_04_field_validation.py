import math

import pytest
from pydantic import ValidationError

from docrisk_core.contracts import AnalisePagina, CamposPagina, StatusDocumento, normalizar_duracao
from docrisk_core.ai.textlayer import analisar_texto
from docrisk_core.pipeline.routing import rotear
from docrisk_core.pipeline.segmentation import segmentar


@pytest.mark.parametrize("valor, esperado", [
    ("8h30", 8.5),
    ("8 h 30 min", 8.5),
    ("8:30", 8.5),
    ("8,5 h", 8.5),
    ("8h", 8.0),
    (8.5, 8.5),
])
def test_converte_duracoes_com_unidade_e_minutos_validos(valor, esperado):
    assert normalizar_duracao(valor) == esperado
    assert CamposPagina(horas_extras_h=valor).horas_extras_h == esperado


@pytest.mark.parametrize("valor", [
    -1,
    float("nan"),
    float("inf"),
    float("-inf"),
    "NaN",
    "Infinity",
    "R$ 230,00",
    "8:",
    "8h75",
    "8:75",
])
def test_campos_pagina_rejeita_horas_invalidas(valor):
    with pytest.raises(ValidationError):
        CamposPagina(horas_extras_h=valor)


@pytest.mark.parametrize("campo", ["horas_extras_h", "horas_extras_valor", "valor_liquido", "valor_pago"])
@pytest.mark.parametrize("valor", [float("nan"), float("inf"), float("-inf")])
def test_campos_pagina_rejeita_nao_finitos_em_todos_os_numericos(campo, valor):
    with pytest.raises(ValidationError):
        CamposPagina(**{campo: valor})


@pytest.mark.parametrize("campo", ["horas_extras_h", "horas_extras_valor", "valor_liquido", "valor_pago"])
def test_analise_anula_numero_nao_finito_e_registra_aviso(campo):
    analise = AnalisePagina.model_validate({"campos": {campo: float("inf")}})
    assert getattr(analise.campos, campo) is None
    assert any(campo in aviso and "finito" in aviso for aviso in analise.avisos_validacao)


def test_objeto_campos_malformado_e_rejeitado():
    with pytest.raises(ValidationError):
        AnalisePagina.model_validate({"campos": None})


def test_textlayer_converte_8h30_e_separa_valor_monetario():
    ponto = analisar_texto("ESPELHO DE PONTO\nEntrada Saída\nTOTAL DE HORAS EXTRAS: 8h30")
    assert ponto.campos.horas_extras_h == 8.5

    holerite_horas = analisar_texto(
        "HOLERITE\nProventos\nHoras extras 50% | Ref.: 8h30 | R$ 160,00")
    assert holerite_horas.campos.horas_extras_h == 8.5
    assert holerite_horas.campos.horas_extras_valor == 160.0

    holerite = analisar_texto("HOLERITE\nProventos\nHoras extras 50% | R$ 230,00")
    assert holerite.campos.horas_extras_h is None
    assert holerite.campos.horas_extras_valor == 230.0


def test_duracao_incompleta_vai_para_revisao_humana():
    analise = analisar_texto("ESPELHO DE PONTO\nEntrada Saída\nTOTAL DE HORAS EXTRAS: 8:75")
    assert analise.campos.horas_extras_h is None
    assert analise.avisos_validacao

    analise = AnalisePagina.model_validate({
        "tipo": "HOLERITE", "trabalhador_id": "T001", "competencia": "10/2026",
        "confianca_tipo": 0.99,
        "campos": {"horas_extras_h": "R$ 230,00", "horas_extras_valor": 230.0},
    })
    [segmento] = segmentar([analise], [1])
    rota = rotear(segmento, {"T001"}, limiar_confianca=0.75)
    assert rota.status is StatusDocumento.REVISAO_HUMANA
    assert any("horas_extras_h" in motivo for motivo in rota.motivos_revisao)


def test_tolerancia_float_fica_limitada_a_numeros_finitos():
    assert math.isfinite(normalizar_duracao("8h30"))
