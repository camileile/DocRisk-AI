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


def _script(nome: str):
    import importlib.util
    from pathlib import Path

    caminho = Path(__file__).resolve().parents[1] / "scripts" / f"{nome}.py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_seed_100_recusa_fora_do_modo_demo_sem_tocar_no_banco(monkeypatch, tmp_path):
    import pytest

    _usar_ambiente(monkeypatch, tmp_path, demo=False)
    with pytest.raises(SystemExit, match="DOCRISK_DEMO_MODE=1"):
        _script("seed_100").main()
    assert not (tmp_path / "docrisk.sqlite").exists()


def test_seed_100_no_modo_demo_completa_100_trabalhadores(monkeypatch, tmp_path, capsys):
    _usar_ambiente(monkeypatch, tmp_path, demo=True)
    _script("seed_100").main()
    assert "100 trabalhadores" in capsys.readouterr().out
