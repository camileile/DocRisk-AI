"""Revisão do Admin: gestão apenas, auditoria segregada e cadastro consistente."""
from fastapi.testclient import TestClient
from docrisk_core import config, db
from docrisk_core.api import app
from test_f2_worker import banco  # noqa: F401
from test_f1_security import create_batch_and_page, headers


def test_admin_management_only_even_with_known_document_ids(banco):
    batch, page = create_batch_and_page()
    with db.tx() as conn:
        doc = conn.execute("INSERT INTO documents (batch_id,contract_id,tipo,status,confianca,created_at,updated_at) "
                           "VALUES (?,'CT-001','HOLERITE','APTO',1,?,?)", (batch, db.agora(), db.agora())).lastrowid
        report = conn.execute("INSERT INTO reports (contract_id,competencia,versao,status,autor_id,created_at) "
                              "VALUES ('CT-001','10/2026',1,'RASCUNHO','u-analista',?)", (db.agora(),)).lastrowid
    with TestClient(app) as client:
        h = headers("u-admin")
        for path in ["/api/documents", f"/api/documents/{doc}", f"/api/documents/{doc}/anonimizado",
                     "/api/batches", f"/api/batches/{batch}",
                     f"/api/batches/{batch}/source", f"/api/batches/{batch}/documents", f"/api/pages/{page}/image",
                     "/api/analyses", "/api/issues", "/api/reports", f"/api/reports/{report}/preview",
                     "/api/search?q=holerite", "/api/contracts/CT-001/aej-mappings"]:
            assert client.get(path, headers=h).status_code == 403, path
        assert client.post(f"/api/batches/{batch}/reprocess", headers=h).status_code == 403
        assert client.patch(f"/api/documents/{doc}/review", headers=h, json={"acao": "aprovar"}).status_code == 403
        for path in ["/api/admin/registry", "/api/admin/overview", "/api/bernhoeft/metrics", "/api/audit"]:
            assert client.get(path, headers=h).status_code == 200, path
        assert client.get(f"/api/documents/{doc}", headers=headers("u-analista")).status_code == 200


def test_audit_scopes_contract_events_before_limit_even_for_shared_supplier(banco):
    own, _ = create_batch_and_page()
    with db.tx() as conn:
        conn.execute("INSERT INTO organizations VALUES ('AUDITORA-EXT','Outra auditora','BERNHOEFT')")
        conn.execute("INSERT INTO contracts (id,nome,contratante_id,fornecedora_id,bernhoeft_id) "
                     "VALUES ('CT-EXT','Externo','ORG-ALFA','ORG-BETA','AUDITORA-EXT')")
    external, _ = create_batch_and_page("CT-EXT")
    with db.tx() as conn:
        sql = "INSERT INTO audit (org_id,acao,alvo,resultado,instante) VALUES (?,?,?,'OK',?)"
        conn.execute(sql, ("ORG-BH", "USUARIO_CRIADO", "u-local", db.agora()))
        conn.execute(sql, ("ORG-BETA", "LOTE_ENVIADO", str(own), db.agora()))
        conn.executemany(sql, [("ORG-BETA", "LOTE_ENVIADO", str(external), db.agora())] * 501)
        conn.execute(sql, ("DOCRISK", "AUDITORA_CRIADA", "externa", db.agora()))
        conn.execute(sql, ("AUDITORA-EXT", "USUARIO_CRIADO", "u-externo", db.agora()))
    with TestClient(app) as client:
        rows = client.get("/api/audit", headers=headers("u-admin")).json()
        assert [(r["acao"], r["alvo"]) for r in rows] == [("LOTE_ENVIADO", str(own)), ("USUARIO_CRIADO", "u-local")]


def test_admin_counts_registered_company_without_contract_and_rejects_blank_names(banco, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    with TestClient(app) as client:
        h = headers("u-admin")
        company = client.post("/api/admin/companies", headers=h, json={"tipo": "CONTRATANTE", "nome": " Cliente sem contrato "})
        assert company.status_code == 201
        assert company.json()["nome"] == "Cliente sem contrato"
        company_id = company.json()["id"]
        overview = client.get("/api/admin/overview", headers=h).json()
        assert overview["contratantes"] == 2
        filtered = client.get("/api/admin/overview", headers=h, params={"contratante_id": company_id}).json()
        assert filtered["contratantes"] == 1 and filtered["fornecedoras"] == 0 and filtered["contratos_ativos"] == 0
        for path, payload in [
            ("/api/admin/companies", {"tipo": "CONTRATANTE", "nome": "  "}),
            ("/api/admin/contracts", {"contratante_id": "ORG-ALFA", "fornecedora_id": "ORG-BETA", "nome": "   "}),
            ("/api/admin/users", {"nome": "  ", "org_id": "ORG-BH", "papel": "ANALISTA_BH"}),
        ]:
            assert client.post(path, headers=h, json=payload).status_code == 422
