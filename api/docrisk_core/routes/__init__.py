"""Rotas da API F1: autenticação, isolamento por contrato e fluxos de revisão."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from .. import config, db
from ..auth import (Usuario, auditar, contratos_do_usuario, exigir_contrato,
                    exigir_papel, usuario_atual)
from ..contracts import (CategoriaPendencia, PAPEIS_BERNHOEFT, PAPEIS_FORNECEDORA,
                         Papel, StatusDocumento, StatusParecer, StatusPendencia)
from ..pipeline.render import ArquivoInvalido
from ..pipeline import worker
from ..rules import metricas, parecer

router = APIRouter()


def get_conn():
    conn = db.connect()
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _rows(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def _json_list(value: str | None) -> list[Any]:
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def _json_object(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _contract_or_404(conn: sqlite3.Connection, user: Usuario, contract_id: str) -> None:
    exigir_contrato(conn, user, contract_id)


def _batch_or_404(conn: sqlite3.Connection, user: Usuario, batch_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM batches WHERE id=?", (batch_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Lote não encontrado")
    _contract_or_404(conn, user, row["contract_id"])
    return row


def _document_or_404(conn: sqlite3.Connection, user: Usuario, document_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Documento não encontrado")
    _contract_or_404(conn, user, row["contract_id"])
    return row


def _require_ber_user(user: Usuario) -> None:
    exigir_papel(user, PAPEIS_BERNHOEFT)


def _require_batch_reader(user: Usuario) -> None:
    exigir_papel(user, [*PAPEIS_FORNECEDORA, *PAPEIS_BERNHOEFT])


@router.get("/api/demo/users")
def demo_users(conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, str]]:
    if not config.DEMO_MODE:
        raise HTTPException(404, "Rota não encontrada")
    rows = conn.execute(
        "SELECT u.id, u.nome, u.org_id, o.tipo AS org_tipo, u.role, u.token "
        "FROM users u JOIN organizations o ON o.id=u.org_id WHERE u.ativo=1 ORDER BY u.rowid"
    ).fetchall()
    return _rows(rows)


@router.get("/api/me")
def me(user: Usuario = Depends(usuario_atual)) -> dict[str, str]:
    return {"id": user.id, "nome": user.nome, "org_id": user.org_id,
            "org_tipo": user.org_tipo, "papel": user.papel.value}


@router.get("/api/contracts")
def list_contracts(user: Usuario = Depends(usuario_atual),
                   conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    ids = contratos_do_usuario(conn, user)
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    return _rows(conn.execute(
        f"SELECT id, nome, contratante_id, fornecedora_id, bernhoeft_id, prazo_correcao_dias "
        f"FROM contracts WHERE id IN ({marks}) ORDER BY id", ids).fetchall())


@router.post("/api/supplier/batches", status_code=202)
async def upload_batch(contract_id: str = Form(...), file: UploadFile = File(...),
                       user: Usuario = Depends(usuario_atual),
                       conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, int | str]:
    exigir_papel(user, PAPEIS_FORNECEDORA)
    _contract_or_404(conn, user, contract_id)
    data = await file.read(config.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if not data or len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(422, "Arquivo vazio ou acima do limite de upload")
    try:
        batch_id = worker.criar_lote(user, contract_id, file.filename or "arquivo", data)
        worker.enfileirar(batch_id)
    except ArquivoInvalido as exc:
        raise HTTPException(422, str(exc)) from exc
    except NotImplementedError as exc:
        raise HTTPException(503, "Processamento de lotes ainda não está disponível (F2)") from exc
    auditar(conn, user, "LOTE_ENVIADO", str(batch_id))
    return {"batch_id": batch_id, "status": "RECEBIDO"}


@router.get("/api/batches")
def list_batches(user: Usuario = Depends(usuario_atual),
                 conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    _require_batch_reader(user)
    ids = contratos_do_usuario(conn, user)
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    return _rows(conn.execute(
        f"SELECT id, contract_id, uploaded_by, filename, tipo_arquivo, status, total_pages, "
        f"issue_id, erro, created_at, finished_at FROM batches WHERE contract_id IN ({marks}) "
        "ORDER BY id DESC", ids).fetchall())


@router.get("/api/batches/{batch_id}")
def get_batch(batch_id: int, user: Usuario = Depends(usuario_atual),
              conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    _require_batch_reader(user)
    row = _batch_or_404(conn, user, batch_id)
    return {key: row[key] for key in (
        "id", "contract_id", "uploaded_by", "filename", "sha256", "tipo_arquivo", "status",
        "total_pages", "issue_id", "erro", "created_at", "finished_at")}


@router.get("/api/batches/{batch_id}/documents")
def batch_documents(batch_id: int, user: Usuario = Depends(usuario_atual),
                    conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    _require_batch_reader(user)
    _batch_or_404(conn, user, batch_id)
    rows = conn.execute("SELECT * FROM documents WHERE batch_id=? ORDER BY id", (batch_id,)).fetchall()
    results = []
    for row in rows:
        item = dict(row)
        item["motivos_pendencia"] = _json_list(item["motivos_pendencia"])
        item["motivos_revisao"] = _json_list(item["motivos_revisao"])
        item["campos"] = _json_object(item.pop("campos_json"))
        if user.org_tipo == "FORNECEDORA":
            if item["status"] == StatusDocumento.REVISAO_HUMANA.value:
                item["status"] = "EM_ANALISE"
            item.pop("motivos_revisao", None)
            item["campos"] = {}
            item.pop("confianca", None)
        results.append(item)
    return results


@router.get("/api/pages/{page_id}/image")
def page_image(page_id: int, user: Usuario = Depends(usuario_atual),
               conn: sqlite3.Connection = Depends(get_conn)) -> FileResponse:
    row = conn.execute(
        "SELECT p.image_path, b.contract_id FROM pages p JOIN batches b ON b.id=p.batch_id "
        "WHERE p.id=?", (page_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Página não encontrada")
    _contract_or_404(conn, user, row["contract_id"])
    if user.org_tipo == "CONTRATANTE":
        raise HTTPException(403, "A contratante não tem acesso às imagens de páginas")
    path = Path(row["image_path"]).resolve()
    try:
        path.relative_to(config.PAGES_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(404, "Imagem não encontrada") from exc
    if not path.is_file():
        raise HTTPException(404, "Imagem não encontrada")
    return FileResponse(path, media_type="image/png", filename=f"pagina-{page_id}.png")


@router.get("/api/review-queue")
def review_queue(user: Usuario = Depends(usuario_atual),
                 conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    exigir_papel(user, [Papel.ANALISTA_BH])
    ids = contratos_do_usuario(conn, user)
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT * FROM documents WHERE status=? AND contract_id IN ({marks}) ORDER BY created_at",
        [StatusDocumento.REVISAO_HUMANA.value, *ids]).fetchall()
    result = _rows(rows)
    for item in result:
        item["motivos_pendencia"] = _json_list(item["motivos_pendencia"])
        item["motivos_revisao"] = _json_list(item["motivos_revisao"])
        item["campos"] = _json_object(item.pop("campos_json"))
    return result


@router.patch("/api/documents/{document_id}/review")
def review_document(document_id: int, payload: dict[str, Any],
                    user: Usuario = Depends(usuario_atual),
                    conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    exigir_papel(user, [Papel.ANALISTA_BH])
    doc = _document_or_404(conn, user, document_id)
    action = str(payload.get("acao", "")).strip().lower()
    now = db.agora()
    if action == "aprovar":
        conn.execute("UPDATE documents SET status=?, revisado_por=?, updated_at=? WHERE id=?",
                     (StatusDocumento.APTO.value, user.id, now, document_id))
    elif action == "solicitar_correcao":
        motivo = str(payload.get("motivo", "")).strip()
        acao = str(payload.get("acao_solicitada", "")).strip()
        if not motivo or not acao:
            raise HTTPException(422, "Informe motivo e ação solicitada")
        conn.execute("UPDATE documents SET status=?, revisado_por=?, updated_at=? WHERE id=?",
                     (StatusDocumento.PENDENTE_CORRECAO.value, user.id, now, document_id))
        conn.execute(
            "INSERT INTO issues (contract_id, document_id, worker_id, competencia, tipo_documento, "
            "categoria, motivo, evidencia, acao, status, prazo, created_at, updated_at) "
            "SELECT contract_id, id, worker_id, competencia, tipo, ?, ?, ?, ?, ?, "
            "datetime('now', '+' || (SELECT prazo_correcao_dias FROM contracts WHERE id=?) || ' days'), ?, ? "
            "FROM documents WHERE id=?",
            (CategoriaPendencia.SOLICITADA_NA_REVISAO.value, motivo, f"documento:{document_id}",
             acao, StatusPendencia.NOTIFICADA.value, doc["contract_id"], now, now, document_id))
    elif action in {"dividir", "unir_proximo"}:
        _edit_document_pages(conn, user, doc, document_id, action, payload, now)
    else:
        raise HTTPException(422, "Ação deve ser aprovar, dividir, unir_proximo ou solicitar_correcao")
    auditar(conn, user, f"DOCUMENTO_{action.upper()}", str(document_id))
    return {"document_id": document_id, "acao": action, "status": conn.execute(
        "SELECT status FROM documents WHERE id=?", (document_id,)).fetchone()[0]}


def _edit_document_pages(conn: sqlite3.Connection, user: Usuario, doc: sqlite3.Row,
                          document_id: int, action: str, payload: dict[str, Any], now: str) -> None:
    docs = conn.execute("SELECT id, batch_id FROM documents WHERE batch_id=? AND contract_id=? "
                        "AND status<>? ORDER BY id", (doc["batch_id"], doc["contract_id"],
                                                       StatusDocumento.SUBSTITUIDO.value)).fetchall()
    pages = conn.execute(
        "SELECT dp.page_id, dp.posicao, p.ordem FROM doc_pages dp JOIN pages p ON p.id=dp.page_id "
        "WHERE dp.document_id=? ORDER BY dp.posicao", (document_id,)).fetchall()
    if action == "dividir":
        split_after = payload.get("apos_pagina")
        if not isinstance(split_after, int) or not 1 <= split_after < len(pages):
            raise HTTPException(422, "apos_pagina deve indicar a posição interna de divisão")
        first, second = pages[:split_after], pages[split_after:]
        conn.execute("DELETE FROM doc_pages WHERE document_id=?", (document_id,))
        conn.executemany("INSERT INTO doc_pages (document_id, page_id, posicao) VALUES (?, ?, ?)",
                         [(document_id, row["page_id"], i) for i, row in enumerate(first, 1)])
        cur = conn.execute(
            "INSERT INTO documents (batch_id, contract_id, tipo, worker_id, competencia, status, "
            "confianca, motivos_pendencia, motivos_revisao, campos_json, versao, substitui_id, "
            "revisado_por, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (doc["batch_id"], doc["contract_id"], doc["tipo"], doc["worker_id"], doc["competencia"],
             StatusDocumento.REVISAO_HUMANA.value, doc["confianca"], "[]", "[]", doc["campos_json"],
             doc["versao"], document_id, user.id, now, now))
        new_id = cur.lastrowid
        conn.executemany("INSERT INTO doc_pages (document_id, page_id, posicao) VALUES (?, ?, ?)",
                         [(new_id, row["page_id"], i) for i, row in enumerate(second, 1)])
        conn.execute("UPDATE documents SET status=?, revisado_por=?, updated_at=? WHERE id=?",
                     (StatusDocumento.REVISAO_HUMANA.value, user.id, now, document_id))
    else:
        next_doc = conn.execute(
            "SELECT d.* FROM documents d JOIN (SELECT MIN(id) id FROM documents WHERE batch_id=? "
            "AND id>? AND status<>?) n ON n.id=d.id",
            (doc["batch_id"], document_id, StatusDocumento.SUBSTITUIDO.value)).fetchone()
        if next_doc is None:
            raise HTTPException(422, "Não há próximo documento para unir")
        _contract_or_404(conn, user, next_doc["contract_id"])
        if next_doc["contract_id"] != doc["contract_id"]:
            raise HTTPException(422, "Os documentos precisam pertencer ao mesmo contrato")
        next_pages = conn.execute("SELECT page_id FROM doc_pages WHERE document_id=? ORDER BY posicao",
                                  (next_doc["id"],)).fetchall()
        conn.executemany("INSERT INTO doc_pages (document_id, page_id, posicao) VALUES (?, ?, ?)",
                         [(document_id, row["page_id"], len(pages) + i)
                          for i, row in enumerate(next_pages, 1)])
        conn.execute("UPDATE documents SET status=?, revisado_por=?, updated_at=? WHERE id=?",
                     (StatusDocumento.SUBSTITUIDO.value, user.id, now, next_doc["id"]))
        conn.execute("UPDATE documents SET status=?, revisado_por=?, updated_at=? WHERE id=?",
                     (StatusDocumento.REVISAO_HUMANA.value, user.id, now, document_id))


@router.get("/api/supplier/issues")
def supplier_issues(user: Usuario = Depends(usuario_atual),
                    conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    exigir_papel(user, PAPEIS_FORNECEDORA)
    ids = contratos_do_usuario(conn, user)
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    return _rows(conn.execute(f"SELECT * FROM issues WHERE contract_id IN ({marks}) ORDER BY id DESC",
                              ids).fetchall())


@router.get("/api/issues")
def issues(user: Usuario = Depends(usuario_atual),
           conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    _require_ber_user(user)
    ids = contratos_do_usuario(conn, user)
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    return _rows(conn.execute(f"SELECT * FROM issues WHERE contract_id IN ({marks}) ORDER BY id DESC",
                              ids).fetchall())


@router.get("/api/analyses")
def analyses(user: Usuario = Depends(usuario_atual),
             conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    _require_ber_user(user)
    ids = contratos_do_usuario(conn, user)
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    return _rows(conn.execute(f"SELECT * FROM analyses WHERE contract_id IN ({marks}) ORDER BY id DESC",
                              ids).fetchall())


@router.post("/api/issues/{issue_id}/resubmit", status_code=202)
async def resubmit_issue(issue_id: int, file: UploadFile = File(...),
                         user: Usuario = Depends(usuario_atual),
                         conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, int | str]:
    exigir_papel(user, PAPEIS_FORNECEDORA)
    issue = conn.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()
    if issue is None:
        raise HTTPException(404, "Pendência não encontrada")
    _contract_or_404(conn, user, issue["contract_id"])
    data = await file.read(config.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if not data or len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(422, "Arquivo vazio ou acima do limite de upload")
    try:
        batch_id = worker.criar_lote(user, issue["contract_id"], file.filename or "arquivo", data,
                                     issue_id=issue_id)
        worker.enfileirar(batch_id)
    except ArquivoInvalido as exc:
        raise HTTPException(422, str(exc)) from exc
    except NotImplementedError as exc:
        raise HTTPException(503, "Reenvio ainda não está disponível (F2)") from exc
    auditar(conn, user, "PENDENCIA_REENVIADA", str(issue_id))
    return {"batch_id": batch_id, "issue_id": issue_id, "status": "RECEBIDO"}


@router.get("/api/search")
def search(q: str = Query(min_length=1, max_length=250),
          user: Usuario = Depends(usuario_atual),
          conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    if user.org_tipo == "CONTRATANTE":
        raise HTTPException(403, "Busca textual não está disponível para a contratante")
    ids = contratos_do_usuario(conn, user)
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    try:
        rows = conn.execute(
            f"SELECT f.page_id, f.contract_id, snippet(page_fts, 0, '<b>', '</b>', '…', 12) AS trecho "
            f"FROM page_fts f WHERE page_fts MATCH ? AND f.contract_id IN ({marks}) LIMIT 100",
            (q, *ids)).fetchall()
    except sqlite3.OperationalError as exc:
        raise HTTPException(400, "Consulta de busca inválida") from exc
    return _rows(rows)


@router.post("/api/reports", status_code=201)
def create_report(payload: dict[str, Any], user: Usuario = Depends(usuario_atual),
                  conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    exigir_papel(user, [Papel.ANALISTA_BH])
    contract_id = str(payload.get("contract_id", ""))
    competencia = str(payload.get("competencia", ""))
    if not contract_id or not competencia:
        raise HTTPException(422, "contract_id e competencia são obrigatórios")
    _contract_or_404(conn, user, contract_id)
    latest = conn.execute("SELECT COALESCE(MAX(versao), 0) FROM reports WHERE contract_id=? AND competencia=?",
                          (contract_id, competencia)).fetchone()[0]
    now = db.agora()
    cursor = conn.execute(
        "INSERT INTO reports (contract_id, competencia, versao, status, observacoes, autor_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (contract_id, competencia, latest + 1, StatusParecer.RASCUNHO.value,
         str(payload.get("observacoes", ""))[:2000], user.id, now))
    auditar(conn, user, "PARECER_RASCUNHO_CRIADO", str(cursor.lastrowid))
    return dict(conn.execute("SELECT * FROM reports WHERE id=?", (cursor.lastrowid,)).fetchone())


@router.post("/api/reports/{report_id}/publish")
def publish_report(report_id: int, user: Usuario = Depends(usuario_atual),
                   conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    exigir_papel(user, [Papel.ANALISTA_BH])
    report = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    if report is None:
        raise HTTPException(404, "Parecer não encontrado")
    _contract_or_404(conn, user, report["contract_id"])
    if report["status"] != StatusParecer.RASCUNHO.value:
        raise HTTPException(409, "Somente rascunhos podem ser publicados")
    try:
        snapshot = parecer.snapshot_parecer(conn, report["contract_id"], report["competencia"])
    except NotImplementedError as exc:
        raise HTTPException(503, "Geração de parecer ainda não está disponível (F3)") from exc
    now = db.agora()
    conn.execute("UPDATE reports SET status=?, conteudo_json=?, publicado_em=?, publicado_por=? WHERE id=?",
                 (StatusParecer.APROVADO_PUBLICADO.value, json.dumps(snapshot, ensure_ascii=False),
                  now, user.id, report_id))
    conn.execute("UPDATE reports SET status=? WHERE contract_id=? AND competencia=? AND id<>? "
                 "AND status=?", (StatusParecer.SUBSTITUIDO_POR_VERSAO.value, report["contract_id"],
                                  report["competencia"], report_id,
                                  StatusParecer.APROVADO_PUBLICADO.value))
    auditar(conn, user, "PARECER_PUBLICADO", str(report_id))
    return dict(conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone())


@router.get("/api/client/reports")
def client_reports(user: Usuario = Depends(usuario_atual),
                   conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    exigir_papel(user, [Papel.GESTOR_CONTR])
    ids = contratos_do_usuario(conn, user)
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    return _rows(conn.execute(
        f"SELECT id, contract_id, competencia, versao, status, conteudo_json, publicado_em "
        f"FROM reports WHERE contract_id IN ({marks}) AND status=? ORDER BY publicado_em DESC",
        (*ids, StatusParecer.APROVADO_PUBLICADO.value)).fetchall())


@router.get("/api/bernhoeft/metrics")
def bernhoeft_metrics(user: Usuario = Depends(usuario_atual),
                      conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    _require_ber_user(user)
    ids = contratos_do_usuario(conn, user)
    try:
        return metricas.calcular_metricas(conn, ids)
    except NotImplementedError as exc:
        raise HTTPException(503, "Métricas ainda não estão disponíveis (F3)") from exc


@router.get("/api/audit")
def audit_log(user: Usuario = Depends(usuario_atual),
              conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    exigir_papel(user, [Papel.ADMIN_BH])
    return _rows(conn.execute("SELECT id, user_id, org_id, acao, alvo, resultado, instante "
                              "FROM audit ORDER BY id DESC LIMIT 500").fetchall())
