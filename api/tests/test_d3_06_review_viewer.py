"""D3-06: leitura sob demanda, correção rastreável e permissões afetadas."""
import json

import pytest
from fastapi.testclient import TestClient

from docrisk_core import config, db
from docrisk_core.api import app
from test_f2_worker import banco


def headers(user="u-analista"):
    with db.tx() as conn:
        token = conn.execute("SELECT token FROM users WHERE id=?", (user,)).fetchone()[0]
    return {"Authorization": "Bearer " + token}


@pytest.fixture
def document(banco):
    with db.tx() as conn:
        now = db.agora()
        batch = conn.execute(
            "INSERT INTO batches (contract_id,uploaded_by,filename,arquivo,sha256,tipo_arquivo,status,total_pages,created_at) "
            "VALUES ('CT-001','u-oper-beta','synthetic.pdf','unused','test','PDF','CONCLUIDO',3,?)", (now,)).lastrowid
        doc = conn.execute(
            "INSERT INTO documents (batch_id,contract_id,tipo,worker_id,competencia,status,confianca,campos_json,created_at,updated_at) "
            "VALUES (?,'CT-001','HOLERITE','T001','10/2026','REVISAO_HUMANA',0.55,?,?,?)",
            (batch, '{"horas_extras_h":8,"valor_liquido":1000}', now, now)).lastrowid
        pages = []
        for index in range(1, 4):
            page = conn.execute(
                "INSERT INTO pages (batch_id,ordem,image_path,sha256,status,texto,analise_json) VALUES (?,?,?,'test','OK',?,?)",
                (batch, index, str(config.PAGES_DIR / 'page.png'), f'OCR {index} CPF 123.456.789-09',
                 json.dumps({"campos": {"horas_extras_h": 8}, "origem": "TEXTO_PDF", "confianca_tipo": .55}))).lastrowid
            pages.append(page)
            if index < 3:
                conn.execute("INSERT INTO doc_pages (document_id,page_id,posicao) VALUES (?,?,?)", (doc, page, index))
    return {"id": doc, "pages": pages, "updated_at": now}


def payload(document, **changes):
    return {"acao": "corrigir_campos", "esperado_em": document["updated_at"], "campos": {"horas_extras_h": 12},
            "fontes": {"horas_extras_h": document["pages"][1]}, "motivo": "Total conferido na página 2", **changes}


def test_page_text_is_on_demand_and_evidence_retains_real_origin(document):
    with TestClient(app) as client:
        summary = client.get(f"/api/documents/{document['id']}?include_page_text=false", headers=headers()).json()
        detail = client.get(f"/api/documents/{document['id']}", headers=headers()).json()
        page = client.get(f"/api/documents/{document['id']}/pages/{document['pages'][1]}", headers=headers()).json()
        wrong = client.get(f"/api/documents/{document['id']}/pages/{document['pages'][2]}", headers=headers())
    assert all("texto" not in page for page in summary["paginas_detalhe"])
    assert len(detail["paginas_detalhe"]) == 2 and "OCR 1" in detail["paginas_detalhe"][0]["texto"]
    assert page["ordem"] == 2 and "OCR 2" in page["texto"]
    assert wrong.status_code == 404
    evidence = summary["evidencias_campos"]["horas_extras_h"][1]
    assert evidence["page_id"] == document["pages"][1] and evidence["origem"] == "TEXTO_PDF"
    assert evidence["confianca_classificacao"] == .55 and "confianca_campo" not in evidence


def test_edit_preserves_ocr_history_and_pending_review_and_reconciles(document, monkeypatch):
    from docrisk_core.rules import conciliacao
    calls = []
    monkeypatch.setattr(conciliacao, "conciliar", lambda *args: calls.append(args[1:]))
    with TestClient(app) as client:
        response = client.patch(f"/api/documents/{document['id']}/review", headers=headers(), json=payload(document))
        assert response.status_code == 200, response.text
        detail = client.get(f"/api/documents/{document['id']}?include_page_text=false", headers=headers()).json()
        supplier = client.get(f"/api/documents/{document['id']}", headers=headers("u-oper-beta")).json()
    assert detail["campos"]["horas_extras_h"] == 12
    assert detail["status"] == "REVISAO_HUMANA" and detail["confianca"] == .55
    review = detail["revisoes_campos"][0]
    assert review["valor_original"] == 8 and review["valor_corrigido"] == 12
    assert review["author_id"] == "u-analista" and review["reason"] == payload(document)["motivo"]
    assert detail["evidencias_campos"]["horas_extras_h"][0]["valor"] == 8
    assert "evidencias_campos" not in supplier and "revisoes_campos" not in supplier and supplier["campos"] == {}
    assert calls == [("CT-001", "T001", "10/2026")]
    with db.tx() as conn:
        assert all("Total conferido" not in str(tuple(row)) for row in conn.execute("SELECT * FROM audit"))
        assert "OCR 2" in conn.execute("SELECT texto FROM pages WHERE id=?", (document["pages"][1],)).fetchone()[0]


@pytest.mark.parametrize("changes", [
    {"motivo": "   "}, {"motivo": "x" * 501}, {"fontes": {}},
    {"fontes": {"horas_extras_h": True}}, {"campos": {"horas_extras_h": -1}},
    {"campos": {"horas_extras_h": "12"}}, {"campos": {"horas_extras_h": True}}, {"campos": {"horas_extras_h": 10**400}},
    {"campos": {"unknown": 10}}, {"campos": {"horas_extras_h": 8}},
    {"campos": {"data_pagamento": "31/02/2026"}, "fontes": {"data_pagamento": 1}},
])
def test_invalid_edits_are_atomic(document, changes):
    with TestClient(app) as client:
        response = client.patch(f"/api/documents/{document['id']}/review", headers=headers(), json=payload(document, **changes))
    assert response.status_code == 422
    with db.tx() as conn:
        assert json.loads(conn.execute("SELECT campos_json FROM documents WHERE id=?", (document["id"],)).fetchone()[0])["horas_extras_h"] == 8
        assert conn.execute("SELECT count(*) FROM document_field_reviews").fetchone()[0] == 0


def test_source_membership_and_stale_snapshot_are_checked(document):
    with TestClient(app) as client:
        wrong = client.patch(f"/api/documents/{document['id']}/review", headers=headers(),
                             json=payload(document, fontes={"horas_extras_h": document["pages"][2]}))
        first = client.patch(f"/api/documents/{document['id']}/review", headers=headers(), json=payload(document))
        stale = client.patch(f"/api/documents/{document['id']}/review", headers=headers(), json=payload(document))
    assert wrong.status_code == 422 and first.status_code == 200 and stale.status_code == 409


@pytest.mark.parametrize("role", ["u-admin", "u-gestor-alfa", "u-gestor-beta", "u-oper-beta"])
def test_only_analyst_may_edit(document, role):
    with TestClient(app) as client:
        response = client.patch(f"/api/documents/{document['id']}/review", headers=headers(role), json=payload(document))
        page = client.get(f"/api/documents/{document['id']}/pages/{document['pages'][0]}", headers=headers(role))
    assert response.status_code == 403
    if role in {"u-admin", "u-gestor-alfa"}:
        assert page.status_code == 403
    else:
        assert page.status_code == 200 and '123.456.789-09' not in page.json()["texto"]


def test_other_supplier_has_no_page_access(document):
    with TestClient(app) as client:
        page = client.get(f"/api/documents/{document['id']}/pages/{document['pages'][0]}", headers=headers("u-oper-gama"))
    assert page.status_code in {403, 404}


def test_absent_value_stays_null_and_approved_document_cannot_be_edited(document):
    with TestClient(app) as client:
        response = client.patch(f"/api/documents/{document['id']}/review", headers=headers(),
                                json=payload(document, campos={"horas_extras_h": None}))
        assert response.status_code == 200
        detail = client.get(f"/api/documents/{document['id']}", headers=headers()).json()
        assert detail["campos"]["horas_extras_h"] is None
        assert detail["revisoes_campos"][0]["valor_corrigido"] is None
        approved = client.patch(f"/api/documents/{document['id']}/review", headers=headers(), json={"acao": "aprovar"})
        assert approved.status_code == 200
        denied = client.patch(f"/api/documents/{document['id']}/review", headers=headers(),
                              json=payload(document, esperado_em=detail["updated_at"]))
        assert denied.status_code == 409

def test_legacy_field_review_is_rejected_and_document_history_only_records_valid_edits(document):
    with TestClient(app) as client:
        url = f"/api/documents/{document['id']}/review"
        legacy = client.patch(url, headers=headers(), json={
            "acao": "corrigir_campos", "campos": {"horas_extras_h": 10},
            "motivo": "Conferência D1-06", "fonte": "Holerite, página 1"})
        assert legacy.status_code == 422
        before = client.get(f"/api/documents/{document['id']}", headers=headers()).json()
        assert before["revisoes_campos"] == []
        updated = client.patch(url, headers=headers(), json=payload(document, esperado_em=before["updated_at"]))
        assert updated.status_code == 200, updated.text
        after = client.get(f"/api/documents/{document['id']}", headers=headers()).json()
    history = after["revisoes_campos"]
    assert len(history) == 1
    assert history[0]["revision_number"] == 1
    assert history[0]["source"] == f"Página #{document['pages'][1]}"
    assert history[0]["author_id"] == "u-analista"

def test_manual_review_of_apt_document_is_audited_and_recalculates(document, monkeypatch):
    from docrisk_core.rules import conciliacao
    recalculated = []
    monkeypatch.setattr(conciliacao, "conciliar", lambda *args: recalculated.append(args[1:]))
    with db.tx() as conn:
        conn.execute("UPDATE documents SET status='APTO' WHERE id=?", (document["id"],))
    endpoint = f"/api/documents/{document['id']}/review"
    with TestClient(app) as client:
        before = client.get(f"/api/documents/{document['id']}", headers=headers()).json()
        assert before["status"] == "APTO"
        response = client.patch(endpoint, headers=headers(), json={
            "acao": "iniciar_revisao",
            "motivo": "Conferir divergência identificada pelo analista.",
            "esperado_em": before["updated_at"],
        })
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "REVISAO_HUMANA"
        detail = client.get(f"/api/documents/{document['id']}", headers=headers()).json()
        queue = client.get("/api/review-queue", headers=headers()).json()
        supplier = client.get(f"/api/documents/{document['id']}", headers=headers("u-oper-beta")).json()
    assert detail["status"] == "REVISAO_HUMANA" and detail["updated_at"] != before["updated_at"]
    assert detail["revisado_por"] == "u-analista"
    assert any("Conferir divergência identificada" in item for item in detail["motivos_revisao"])
    assert any(row["id"] == document["id"] for row in queue)
    assert supplier["status"] == "EM_ANALISE" and "motivos_revisao" not in supplier
    assert recalculated == [("CT-001", "T001", "10/2026")]
    with db.tx() as conn:
        events = conn.execute(
            "SELECT acao, alvo, resultado FROM audit WHERE acao='DOCUMENTO_INICIAR_REVISAO' "
            "AND alvo=?", (str(document["id"]),)).fetchall()
        assert len(events) == 1
        assert events[0]["resultado"] == "OK"


@pytest.mark.parametrize("role", ["u-admin", "u-gestor-alfa", "u-gestor-beta", "u-oper-beta"])
def test_manual_review_start_is_exclusive_to_analyst(document, role):
    with db.tx() as conn:
        conn.execute("UPDATE documents SET status='APTO' WHERE id=?", (document["id"],))
    with TestClient(app) as client:
        response = client.patch(f"/api/documents/{document['id']}/review", headers=headers(role),
                                json={"acao": "iniciar_revisao", "motivo": "Revisão manual de conferência.",
                                      "esperado_em": document["updated_at"]})
    assert response.status_code == 403
    with db.tx() as conn:
        assert conn.execute("SELECT status FROM documents WHERE id=?",
                            (document["id"],)).fetchone()[0] == "APTO"


@pytest.mark.parametrize("invalid", [
    {"motivo": "curto"}, {"motivo": " " * 20}, {"motivo": "x" * 501},
    {"motivo": None}, {"motivo": 12345678912}, {"esperado_em": "2000-01-01"},
    {"esperado_em": None},
])
def test_manual_review_start_rejects_invalid_request(document, invalid):
    with db.tx() as conn:
        conn.execute("UPDATE documents SET status='APTO' WHERE id=?", (document["id"],))
    request = {
        "acao": "iniciar_revisao", "motivo": "O analista identificou uma inconsistência.",
        "esperado_em": document["updated_at"], **invalid,
    }
    with TestClient(app) as client:
        response = client.patch(f"/api/documents/{document['id']}/review",
                                headers=headers(), json=request)
    assert response.status_code in {409, 422}, response.text
    with db.tx() as conn:
        assert conn.execute("SELECT status FROM documents WHERE id=?",
                            (document["id"],)).fetchone()[0] == "APTO"


@pytest.mark.parametrize("status", ["REVISAO_HUMANA", "PENDENTE_CORRECAO", "SUBSTITUIDO"])
def test_manual_review_start_does_not_overwrite_existing_state(document, status):
    with db.tx() as conn:
        conn.execute("UPDATE documents SET status=? WHERE id=?", (status, document["id"]))
    with TestClient(app) as client:
        response = client.patch(f"/api/documents/{document['id']}/review",
                                headers=headers(), json={
            "acao": "iniciar_revisao", "motivo": "Revisão manual de conferência.",
            "esperado_em": document["updated_at"],
        })
    assert response.status_code == 409
    with db.tx() as conn:
        assert conn.execute("SELECT status FROM documents WHERE id=?",
                            (document["id"],)).fetchone()[0] == status
