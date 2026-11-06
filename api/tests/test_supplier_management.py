from fastapi.testclient import TestClient
from docrisk_core import config, db
from docrisk_core.api import app
from docrisk_core.routes import worker
from test_f2_worker import banco  # noqa: F401
from test_analyst_overview import _token
from test_f1_security import create_batch_and_page


def test_manager_creates_operator_shared_access_and_revokes_token(banco, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    with TestClient(app) as client:
        batch, _ = create_batch_and_page()
        h = _token("u-gestor-beta")
        created = client.post("/api/supplier/operators", headers=h, json={"nome": " Novo operador "})
        assert created.status_code == 201, created.text
        user = created.json()
        assert user["nome"] == "Novo operador" and user["org_id"] == "ORG-BETA"
        assert user["papel"] == "OPERADOR_FORN"
        token = {"Authorization": "Bearer " + user["token_teste"]}
        # Novo operador pode consultar lote de outro usuário da mesma empresa.
        assert client.get(f"/api/batches/{batch}", headers=token).status_code == 200
        assert client.get("/api/me", headers=token).json()["papel"] == "OPERADOR_FORN"
        listing = client.get("/api/supplier/operators", headers=h)
        assert user["id"] in [r["id"] for r in listing.json()]
        assert "token" not in listing.text
        assert client.patch(f"/api/supplier/operators/{user['id']}/status", headers=h, json={"ativo": False}).status_code == 200
        assert client.get("/api/me", headers=token).status_code == 401
        assert client.get(f"/api/batches/{batch}", headers=h).status_code == 200
        assert client.patch(f"/api/supplier/operators/{user['id']}/status", headers=h, json={"ativo": True}).status_code == 200
        assert client.get("/api/me", headers=token).status_code == 200
        with db.tx() as conn:
            assert conn.execute("SELECT COUNT(*) FROM audit WHERE alvo=?", (user["id"],)).fetchone()[0] == 3


def test_operator_management_is_scoped_and_demo_only(banco, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    with TestClient(app) as client:
        path = "/api/supplier/operators"
        assert client.get(path).status_code == 401
        for uid in ["u-oper-beta", "u-analista", "u-admin", "u-gestor-alfa"]:
            assert client.get(path, headers=_token(uid)).status_code == 403
            assert client.post(path, headers=_token(uid), json={"nome": "Operador"}).status_code == 403
        h = _token("u-gestor-beta")
        assert "u-oper-gama" not in client.get(path, headers=h).text
        for uid in ["u-oper-gama", "u-gestor-beta", "u-admin"]:
            assert client.patch(path + f"/{uid}/status", headers=h, json={"ativo": False}).status_code == 404
        assert client.post(path, headers=h, json={"nome": "   "}).status_code == 422
        assert client.post(path, headers=h, json={"nome": "Operador", "org_id": "ORG-GAMA", "papel": "ADMIN_BH"}).status_code == 422
        monkeypatch.setattr(config, "DEMO_MODE", False)
        assert client.post(path, headers=h, json={"nome": "Operador"}).status_code == 401
        assert client.patch(path + "/u-oper-beta/status", headers=h, json={"ativo": False}).status_code == 401
        assert client.get(path, headers=h).status_code == 401


def test_manager_reprocesses_own_company_batch_only(banco, monkeypatch):
    queued = []
    monkeypatch.setattr(worker, "enfileirar", queued.append)
    with TestClient(app) as client:
        batch, _ = create_batch_and_page()
        with db.tx() as conn:
            conn.execute("UPDATE batches SET status='FALHA_PROCESSAMENTO' WHERE id=?", (batch,))
        path = f"/api/batches/{batch}/reprocess"
        assert client.post(path, headers=_token("u-oper-gama")).status_code == 404
        assert client.post(path, headers=_token("u-gestor-beta")).status_code == 202
        assert queued == [batch]
