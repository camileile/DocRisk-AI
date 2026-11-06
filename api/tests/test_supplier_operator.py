"""Validação focada do operador: consultas da empresa e correção de outro remetente."""
from fastapi.testclient import TestClient
from docrisk_core import db
from docrisk_core.api import app
from test_f2_worker import banco, pdf, HOLERITE  # noqa: F401
from test_f1_security import create_batch_and_page, headers


def test_shared_document_filters_versions_and_internal_permissions(banco):
    batch, _ = create_batch_and_page()
    with db.tx() as conn:
        doc = conn.execute(
            "INSERT INTO documents (batch_id,contract_id,tipo,worker_id,competencia,status,confianca,versao,created_at,updated_at) "
            "VALUES (?,'CT-001','HOLERITE','T001','10/2026','REVISAO_HUMANA',0.4,1,?,?)",
            (batch, db.agora(), db.agora())).lastrowid
    with TestClient(app) as client:
        h = headers("u-oper-beta")
        rows = client.get("/api/documents", headers=h, params={"contract_id": "CT-001", "status": "EM_ANALISE"})
        assert rows.status_code == 200 and [r["id"] for r in rows.json()] == [doc]
        detail = client.get(f"/api/documents/{doc}", headers=h).json()
        assert detail["status"] == detail["versoes"][0]["status"] == "EM_ANALISE"
        assert "motivos_revisao" not in detail and "confianca" not in detail
        assert detail["campos"] == {}
        assert client.get(f"/api/documents/{doc}", headers=headers("u-oper-gama")).status_code == 404
        assert client.get("/api/documents", headers=h, params={"contract_id": "CT-002"}).status_code == 404
        assert client.patch(f"/api/documents/{doc}/review", headers=h, json={"acao": "aprovar"}).status_code == 403
        assert client.post("/api/reports", headers=h, json={"contract_id": "CT-001", "competencia": "10/2026"}).status_code == 403


def test_search_is_limited_to_selected_authorized_contract(banco):
    batch, page = create_batch_and_page()
    with db.tx() as conn:
        conn.execute("INSERT INTO contracts (id,nome,contratante_id,fornecedora_id,bernhoeft_id) "
                     "VALUES ('CT-BETA-2','Outro contrato','ORG-ALFA','ORG-BETA','ORG-BH')")
        conn.execute("INSERT INTO page_fts (texto,page_id,contract_id) VALUES ('horas extras',?,'CT-001')", (page,))
    with TestClient(app) as client:
        h = headers("u-oper-beta")
        assert client.get("/api/search", headers=h, params={"q": "horas", "contract_id": "CT-001"}).json()[0]["page_id"] == page
        assert client.get("/api/search", headers=h, params={"q": "horas", "contract_id": "CT-BETA-2"}).json() == []
        assert client.get("/api/search", headers=h, params={"q": "horas", "contract_id": "CT-002"}).status_code == 404


def test_operator_resubmits_document_uploaded_by_colleague_preserving_version(banco):
    with TestClient(app) as client:
        content = pdf(HOLERITE.format(t="T001", h="8,00"))
        initial = client.post("/api/supplier/batches", headers=headers("u-gestor-beta"),
                              data={"contract_id": "CT-001"}, files={"file": ("holerite.pdf", content, "application/pdf")})
        assert initial.status_code == 202, initial.text
        batch = initial.json()["batch_id"]
        docs = client.get(f"/api/batches/{batch}/documents", headers=headers("u-oper-beta")).json()
        doc = docs[0]["id"]
        with db.tx() as conn:
            conn.execute("UPDATE documents SET status='PENDENTE_CORRECAO' WHERE id=?", (doc,))
            issue = conn.execute(
                "INSERT INTO issues (contract_id,document_id,worker_id,competencia,tipo_documento,categoria,motivo,acao,status,created_at,updated_at) "
                "VALUES ('CT-001',?,'T001','10/2026','HOLERITE','SOLICITADA_NA_REVISAO','Conferir','Reenviar','ABERTA',?,?)",
                (doc, db.agora(), db.agora())).lastrowid
        path = f"/api/issues/{issue}/resubmit"
        file = {"file": ("corrigido.pdf", content, "application/pdf")}
        assert client.post(path, headers=headers("u-oper-gama"), files=file).status_code == 404
        corrected = client.post(path, headers=headers("u-oper-beta"), files=file)
        assert corrected.status_code == 202, corrected.text
        detail = client.get(f"/api/documents/{doc}", headers=headers("u-oper-beta")).json()
        assert detail["status"] == "SUBSTITUIDO"
        assert [v["versao"] for v in detail["versoes"]] == [1, 2]
        assert client.post(path, headers=headers("u-oper-beta"), files=file).status_code == 409
