"""Compatibilidade restrita com o cache preparado antes da versão de schema."""
import json
from pathlib import Path

import pytest

from docrisk_core import ai, db
from docrisk_core.pipeline import worker
from test_f2_worker import BETA, Contador, LOTE, banco, pdf, q


class GeminiContador(Contador):
    # Sem rede: o contador continua lendo somente a camada de texto sintética.
    nome = "gemini"


def warm_legacy_cache():
    content = pdf(*LOTE[:5])
    reader = GeminiContador()
    worker.processar_lote(worker.criar_lote(BETA, "CT-001", "before.pdf", content), provedor=reader)
    assert len(reader.chamadas) == 5
    with db.tx() as conn:
        conn.execute("UPDATE ai_cache SET chave=replace(chave, ':p1:s1:', ':p1:')")
    return content, reader


def test_legacy_cache_is_validated_promoted_and_reused_without_provider_calls(banco):
    content, reader = warm_legacy_cache()
    old_keys = {row["chave"] for row in q("SELECT chave FROM ai_cache")}
    for name in ("after.pdf", "again.pdf"):
        batch = worker.criar_lote(BETA, "CT-001", name, content)
        worker.processar_lote(batch, provedor=reader)
        assert q("SELECT status FROM batches WHERE id=?", batch)[0]["status"] == "CONCLUIDO"
    assert len(reader.chamadas) == 5
    keys = {row["chave"] for row in q("SELECT chave FROM ai_cache")}
    assert old_keys <= keys and len(keys) == 10
    assert {key.replace(":p1:", ":p1:s1:") for key in old_keys} <= keys
    telemetry = q("SELECT cache_hit,input_tokens,output_tokens,total_tokens,estimated_cost_usd FROM ai_telemetry ORDER BY page_id")
    assert all(row == {"cache_hit": 1, "input_tokens": 0, "output_tokens": 0,
                       "total_tokens": 0, "estimated_cost_usd": 0.0} for row in telemetry[5:])


@pytest.mark.parametrize("invalid", ["not valid JSON", '[]'])
def test_invalid_legacy_results_are_read_again_instead_of_failing_the_batch(banco, invalid):
    content, reader = warm_legacy_cache()
    with db.tx() as conn:
        conn.execute("UPDATE ai_cache SET resultado_json=?", (invalid,))
    batch = worker.criar_lote(BETA, "CT-001", "after.pdf", content)
    worker.processar_lote(batch, provedor=reader)
    assert len(reader.chamadas) == 10
    assert q("SELECT status FROM batches WHERE id=?", batch)[0]["status"] == "CONCLUIDO"


@pytest.mark.parametrize("change", ["prompt", "schema", "model", "provider"])
def test_legacy_cache_does_not_cross_version_model_or_provider(banco, monkeypatch, change):
    content, reader = warm_legacy_cache()
    if change == "prompt":
        monkeypatch.setattr(ai, "VERSAO_PROMPT", "p2")
    elif change == "schema":
        monkeypatch.setattr(ai, "VERSAO_SCHEMA", "s2")
    elif change == "model":
        reader.modelo = "different-model"
    else:
        reader.nome = "different-provider"
    worker.processar_lote(worker.criar_lote(BETA, "CT-001", "after.pdf", content), provedor=reader)
    assert len(reader.chamadas) == 10


def test_current_cache_takes_precedence_over_valid_legacy_results(banco):
    content, reader = warm_legacy_cache()
    with db.tx() as conn:
        for row in conn.execute("SELECT chave,resultado_json FROM ai_cache").fetchall():
            conn.execute("INSERT INTO ai_cache (chave,resultado_json,created_at) VALUES (?,?,?)",
                         (row["chave"].replace(":p1:", ":p1:s1:"), row["resultado_json"], db.agora()))
            obsolete = json.loads(row["resultado_json"])
            obsolete["texto"] = "obsolete legacy text"
            conn.execute("UPDATE ai_cache SET resultado_json=? WHERE chave=?", (json.dumps(obsolete), row["chave"]))
    batch = worker.criar_lote(BETA, "CT-001", "after.pdf", content)
    worker.processar_lote(batch, provedor=reader)
    assert len(reader.chamadas) == 5
    assert all(row["texto"] != "obsolete legacy text" for row in q("SELECT texto FROM pages WHERE batch_id=?", batch))


def test_real_demo_pdf_reuses_legacy_cache_and_preserves_reconciliation(banco):
    content = (Path(__file__).resolve().parents[1] / "scripts/lote_demo/lote_demo.pdf").read_bytes()
    reader = GeminiContador()
    worker.processar_lote(worker.criar_lote(BETA, "CT-001", "before.pdf", content), provedor=reader)
    assert len(reader.chamadas) == 16
    with db.tx() as conn:
        conn.execute("UPDATE ai_cache SET chave=replace(chave, ':p1:s1:', ':p1:')")
    worker.processar_lote(worker.criar_lote(BETA, "CT-001", "after.pdf", content), provedor=reader)
    assert len(reader.chamadas) == 16
    analyses = {row["worker_id"]: row for row in q("SELECT worker_id,status,resultado_json FROM analyses WHERE atual=1")}
    assert all(analyses[worker_id]["status"] == "BLOQUEADA_PENDENCIA" for worker_id in ("T002", "T003"))
    assert json.loads(analyses["T001"]["resultado_json"])["tipo"] == "DIVERGENCIA_A_VERIFICAR"
    assert json.loads(analyses["T001"]["resultado_json"])["diferenca_h"] == 4
    assert json.loads(analyses["T004"]["resultado_json"])["tipo"] == "DADOS_INSUFICIENTES"
    assert json.loads(analyses["T005"]["resultado_json"])["tipo"] == "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS"
