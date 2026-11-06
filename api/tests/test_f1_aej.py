"""AEJ de ponta a ponta pela API: envio, mapeamento do vínculo, versões, revisão manual e acesso."""
from fastapi.testclient import TestClient

from docrisk_core.api import app
from test_aej import example_aej
from test_f1_revision import _api_lote, _headers
from test_f2_worker import banco, q  # noqa: F401  (fixture)

#: AEJ sem registro de compensação e com saída às 19h numa jornada de 8 h: 2 h de excedente.
AEJ_LIMPO = (example_aej()
             .replace(b"07|1|3|2026-10-01|30|1\r\n", b"")
             .replace(b"99|1|1|1|1|4|1|1|1", b"99|1|1|1|1|4|1|0|1")
             .replace(b"2026-10-01T17:00:00-0300|1|S", b"2026-10-01T19:00:00-0300|1|S"))


def _enviar(client, data, nome="jornada.aej"):
    r = client.post("/api/supplier/batches", headers=_headers("u-oper-beta"),
                    data={"contract_id": "CT-001"}, files={"file": (nome, data)})
    assert r.status_code == 202, r.text
    return r.json()["batch_id"]


def _mapear(client, worker="T001", link="1", user="u-analista"):
    return client.put(f"/api/contracts/CT-001/aej-mappings/{link}", headers=_headers(user),
                      json={"worker_id": worker})


def _espelhos_vigentes(worker):
    return q("SELECT id, batch_id, versao, campos_json FROM documents WHERE tipo='ESPELHO_PONTO' "
             "AND worker_id=? AND competencia='10/2026' AND status<>'SUBSTITUIDO'", worker)


def test_aej_vira_espelho_sem_ia_e_so_concilia_depois_do_mapeamento(banco):
    with TestClient(app) as client:
        batch_id = _enviar(client, AEJ_LIMPO)
        [lote] = q("SELECT status, total_pages FROM batches WHERE id=?", batch_id)
        assert (lote["status"], lote["total_pages"]) == ("CONCLUIDO", 0)
        assert q("SELECT COUNT(*) AS n FROM pages WHERE batch_id=?", batch_id)[0]["n"] == 0
        [doc] = q("SELECT * FROM documents WHERE batch_id=?", batch_id)
        assert (doc["tipo"], doc["worker_id"], doc["status"]) == ("ESPELHO_PONTO", None, "REVISAO_HUMANA")

        assert _mapear(client).status_code == 200
        [doc] = q("SELECT status, campos_json FROM documents WHERE batch_id=?", batch_id)
        assert doc["status"] == "APTO" and '"horas_extras_h": 2.0' in doc["campos_json"]
        [analise] = q("SELECT status FROM analyses WHERE worker_id='T001' AND atual=1")
        assert analise["status"] == "BLOQUEADA_PENDENCIA"  # falta o holerite do T001 nesta base


def test_mapeamento_substitui_o_espelho_em_pdf_do_mesmo_trabalhador(banco):
    _api_lote()  # espelho em PDF do T001 (12 h) já vigente
    [pdf_ponto] = _espelhos_vigentes("T001")
    with TestClient(app) as client:
        batch_id = _enviar(client, AEJ_LIMPO)
        assert _mapear(client).status_code == 200
    [vigente] = _espelhos_vigentes("T001")  # nunca dois espelhos vigentes para o mesmo par
    assert vigente["batch_id"] == batch_id and vigente["versao"] == pdf_ponto["versao"] + 1
    assert q("SELECT status FROM documents WHERE id=?", pdf_ponto["id"])[0]["status"] == "SUBSTITUIDO"


def test_dois_aej_mapeados_depois_deixam_so_o_mais_recente_vigente(banco):
    with TestClient(app) as client:
        _enviar(client, AEJ_LIMPO, "outubro-v1.aej")
        segundo = _enviar(client, AEJ_LIMPO.replace(b"2026-10-01T19:00:00", b"2026-10-01T18:00:00"),
                          "outubro-v2.aej")
        assert _mapear(client).status_code == 200
    [vigente] = _espelhos_vigentes("T001")
    assert vigente["batch_id"] == segundo and '"horas_extras_h": 1.0' in vigente["campos_json"]


def test_compensacao_exige_revisao_manual_com_justificativa(banco):
    with TestClient(app) as client:
        batch_id = _enviar(client, example_aej())  # tem registro 07 (ausência/compensação)
        assert _mapear(client).status_code == 200
        [doc] = q("SELECT id, status FROM documents WHERE batch_id=?", batch_id)
        assert doc["status"] == "REVISAO_HUMANA"
        url = f"/api/documents/{doc['id']}/aej-review"
        assert client.patch(url, headers=_headers(), json={"horas_extras_h": 0.5}).status_code == 422
        assert client.patch(f"/api/documents/{doc['id']}/review", headers=_headers(),
                            json={"acao": "aprovar"}).status_code == 409  # tela própria do AEJ
        r = client.patch(url, headers=_headers(), json={"horas_extras_h": 0.5, "justificativa": "conferido"})
        assert r.status_code == 200 and r.json()["status"] == "APTO"
        detalhe = client.get(f"/api/documents/{doc['id']}", headers=_headers()).json()["aej"]
        assert detalhe["calculation_status"] == "HUMAN_CONFIRMED"
        assert detalhe["human_review"]["reviewer_id"] == "u-analista"


def test_permissoes_do_aej(banco):
    with TestClient(app) as client:
        batch_id = _enviar(client, AEJ_LIMPO)
        assert _mapear(client, user="u-oper-beta").status_code == 403  # só a Bernhoeft mapeia
        assert _mapear(client, worker="T101").status_code == 422  # trabalhador de outro contrato
        assert _mapear(client).status_code == 200
        assert _mapear(client, worker="T001", link="2").status_code == 409  # T001 já está no vínculo 1
        source = f"/api/batches/{batch_id}/source"
        assert client.get(source, headers=_headers("u-oper-beta")).content == AEJ_LIMPO
        assert client.get(source, headers=_headers("u-gestor-alfa")).status_code == 403
        assert client.get(source, headers=_headers("u-oper-gama")).status_code == 404
        [doc] = q("SELECT id FROM documents WHERE batch_id=?", batch_id)
        fornecedora = client.get(f"/api/documents/{doc['id']}", headers=_headers("u-oper-beta")).json()
        assert "days" not in (fornecedora.get("aej") or {})  # cálculo detalhado só para a Bernhoeft
