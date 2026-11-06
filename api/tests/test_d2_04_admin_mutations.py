from fastapi.testclient import TestClient

from docrisk_core import config, db
from docrisk_core.api import app
from test_f2_worker import banco  # noqa: F401


def _auth_for_user(user_id: str) -> dict[str, str]:
    with db.tx() as conn:
        token = conn.execute("SELECT token FROM users WHERE id=?", (user_id,)).fetchone()[0]
    return {"Authorization": "Bearer " + token}


def _auth_for_platform() -> dict[str, str]:
    with db.tx() as conn:
        token = conn.execute(
            "SELECT token FROM platform_accounts WHERE id='u-plataforma'"
        ).fetchone()[0]
    return {"Authorization": "Bearer " + token}


def _verify_repeatable_activation(client, path, operator, credential, list_path, collection, uid):
    deactivated = client.patch(path, headers=operator, json={"ativo": False})
    assert deactivated.status_code == 200
    assert client.get("/api/me", headers=credential).status_code == 401

    for _ in range(3):
        activated = client.patch(path, headers=operator, json={"ativo": True})
        assert activated.status_code == 200
        assert activated.json() == {"id": uid, "ativo": True}
        assert client.get("/api/me", headers=credential).status_code == 200

    listing = client.get(list_path, headers=operator)
    assert listing.status_code == 200
    entries = listing.json() if isinstance(listing.json(), list) else listing.json()[collection]
    assert next(item for item in entries if item["id"] == uid)["ativo"] == 1


def test_admin_mutations_are_visible_immediately_and_activation_is_repeatable(
    banco, monkeypatch
):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    db.init_db()

    with TestClient(app) as client:
        admin = _auth_for_user("u-admin")
        supplier_manager = _auth_for_user("u-gestor-beta")
        platform = _auth_for_platform()

        admin_user = client.post(
            "/api/admin/users",
            headers=admin,
            json={"nome": "Gestor de teste", "org_id": "ORG-BETA", "papel": "GESTOR_FORN"},
        ).json()
        operator = client.post(
            "/api/supplier/operators", headers=supplier_manager, json={"nome": "Operador de teste"}
        ).json()
        administrator = client.post(
            "/api/platform/auditors",
            headers=platform,
            json={"nome": "Auditora de teste", "administrador": "Admin de teste"},
        ).json()

        _verify_repeatable_activation(
            client,
            f"/api/admin/users/{admin_user['id']}/status",
            admin,
            {"Authorization": "Bearer " + admin_user["token_teste"]},
            "/api/admin/registry",
            "usuarios",
            admin_user["id"],
        )
        _verify_repeatable_activation(
            client,
            f"/api/supplier/operators/{operator['id']}/status",
            supplier_manager,
            {"Authorization": "Bearer " + operator["token_teste"]},
            "/api/supplier/operators",
            "",
            operator["id"],
        )
        _verify_repeatable_activation(
            client,
            f"/api/platform/administrators/{administrator['administrador_id']}/status",
            platform,
            _auth_for_user(administrator["administrador_id"]),
            "/api/platform/registry",
            "administradores",
            administrator["administrador_id"],
        )
