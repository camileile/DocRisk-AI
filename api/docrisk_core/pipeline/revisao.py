"""Ajuste manual de agrupamento na fila de revisão: dividir e unir documentos. Dono: FRENTE 2.

A rota da F1 (PATCH /api/documents/{id}/review) autoriza (ANALISTA_BH + contrato),
chama estas funções dentro da transação da requisição e grava a auditoria.

Regras:
- campos, tipo, trabalhador e competência são RECALCULADOS a partir da leitura das
  páginas (segmentation.resumir_paginas) — nunca copiados entre as partes;
- todo documento ajustado volta para REVISAO_HUMANA (a decisão final é "aprovar");
- uma página pertence a um único documento (doc_pages.page_id é único);
- `substitui_id`/`versao` ficam reservados ao REENVIO e não são usados aqui;
- documentos em histórico de versões não são unidos (o histórico seria perdido);
- a conciliação (F3) é refeita para os pares trabalhador+competência afetados.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from .. import db
from ..contracts import TIPOS_FOCO, AnalisePagina, StatusDocumento, TipoDocumento
from . import integracao_f3 as f3
from .segmentation import resumir_paginas

_SUBST = StatusDocumento.SUBSTITUIDO.value


class RevisaoInvalida(ValueError):
    """Pedido de ajuste impossível. A rota devolve 409 (estado) ou 422 (parâmetro)."""

    def __init__(self, mensagem: str, conflito: bool = False) -> None:
        super().__init__(mensagem)
        self.conflito = conflito  # True -> 409; False -> 422


@dataclass
class ResultadoRevisao:
    documentos: list[int]  # documentos resultantes, na ordem das páginas
    removidos: list[int] = field(default_factory=list)  # documentos absorvidos por união
    pares_afetados: set[tuple[str, str]] = field(default_factory=set)


def _documento(conn: sqlite3.Connection, doc_id: int) -> sqlite3.Row:
    doc = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if doc is None:
        raise RevisaoInvalida(f"Documento {doc_id} não encontrado.")
    if doc["status"] == _SUBST:
        raise RevisaoInvalida("Documento substituído por versão mais nova não pode ser ajustado.", conflito=True)
    return doc


def _paginas(conn: sqlite3.Connection, doc_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT dp.page_id, dp.posicao, p.ordem, p.analise_json FROM doc_pages dp"
        " JOIN pages p ON p.id = dp.page_id WHERE dp.document_id = ? ORDER BY dp.posicao",
        (doc_id,)).fetchall()


def _par(doc: sqlite3.Row | dict) -> tuple[str, str] | None:
    if doc["tipo"] in {t.value for t in TIPOS_FOCO} and doc["worker_id"] and doc["competencia"]:
        return doc["worker_id"], doc["competencia"]
    return None


def _em_historico(conn: sqlite3.Connection, doc: sqlite3.Row) -> bool:
    if doc["substitui_id"] is not None:
        return True
    return conn.execute("SELECT 1 FROM documents WHERE substitui_id = ? LIMIT 1", (doc["id"],)).fetchone() is not None


def _recalcular(conn: sqlite3.Connection, doc_id: int, motivo: str, usuario_id: str | None) -> dict:
    """Reescreve tipo/trabalhador/competência/campos/confiança a partir das páginas do documento."""
    paginas = _paginas(conn, doc_id)
    analises = [AnalisePagina.model_validate_json(p["analise_json"]) for p in paginas]
    seg = resumir_paginas(analises, [int(p["ordem"]) for p in paginas])
    motivos = [motivo, *seg.alertas]
    if seg.paginas_faltantes:
        motivos.append(f"Página(s) {', '.join(map(str, seg.paginas_faltantes))} do documento não recebida(s)")
    if seg.paginas_ilegiveis:
        motivos.append(f"Página(s) {', '.join(map(str, seg.paginas_ilegiveis))} do lote com legibilidade insuficiente")
    if seg.tipo is TipoDocumento.DESCONHECIDO:
        motivos.append("Tipo documental não identificado")
    conn.execute(
        "UPDATE documents SET tipo = ?, worker_id = ?, competencia = ?, status = ?, confianca = ?,"
        " motivos_pendencia = '[]', motivos_revisao = ?, campos_json = ?, revisado_por = ?, updated_at = ?"
        " WHERE id = ?",
        (seg.tipo.value, seg.trabalhador_id, seg.competencia, StatusDocumento.REVISAO_HUMANA.value,
         seg.confianca, json.dumps(list(dict.fromkeys(motivos)), ensure_ascii=False),
         seg.campos.model_dump_json(), usuario_id, db.agora(), doc_id))
    return {"tipo": seg.tipo.value, "worker_id": seg.trabalhador_id, "competencia": seg.competencia}


def _conciliar(conn: sqlite3.Connection, contract_id: str, pares: set[tuple[str, str]]) -> None:
    for worker_id, competencia in sorted(pares):
        f3.conciliar(conn, contract_id, worker_id, competencia)


def dividir(conn: sqlite3.Connection, doc_id: int, apos_posicao: int,
            usuario_id: str | None = None) -> ResultadoRevisao:
    """Divide o documento DEPOIS da página na posição `apos_posicao` (1..n-1).

    As páginas 1..k ficam no documento original; k+1..n vão para um documento novo.
    Pendências já abertas continuam ligadas ao documento original.
    """
    doc = _documento(conn, doc_id)
    paginas = _paginas(conn, doc_id)
    if len(paginas) < 2:
        raise RevisaoInvalida("Documento de uma página não pode ser dividido.")
    if isinstance(apos_posicao, bool) or not isinstance(apos_posicao, int) or not 1 <= apos_posicao < len(paginas):
        raise RevisaoInvalida(f"apos_posicao deve estar entre 1 e {len(paginas) - 1}.")

    antes = _par(doc)
    agora = db.agora()
    cur = conn.execute(
        "INSERT INTO documents (batch_id, contract_id, tipo, status, confianca, versao, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, 0, 1, ?, ?)",
        (doc["batch_id"], doc["contract_id"], doc["tipo"], StatusDocumento.REVISAO_HUMANA.value, agora, agora))
    novo_id = int(cur.lastrowid)
    segunda = paginas[apos_posicao:]
    for posicao, p in enumerate(segunda, start=1):
        conn.execute("UPDATE doc_pages SET document_id = ?, posicao = ? WHERE page_id = ?",
                     (novo_id, posicao, p["page_id"]))

    ordens = (paginas[0]["ordem"], paginas[apos_posicao - 1]["ordem"], segunda[0]["ordem"], segunda[-1]["ordem"])
    motivo_1 = f"Documento dividido na revisão (páginas {ordens[0]}–{ordens[1]}); confirmar tipo e vínculo"
    motivo_2 = (f"Criado na revisão a partir do documento #{doc_id} (páginas {ordens[2]}–{ordens[3]});"
                " confirmar tipo e vínculo")
    depois_1 = _recalcular(conn, doc_id, motivo_1, usuario_id)
    depois_2 = _recalcular(conn, novo_id, motivo_2, usuario_id)

    pares = {p for p in (antes, _par(depois_1), _par(depois_2)) if p}
    _conciliar(conn, doc["contract_id"], pares)
    return ResultadoRevisao(documentos=[doc_id, novo_id], pares_afetados=pares)


def unir_proximo(conn: sqlite3.Connection, doc_id: int, usuario_id: str | None = None) -> ResultadoRevisao:
    """Une ao documento cuja primeira página vem LOGO DEPOIS da última página deste
    (mesmo lote). O próximo deixa de existir; suas páginas e pendências passam para este.
    """
    doc = _documento(conn, doc_id)
    paginas = _paginas(conn, doc_id)
    if not paginas:
        raise RevisaoInvalida("Documento sem páginas.", conflito=True)
    ultima = max(int(p["ordem"]) for p in paginas)

    proximo = conn.execute(
        "SELECT d.* FROM documents d JOIN doc_pages dp ON dp.document_id = d.id JOIN pages p ON p.id = dp.page_id"
        " WHERE d.batch_id = ? AND d.id <> ? AND d.status <> ? AND p.ordem = ? LIMIT 1",
        (doc["batch_id"], doc_id, _SUBST, ultima + 1)).fetchone()
    if proximo is None:
        raise RevisaoInvalida("Não há documento contíguo depois deste no mesmo lote.", conflito=True)
    if min(int(p["ordem"]) for p in _paginas(conn, proximo["id"])) != ultima + 1:
        raise RevisaoInvalida("O próximo documento não começa logo após este.", conflito=True)
    if _em_historico(conn, doc) or _em_historico(conn, proximo):
        raise RevisaoInvalida("Documento com histórico de versões (reenvio) não pode ser unido.", conflito=True)

    antes = {p for p in (_par(doc), _par(proximo)) if p}
    paginas_proximo = _paginas(conn, proximo["id"])
    for i, p in enumerate(paginas_proximo, start=len(paginas) + 1):
        conn.execute("UPDATE doc_pages SET document_id = ?, posicao = ? WHERE page_id = ?",
                     (doc_id, i, p["page_id"]))
    conn.execute("UPDATE issues SET document_id = ?, updated_at = ? WHERE document_id = ?",
                 (doc_id, db.agora(), proximo["id"]))
    conn.execute("DELETE FROM documents WHERE id = ?", (proximo["id"],))

    primeira = min(int(p["ordem"]) for p in paginas)
    ultima_unida = max(int(p["ordem"]) for p in paginas_proximo)
    depois = _recalcular(
        conn, doc_id,
        f"Documentos #{doc_id} e #{proximo['id']} unidos na revisão (páginas {primeira}–{ultima_unida});"
        " confirmar tipo e vínculo", usuario_id)

    pares = antes | ({_par(depois)} - {None})
    _conciliar(conn, doc["contract_id"], pares)
    return ResultadoRevisao(documentos=[doc_id], removidos=[int(proximo["id"])], pares_afetados=pares)
