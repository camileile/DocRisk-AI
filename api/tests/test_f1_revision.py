import json

from fastapi.testclient import TestClient

from docrisk_core import config, db
from docrisk_core.ai.textlayer import TextLayerProvider
from docrisk_core.api import app
from docrisk_core.pipeline import worker
from test_f2_worker import BETA, LOTE, banco, documentos, pdf, q


def _token(user_id):
    with db.tx() as conn:
        return conn.execute("SELECT token FROM users WHERE id=?", (user_id,)).fetchone()[0]


def _headers(user_id="u-analista"):
    return {"Authorization": f"Bearer {_token(user_id)}"}


def _api_lote():
    batch_id = worker.criar_lote(BETA, "CT-001", "revisao.pdf", pdf(*LOTE))
    worker.processar_lote(batch_id, provedor=TextLayerProvider())
    return batch_id


def _doc_with_pages(batch_id, pages):
    return next(item for item in documentos(batch_id) if item["paginas"] == pages)


def _insert_batch(status="FALHA_PROCESSAMENTO", uploaded_by="u-oper-beta", contract_id="CT-001"):
    with db.tx() as conn:
        return conn.execute(
            "INSERT INTO batches (contract_id, uploaded_by, filename, arquivo, sha256, tipo_arquivo, "
            "status, total_pages, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (contract_id, uploaded_by, "reprocess.pdf", str(config.UPLOAD_DIR / "x.pdf"), "hash",
             "PDF", status, 1, db.agora()),
        ).lastrowid


def test_approve_rejects_substituted_and_unknown_documents(banco):
    batch_id = _api_lote()
    substituted = _doc_with_pages(batch_id, [1, 2])
    unknown = _doc_with_pages(batch_id, [6])
    with db.tx() as conn:
        conn.execute("UPDATE documents SET status='SUBSTITUIDO' WHERE id=?", (substituted["id"],))
    with TestClient(app) as client:
        old_result = client.patch(f"/api/documents/{substituted['id']}/review",
                                  headers=_headers(), json={"acao": "aprovar"})
        unknown_result = client.patch(f"/api/documents/{unknown['id']}/review",
                                      headers=_headers(), json={"acao": "aprovar"})
    assert old_result.status_code == 409
    assert unknown_result.status_code == 422


def test_approve_saves_corrections_and_resolves_open_issues(banco):
    batch_id = _api_lote()
    doc = _doc_with_pages(batch_id, [6])
    with db.tx() as conn:
        conn.execute("UPDATE documents SET status='PENDENTE_CORRECAO' WHERE id=?", (doc["id"],))
        issue_id = conn.execute(
            "INSERT INTO issues (contract_id, document_id, categoria, motivo, acao, status, "
            "created_at, updated_at, historico_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("CT-001", doc["id"], "SOLICITADA_NA_REVISAO", "motivo", "corrigir", "NOTIFICADA",
             db.agora(), db.agora(), '[{"status":"NOTIFICADA"}]'),
        ).lastrowid
    with TestClient(app) as client:
        response = client.patch(
            f"/api/documents/{doc['id']}/review", headers=_headers(),
            json={"acao": "aprovar", "tipo": "HOLERITE", "trabalhador_id": "T001",
                  "competencia": "11/2026"},
        )
    assert response.status_code == 200
    with db.tx() as conn:
        saved = conn.execute("SELECT * FROM documents WHERE id=?", (doc["id"],)).fetchone()
        issue = conn.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()
    assert (saved["tipo"], saved["worker_id"], saved["competencia"]) == ("HOLERITE", "T001", "11/2026")
    assert saved["status"] == "APTO" and saved["revisado_por"] == "u-analista"
    assert saved["motivos_pendencia"] == "[]"
    assert issue["status"] == "RESOLVIDA"
    assert json.loads(issue["historico_json"])[-1]["motivo"] == "resolvida na revisão"


def test_approve_validates_worker_and_competencia(banco):
    batch_id = _api_lote()
    doc = _doc_with_pages(batch_id, [6])
    with TestClient(app) as client:
        worker_result = client.patch(
            f"/api/documents/{doc['id']}/review", headers=_headers(),
            json={"acao": "aprovar", "tipo": "HOLERITE", "trabalhador_id": "T101",
                  "competencia": "10/2026"},
        )
        competence_result = client.patch(
            f"/api/documents/{doc['id']}/review", headers=_headers(),
            json={"acao": "aprovar", "tipo": "HOLERITE", "trabalhador_id": "T001",
                  "competencia": "2026-10"},
        )
    assert worker_result.status_code == competence_result.status_code == 422


def test_structured_field_review_preserves_history_and_reconciles(banco, monkeypatch):
    from docrisk_core.rules import conciliacao

    batch_id = _api_lote()
    doc = _doc_with_pages(batch_id, [3, 4])
    original = json.loads(doc["campos_json"])
    calls = []
    monkeypatch.setattr(conciliacao, "conciliar",
                        lambda conn, contract_id, worker_id, competencia:
                        calls.append((contract_id, worker_id, competencia)))
    with TestClient(app) as client:
        first = client.patch(
            f"/api/documents/{doc['id']}/review", headers=_headers(),
            json={"acao": "corrigir_campos", "campos": {"horas_extras_h": 10,
                                                              "horas_extras_valor": 150.5},
                  "motivo": "Conferido no comprovante", "fonte": "Holerite, página 2"},
        )
        second = client.patch(
            f"/api/documents/{doc['id']}/review", headers=_headers(),
            json={"acao": "corrigir_campos", "campos": {"horas_extras_h": 11},
                  "motivo": "Segunda conferência", "fonte": "Espelho de ponto, página 4"},
        )
        detail = client.get(f"/api/documents/{doc['id']}", headers=_headers())

    assert first.status_code == second.status_code == detail.status_code == 200
    assert calls == [("CT-001", "T001", "10/2026")] * 2
    reviews = detail.json()["revisoes_campos"]
    assert [r["revision_number"] for r in reviews] == [1, 2, 3]
    assert all(r["author_id"] == "u-analista" and r["document_version"] == doc["versao"]
               for r in reviews)
    assert reviews[0]["valor_original"] == original["horas_extras_h"]
    assert reviews[0]["valor_corrigido"] == 10
    assert reviews[1]["valor_original"] == original["horas_extras_valor"]
    assert reviews[1]["valor_corrigido"] == 150.5
    assert reviews[2]["valor_original"] == 10 and reviews[2]["valor_corrigido"] == 11
    assert reviews[0]["reason"] == "Conferido no comprovante"
    assert reviews[0]["source"] == "Holerite, página 2"
    assert detail.json()["campos"]["horas_extras_h"] == 11
    assert detail.json()["campos"]["horas_extras_valor"] == 150.5


def test_structured_field_review_validates_and_hides_history_from_supplier(banco):
    batch_id = _api_lote()
    doc = _doc_with_pages(batch_id, [3, 4])
    before = json.loads(doc["campos_json"])
    with TestClient(app) as client:
        missing_reason = client.patch(
            f"/api/documents/{doc['id']}/review", headers=_headers(),
            json={"acao": "corrigir_campos", "campos": {"horas_extras_h": 9},
                  "fonte": "página 2"},
        )
        unknown_field = client.patch(
            f"/api/documents/{doc['id']}/review", headers=_headers(),
            json={"acao": "corrigir_campos", "campos": {"cpf": "123"},
                  "motivo": "Conferência", "fonte": "página 2"},
        )
        negative_value = client.patch(
            f"/api/documents/{doc['id']}/review", headers=_headers(),
            json={"acao": "corrigir_campos", "campos": {"horas_extras_h": -2},
                  "motivo": "Conferência", "fonte": "página 2"},
        )
        corrected = client.patch(
            f"/api/documents/{doc['id']}/review", headers=_headers(),
            json={"acao": "corrigir_campos", "campos": {"horas_extras_h": 9},
                  "motivo": "Conferência", "fonte": "página 2"},
        )
        supplier_detail = client.get(f"/api/documents/{doc['id']}", headers=_headers("u-oper-beta"))

    assert missing_reason.status_code == unknown_field.status_code == negative_value.status_code == 422
    assert corrected.status_code == supplier_detail.status_code == 200
    assert "revisoes_campos" not in supplier_detail.json()
    assert q("SELECT COUNT(*) AS n FROM document_field_reviews WHERE document_id=?", doc["id"])[0]["n"] == 1
    assert json.loads(q("SELECT campos_json FROM documents WHERE id=?", doc["id"])[0]["campos_json"])[
        "horas_extras_valor"] == before["horas_extras_valor"]


def test_approve_and_request_correction_reconcile_affected_pair(banco, monkeypatch):
    from docrisk_core.rules import conciliacao

    batch_id = _api_lote()
    doc = _doc_with_pages(batch_id, [3, 4])
    with db.tx() as conn:
        conn.execute("UPDATE documents SET status='REVISAO_HUMANA' WHERE id=?", (doc["id"],))
    calls = []
    monkeypatch.setattr(conciliacao, "conciliar",
                        lambda conn, contract_id, worker_id, competencia:
                        calls.append((contract_id, worker_id, competencia)))
    with TestClient(app) as client:
        approved = client.patch(
            f"/api/documents/{doc['id']}/review", headers=_headers(),
            json={"acao": "aprovar", "trabalhador_id": "T002", "competencia": "11/2026"},
        )
        correction = client.patch(
            f"/api/documents/{doc['id']}/review", headers=_headers(),
            json={"acao": "solicitar_correcao", "motivo": "Verificar", "acao_solicitada": "Reenviar"},
        )
    assert approved.status_code == correction.status_code == 200
    assert calls == [("CT-001", "T001", "10/2026"), ("CT-001", "T002", "11/2026"),
                     ("CT-001", "T002", "11/2026")]


def test_approve_substitutes_existing_document_for_corrected_pair(banco):
    batch_id = _api_lote()
    point = _doc_with_pages(batch_id, [3, 4])
    with db.tx() as conn:
        conn.execute("UPDATE documents SET status='REVISAO_HUMANA' WHERE id=?", (point["id"],))
        prior_id = conn.execute(
            "INSERT INTO documents (batch_id, contract_id, tipo, worker_id, competencia, status, "
            "confianca, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (batch_id, "CT-001", "HOLERITE", "T002", "11/2026", "APTO", 0.9,
             db.agora(), db.agora()),
        ).lastrowid
    with TestClient(app) as client:
        response = client.patch(
            f"/api/documents/{point['id']}/review", headers=_headers(),
            json={"acao": "aprovar", "tipo": "HOLERITE", "trabalhador_id": "T002",
                  "competencia": "11/2026"},
        )
    assert response.status_code == 200
    with db.tx() as conn:
        prior = conn.execute("SELECT status FROM documents WHERE id=?", (prior_id,)).fetchone()
    assert prior["status"] == "SUBSTITUIDO"


def test_request_correction_rejects_pending_document(banco):
    batch_id = _api_lote()
    doc = _doc_with_pages(batch_id, [7])
    # A F3 já abre a pendência de ilegível na consolidação; o pedido recusado não pode criar outra.
    antes = q("SELECT COUNT(*) AS n FROM issues WHERE document_id=?", doc["id"])[0]["n"]
    with TestClient(app) as client:
        response = client.patch(
            f"/api/documents/{doc['id']}/review", headers=_headers(),
            json={"acao": "solicitar_correcao", "motivo": "Outra", "acao_solicitada": "Reenviar"},
        )
    assert response.status_code == 409
    assert q("SELECT COUNT(*) AS n FROM issues WHERE document_id=?", doc["id"])[0]["n"] == antes


def test_review_routes_use_f2_split_and_merge(banco):
    batch_id = _api_lote()
    point = _doc_with_pages(batch_id, [3, 4])
    with TestClient(app) as client:
        split = client.patch(f"/api/documents/{point['id']}/review", headers=_headers(),
                             json={"acao": "dividir", "apos_pagina": 1})
        assert split.status_code == 200
        new_doc = next(d for d in documentos(batch_id) if d["paginas"] == [4])
        merge = client.patch(f"/api/documents/{point['id']}/review", headers=_headers(),
                             json={"acao": "unir_proximo"})
        final_doc = _doc_with_pages(batch_id, [8])
        last = client.patch(f"/api/documents/{final_doc['id']}/review", headers=_headers(),
                            json={"acao": "unir_proximo"})
    assert merge.status_code == 200
    assert last.status_code == 409
    assert new_doc["id"] != point["id"]


def test_document_lists_include_pages(banco):
    batch_id = _api_lote()
    doc = _doc_with_pages(batch_id, [3, 4])
    with db.tx() as conn:
        conn.execute("UPDATE documents SET status='REVISAO_HUMANA' WHERE id=?", (doc["id"],))
    with TestClient(app) as client:
        batch_response = client.get(f"/api/batches/{batch_id}/documents", headers=_headers())
        queue_response = client.get("/api/review-queue", headers=_headers())
    batch_doc = next(item for item in batch_response.json() if item["id"] == doc["id"])
    queue_doc = next(item for item in queue_response.json() if item["id"] == doc["id"])
    expected = [
        {"page_id": page["id"], "ordem": page["ordem"]} for page in q(
            "SELECT p.id, p.ordem FROM doc_pages dp JOIN pages p ON p.id=dp.page_id "
            "WHERE dp.document_id=? ORDER BY dp.posicao", doc["id"]
        )
    ]
    assert batch_doc["paginas"] == queue_doc["paginas"] == expected


def test_reprocess_authorization_and_status(banco, monkeypatch):
    failed = _insert_batch()
    completed = _insert_batch(status="CONCLUIDO")
    queued = []
    monkeypatch.setattr(worker, "enfileirar", queued.append)
    with TestClient(app) as client:
        cross_org = client.post(f"/api/batches/{failed}/reprocess", headers=_headers("u-oper-gama"))
        invalid_status = client.post(f"/api/batches/{completed}/reprocess", headers=_headers())
        accepted = client.post(f"/api/batches/{failed}/reprocess", headers=_headers())
    assert cross_org.status_code == 404
    assert invalid_status.status_code == 409
    assert accepted.status_code == 202 and queued == [failed]


def test_resubmit_updates_issue_status_and_history(banco, monkeypatch):
    with db.tx() as conn:
        issue_id = conn.execute(
            "INSERT INTO issues (contract_id, categoria, motivo, acao, status, created_at, updated_at) "
            "VALUES ('CT-001', 'ILEGIVEL', 'ilegível', 'reenviar', 'NOTIFICADA', ?, ?)",
            (db.agora(), db.agora()),
        ).lastrowid
    monkeypatch.setattr(worker, "criar_lote", lambda *args, **kwargs: 555)
    monkeypatch.setattr(worker, "enfileirar", lambda batch_id: None)
    with TestClient(app) as client:
        response = client.post(f"/api/issues/{issue_id}/resubmit", headers=_headers("u-oper-beta"),
                               files={"file": ("reenviado.pdf", b"fake")})
    assert response.status_code == 202
    with db.tx() as conn:
        issue = conn.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()
    assert issue["status"] == "REENVIADA"
    assert json.loads(issue["historico_json"])[-1]["lote"] == 555


def test_resubmit_does_not_overwrite_f3_resolution(banco, monkeypatch):
    with db.tx() as conn:
        issue_id = conn.execute(
            "INSERT INTO issues (contract_id, categoria, motivo, acao, status, created_at, updated_at, "
            "historico_json) VALUES ('CT-001', 'ILEGIVEL', 'ilegível', 'reenviar', 'NOTIFICADA', ?, ?, '[]')",
            (db.agora(), db.agora()),
        ).lastrowid

    def resolve_during_enqueue(batch_id):
        with db.tx() as conn:
            conn.execute("UPDATE issues SET status='RESOLVIDA', historico_json='[{\"status\":\"RESOLVIDA\"}]' "
                         "WHERE id=?", (issue_id,))

    monkeypatch.setattr(worker, "criar_lote", lambda *args, **kwargs: 555)
    monkeypatch.setattr(worker, "enfileirar", resolve_during_enqueue)
    with TestClient(app) as client:
        response = client.post(f"/api/issues/{issue_id}/resubmit", headers=_headers("u-oper-beta"),
                               files={"file": ("reenviado.pdf", b"fake")})
    assert response.status_code == 202
    with db.tx() as conn:
        issue = conn.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()
    assert issue["status"] == "RESOLVIDA"
    assert json.loads(issue["historico_json"]) == [{"status": "RESOLVIDA"}]


def test_reports_are_restricted_and_json_is_decoded(banco):
    with db.tx() as conn:
        report_id = conn.execute(
            "INSERT INTO reports (contract_id, competencia, versao, status, conteudo_json, autor_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("CT-001", "10/2026", 1, "RASCUNHO", '{"total": 2}', "u-analista", db.agora()),
        ).lastrowid
        published_id = conn.execute(
            "INSERT INTO reports (contract_id, competencia, versao, status, conteudo_json, autor_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("CT-001", "10/2026", 2, "APROVADO_PUBLICADO", '{"published": true}',
             "u-analista", db.agora()),
        ).lastrowid
        review_id = conn.execute(
            "INSERT INTO reports (contract_id, competencia, versao, status, conteudo_json, autor_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("CT-001", "10/2026", 3, "EM_REVISAO", '{"review": true}', "u-analista", db.agora()),
        ).lastrowid
        replaced_id = conn.execute(
            "INSERT INTO reports (contract_id, competencia, versao, status, conteudo_json, autor_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("CT-001", "10/2026", 4, "SUBSTITUIDO_POR_VERSAO", '{"old": true}',
             "u-analista", db.agora()),
        ).lastrowid
    with TestClient(app) as client:
        forbidden = client.get("/api/reports", headers=_headers("u-oper-beta"))
        visible = client.get("/api/reports", headers=_headers())
        client_reports = client.get("/api/client/reports", headers=_headers("u-gestor-alfa"))
    assert forbidden.status_code == 403
    assert next(item for item in visible.json() if item["id"] == report_id)["conteudo_json"] == {"total": 2}
    assert next(item for item in client_reports.json()
                if item["id"] == published_id)["conteudo_json"] == {"published": True}
    visible_ids = {item["id"] for item in visible.json()}
    assert {review_id, replaced_id}.issubset(visible_ids)

def test_publish_new_report_version_replaces_previous(banco, monkeypatch):
    from docrisk_core.routes import parecer

    with db.tx() as conn:
        previous_id = conn.execute(
            "INSERT INTO reports (contract_id, competencia, versao, status, "
            "conteudo_json, autor_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "CT-001", "10/2026", 1, "APROVADO_PUBLICADO",
                '{"versao": 1}', "u-analista", db.agora(),
            ),
        ).lastrowid

    monkeypatch.setattr(
        parecer,
        "snapshot_parecer",
        lambda conn, contract_id, competencia: {"versao": 2},
    )

    with TestClient(app) as client:
        create_response = client.post(
            "/api/reports",
            headers=_headers(),
            json={"contract_id": "CT-001", "competencia": "10/2026"},
        )

        assert create_response.status_code == 201, create_response.text
        new_report = create_response.json()
        assert new_report["versao"] == 2
        assert new_report["status"] == "RASCUNHO"

        publish_response = client.post(
            f"/api/reports/{new_report['id']}/publish",
            headers=_headers(),
        )

    assert publish_response.status_code == 200, publish_response.text

    with db.tx() as conn:
        previous = conn.execute(
            "SELECT status FROM reports WHERE id=?", (previous_id,)
        ).fetchone()
        current = conn.execute(
            "SELECT status, versao, conteudo_json FROM reports WHERE id=?",
            (new_report["id"],),
        ).fetchone()

    assert previous["status"] == "SUBSTITUIDO_POR_VERSAO"
    assert current["status"] == "APROVADO_PUBLICADO"
    assert current["versao"] == 2
    assert json.loads(current["conteudo_json"]) == {"versao": 2}

def test_search_snippet_uses_neutral_markers(banco):
    batch_id = _insert_batch(status="CONCLUIDO")
    with db.tx() as conn:
        page_id = conn.execute(
            "INSERT INTO pages (batch_id, ordem, image_path, sha256) "
            "VALUES (?, 99, 'x.png', 'x')", (batch_id,)
        ).lastrowid
        conn.execute("INSERT INTO page_fts (texto, page_id, contract_id) VALUES (?, ?, ?)",
                     ("A&B malicious search text", page_id, "CT-001"))
    with TestClient(app) as client:
        response = client.get("/api/search?q=malicious", headers=_headers("u-oper-beta"))
    assert response.status_code == 200
    assert "A&B [[malicious]]" in response.text
    assert "&amp;" not in response.text

def test_resubmit_processes_real_batch_sync(banco, monkeypatch):
    from docrisk_core.routes import worker as route_worker

    with db.tx() as conn:
        issue_id = conn.execute(
            "INSERT INTO issues (contract_id, categoria, motivo, acao, status, "
            "created_at, updated_at, historico_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("CT-001", "ILEGIVEL", "ilegível", "reenviar", "NOTIFICADA",
             db.agora(), db.agora(), "[]"),
        ).lastrowid

    monkeypatch.setattr(config, "SYNC", True)

    with TestClient(app) as client:
        response = client.post(
            f"/api/issues/{issue_id}/resubmit",
            headers=_headers("u-oper-beta"),
            files={"file": ("reenviado.pdf", pdf(*LOTE))},
        )

    assert response.status_code == 202
    batch_id = response.json()["batch_id"]

    with db.tx() as conn:
        batch = conn.execute(
            "SELECT status FROM batches WHERE id=?", (batch_id,)
        ).fetchone()

    assert batch["status"] == "CONCLUIDO"

def test_resubmit_enqueues_batch_async(banco, monkeypatch):
    from docrisk_core.routes import worker as route_worker

    with db.tx() as conn:
        issue_id = conn.execute(
            "INSERT INTO issues (contract_id, categoria, motivo, acao, status, "
            "created_at, updated_at, historico_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("CT-001", "ILEGIVEL", "ilegível", "reenviar", "NOTIFICADA",
             db.agora(), db.agora(), "[]"),
        ).lastrowid

    queued = []
    monkeypatch.setattr(config, "SYNC", False)
    monkeypatch.setattr(route_worker, "enfileirar", queued.append)

    with TestClient(app) as client:
        response = client.post(
            f"/api/issues/{issue_id}/resubmit",
            headers=_headers("u-oper-beta"),
            files={"file": ("reenviado.pdf", pdf(*LOTE))},
        )

    assert response.status_code == 202
    assert queued == [response.json()["batch_id"]]

def test_resubmit_repetido_nao_cria_lote_duplicado(banco, monkeypatch):
    with db.tx() as conn:
        issue_id = conn.execute(
            "INSERT INTO issues (contract_id, categoria, motivo, acao, "
            "status, created_at, updated_at, historico_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "CT-001", "ILEGIVEL", "ilegível", "reenviar",
                "NOTIFICADA", db.agora(), db.agora(), "[]",
            ),
        ).lastrowid

    criados = []
    enfileirados = []

    def criar_lote(*args, **kwargs):
        batch_id = 700 + len(criados)
        criados.append(batch_id)
        return batch_id

    monkeypatch.setattr(worker, "criar_lote", criar_lote)
    monkeypatch.setattr(worker, "enfileirar", enfileirados.append)

    with TestClient(app) as client:
        primeira = client.post(
            f"/api/issues/{issue_id}/resubmit",
            headers=_headers("u-oper-beta"),
            files={"file": ("reenviado.pdf", b"fake")},
        )
        segunda = client.post(
            f"/api/issues/{issue_id}/resubmit",
            headers=_headers("u-oper-beta"),
            files={"file": ("reenviado.pdf", b"fake")},
        )

    assert primeira.status_code == 202, primeira.text
    assert segunda.status_code == 409, segunda.text
    assert len(criados) == 1
    assert enfileirados == criados

    with db.tx() as conn:
        issue = conn.execute(
            "SELECT status, historico_json FROM issues WHERE id=?",
            (issue_id,),
        ).fetchone()

    assert issue["status"] == "REENVIADA"
    assert len(json.loads(issue["historico_json"])) == 1
