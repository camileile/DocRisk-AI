"""F2 — ajuste manual de agrupamento (pipeline/revisao.py)."""
import pytest

from docrisk_core import db
from docrisk_core.ai.textlayer import TextLayerProvider
from docrisk_core.pipeline import revisao, worker
from docrisk_core.pipeline.revisao import RevisaoInvalida
from test_f2_worker import BETA, GAMA, HOLERITE, HOLERITE_ILEGIVEL, LOTE, banco, documentos, pdf, q  # noqa: F401


@pytest.fixture
def lote(banco):
    bid = worker.criar_lote(BETA, "CT-001", "lote.pdf", pdf(*LOTE))
    worker.processar_lote(bid, provedor=TextLayerProvider())
    return bid


def doc_por_paginas(bid, paginas):
    return next(d for d in documentos(bid) if d["paginas"] == paginas)


def ajustar(funcao, *args):
    with db.tx() as conn:
        return funcao(conn, *args)


def test_dividir_recalcula_campos_sem_copiar(lote):
    ponto = doc_por_paginas(lote, [3, 4])
    r = ajustar(revisao.dividir, ponto["id"], 1, "u-analista")
    assert r.documentos[0] == ponto["id"] and len(r.documentos) == 2

    p1, p2 = doc_por_paginas(lote, [3]), doc_por_paginas(lote, [4])
    assert p1["id"] == ponto["id"] and p2["id"] == r.documentos[1]
    assert '"horas_extras_h":null' in p1["campos_json"]  # a página 3 não tem total de horas
    assert '"horas_extras_h":12.0' in p2["campos_json"]  # o total estava só na página 4
    assert p1["tipo"] == "ESPELHO_PONTO" and p1["worker_id"] == "T001"
    assert p2["tipo"] == "DESCONHECIDO" and p2["worker_id"] == "T001"  # continuação sem título
    for d in (p1, p2):
        assert d["status"] == "REVISAO_HUMANA" and d["substitui_id"] is None and d["versao"] == 1
        assert d["revisado_por"] == "u-analista"
    assert "dividido na revisão" in p1["motivos_revisao"]
    assert f"a partir do documento #{ponto['id']}" in p2["motivos_revisao"]
    assert "Página(s) 1 do documento não recebida(s)" in p2["motivos_revisao"]  # a parte isolada fica incompleta
    assert r.pares_afetados == {("T001", "10/2026")}
    assert q("SELECT COUNT(*) AS n FROM doc_pages")[0]["n"] == 8  # nenhuma página duplicada ou perdida


def test_unir_desfaz_a_divisao(lote):
    ponto = doc_por_paginas(lote, [3, 4])
    r1 = ajustar(revisao.dividir, ponto["id"], 1)
    r2 = ajustar(revisao.unir_proximo, ponto["id"])
    assert r2.documentos == [ponto["id"]] and r2.removidos == [r1.documentos[1]]
    unido = doc_por_paginas(lote, [3, 4])
    assert unido["tipo"] == "ESPELHO_PONTO" and '"horas_extras_h":12.0' in unido["campos_json"]
    assert unido["status"] == "REVISAO_HUMANA" and "unidos" in unido["motivos_revisao"]
    assert q("SELECT COUNT(*) AS n FROM documents WHERE id = ?", r1.documentos[1])[0]["n"] == 0
    assert q("SELECT COUNT(*) AS n FROM doc_pages")[0]["n"] == 8


def test_unir_leva_pendencias_do_documento_absorvido(lote):
    nota, holerite = doc_por_paginas(lote, [6]), doc_por_paginas(lote, [7])
    with db.tx() as conn:
        conn.execute("INSERT INTO issues (contract_id, document_id, categoria, motivo, acao, status, created_at,"
                     " updated_at) VALUES ('CT-001', ?, 'ILEGIVEL', 'm', 'a', 'NOTIFICADA', 'x', 'x')",
                     (holerite["id"],))
    ajustar(revisao.unir_proximo, nota["id"])
    assert q("SELECT document_id FROM issues")[0]["document_id"] == nota["id"]
    unido = doc_por_paginas(lote, [6, 7])
    assert unido["tipo"] == "HOLERITE" and unido["worker_id"] == "T002"


def test_unir_sem_documento_contiguo(lote):
    ultimo = doc_por_paginas(lote, [8])
    with pytest.raises(RevisaoInvalida, match="contíguo") as exc:
        ajustar(revisao.unir_proximo, ultimo["id"])
    assert exc.value.conflito is True


def test_dividir_parametros_invalidos(lote):
    ponto = doc_por_paginas(lote, [3, 4])
    for posicao in (0, 2, True, "1"):
        with pytest.raises(RevisaoInvalida, match="apos_posicao") as exc:
            ajustar(revisao.dividir, ponto["id"], posicao)
        assert exc.value.conflito is False
    with pytest.raises(RevisaoInvalida, match="uma página"):
        ajustar(revisao.dividir, doc_por_paginas(lote, [5])["id"], 1)
    with pytest.raises(RevisaoInvalida, match="não encontrado"):
        ajustar(revisao.dividir, 9999, 1)


def test_documento_substituido_nao_pode_ser_ajustado(lote):
    ponto = doc_por_paginas(lote, [3, 4])
    with db.tx() as conn:
        conn.execute("UPDATE documents SET status = 'SUBSTITUIDO' WHERE id = ?", (ponto["id"],))
    with pytest.raises(RevisaoInvalida, match="substituído") as exc:
        ajustar(revisao.dividir, ponto["id"], 1)
    assert exc.value.conflito is True


def test_falha_desfaz_tudo(lote, monkeypatch):
    ponto = doc_por_paginas(lote, [3, 4])
    antes = documentos(lote)
    from docrisk_core.rules import conciliacao

    def quebra(*a):
        raise KeyError("erro simulado da F3")
    monkeypatch.setattr(conciliacao, "conciliar", quebra)
    with pytest.raises(KeyError):
        ajustar(revisao.dividir, ponto["id"], 1)
    assert documentos(lote) == antes  # transação desfeita


def test_conciliacao_refeita_para_pares_afetados(lote, monkeypatch):
    from docrisk_core.rules import conciliacao
    chamadas = []
    monkeypatch.setattr(conciliacao, "conciliar", lambda conn, c, w, comp: chamadas.append((c, w, comp)))
    ajustar(revisao.unir_proximo, doc_por_paginas(lote, [5])["id"])  # holerite T001 + anotação
    assert chamadas == [("CT-001", "T001", "10/2026")]


def test_documento_com_historico_de_versao_nao_e_unido(banco):
    b1 = worker.criar_lote(GAMA, "CT-002", "a.pdf", pdf(HOLERITE_ILEGIVEL.format(t="T101")))
    worker.processar_lote(b1, provedor=TextLayerProvider())
    b2 = worker.criar_lote(GAMA, "CT-002", "b.pdf", pdf(HOLERITE.format(t="T101", h="6,00"), LOTE[5]))
    worker.processar_lote(b2, provedor=TextLayerProvider())
    nova_versao = doc_por_paginas(b2, [1])
    assert nova_versao["substitui_id"] is not None
    with pytest.raises(RevisaoInvalida, match="histórico"):
        ajustar(revisao.unir_proximo, nova_versao["id"])
