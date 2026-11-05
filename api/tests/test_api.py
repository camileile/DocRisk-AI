import os
from fastapi.testclient import TestClient
from docrisk_core.api import app

def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("DOCRISK_DEMO_MODE", raising=False)
    with TestClient(app) as client:
        r = client.post("/api/v1/inspect", files={"file": ("arquivo.txt", b"not AEJ")})
        assert r.status_code == 503

def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.json()["production_ready"] is False
