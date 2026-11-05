"""F2 — segmentação (função pura) e roteamento."""
import copy

import pytest

from docrisk_core.ai.textlayer import analisar_texto
from docrisk_core.contracts import (
    AnalisePagina as A, CamposPagina, SegmentoDocumento, StatusDocumento as S, TipoDocumento as T,
)
from docrisk_core.documents import group_pages
from docrisk_core.pipeline.routing import rotear
from docrisk_core.pipeline.segmentation import segmentar

CONTRATO = {"T001", "T002", "T003"}


def pg(tipo="DESCONHECIDO", x=None, de=None, trab=None, comp=None, inicio=None, legivel=True,
       qualidade=0.9, conf=0.9, **campos):
    return A(tipo=tipo, pagina_x=x, pagina_de=de, trabalhador_id=trab, competencia=comp,
             inicio_documento=(x == 1) if inicio is None else inicio, legivel=legivel,
             qualidade=qualidade, confianca_tipo=conf if tipo != "DESCONHECIDO" else 0.3,
             campos=CamposPagina(**campos), texto="...")


def paginas(segs):
    return [s.paginas for s in segs]


# --- segmentação -----------------------------------------------------------
def test_lista_vazia():
    assert segmentar([]) == []


def test_pagina_unica():
    [s] = segmentar([pg("HOLERITE", 1, 1, "T001", "10/2026", horas_extras_h=8)])
    assert s.paginas == [1] and s.tipo is T.HOLERITE and s.campos.horas_extras_h == 8
    assert s.alertas == [] and s.paginas_faltantes == []


def test_multipagina_continuacao_sem_cabecalho():
    segs = segmentar([pg("ESPELHO_PONTO", 1, 2, "T001", "10/2026"),
                      pg(x=2, de=2, horas_extras_h=12)])
    assert paginas(segs) == [[1, 2]]
    s = segs[0]
    assert s.tipo is T.ESPELHO_PONTO and s.trabalhador_id == "T001" and s.campos.horas_extras_h == 12
    assert s.alertas == []


def test_pagina_1_abre_novo_documento():
    segs = segmentar([pg("HOLERITE", 1, 1, "T001", "10/2026"), pg("HOLERITE", 1, 1, "T002", "10/2026")])
    assert paginas(segs) == [[1], [2]]


def test_mudanca_de_tipo():
    segs = segmentar([pg("ESPELHO_PONTO", trab="T001", inicio=True), pg("HOLERITE", trab="T001", inicio=False)])
    assert paginas(segs) == [[1], [2]]


def test_mudanca_de_trabalhador():
    segs = segmentar([pg("ESPELHO_PONTO", trab="T001", inicio=True), pg("ESPELHO_PONTO", trab="T002", inicio=False)])
    assert paginas(segs) == [[1], [2]]


def test_mudanca_de_competencia():
    segs = segmentar([pg("ESPELHO_PONTO", trab="T001", comp="09/2026", inicio=True),
                      pg("ESPELHO_PONTO", trab="T001", comp="10/2026", inicio=False)])
    assert paginas(segs) == [[1], [2]]


def test_pagina_desconhecida_vira_grupo_proprio_com_alerta():
    segs = segmentar([pg("HOLERITE", 1, 1, "T001", "10/2026"), pg(), pg("ESPELHO_PONTO", 1, 1, "T005")])
    assert paginas(segs) == [[1], [2], [3]]
    assert segs[1].tipo is T.DESCONHECIDO and "fronteira incerta" in segs[1].alertas[0]
    assert segs[1].confianca <= 0.3


def test_pagina_faltante_comprovada():
    [s] = segmentar([pg("ESPELHO_PONTO", 1, 3, "T001", "10/2026"), pg(x=3, de=3)])
    assert s.paginas == [1, 2] and s.paginas_faltantes == [2]


def test_documento_que_termina_antes_do_total():
    segs = segmentar([pg("ESPELHO_PONTO", 1, 2, "T003", "10/2026"), pg("HOLERITE", 1, 1, "T003", "10/2026")])
    assert paginas(segs) == [[1], [2]] and segs[0].paginas_faltantes == [2]


def test_falta_sem_numeracao_completa_e_so_incerteza():
    [s] = segmentar([pg("ESPELHO_PONTO", trab="T001", inicio=True, de=None),
                     pg(x=3, de=3, trab="T001")])
    assert s.paginas_faltantes == []
    assert any("impede confirmar" in a for a in s.alertas)


def test_informacao_contraditoria_na_continuacao():
    segs = segmentar([pg("ESPELHO_PONTO", 1, 2, "T001", "10/2026"), pg("ESPELHO_PONTO", 2, 2, "T009", "10/2026")])
    assert paginas(segs) == [[1], [2]]
    assert "não confere" in segs[1].alertas[0] and segs[1].confianca <= 0.6


def test_valores_divergentes_nao_sao_escolhidos():
    [s] = segmentar([pg("ESPELHO_PONTO", 1, 2, "T001", horas_extras_h=10), pg(x=2, de=2, horas_extras_h=12)])
    assert s.campos.horas_extras_h is None and any("divergentes" in a for a in s.alertas)


def test_reproduzivel_e_nao_altera_entrada():
    entrada = [pg("ESPELHO_PONTO", 1, 2, "T001", "10/2026"), pg(x=2, de=2), pg(), pg("HOLERITE", 1, 1, "T001")]
    copia = copy.deepcopy(entrada)
    assert segmentar(entrada) == segmentar(entrada)
    assert entrada == copia


def test_ordens_do_lote_sao_preservadas():
    segs = segmentar([pg("HOLERITE", 1, 1, "T001"), pg("HOLERITE", 1, 1, "T002")], ordens=[7, 8])
    assert paginas(segs) == [[7], [8]]
    with pytest.raises(ValueError):
        segmentar([pg()], ordens=[1, 2])


def test_paginas_ilegiveis_listadas():
    [s] = segmentar([pg("HOLERITE", 1, 1, "T002", "10/2026", legivel=False, qualidade=0.2)], ordens=[7])
    assert s.paginas_ilegiveis == [7]


# --- regressão dos 4 bugs do sprint01 (documents.group_pages) ---------------
def _sprint01(textos):
    paginas_ = [{"page_number": i + 1, "text": t, "document_type": "X"} for i, t in enumerate(textos)]
    from docrisk_core.documents import classify
    for p in paginas_:
        p["document_type"] = classify(p["text"])[0]
    return group_pages(paginas_)


PONTO_P1 = "ESPELHO DE PONTO\nMatrícula: T001\nCompetência: 10/2026\nEntrada 08:00\n" + "linha\n" * 60 + "Página 1 de 2"
PONTO_P2 = "Matrícula: T001\n" + "16/10 08:00 12:00 13:00 17:00\n" * 40 + "TOTAL DE HORAS EXTRAS: 12,00 h\nPágina 2 de 2"


def test_bug1_revisao_nao_e_forcada_para_todos():
    assert all(g["needs_review"] for g in _sprint01([PONTO_P1]))  # comportamento antigo
    [s] = segmentar([analisar_texto(PONTO_P1.replace("Página 1 de 2", "Página 1 de 1"))])
    assert s.alertas == [] and rotear(s, CONTRATO, 0.75).status is S.APTO


def test_bug2_numeracao_no_rodape_de_pagina_longa():
    # Antes: continuação só era vista nos primeiros 450 caracteres.
    p2_titulada = "ESPELHO DE PONTO\n" + PONTO_P2
    assert [g["pages"] for g in _sprint01([PONTO_P1, p2_titulada])] == [[1], [2]]
    segs = segmentar([analisar_texto(PONTO_P1), analisar_texto(p2_titulada)])
    assert paginas(segs) == [[1, 2]]


def test_bug3_pagina_desconhecida_nao_gruda_no_documento_anterior():
    nota = "anotações — conferir com o RH\nligar para o setor pessoal sobre o lote de outubro"
    holerite = "HOLERITE\nMatrícula: T001\nProventos\nSalário base R$ 1.800,00\nPágina 1 de 1"
    assert [g["pages"] for g in _sprint01([holerite, nota])] == [[1, 2]]  # antes: grudava
    segs = segmentar([analisar_texto(holerite), analisar_texto(nota)])
    assert paginas(segs) == [[1], [2]] and segs[1].tipo is T.DESCONHECIDO


def test_bug4_troca_de_trabalhador_em_pagina_de_continuacao():
    outro = "Página 2 de 2\nMatrícula: T002\nCompetência: 10/2026\nTOTAL DE HORAS EXTRAS: 3,00 h"
    p1_curta = "ESPELHO DE PONTO\nMatrícula: T001\nCompetência: 10/2026\nEntrada 08:00\nPágina 1 de 2"
    assert [g["pages"] for g in _sprint01([p1_curta, outro])] == [[1, 2]]  # antes: T001 e T002 juntos
    segs = segmentar([analisar_texto(p1_curta), analisar_texto(outro)])
    assert paginas(segs) == [[1], [2]] and segs[1].alertas


# --- roteamento -----------------------------------------------------------
def seg(tipo=T.HOLERITE, trab="T001", comp="10/2026", conf=0.9, ileg=(), falt=(), alertas=()):
    return SegmentoDocumento(paginas=[1], tipo=tipo, trabalhador_id=trab, competencia=comp, confianca=conf,
                             campos=CamposPagina(), paginas_ilegiveis=list(ileg),
                             paginas_faltantes=list(falt), alertas=list(alertas))


def test_apto():
    r = rotear(seg(), CONTRATO, 0.75)
    assert r.status is S.APTO and not r.motivos_pendencia and not r.motivos_revisao


def test_ilegivel_em_foco_e_pendencia_objetiva():
    r = rotear(seg(ileg=[7], conf=0.6), CONTRATO, 0.75)
    assert r.status is S.PENDENTE_CORRECAO and "7" in r.motivos_pendencia[0]


def test_incompleto_em_foco_e_pendencia():
    r = rotear(seg(T.ESPELHO_PONTO, falt=[2]), CONTRATO, 0.75)
    assert r.status is S.PENDENTE_CORRECAO and "não recebida" in r.motivos_pendencia[0]


def test_desconhecido_vai_para_revisao():
    r = rotear(seg(T.DESCONHECIDO, trab=None, comp=None, conf=0.3), CONTRATO, 0.75)
    assert r.status is S.REVISAO_HUMANA and "não identificado" in r.motivos_revisao[0]


def test_associacao_incerta_vai_para_revisao():
    assert rotear(seg(trab=None), CONTRATO, 0.75).status is S.REVISAO_HUMANA
    r = rotear(seg(trab="T999"), CONTRATO, 0.75)
    assert r.status is S.REVISAO_HUMANA and "não cadastrado" in r.motivos_revisao[0]
    assert rotear(seg(comp=None), CONTRATO, 0.75).status is S.REVISAO_HUMANA


def test_nao_prioritario_nao_gera_pendencia():
    r = rotear(seg(T.CONTRATO, trab=None, comp=None, falt=[2]), CONTRATO, 0.75)
    assert r.status is S.REVISAO_HUMANA and r.motivos_pendencia == []
    assert rotear(seg(T.CONTRATO, trab=None, comp=None), CONTRATO, 0.75).status is S.APTO


def test_baixa_confianca_ou_alerta_e_incerteza_nao_pendencia():
    assert rotear(seg(conf=0.5), CONTRATO, 0.75).status is S.REVISAO_HUMANA
    r = rotear(seg(alertas=["Página 2: fronteira incerta"]), CONTRATO, 0.75)
    assert r.status is S.REVISAO_HUMANA and r.motivos_pendencia == []
