from __future__ import annotations

from fastapi.testclient import TestClient

from docrisk_core import config, db
from docrisk_core.api import app
from docrisk_core.routes import worker


def token_for(user_id: str) -> str:
    with db.tx() as conn:
        return conn.execute("SELECT token FROM users WHERE id=?", (user_id,)).fetchone()[0]


def create_batch_and_page(contract_id: str = "CT-001") -> tuple[int, int]:
    with db.tx() as conn:
        batch_id = conn.execute(
            "INSERT INTO batches (contract_id, uploaded_by, filename, arquivo, sha256, tipo_arquivo, "
            "status, total_pages, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (contract_id, "u-gestor-beta", "lote-demo.pdf", "demo.pdf", "abc", "PDF",
             "CONCLUIDO", 1, db.agora()),
        ).lastrowid
        page_id = conn.execute(
            "INSERT INTO pages (batch_id, ordem, image_path, sha256) VALUES (?, ?, ?, ?)",
            (batch_id, 1, str(config.PAGES_DIR / "inexistente.png"), "page-hash"),
        ).lastrowid
        return batch_id, page_id


def headers(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(user_id)}"}


def test_missing_token_is_401():
    with TestClient(app) as client:
        response = client.get("/api/me")
    assert response.status_code == 401


def test_gama_cannot_read_beta_batch_and_denial_is_audited():
    with TestClient(app) as client:
        batch_id, _ = create_batch_and_page()
        response = client.get(f"/api/batches/{batch_id}", headers=headers("u-oper-gama"))
    assert response.status_code == 404
    with db.tx() as conn:
        audit = conn.execute("SELECT resultado, alvo FROM audit ORDER BY id DESC LIMIT 1").fetchone()
    assert audit["resultado"] == "NEGADO"
    assert audit["alvo"] == "CT-001"


def test_upload_calls_f2_worker_with_authorized_contract(monkeypatch):
    received = {}

    def create(user, contract_id, filename, data, issue_id=None):
        received.update(contract_id=contract_id, filename=filename, data=data, issue_id=issue_id)
        return 73

    monkeypatch.setattr(worker, "criar_lote", create)
    monkeypatch.setattr(worker, "enfileirar", lambda batch_id: received.update(enqueued=batch_id))
    with TestClient(app) as client:
        response = client.post(
            "/api/supplier/batches", headers=headers("u-oper-beta"),
            data={"contract_id": "CT-001"}, files={"file": ("lote.pdf", b"fake-pdf")},
        )
    assert response.status_code == 202
    assert response.json() == {"batch_id": 73, "status": "RECEBIDO"}
    assert received == {"contract_id": "CT-001", "filename": "lote.pdf",
                        "data": b"fake-pdf", "issue_id": None, "enqueued": 73}


def test_contractor_sees_no_draft_and_cannot_open_page_image():
    with TestClient(app) as client:
        batch_id, page_id = create_batch_and_page()
        with db.tx() as conn:
            conn.execute(
                "INSERT INTO reports (contract_id, competencia, versao, status, autor_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("CT-001", "10/2026", 1, "RASCUNHO", "u-analista", db.agora()),
            )
        report_response = client.get("/api/client/reports", headers=headers("u-gestor-alfa"))
        image_response = client.get(f"/api/pages/{page_id}/image", headers=headers("u-gestor-alfa"))
        batch_response = client.get(f"/api/batches/{batch_id}", headers=headers("u-gestor-alfa"))
    assert report_response.status_code == 200
    assert report_response.json() == []
    assert image_response.status_code == 403
    assert batch_response.status_code == 403


def test_batch_response_does_not_expose_private_storage_path():
    with TestClient(app) as client:
        batch_id, _ = create_batch_and_page()
        response = client.get(f"/api/batches/{batch_id}", headers=headers("u-oper-beta"))
    assert response.status_code == 200
    assert "arquivo" not in response.json()


def test_supplier_document_view_hides_internal_fields_and_masks_review_status():
    with TestClient(app) as client:
        batch_id, _ = create_batch_and_page()
        with db.tx() as conn:
            conn.execute(
                "INSERT INTO documents (batch_id, contract_id, tipo, status, confianca, "
                "motivos_pendencia, motivos_revisao, campos_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (batch_id, "CT-001", "HOLERITE", "REVISAO_HUMANA", 0.42,
                 '["reenviar página"]', '["baixa confiança do modelo"]',
                 '{"valor_liquido": 1234.5}', db.agora(), db.agora()),
            )
        response = client.get(f"/api/batches/{batch_id}/documents", headers=headers("u-oper-beta"))
    assert response.status_code == 200
    doc = response.json()[0]
    assert doc["status"] == "EM_ANALISE"
    assert doc["motivos_pendencia"] == ["reenviar página"]
    assert "motivos_revisao" not in doc
    assert "confianca" not in doc
    assert doc["campos"] == {}


def test_supplier_operator_cannot_publish_report():
    with TestClient(app) as client:
        with db.tx() as conn:
            report_id = conn.execute(
                "INSERT INTO reports (contract_id, competencia, versao, status, autor_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("CT-001", "10/2026", 1, "RASCUNHO", "u-analista", db.agora()),
            ).lastrowid
        response = client.post(f"/api/reports/{report_id}/publish", headers=headers("u-oper-beta"))
    assert response.status_code == 403
