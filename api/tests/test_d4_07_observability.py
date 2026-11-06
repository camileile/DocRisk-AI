"""D4-07 — liveness, readiness, métricas reais e logs correlacionados sem dados sensíveis."""
from __future__ import annotations

import json
import logging

import pytest
from fastapi.testclient import TestClient

from docrisk_core import config, db, observability
from docrisk_core.ai.textlayer import TextLayerProvider
from docrisk_core.api import app
from docrisk_core.pipeline import worker
from test_f2_worker import BETA, LOTE, banco, pdf  # noqa: F401


def _h(uid: str) -> dict[str, str]:
    with db.tx() as conn:
        row = conn.execute("SELECT token FROM users WHERE id=?", (uid,)).fetchone() or \
            conn.execute("SELECT token FROM platform_accounts WHERE id=?", (uid,)).fetchone()
    return {"Authorization": "Bearer " + row[0]}


@pytest.fixture
def demo(banco, monkeypatch):  # noqa: F811
    monkeypatch.setattr(config, "DEMO_MODE", True)
    db.init_db()
    return banco


def test_health_original_inalterado_e_live(banco):  # noqa: F811
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok", "production_ready": False}
        assert client.get("/health/live").json() == {"status": "ok"}


def test_ready_ok_em_modo_sincrono(banco):  # noqa: F811
    with TestClient(app) as client:
        r = client.get("/health/ready")
    assert r.status_code == 200 and r.json()["status"] == "ready"
    assert r.json()["checks"]["worker"]["detalhe"] == "sincrono"


def test_ready_detecta_worker_parado_com_processo_vivo(banco, monkeypatch):  # noqa: F811
    monkeypatch.setattr(config, "SYNC", False)
    with TestClient(app) as client:
        assert client.get("/health/ready").status_code == 200   # thread iniciada no lifespan
        worker.parar_worker()                                    # simula morte da thread
        r = client.get("/health/ready")
        assert r.status_code == 503 and r.json()["checks"]["worker"]["ok"] is False
        assert client.get("/health/live").status_code == 200    # liveness continua ok
    # parar_worker() do lifespan com a thread já parada deixa um sentinela None na
    # fila que encerraria o próximo worker (defeito F2 registrado em D4-07). Limpar.
    while not worker._fila.empty():
        worker._fila.get_nowait()
        worker._fila.task_done()


def test_ready_detecta_banco_e_armazenamento_indisponiveis(banco, monkeypatch, tmp_path):  # noqa: F811
    with TestClient(app) as client:
        monkeypatch.setattr(config, "DB_PATH", tmp_path / "nao-existe" / "x.sqlite")
        r = client.get("/health/ready")
        assert r.status_code == 503 and r.json()["checks"]["banco"]["ok"] is False
        monkeypatch.undo()
        monkeypatch.setattr(config, "SYNC", True)
        monkeypatch.setattr(config, "PAGES_DIR", tmp_path / "sumiu")
        r = client.get("/health/ready")
        assert r.status_code == 503 and r.json()["checks"]["armazenamento"]["ok"] is False


def test_metricas_somente_admin_plataforma(demo):
    with TestClient(app) as client:
        assert client.get("/api/ops/metrics").status_code == 401
        for uid in ["u-admin", "u-analista", "u-gestor-beta", "u-oper-beta", "u-gestor-alfa"]:
            assert client.get("/api/ops/metrics", headers=_h(uid)).status_code == 403
        assert client.get("/api/ops/metrics", headers=_h("u-plataforma")).status_code == 200


def test_metricas_refletem_o_banco_sem_inventar(demo):
    bid = worker.criar_lote(BETA, "CT-001", "lote.pdf", pdf(*LOTE))
    worker.processar_lote(bid, provedor=TextLayerProvider())
    worker.criar_lote(BETA, "CT-001", "pendente.pdf", pdf("Pagina 1 de 1"))  # fica RECEBIDO
    with TestClient(app) as client:
        m = client.get("/api/ops/metrics", headers=_h("u-plataforma")).json()
    assert m["lotes"]["concluidos"] == 1 and m["lotes"]["backlog"] == 1
    assert m["paginas"]["por_status"]["OK"] == 8
    assert m["paginas"]["leitura_ms_p50"] is not None
    assert m["lotes"]["taxa_falha"] == 0.0
    assert m["ia"]["chamadas"] is None and m["ia"]["custo_estimado_usd"] is None
    assert "T001" not in json.dumps(m) and "lote.pdf" not in json.dumps(m)


def test_request_id_propagado_e_sanitizado(banco):  # noqa: F811
    with TestClient(app) as client:
        assert client.get("/health/live", headers={"X-Request-ID": "abc-123"}).headers["x-request-id"] == "abc-123"
        gerado = client.get("/health/live", headers={"X-Request-ID": "x" * 200 + "\n<script>"}).headers["x-request-id"]
        assert len(gerado) == 16 and gerado.isalnum()


def test_log_json_correlacionado_e_sem_token(banco, capsys, monkeypatch):  # noqa: F811
    monkeypatch.setenv("DOCRISK_LOG_JSON", "1")
    raiz = logging.getLogger("docrisk")
    antigos = list(raiz.handlers)
    for h in antigos:
        raiz.removeHandler(h)
    try:
        observability.configurar_logs()
        segredo = "segredo-token-abcdef123456"
        with TestClient(app) as client:
            client.get("/api/me", headers={"Authorization": "Bearer " + segredo, "X-Request-ID": "req-777"})
            logging.getLogger("docrisk.teste").info("chamada com Bearer %s", segredo)
        err = capsys.readouterr().err
        linhas = [json.loads(l) for l in err.splitlines() if l.startswith("{")]
        http = [l for l in linhas if l["logger"] == "docrisk.http" and l.get("path") == "/api/me"]
        assert http and http[0]["request_id"] == "req-777" and http[0]["status"] == 401
        assert segredo not in err and "[REDACTED]" in err
    finally:
        for h in list(raiz.handlers):
            raiz.removeHandler(h)
        for h in antigos:
            raiz.addHandler(h)
