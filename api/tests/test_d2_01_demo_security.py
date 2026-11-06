from fastapi.testclient import TestClient

from docrisk_core import config, db
from docrisk_core.api import app


def _usar_ambiente(monkeypatch, tmp_path, demo: bool) -> None:
    monkeypatch.setenv("DOCRISK_DEMO_MODE", "1" if demo else "0")
    monkeypatch.setattr(config, "DEMO_MODE", demo)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "docrisk.sqlite")
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(config, "PAGES_DIR", tmp_path / "pages")


def test_startup_operacional_nao_cria_dados_sinteticos_nem_expoe_tokens(
    monkeypatch, tmp_path
):
    _usar_ambiente(monkeypatch, tmp_path, demo=False)

    with TestClient(app) as client:
        assert client.get("/api/demo/users").status_code == 404
        assert client.get("/api/me").status_code == 401
        assert client.get("/api/platform/registry").status_code == 401
        assert client.get("/api/admin/registry").status_code == 401
        assert client.post("/api/v1/inspect", files={"file": ("x.txt", b"x")}).status_code == 503

    with db.tx() as conn:
        for tabela in ("organizations", "users", "contracts", "workers", "platform_accounts"):
            assert conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0] == 0


def test_startup_demo_expone_perfis_com_token_somente_no_modo_demo(
    monkeypatch, tmp_path
):
    _usar_ambiente(monkeypatch, tmp_path, demo=True)

    with TestClient(app) as client:
        response = client.get("/api/demo/users")

    assert response.status_code == 200
    perfis = response.json()
    assert len([perfil for perfil in perfis if perfil["org_tipo"] != "PLATAFORMA"]) == 6
    assert all(perfil["token"] for perfil in perfis)
