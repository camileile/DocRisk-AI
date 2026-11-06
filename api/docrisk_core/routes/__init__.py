from __future__ import annotations

import json
import math
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

import pymupdf
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from .. import config, db
from ..api_models import ReportCreate, ReportResponse
from ..auth import (Usuario, auditar, contratos_do_usuario, exigir_contrato,
                    exigir_papel, usuario_atual)
from ..contracts import (CategoriaPendencia, PAPEIS_BERNHOEFT,
                         PAPEIS_FORNECEDORA, TIPOS_FOCO, Papel, StatusDocumento,
                         StatusParecer, StatusPendencia, StatusLote, TipoDocumento)
from ..pipeline.render import ArquivoInvalido
from ..pipeline import integracao_f3 as f3, revisao, worker
from ..privacidade import SemCamadaDeTexto, anonimizar_pdf, mascarar_texto
from ..rules import metricas, metricas_analista, parecer, pendencias, portal_contratante

router = APIRouter()

from .admin_management import audit_for_admin, router as admin_management_router
router.include_router(admin_management_router)


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


def _require_analyst(user: Usuario) -> None:
    exigir_papel(user, [Papel.ANALISTA_BH])


def _require_aej_association(user: Usuario) -> None:
    exigir_papel(user, [Papel.ANALISTA_BH])


def _require_aej_review(user: Usuario) -> None:
    exigir_papel(user, [Papel.ANALISTA_BH])


def _require_batch_reader(user: Usuario) -> None:
    exigir_papel(user, [*PAPEIS_FORNECEDORA, Papel.ANALISTA_BH])


@router.get("/api/demo/users")
def demo_users(conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, str]]:
    if not config.DEMO_MODE:
        raise HTTPException(404, "Rota não encontrada")
    rows = conn.execute(
        "SELECT u.id, u.nome, u.org_id, o.tipo AS org_tipo, u.role, u.token "
        "FROM users u JOIN organizations o ON o.id=u.org_id WHERE u.ativo=1 ORDER BY u.rowid"
    ).fetchall()
    platform = conn.execute("SELECT id,nome,'DOCRISK' AS org_id,'PLATAFORMA' AS org_tipo,"
                            "'ADMIN_PLATAFORMA' AS role,token FROM platform_accounts WHERE ativo=1").fetchall()
    return [*_rows(rows), *_rows(platform)]


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


def _substituir_espelho_anterior(conn: sqlite3.Connection, contract_id: str, worker_id: str,
                                 competencia: str, novo_id: int, novo_status: StatusDocumento) -> None:
    """O espelho AEJ recém-associado vira a versão vigente do par: o anterior (PDF ou outro AEJ)
    passa a SUBSTITUIDO, como no reenvio, para nunca haver dois espelhos vigentes."""
    anterior = conn.execute(
        "SELECT id, versao FROM documents WHERE contract_id=? AND tipo='ESPELHO_PONTO' AND worker_id=? "
        "AND competencia=? AND status<>? AND id<>? ORDER BY versao DESC, id DESC LIMIT 1",
        (contract_id, worker_id, competencia, StatusDocumento.SUBSTITUIDO.value, novo_id),
    ).fetchone()
    if anterior is None:
        return
    conn.execute("UPDATE documents SET status=?, updated_at=? WHERE id=?",
                 (StatusDocumento.SUBSTITUIDO.value, db.agora(), anterior["id"]))
    conn.execute("UPDATE documents SET versao=?, substitui_id=? WHERE id=?",
                 (int(anterior["versao"]) + 1, anterior["id"], novo_id))
    f3.atualizar_por_nova_versao(conn, int(anterior["id"]), novo_status)


@router.get("/api/contracts/{contract_id}/aej-mappings")
def list_aej_mappings(contract_id: str, user: Usuario = Depends(usuario_atual),
                      conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, str]]:
    _require_aej_association(user)
    _contract_or_404(conn, user, contract_id)
    return _rows(conn.execute(
        "SELECT m.worker_link_id, m.worker_id, w.nome AS worker_name "
        "FROM aej_worker_mappings m JOIN workers w ON w.id=m.worker_id "
        "WHERE m.contract_id=? ORDER BY m.worker_link_id", (contract_id,)).fetchall())


@router.put("/api/contracts/{contract_id}/aej-mappings/{worker_link_id}")
def put_aej_mapping(contract_id: str, worker_link_id: str, worker_id: str = Body(embed=True),
                    user: Usuario = Depends(usuario_atual),
                    conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, str]:
    _require_aej_association(user)
    _contract_or_404(conn, user, contract_id)
    if not worker_link_id.isdigit() or not worker_id.strip():
        raise HTTPException(422, "Informe vínculo AEJ numérico e trabalhador do contrato.")
    trabalhador = conn.execute("SELECT id FROM workers WHERE id=? AND contract_id=?",
                               (worker_id.strip(), contract_id)).fetchone()
    if trabalhador is None:
        raise HTTPException(422, "Trabalhador não pertence ao contrato.")
    conflito = conn.execute(
        "SELECT worker_link_id FROM aej_worker_mappings WHERE contract_id=? AND worker_id=? "
        "AND worker_link_id<>?", (contract_id, worker_id.strip(), worker_link_id),
    ).fetchone()
    if conflito:
        raise HTTPException(409, f"Trabalhador já associado ao vínculo AEJ {conflito[0]}.")
    atual = conn.execute(
        "SELECT worker_id FROM aej_worker_mappings WHERE contract_id=? AND worker_link_id=?",
        (contract_id, worker_link_id),
    ).fetchone()
    if atual and atual[0] != worker_id.strip():
        ja_processado = conn.execute(
            "SELECT 1 FROM aej_documents ad JOIN documents d ON d.id=ad.document_id "
            "WHERE d.contract_id=? AND ad.worker_link_id=? AND d.worker_id IS NOT NULL LIMIT 1",
            (contract_id, worker_link_id),
        ).fetchone()
        if ja_processado:
            raise HTTPException(409, "Vínculo já aplicado a documentos. Não altere o mapeamento retroativamente.")
    conn.execute(
        "INSERT INTO aej_worker_mappings (contract_id, worker_link_id, worker_id, created_by, created_at) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(contract_id, worker_link_id) DO UPDATE SET "
        "worker_id=excluded.worker_id, created_by=excluded.created_by, created_at=excluded.created_at",
        (contract_id, worker_link_id, worker_id.strip(), user.id, db.agora()),
    )
    pares: set[tuple[str, str]] = set()
    pendentes = conn.execute(
        "SELECT d.id, d.competencia, ad.calculation_json FROM aej_documents ad "
        "JOIN documents d ON d.id=ad.document_id WHERE d.contract_id=? AND ad.worker_link_id=? "
        "AND d.worker_id IS NULL ORDER BY d.id", (contract_id, worker_link_id),
    ).fetchall()
    for doc in pendentes:  # em ordem de chegada: o AEJ mais recente termina como versão vigente
        detail = _json_object(doc["calculation_json"])
        warnings = [w for w in detail.get("warnings", [])
                    if w != "Vínculo AEJ sem mapeamento explícito para trabalhador do contrato."]
        detail["worker_id"] = worker_id.strip()
        detail["warnings"] = warnings
        dias = detail.get("days", [])
        horas = None
        status = StatusDocumento.REVISAO_HUMANA
        if detail.get("calculation_status") == "CALCULATED" and dias and not warnings:
            horas = round(sum(int(d.get("observed_daily_excess_minutes") or 0) for d in dias) / 60, 2)
            status = StatusDocumento.APTO
        detail["hours"] = horas
        conn.execute(
            "UPDATE documents SET worker_id=?, status=?, confianca=?, campos_json=?, motivos_revisao=?, "
            "updated_at=? WHERE id=?",
            (worker_id.strip(), status.value, 1.0 if horas is not None else 0.0,
             json.dumps({"horas_extras_h": horas}), json.dumps(warnings, ensure_ascii=False),
             db.agora(), doc["id"]),
        )
        conn.execute("UPDATE aej_documents SET calculation_json=? WHERE document_id=?",
                     (json.dumps(detail, ensure_ascii=False), doc["id"]))
        _substituir_espelho_anterior(conn, contract_id, worker_id.strip(), doc["competencia"],
                                     int(doc["id"]), status)
        pares.add((worker_id.strip(), doc["competencia"]))
    for mapped_worker, competencia in sorted(pares):
        f3.conciliar(conn, contract_id, mapped_worker, competencia)
    auditar(conn, user, "AEJ_VINCULO_MAPEADO", f"{contract_id}:{worker_link_id}")
    return {"contract_id": contract_id, "worker_link_id": worker_link_id, "worker_id": worker_id.strip()}


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


@router.get("/api/batches/{batch_id}/source")
def batch_source(batch_id: int, user: Usuario = Depends(usuario_atual),
                 conn: sqlite3.Connection = Depends(get_conn)) -> FileResponse:
    _require_batch_reader(user)
    row = _batch_or_404(conn, user, batch_id)
    if user.org_tipo not in {"BERNHOEFT", "FORNECEDORA"}:
        raise HTTPException(403, "Acesso ao arquivo original não permitido.")
    path = Path(row["arquivo"]).resolve()
    try:
        path.relative_to(config.UPLOAD_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(404, "Arquivo original não encontrado.") from exc
    if not path.is_file():
        raise HTTPException(404, "Arquivo original não encontrado.")
    nome = Path(row["filename"]).name or f"lote-{batch_id}"
    return FileResponse(path, media_type="application/octet-stream", filename=nome)


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
    _require_batch_reader(user)
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
    if conn.execute("SELECT 1 FROM aej_documents WHERE document_id=?", (document_id,)).fetchone():
        raise HTTPException(409, "Documento AEJ deve ser conferido na tela de cálculo estruturado.")
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
    _require_analyst(user)
    ids = contratos_do_usuario(conn, user)
    if not ids:
        return []
    return _issue_rows(conn, ids)


@router.get("/api/analyses")
def analyses(historico: bool = False, user: Usuario = Depends(usuario_atual),
             conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    """Análises por par trabalhador+competência. Padrão: só a atual; historico=true traz as versões."""
    _require_analyst(user)
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
                   contract_id: str | None = None,
                   user: Usuario = Depends(usuario_atual),
                   conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    """Documentos classificados dos contratos do usuário (Bernhoeft e fornecedora)."""
    _require_batch_reader(user)
    ids = contratos_do_usuario(conn, user)
    if contract_id:
        _contract_or_404(conn, user, contract_id)
        ids = [contract_id]
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    sql = f"SELECT * FROM documents WHERE contract_id IN ({marks})"
    params: list[Any] = list(ids)
    if status:
        sql += " AND status=?"
        params.append("REVISAO_HUMANA" if user.papel in PAPEIS_FORNECEDORA and status.upper() == "EM_ANALISE" else status.upper())
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
        {"page_id": int(p["id"]), "ordem": int(p["ordem"]),
         "texto": (p["texto"] or "") if user.org_tipo == "BERNHOEFT"
         else mascarar_texto(p["texto"] or "")[0]} for p in paginas]
    versoes = []
    if row["worker_id"] and row["competencia"]:
        versoes = _rows(conn.execute(
            "SELECT id, versao, status, batch_id, created_at FROM documents WHERE contract_id=? AND tipo=? "
            "AND worker_id=? AND competencia=? ORDER BY versao, id",
            (row["contract_id"], row["tipo"], row["worker_id"], row["competencia"])).fetchall())
    if user.papel in PAPEIS_FORNECEDORA:
        for version in versoes:
            if version["status"] == StatusDocumento.REVISAO_HUMANA.value:
                version["status"] = "EM_ANALISE"
    item["versoes"] = versoes
    aej = conn.execute("SELECT calculation_json FROM aej_documents WHERE document_id=?", (document_id,)).fetchone()
    if aej is not None and user.org_tipo == "BERNHOEFT":
        item["aej"] = _json_object(aej["calculation_json"])
    return item


@router.get("/api/documents/{document_id}/anonimizado")
def document_anonimizado(document_id: int, user: Usuario = Depends(usuario_atual),
                         conn: sqlite3.Connection = Depends(get_conn)) -> Response:
    # A contratante consulta apenas pareceres publicados, nunca documentos operacionais.
    _require_batch_reader(user)
    row = _document_or_404(conn, user, document_id)
    lote = conn.execute("SELECT arquivo, tipo_arquivo FROM batches WHERE id=?", (row["batch_id"],)).fetchone()
    if lote is None or lote["tipo_arquivo"] != "PDF":
        raise HTTPException(422, "A versão anonimizada só está disponível para PDF")
    ordens = [int(r["ordem"]) for r in conn.execute(
        "SELECT p.ordem FROM doc_pages dp JOIN pages p ON p.id=dp.page_id "
        "WHERE dp.document_id=? ORDER BY dp.posicao", (document_id,))]
    if not ordens or min(ordens) < 1:
        raise HTTPException(409, "Documento sem páginas válidas para anonimização")
    path = Path(lote["arquivo"]).resolve()
    try:
        path.relative_to(config.UPLOAD_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(404, "Arquivo não encontrado") from exc
    if not path.is_file():
        raise HTTPException(404, "Arquivo não encontrado")

    data = path.read_bytes()
    try:
        with pymupdf.open(stream=data, filetype="pdf") as original:
            if max(ordens) > original.page_count:
                raise HTTPException(409, "Páginas do documento não correspondem ao PDF original")
            for ordem in ordens:
                page = original[ordem - 1]
                # Anotações, campos e links não entram no texto usado pelas tarjas.
                # Recusar a página evita devolver dados pessoais fora dessa camada.
                if page.annot_xrefs():
                    raise HTTPException(
                        422, "PDF contém anotações, links ou formulários; não é possível anonimizar com segurança")
                blocos = page.get_text("dict").get("blocks", [])
                if any(bloco.get("type") == 1 for bloco in blocos):
                    raise HTTPException(
                        422, "PDF contém imagem; a anonimização não consegue garantir a remoção dos dados nela")
        pdf = anonimizar_pdf(data, ordens)
    except SemCamadaDeTexto as exc:
        raise HTTPException(422, "Documento sem camada de texto: não dá para anonimizar com segurança") from exc
    except (pymupdf.FileDataError, pymupdf.FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(422, "Não foi possível anonimizar este PDF com segurança") from exc

    auditar(conn, user, "DOCUMENTO_ANONIMIZADO_BAIXADO", str(document_id))
    return Response(pdf, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="documento-{document_id}-anonimizado.pdf"'})


@router.patch("/api/documents/{document_id}/aej-review")
def review_aej_document(document_id: int, payload: dict[str, Any] = Body(...),
                        user: Usuario = Depends(usuario_atual),
                        conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    _require_aej_review(user)
    doc = _document_or_404(conn, user, document_id)
    if conn.execute("SELECT 1 FROM aej_documents WHERE document_id=?", (document_id,)).fetchone() is None:
        raise HTTPException(409, "Documento não é uma derivação AEJ.")
    if doc["status"] != StatusDocumento.REVISAO_HUMANA.value:
        raise HTTPException(409, "Documento AEJ não está aguardando revisão.")
    if not doc["worker_id"]:
        raise HTTPException(409, "Mapeie primeiro o vínculo AEJ para um trabalhador do contrato.")
    horas = payload.get("horas_extras_h")
    justificativa = str(payload.get("justificativa", "")).strip()
    if (isinstance(horas, bool) or not isinstance(horas, (int, float)) or
            not math.isfinite(horas) or horas < 0):
        raise HTTPException(422, "Informe horas_extras_h numérico, não negativo, após conferir o AEJ.")
    if not justificativa:
        raise HTTPException(422, "Justificativa obrigatória para ajuste manual do cálculo AEJ.")
    calculo = conn.execute("SELECT calculation_json FROM aej_documents WHERE document_id=?",
                           (document_id,)).fetchone()
    detail = _json_object(calculo["calculation_json"])
    detail["hours"] = float(horas)
    detail["calculation_status"] = "HUMAN_CONFIRMED"
    detail["human_review"] = {"hours_override": float(horas), "justification": justificativa[:500],
                              "reviewer_id": user.id, "reviewed_at": db.agora()}
    now = db.agora()
    conn.execute(
        "UPDATE documents SET status=?, confianca=1, campos_json=?, revisado_por=?, updated_at=? WHERE id=?",
        (StatusDocumento.APTO.value, json.dumps({"horas_extras_h": float(horas)}), user.id, now, document_id),
    )
    conn.execute("UPDATE aej_documents SET calculation_json=? WHERE document_id=?",
                 (json.dumps(detail, ensure_ascii=False), document_id))
    if doc["worker_id"] and doc["competencia"]:
        f3.conciliar(conn, doc["contract_id"], doc["worker_id"], doc["competencia"])
    auditar(conn, user, "AEJ_DOCUMENTO_REVISTO", str(document_id))
    return {"id": document_id, "status": StatusDocumento.APTO.value,
            "horas_extras_h": float(horas)}


def _document_view(conn: sqlite3.Connection, user: Usuario, row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["paginas"] = _document_pages(conn, int(item["id"]))
    item["motivos_pendencia"] = _json_list(item["motivos_pendencia"])
    item["motivos_revisao"] = _json_list(item["motivos_revisao"])
    item["campos"] = _json_object(item.pop("campos_json"))
    aej = conn.execute("SELECT worker_link_id, calculation_json FROM aej_documents WHERE document_id=?",
                       (item["id"],)).fetchone()
    if aej is not None:
        derivacao = _json_object(aej["calculation_json"])
        item["aej"] = {"origem": "AEJ", "worker_link_id": aej["worker_link_id"],
                       "calculation_status": derivacao.get("calculation_status"),
                       "p7s_validated": False}
    if user.org_tipo == "FORNECEDORA":
        if item["status"] == StatusDocumento.REVISAO_HUMANA.value:
            item["status"] = "EM_ANALISE"
        item.pop("motivos_revisao", None)
        item["campos"] = {}
        item.pop("confianca", None)
    return item


def _normalizar_busca(texto: str) -> tuple[str, list[int]]:
    normalizado: list[str] = []
    offsets: list[int] = []
    for indice, caractere in enumerate(texto):
        for letra in unicodedata.normalize("NFKD", caractere).casefold():
            if not unicodedata.combining(letra):
                normalizado.append(letra)
                offsets.append(indice)
    return "".join(normalizado), offsets


def _trecho_busca_mascarado(texto: str, consulta: str, contexto: int = 90) -> str:
    seguro = mascarar_texto(texto)[0]
    normalizado, offsets = _normalizar_busca(seguro)
    termos = ["".join(c for c in unicodedata.normalize("NFKD", termo).casefold()
                      if not unicodedata.combining(c))
              for termo in re.findall(r"\w+", consulta, flags=re.UNICODE)]
    ocorrencias = []
    for termo in termos:
        if not termo:
            continue
        inicio = normalizado.find(termo)
        if inicio >= 0:
            ocorrencias.append((inicio, inicio + len(termo)))
    if not ocorrencias or not offsets:
        return ""
    inicio_norm, fim_norm = min(ocorrencias)
    inicio = offsets[inicio_norm]
    fim = offsets[min(fim_norm - 1, len(offsets) - 1)] + 1
    recorte_inicio = max(0, inicio - contexto)
    while recorte_inicio > 0 and not seguro[recorte_inicio - 1].isspace():
        recorte_inicio -= 1
    recorte_fim = min(len(seguro), fim + contexto)
    while recorte_fim < len(seguro) and not seguro[recorte_fim].isspace():
        recorte_fim += 1
    trecho = seguro[recorte_inicio:inicio] + "[[" + seguro[inicio:fim] + "]]" + seguro[fim:recorte_fim]
    if recorte_inicio:
        trecho = "…" + trecho
    if recorte_fim < len(seguro):
        trecho += "…"
    return trecho


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
          contract_id: str | None = None,
          user: Usuario = Depends(usuario_atual),
          conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    _require_batch_reader(user)
    if user.org_tipo == "CONTRATANTE":
        raise HTTPException(403, "Busca textual não está disponível para a contratante")
    ids = contratos_do_usuario(conn, user)
    if contract_id:
        _contract_or_404(conn, user, contract_id)
        ids = [contract_id]
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
            f"dp.document_id, p.ordem, p.batch_id, f.texto AS texto_completo "
            f"FROM page_fts f JOIN pages p ON p.id=f.page_id "
            f"LEFT JOIN doc_pages dp ON dp.page_id=f.page_id "
            f"WHERE page_fts MATCH ? AND f.contract_id IN ({marks}) ORDER BY rank LIMIT 100",
            (termos, *ids)).fetchall()
    except sqlite3.OperationalError as exc:
        raise HTTPException(400, "Consulta de busca inválida") from exc
    result = _rows(rows)
    if user.org_tipo != "BERNHOEFT":
        for item in result:
            texto = item.pop("texto_completo", None)
            item["trecho"] = _trecho_busca_mascarado(texto or "", q) if texto else ""
    else:
        for item in result:
            item.pop("texto_completo", None)
    return result


@router.post("/api/reports", status_code=201, response_model=ReportResponse,
             response_model_exclude_unset=True)
def create_report(payload: ReportCreate, user: Usuario = Depends(usuario_atual),
                  conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    exigir_papel(user, [Papel.ANALISTA_BH])
    contract_id = payload.contract_id
    competencia = payload.competencia
    _contract_or_404(conn, user, contract_id)
    latest = conn.execute("SELECT COALESCE(MAX(versao), 0) FROM reports WHERE contract_id=? AND competencia=?",
                          (contract_id, competencia)).fetchone()[0]
    now = db.agora()
    cursor = conn.execute(
        "INSERT INTO reports (contract_id, competencia, versao, status, observacoes, autor_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (contract_id, competencia, latest + 1, StatusParecer.RASCUNHO.value,
         payload.observacoes, user.id, now))
    auditar(conn, user, "PARECER_RASCUNHO_CRIADO", str(cursor.lastrowid))
    return _report_result(conn.execute(
        "SELECT * FROM reports WHERE id=?", (cursor.lastrowid,)).fetchone())


@router.get("/api/reports", response_model=list[ReportResponse], response_model_exclude_unset=True)
def list_reports(user: Usuario = Depends(usuario_atual),
                 conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    exigir_papel(user, [Papel.ANALISTA_BH])
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


@router.get("/api/reports/{report_id}/preview", response_model=ReportResponse,
            response_model_exclude_unset=True)
def preview_report(report_id: int, user: Usuario = Depends(usuario_atual),
                   conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    """Prévia do parecer com as análises ATUAIS (nada é gravado). Só Bernhoeft."""
    _require_analyst(user)
    report = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    if report is None:
        raise HTTPException(404, "Parecer não encontrado")
    _contract_or_404(conn, user, report["contract_id"])
    if report["status"] != StatusParecer.RASCUNHO.value:
        return _report_result(report)
    result = _report_result(report)
    result["conteudo_json"] = parecer.snapshot_parecer(conn, report["contract_id"], report["competencia"])
    return result


@router.post("/api/reports/{report_id}/publish", response_model=ReportResponse,
             response_model_exclude_unset=True)
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
    return _report_result(conn.execute(
        "SELECT * FROM reports WHERE id=?", (report_id,)).fetchone())


@router.get("/api/client/reports", response_model=list[ReportResponse],
            response_model_exclude_unset=True)
def client_reports(fornecedora_id: str | None = None, contract_id: str | None = None,
                   competencia: str | None = Query(default=None, pattern=r"^(0[1-9]|1[0-2])/\d{4}$"),
                   user: Usuario = Depends(usuario_atual),
                   conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    exigir_papel(user, [Papel.GESTOR_CONTR])
    return portal_contratante.publicados(
        conn, portal_contratante.contratos(conn, user), fornecedora_id=fornecedora_id,
        contract_id=contract_id, competencia=competencia,
    )


@router.get("/api/client/overview")
def client_overview(fornecedora_id: str | None = None, contract_id: str | None = None,
                    competencia: str | None = Query(default=None, pattern=r"^(0[1-9]|1[0-2])/\d{4}$"),
                    user: Usuario = Depends(usuario_atual),
                    conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    exigir_papel(user, [Papel.GESTOR_CONTR])
    return portal_contratante.overview(
        conn, user, fornecedora_id=fornecedora_id, contract_id=contract_id,
        competencia=competencia,
    )


@router.post("/api/batches/{batch_id}/reprocess", status_code=202)
def reprocess_batch(batch_id: int, user: Usuario = Depends(usuario_atual),
                    conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, int | str]:
    _require_batch_reader(user)
    batch = _batch_or_404(conn, user, batch_id)
    if user.papel not in PAPEIS_BERNHOEFT and user.papel != Papel.GESTOR_FORN and user.id != batch["uploaded_by"]:
        raise HTTPException(403, "Somente Bernhoeft, o gestor da fornecedora ou quem enviou o lote pode reprocessá-lo")
    if batch["status"] != StatusLote.FALHA_PROCESSAMENTO.value:
        raise HTTPException(409, "Somente lotes com falha de processamento podem ser reprocessados")
    try:
        worker.enfileirar(batch_id)
    except NotImplementedError as exc:
        raise HTTPException(503, "Reprocessamento ainda não está disponível (F2)") from exc
    auditar(conn, user, "LOTE_REPROCESSADO", str(batch_id))
    return {"batch_id": batch_id, "status": "RECEBIDO"}


@router.get("/api/analyst/overview")
def analyst_overview(
    contratante_id: str | None = None,
    fornecedora_id: str | None = None,
    contract_id: str | None = None,
    competencia: str | None = Query(default=None, pattern=r"^(0[1-9]|1[0-2])/\d{4}$"),
    user: Usuario = Depends(usuario_atual),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    """Painel analítico do Analista: filtros e métricas restritos à organização."""
    exigir_papel(user, [Papel.ANALISTA_BH])
    return metricas_analista.montar_dashboard(
        conn, contratos_do_usuario(conn, user),
        contratante_id=contratante_id, fornecedora_id=fornecedora_id,
        contrato_id=contract_id, competencia=competencia,
    )


@router.get("/api/bernhoeft/metrics")
def bernhoeft_metrics(user: Usuario = Depends(usuario_atual),
                      conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    exigir_papel(user, PAPEIS_BERNHOEFT)
    ids = contratos_do_usuario(conn, user)
    try:
        return metricas.calcular_metricas(conn, ids)
    except NotImplementedError as exc:
        raise HTTPException(503, "Métricas ainda não estão disponíveis (F3)") from exc


@router.get("/api/audit")
def audit_log(user: Usuario = Depends(usuario_atual),
              conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    return audit_for_admin(conn, user)
