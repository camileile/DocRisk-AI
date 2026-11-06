"""Portal contratante: snapshots, filtros, versões e isolamento entre empresas."""
import json

from fastapi.testclient import TestClient

from docrisk_core import db
from docrisk_core.api import app
from test_f2_worker import banco  # noqa: F401
from test_analyst_overview import _registrar_analise, _token


def publish(client, contract="CT-001", month="10/2026"):
    headers = _token("u-analista")
    draft = client.post("/api/reports", headers=headers,
                        json={"contract_id": contract, "competencia": month})
    assert draft.status_code == 201
    preview = client.get(f"/api/reports/{draft.json()['id']}/preview", headers=headers)
    result = client.post(f"/api/reports/{draft.json()['id']}/publish", headers=headers,
                         json={"conteudo_sha256": preview.json()["conteudo_sha256"]})
    assert result.status_code == 200
    return result.json()["id"]


def test_publication_is_source_of_truth_and_filters_match_reports(banco):
    with db.tx() as conn:
        _registrar_analise(conn, "CT-001", "T001", "10/2026", "ANALISADA", "DIVERGENCIA_A_VERIFICAR", 4)
        _registrar_analise(conn, "CT-001", "T002", "10/2026", "ANALISADA", "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS", 0)
        _registrar_analise(conn, "CT-001", "T003", "10/2026", "ANALISADA", "DADOS_INSUFICIENTES")
        _registrar_analise(conn, "CT-001", "T004", "10/2026", "BLOQUEADA_PENDENCIA", "NAO_AVALIADO")
        _registrar_analise(conn, "CT-001", "T001", "09/2026", "ANALISADA", "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS", 0)
    h = _token("u-gestor-alfa")
    with TestClient(app) as client:
        october = publish(client)
        publish(client, month="09/2026")
        # Mudança interna não publicada não pode aparecer no dashboard externo.
        with db.tx() as conn:
            conn.execute("UPDATE analyses SET resultado_json=? WHERE competencia='10/2026'",
                         (json.dumps({"tipo": "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS"}),))
        r = client.get("/api/client/overview", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["filtros"]["competencias"] == ["10/2026", "09/2026"]
        assert data["filtros"]["competencia_selecionada"] == "10/2026"
        assert data["resumo"] == {
            "contratos": 2, "contratos_com_parecer": 1, "trabalhadores": 5,
            "analisados": 2, "divergencias": 1, "dados_insuficientes": 1,
            "nao_avaliados": 2, "taxa_divergencias": 0.5, "cobertura": 0.4,
        }
        gamma = next(c for c in data["contratos"] if c["id"] == "CT-002")
        assert gamma["parecer_id"] is None and gamma["resumo"] is None
        beta = next(c for c in data["contratos"] if c["id"] == "CT-001")
        assert beta["parecer_id"] == october
        # Overview não carrega detalhes documentais nem campos internos.
        assert "conteudo_json" not in r.text and "worker_id" not in r.text
        for params, expected in [
            ({"fornecedora_id": "ORG-BETA", "competencia": "09/2026"}, 1),
            ({"contract_id": "CT-002"}, 0),
            ({"fornecedora_id": "ORG-GAMA", "contract_id": "CT-001"}, 0),
            ({"competencia": "08/2026"}, 0),
        ]:
            result = client.get("/api/client/reports", headers=h, params=params)
            assert result.status_code == 200 and len(result.json()) == expected
        september = client.get("/api/client/overview", headers=h, params={"competencia": "09/2026"}).json()
        assert september["resumo"]["cobertura"] == 0.2
        assert september["resumo"]["taxa_divergencias"] == 0.0
        gamma = client.get("/api/client/overview", headers=h, params={"fornecedora_id": "ORG-GAMA"}).json()
        assert gamma["resumo"]["contratos_com_parecer"] == 0
        assert gamma["resumo"]["taxa_divergencias"] is None
        assert gamma["resumo"]["cobertura"] is None
        assert gamma["filtros"]["contratos"] == [{"id": "CT-002", "nome": "Facilities — Alfa × Gama"}]


def test_new_publication_replaces_old_version_without_double_counting(banco):
    with TestClient(app) as client:
        original = publish(client)
        with db.tx() as conn:
            _registrar_analise(conn, "CT-001", "T001", "10/2026", "ANALISADA", "DIVERGENCIA_A_VERIFICAR", 2)
        current = publish(client)
        # Rascunho de uma competência futura não pode criar mês no filtro.
        client.post("/api/reports", headers=_token("u-analista"),
                    json={"contract_id": "CT-001", "competencia": "11/2026"})
        h = _token("u-gestor-alfa")
        reports = client.get("/api/client/reports", headers=h).json()
        assert [r["id"] for r in reports] == [current]
        assert original != current and reports[0]["versao"] == 2
        assert set(reports[0]) == {"id", "contract_id", "competencia", "versao", "status", "conteudo_json", "publicado_em"}
        assert "observacoes" not in reports[0] and "autor_id" not in reports[0]
        overview = client.get("/api/client/overview", headers=h).json()
        assert overview["filtros"]["competencias"] == ["10/2026"]
        assert overview["resumo"]["trabalhadores"] == 5
        assert overview["resumo"]["divergencias"] == 1
        assert overview["resumo"]["contratos_com_parecer"] == 1


def test_shared_supplier_does_not_expose_other_contractor(banco):
    with db.tx() as conn:
        conn.execute("INSERT INTO organizations VALUES ('ORG-EXTERNA', 'Empresa sigilosa', 'CONTRATANTE')")
        conn.execute("INSERT INTO contracts (id,nome,contratante_id,fornecedora_id,bernhoeft_id) "
                     "VALUES ('CT-SECRETO','Contrato sigiloso','ORG-EXTERNA','ORG-BETA','ORG-BH')")
        conn.execute("INSERT INTO users (id,nome,org_id,role,token) "
                     "VALUES ('u-externo','Externo','ORG-EXTERNA','GESTOR_CONTR','teste-externo')")
        conn.execute("INSERT INTO reports (contract_id,competencia,versao,status,conteudo_json,autor_id,created_at,publicado_em) "
                     "VALUES ('CT-SECRETO','12/2026',1,'APROVADO_PUBLICADO','{}','u-analista',?,?)", (db.agora(), db.agora()))
    with TestClient(app) as client:
        publish(client)
        h = _token("u-gestor-alfa")
        for endpoint in ("/api/client/overview", "/api/client/reports"):
            response = client.get(endpoint, headers=h, params={"fornecedora_id": "ORG-BETA"})
            assert response.status_code == 200
            assert "CT-SECRETO" not in response.text and "12/2026" not in response.text
            outside = client.get(endpoint, headers=h, params={"contract_id": "CT-SECRETO"})
            assert outside.status_code == 200
            if endpoint.endswith("overview"):
                assert outside.json()["resumo"]["contratos"] == 0
            else:
                assert outside.json() == []
        external = client.get("/api/client/reports", headers=_token("u-externo")).json()
        assert len(external) == 1 and external[0]["contract_id"] == "CT-SECRETO"
        # Organização sem contrato recebe escopo vazio e taxas indisponíveis.
        with db.tx() as conn:
            conn.execute("INSERT INTO organizations VALUES ('ORG-VAZIA','Sem contratos','CONTRATANTE')")
            conn.execute("UPDATE users SET org_id='ORG-VAZIA' WHERE id='u-externo'")
        empty = client.get("/api/client/overview", headers=_token("u-externo")).json()
        assert empty["filtros"]["fornecedoras"] == []
        assert empty["resumo"]["cobertura"] is None


def test_roles_validation_and_no_raw_document_access(banco):
    with TestClient(app) as client:
        for endpoint in ("/api/client/overview", "/api/client/reports"):
            assert client.get(endpoint).status_code == 401
            for uid in ("u-admin", "u-analista", "u-gestor-beta", "u-oper-beta", "u-oper-gama"):
                assert client.get(endpoint, headers=_token(uid)).status_code == 403
            assert client.get(endpoint, headers=_token("u-gestor-alfa"), params={"competencia": "13/2026"}).status_code == 422
        h = _token("u-gestor-alfa")
        for endpoint in ("/api/reports", "/api/documents", "/api/analyses", "/api/issues", "/api/search?q=horas", "/api/bernhoeft/metrics", "/api/audit"):
            assert client.get(endpoint, headers=h).status_code == 403, endpoint
        assert client.post("/api/reports", headers=h, json={"contract_id": "CT-001", "competencia": "10/2026"}).status_code == 403
        # Um papel associado indevidamente a uma fornecedora também não recebe documentos.
        with db.tx() as conn:
            conn.execute("UPDATE users SET org_id='ORG-BETA' WHERE id='u-gestor-alfa'")
        assert client.get("/api/client/reports", headers=h).json() == []
