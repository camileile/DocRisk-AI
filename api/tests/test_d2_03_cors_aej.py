import pytest
from fastapi.testclient import TestClient

from docrisk_core import config
from docrisk_core.api import _configured_cors_origins, app
from test_f1_revision import _headers
from test_f2_worker import banco  # noqa: F401


def test_cors_allowlist_is_explicit_and_rejects_wildcards(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://app.example.test")
    assert _configured_cors_origins() == ["http://localhost:3000", "https://app.example.test"]

    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="sem wildcard"):
        _configured_cors_origins()

    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000/app")
    with pytest.raises(RuntimeError, match="Origem inválida"):
        _configured_cors_origins()


def test_preflight_permite_put_de_associacao_aej_apenas_na_origem_configurada(banco):
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "PUT",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    with TestClient(app) as client:
        allowed = client.options("/api/contracts/CT-001/aej-mappings/1", headers=headers)
        denied = client.options("/api/contracts/CT-001/aej-mappings/1", headers={
            **headers, "Origin": "https://attacker.invalid",
        })
        wrong_method = client.options("/api/contracts/CT-001/aej-mappings/1", headers={
            **headers, "Access-Control-Request-Method": "DELETE",
        })

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "PUT" in allowed.headers["access-control-allow-methods"]
    assert "authorization" in allowed.headers["access-control-allow-headers"].lower()
    assert denied.status_code == 400 and "access-control-allow-origin" not in denied.headers
    assert wrong_method.status_code == 400


def test_association_and_review_require_explicit_analyst_role(banco, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    with TestClient(app) as client:
        for user_id in ("u-admin", "u-gestor-beta", "u-oper-beta", "u-gestor-alfa"):
            auth = _headers(user_id)
            association = client.put(
                "/api/contracts/CT-001/aej-mappings/1",
                headers=auth,
                json={"worker_id": "T001"},
            )
            review = client.patch(
                "/api/documents/999999/aej-review",
                headers=auth,
                json={"horas_extras_h": 1, "justificativa": "teste"},
            )
            assert association.status_code == 403, user_id
            assert review.status_code == 403, user_id

        assert client.put(
            "/api/contracts/CT-001/aej-mappings/1",
            headers=_headers("u-analista"),
            json={"worker_id": "T001"},
        ).status_code == 200
