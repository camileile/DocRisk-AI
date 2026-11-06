from fastapi.testclient import TestClient
from docrisk_core import config, db
from docrisk_core.api import app
from test_f2_worker import banco  # noqa: F401
from test_f1_security import headers


def platform(monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    db.init_db()
    with db.tx() as conn:
        token = conn.execute("SELECT token FROM platform_accounts WHERE id='u-plataforma'").fetchone()[0]
    return {"Authorization": "Bearer " + token}


def test_platform_identity_is_separate_and_denied_operational_access(banco, monkeypatch):
    h = platform(monkeypatch)
    with TestClient(app) as client:
        me = client.get("/api/me", headers=h).json()
        assert me["papel"] == "ADMIN_PLATAFORMA" and me["org_tipo"] == "PLATAFORMA"
        assert client.get("/api/contracts", headers=h).json() == []
        data = client.get("/api/platform/registry", headers=h)
        assert data.status_code == 200 and "token" not in data.text
        assert [m["status"] for m in data.json()["modulos"]] == ["MVP", "PLANEJADO", "PLANEJADO", "PLANEJADO"]
        for path in ["/api/documents", "/api/batches", "/api/search?q=horas", "/api/reports", "/api/admin/registry", "/api/client/reports", "/api/audit"]:
            assert client.get(path, headers=h).status_code == 403, path
        for uid in ["u-admin", "u-analista", "u-oper-beta", "u-gestor-beta", "u-gestor-alfa"]:
            assert client.get("/api/platform/registry", headers=headers(uid)).status_code == 403
        assert client.get("/api/platform/registry").status_code == 401
        # Inicialização aditiva e idempotente preserva a identidade operacional.
        before = headers("u-admin")
        db.init_db()
        assert headers("u-admin") == before
        with db.tx() as conn:
            assert conn.execute("SELECT COUNT(*) FROM platform_accounts").fetchone()[0] == 1
            assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 6


def test_platform_creates_auditor_with_own_admin_and_controls_access(banco, monkeypatch):
    h = platform(monkeypatch)
    with TestClient(app) as client:
        created = client.post("/api/platform/auditors", headers=h, json={"nome": "Auditora Nova", "administrador": "Gestor Novo"})
        assert created.status_code == 201, created.text
        result = created.json()
        admin = {"Authorization": "Bearer " + result["token_teste"]}
        me = client.get("/api/me", headers=admin).json()
        assert me["papel"] == "ADMIN_BH" and me["org_id"] == result["id"]
        assert client.get("/api/admin/registry", headers=admin).json()["empresas"] == []
        assert client.get("/api/platform/registry", headers=admin).status_code == 403
        path = f"/api/platform/administrators/{result['administrador_id']}/status"
        assert client.patch(path, headers=h, json={"ativo": False}).status_code == 200
        assert client.get("/api/me", headers=admin).status_code == 401
        assert client.patch(path, headers=h, json={"ativo": True}).status_code == 200
        assert client.get("/api/me", headers=admin).status_code == 200
        assert client.patch("/api/platform/administrators/u-analista/status", headers=h, json={"ativo": False}).status_code == 404
        duplicate = client.post("/api/platform/auditors", headers=h, json={"nome": " auditora nova ", "administrador": "Outro"})
        assert duplicate.status_code == 409
        listing = client.get("/api/platform/registry", headers=h).json()
        assert len(listing["auditoria"]) == 3
        assert "token_teste" not in str(listing)


def test_settings_validation_and_writes_require_demo(banco, monkeypatch):
    h = platform(monkeypatch)
    with TestClient(app) as client:
        path = "/api/platform/settings"
        valid = {"nome": "DocRisk AI", "contato": "Suporte de demonstração"}
        assert client.patch(path, headers=h, json=valid).status_code == 200
        assert client.get("/api/platform/registry", headers=h).json()["configuracoes"] == valid
        assert client.patch(path, headers=h, json={**valid, "modulos": ["ambiental"]}).status_code == 422
        monkeypatch.setattr(config, "DEMO_MODE", False)
        assert client.patch(path, headers=h, json=valid).status_code == 403
        assert client.post("/api/platform/auditors", headers=h, json={"nome": "Teste", "administrador": "Teste"}).status_code == 403
        assert client.patch("/api/platform/administrators/u-admin/status", headers=h, json={"ativo": False}).status_code == 403
        assert client.get("/api/platform/registry", headers=h).status_code == 200
