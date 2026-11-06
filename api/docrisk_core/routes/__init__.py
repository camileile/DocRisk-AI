from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from .. import config, db
from ..auth import (Usuario, auditar, contratos_do_usuario, exigir_contrato,
                    exigir_papel, usuario_atual)
from ..contracts import (CategoriaPendencia, PAPEIS_BERNHOEFT, PAPEIS_FORNECEDORA,
                         TIPOS_FOCO, Papel, StatusDocumento, StatusParecer, StatusPendencia,
                         StatusLote, TipoDocumento)
from ..pipeline.render import ArquivoInvalido
from ..pipeline import integracao_f3 as f3, revisao, worker
from ..rules import metricas, parecer, pendencias

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


def _document_pages(conn: sqlite3.Connection, document_id: int) -> list[dict[str, int]]:
    rows = conn.execute(
        "SELECT p.id AS page_id, p.ordem FROM doc_pages dp "
        "JOIN pages p ON p.id=dp.page_id WHERE dp.document_id=? ORDER BY dp.posicao",
        (document_id,),
    ).fetchall()
    return [{"page_id": int(row["page_id"]), "ordem": int(row["ordem"])} for row in rows]


def _document_pair(document: sqlite3.Row | dict[str, Any]) -> tuple[str, str] | None:
    tipo = document["tipo"]
    foco = {item.value for item in TIPOS_FOCO}
    if tipo in foco and document["worker_id"] and document["competencia"]:
        return str(document["worker_id"]), str(document["competencia"])
    return None


def _reconcile_pairs(conn: sqlite3.Connection, contract_id: str,
                     *pairs: tuple[str, str] | None) -> None:
    for worker_id, competencia in sorted({pair for pair in pairs if pair is not None}):
        f3.conciliar(conn, contract_id, worker_id, competencia)


def _report_result(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["conteudo_json"] = _json_object(result.get("conteudo_json"))
    return result


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


@router.get("/api/contracts/{contract_id}/workers")
def list_workers(contract_id: str, user: Usuario = Depends(usuario_atual),
                 conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    """Trabalhadores (sintéticos) do contrato — Bernhoeft e fornecedora do contrato."""
    _require_batch_reader(user)
    _contract_or_404(conn, user, contract_id)
    return _rows(conn.execute("SELECT id, nome FROM workers WHERE contract_id=? ORDER BY id",
                              (contract_id,)).fetchall())


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
    return [_document_view(conn, user, row) for row in rows]


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
        item["paginas"] = _document_pages(conn, int(item["id"]))
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
        if doc["status"] not in {StatusDocumento.REVISAO_HUMANA.value,
                                 StatusDocumento.PENDENTE_CORRECAO.value}:
            raise HTTPException(409, "Somente documentos em revisão ou pendentes de correção podem ser aprovados")
        tipo = str(payload.get("tipo", doc["tipo"])).strip().upper()
        try:
            tipo_final = TipoDocumento(tipo)
        except ValueError as exc:
            raise HTTPException(422, "Tipo de documento inválido") from exc
        trabalhador_id = payload.get("trabalhador_id", doc["worker_id"])
        trabalhador_id = str(trabalhador_id).strip().upper() if trabalhador_id is not None else None
        competencia = payload.get("competencia", doc["competencia"])
        competencia = str(competencia).strip() if competencia is not None else None
        if tipo_final is TipoDocumento.DESCONHECIDO:
            raise HTTPException(422, "Informe um tipo de documento identificado")
        if tipo_final in TIPOS_FOCO and (not trabalhador_id or not competencia):
            raise HTTPException(422, "Tipo de foco exige trabalhador e competência")
        if competencia is not None and re.fullmatch(r"(?:0[1-9]|1[0-2])/\d{4}", competencia) is None:
            raise HTTPException(422, "Competência deve estar no formato MM/AAAA")
        if trabalhador_id is not None and conn.execute(
                "SELECT 1 FROM workers WHERE id=? AND contract_id=?",
                (trabalhador_id, doc["contract_id"])).fetchone() is None:
            raise HTTPException(422, "Trabalhador não pertence ao contrato")
        par_antes = _document_pair(doc)
        dados_corrigidos = (trabalhador_id != doc["worker_id"] or competencia != doc["competencia"])
        conn.execute(
            "UPDATE documents SET tipo=?, worker_id=?, competencia=?, status=?, motivos_pendencia='[]', "
            "revisado_por=?, updated_at=? WHERE id=?",
            (tipo_final.value, trabalhador_id, competencia, StatusDocumento.APTO.value,
             user.id, now, document_id))
        par_depois = _document_pair({"tipo": tipo_final.value, "worker_id": trabalhador_id,
                                     "competencia": competencia})
        if dados_corrigidos and tipo_final in TIPOS_FOCO:
            conn.execute(
                "UPDATE documents SET status=?, revisado_por=?, updated_at=? "
                "WHERE contract_id=? AND tipo=? AND worker_id=? AND competencia=? AND status=? AND id<>?",
                (StatusDocumento.SUBSTITUIDO.value, user.id, now, doc["contract_id"], tipo_final.value,
                 trabalhador_id, competencia, StatusDocumento.APTO.value, document_id),
            )
        pendencias.resolver_do_documento(conn, document_id, "resolvida na revisão")
        _reconcile_pairs(conn, doc["contract_id"], par_antes, par_depois)
    elif action == "solicitar_correcao":
        if doc["status"] not in {StatusDocumento.REVISAO_HUMANA.value, StatusDocumento.APTO.value}:
            raise HTTPException(409, "Somente documentos em revisão ou aptos podem receber pedido de correção")
        motivo = str(payload.get("motivo", "")).strip()
        acao = str(payload.get("acao_solicitada", "")).strip()
        if not motivo or not acao:
            raise HTTPException(422, "Informe motivo e ação solicitada")
        par_antes = _document_pair(doc)
        conn.execute("UPDATE documents SET status=?, revisado_por=?, updated_at=? WHERE id=?",
                     (StatusDocumento.PENDENTE_CORRECAO.value, user.id, now, document_id))
        paginas = ", ".join(str(p["ordem"]) for p in _document_pages(conn, document_id))
        pendencias.criar_pendencia(
            conn, contract_id=doc["contract_id"], document_id=document_id, worker_id=doc["worker_id"],
            competencia=doc["competencia"], tipo_documento=doc["tipo"],
            categoria=CategoriaPendencia.SOLICITADA_NA_REVISAO, motivo=motivo[:1000],
            evidencia=f"Lote {doc['batch_id']}, página(s) {paginas}", acao=acao[:500])
        _reconcile_pairs(conn, doc["contract_id"], par_antes,
                         _document_pair({"tipo": doc["tipo"], "worker_id": doc["worker_id"],
                                         "competencia": doc["competencia"]}))
    elif action in {"dividir", "unir_proximo"}:
        try:
            if action == "dividir":
                revisao.dividir(conn, document_id, payload.get("apos_pagina"), usuario_id=user.id)
            else:
                revisao.unir_proximo(conn, document_id, usuario_id=user.id)
        except revisao.RevisaoInvalida as exc:
            raise HTTPException(409 if exc.conflito else 422, str(exc)) from exc
    else:
        raise HTTPException(422, "Ação deve ser aprovar, dividir, unir_proximo ou solicitar_correcao")
    auditar(conn, user, f"DOCUMENTO_{action.upper()}", str(document_id))
    return {"document_id": document_id, "acao": action, "status": conn.execute(
        "SELECT status FROM documents WHERE id=?", (document_id,)).fetchone()[0]}


@router.get("/api/supplier/issues")
def supplier_issues(user: Usuario = Depends(usuario_atual),
                    conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    exigir_papel(user, PAPEIS_FORNECEDORA)
    ids = contratos_do_usuario(conn, user)
    if not ids:
        return []
    return _issue_rows(conn, ids)


def _issue_rows(conn: sqlite3.Connection, ids: list[str]) -> list[dict[str, Any]]:
    marks = ",".join("?" for _ in ids)
    rows = _rows(conn.execute(f"SELECT * FROM issues WHERE contract_id IN ({marks}) ORDER BY id DESC",
                              ids).fetchall())
    for row in rows:
        row["historico"] = _json_list(row.pop("historico_json"))
    return rows


@router.get("/api/issues")
def issues(user: Usuario = Depends(usuario_atual),
           conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    _require_ber_user(user)
    ids = contratos_do_usuario(conn, user)
    if not ids:
        return []
    return _issue_rows(conn, ids)


@router.get("/api/analyses")
def analyses(historico: bool = False, user: Usuario = Depends(usuario_atual),
             conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    """Análises por par trabalhador+competência. Padrão: só a atual; historico=true traz as versões."""
    _require_ber_user(user)
    ids = contratos_do_usuario(conn, user)
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    filtro = "" if historico else " AND atual=1"
    rows = _rows(conn.execute(
        f"SELECT * FROM analyses WHERE contract_id IN ({marks}){filtro} "
        "ORDER BY contract_id, competencia, worker_id, id DESC", ids).fetchall())
    for row in rows:
        row["resultado"] = _json_object(row.pop("resultado_json"))
        row["insumos"] = _json_list(row.pop("insumos_json"))
    return rows


@router.get("/api/documents")
def list_documents(status: str | None = None, tipo: str | None = None,
                   user: Usuario = Depends(usuario_atual),
                   conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    """Documentos classificados dos contratos do usuário (Bernhoeft e fornecedora)."""
    _require_batch_reader(user)
    ids = contratos_do_usuario(conn, user)
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    sql = f"SELECT * FROM documents WHERE contract_id IN ({marks})"
    params: list[Any] = list(ids)
    if status:
        sql += " AND status=?"
        params.append(status.upper())
    if tipo:
        sql += " AND tipo=?"
        params.append(tipo.upper())
    rows = conn.execute(sql + " ORDER BY id DESC LIMIT 500", params).fetchall()
    return [_document_view(conn, user, row) for row in rows]


@router.get("/api/documents/{document_id}")
def get_document(document_id: int, user: Usuario = Depends(usuario_atual),
                 conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    """Documento com as páginas e o texto (OCR) de cada uma, vinculados à imagem original."""
    _require_batch_reader(user)
    row = _document_or_404(conn, user, document_id)
    item = _document_view(conn, user, row)
    paginas = conn.execute(
        "SELECT p.id, p.ordem, p.texto FROM doc_pages dp JOIN pages p ON p.id=dp.page_id "
        "WHERE dp.document_id=? ORDER BY dp.posicao", (document_id,)).fetchall()
    item["paginas_detalhe"] = [
        {"page_id": int(p["id"]), "ordem": int(p["ordem"]), "texto": p["texto"] or ""} for p in paginas]
    versoes = []
    if row["worker_id"] and row["competencia"]:
        versoes = _rows(conn.execute(
            "SELECT id, versao, status, batch_id, created_at FROM documents WHERE contract_id=? AND tipo=? "
            "AND worker_id=? AND competencia=? ORDER BY versao, id",
            (row["contract_id"], row["tipo"], row["worker_id"], row["competencia"])).fetchall())
    item["versoes"] = versoes
    return item


def _document_view(conn: sqlite3.Connection, user: Usuario, row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["paginas"] = _document_pages(conn, int(item["id"]))
    item["motivos_pendencia"] = _json_list(item["motivos_pendencia"])
    item["motivos_revisao"] = _json_list(item["motivos_revisao"])
    item["campos"] = _json_object(item.pop("campos_json"))
    if user.org_tipo == "FORNECEDORA":
        if item["status"] == StatusDocumento.REVISAO_HUMANA.value:
            item["status"] = "EM_ANALISE"
        item.pop("motivos_revisao", None)
        item["campos"] = {}
        item.pop("confianca", None)
    return item


@router.post("/api/issues/{issue_id}/resubmit", status_code=202)
async def resubmit_issue(issue_id: int, file: UploadFile = File(...),
                         user: Usuario = Depends(usuario_atual),
                         conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, int | str]:
    exigir_papel(user, PAPEIS_FORNECEDORA)
    issue = conn.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()
    if issue is None:
        raise HTTPException(404, "Pendência não encontrada")
    _contract_or_404(conn, user, issue["contract_id"])
    if issue["status"] not in {StatusPendencia.ABERTA.value, StatusPendencia.NOTIFICADA.value,
                                StatusPendencia.REABERTA.value}:
        raise HTTPException(409, "Pendência não pode receber novo reenvio")
    data = await file.read(config.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if not data or len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(422, "Arquivo vazio ou acima do limite de upload")
    try:
        batch_id = worker.criar_lote(user, issue["contract_id"], file.filename or "arquivo", data,
                                     issue_id=issue_id)
    except ArquivoInvalido as exc:
        raise HTTPException(422, str(exc)) from exc
    # REENVIADA é gravada e confirmada ANTES de enfileirar: o worker pode resolver ou
    # reabrir a pendência logo em seguida, e essa decisão não pode ser sobrescrita.
    historico = _json_list(issue["historico_json"])
    now = db.agora()
    historico.append({"status": StatusPendencia.REENVIADA.value, "em": now, "motivo": "reenvio recebido",
                      "lote": batch_id})
    conn.execute("UPDATE issues SET status=?, updated_at=?, historico_json=? WHERE id=?",
                 (StatusPendencia.REENVIADA.value, now,
                  json.dumps(historico, ensure_ascii=False), issue_id))
    auditar(conn, user, "PENDENCIA_REENVIADA", str(issue_id))
    conn.commit()
    try:
        worker.enfileirar(batch_id)
    except NotImplementedError as exc:
        raise HTTPException(503, "Reenvio ainda não está disponível (F2)") from exc
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
        # Cada palavra vira um termo entre aspas: o texto do usuário nunca é sintaxe FTS5.
        termos = " ".join('"' + t.replace('"', '""') + '"' for t in q.split())
        if not termos:
            return []
        rows = conn.execute(
            f"SELECT f.page_id, f.contract_id, snippet(page_fts, 0, '[[', ']]', '…', 12) AS trecho, "
            f"dp.document_id, p.ordem, p.batch_id "
            f"FROM page_fts f JOIN pages p ON p.id=f.page_id "
            f"LEFT JOIN doc_pages dp ON dp.page_id=f.page_id "
            f"WHERE page_fts MATCH ? AND f.contract_id IN ({marks}) ORDER BY rank LIMIT 100",
            (termos, *ids)).fetchall()
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


@router.get("/api/reports")
def list_reports(user: Usuario = Depends(usuario_atual),
                 conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    exigir_papel(user, [Papel.ANALISTA_BH, Papel.ADMIN_BH])
    ids = contratos_do_usuario(conn, user)
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT * FROM reports WHERE contract_id IN ({marks}) AND status IN (?, ?, ?, ?) "
        "ORDER BY created_at DESC, id DESC",
        (*ids, StatusParecer.RASCUNHO.value, StatusParecer.EM_REVISAO.value,
         StatusParecer.APROVADO_PUBLICADO.value, StatusParecer.SUBSTITUIDO_POR_VERSAO.value),
    ).fetchall()
    return [_report_result(row) for row in rows]


@router.get("/api/reports/{report_id}/preview")
def preview_report(report_id: int, user: Usuario = Depends(usuario_atual),
                   conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    """Prévia do parecer com as análises ATUAIS (nada é gravado). Só Bernhoeft."""
    _require_ber_user(user)
    report = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    if report is None:
        raise HTTPException(404, "Parecer não encontrado")
    _contract_or_404(conn, user, report["contract_id"])
    if report["status"] != StatusParecer.RASCUNHO.value:
        return _report_result(report)
    result = _report_result(report)
    result["conteudo_json"] = parecer.snapshot_parecer(conn, report["contract_id"], report["competencia"])
    return result


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
    rows = conn.execute(
        f"SELECT id, contract_id, competencia, versao, status, conteudo_json, publicado_em "
        f"FROM reports WHERE contract_id IN ({marks}) AND status=? ORDER BY publicado_em DESC",
        (*ids, StatusParecer.APROVADO_PUBLICADO.value)).fetchall()
    return [_report_result(row) for row in rows]


@router.post("/api/batches/{batch_id}/reprocess", status_code=202)
def reprocess_batch(batch_id: int, user: Usuario = Depends(usuario_atual),
                    conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, int | str]:
    batch = _batch_or_404(conn, user, batch_id)
    if user.papel not in PAPEIS_BERNHOEFT and user.id != batch["uploaded_by"]:
        raise HTTPException(403, "Somente Bernhoeft ou quem enviou o lote pode reprocessá-lo")
    if batch["status"] != StatusLote.FALHA_PROCESSAMENTO.value:
        raise HTTPException(409, "Somente lotes com falha de processamento podem ser reprocessados")
    try:
        worker.enfileirar(batch_id)
    except NotImplementedError as exc:
        raise HTTPException(503, "Reprocessamento ainda não está disponível (F2)") from exc
    auditar(conn, user, "LOTE_REPROCESSADO", str(batch_id))
    return {"batch_id": batch_id, "status": "RECEBIDO"}


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
