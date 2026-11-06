"""Pendências documentais, devolução e reenvio versionado. Dono: FRENTE 3.

Spec 4.1 e 4.3. Toda devolução tem: tipo de documento, trabalhador/competência
(se identificados), motivo objetivo, evidência (lote/página) e ação solicitada.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from .. import db
from ..contracts import CategoriaPendencia, StatusDocumento, StatusPendencia

#: Estados em que a pendência ainda exige algo da fornecedora ou da Bernhoeft.
STATUS_EM_ABERTO: tuple[str, ...] = (
    StatusPendencia.ABERTA.value, StatusPendencia.NOTIFICADA.value,
    StatusPendencia.REENVIADA.value, StatusPendencia.REABERTA.value,
)


def _historico(valor: str | None) -> list[dict]:
    try:
        dados = json.loads(valor or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return dados if isinstance(dados, list) else []


def _mudar_status(conn: sqlite3.Connection, issue: sqlite3.Row, status: StatusPendencia, motivo: str,
                  **extra: object) -> None:
    agora = db.agora()
    historico = _historico(issue["historico_json"])
    historico.append({"status": status.value, "em": agora, "motivo": motivo, **extra})
    conn.execute(
        "UPDATE issues SET status=?, updated_at=?, resolved_at=?, historico_json=? WHERE id=?",
        (status.value, agora, agora if status is StatusPendencia.RESOLVIDA else None,
         json.dumps(historico, ensure_ascii=False), issue["id"]))


def criar_pendencia(conn: sqlite3.Connection, *, contract_id: str, document_id: int | None,
                    worker_id: str | None, competencia: str | None, tipo_documento: str,
                    categoria: CategoriaPendencia, motivo: str, evidencia: str,
                    acao: str) -> int:
    """Cria a pendência (NOTIFICADA; DOCUMENTO_AUSENTE nasce ABERTA) com prazo =
    hoje + contracts.prazo_correcao_dias e histórico. Não duplica pendência aberta
    do mesmo documento/categoria. Devolve o id."""
    categoria = CategoriaPendencia(categoria)
    marcas = ",".join("?" * len(STATUS_EM_ABERTO))
    if document_id is not None:
        existente = conn.execute(
            f"SELECT id FROM issues WHERE document_id=? AND categoria=? AND status IN ({marcas})",
            (document_id, categoria.value, *STATUS_EM_ABERTO)).fetchone()
    else:
        existente = conn.execute(
            f"SELECT id FROM issues WHERE document_id IS NULL AND contract_id=? AND worker_id IS ?"
            f" AND competencia IS ? AND tipo_documento=? AND categoria=? AND status IN ({marcas})",
            (contract_id, worker_id, competencia, tipo_documento, categoria.value,
             *STATUS_EM_ABERTO)).fetchone()
    if existente is not None:
        return int(existente[0])

    linha = conn.execute("SELECT prazo_correcao_dias FROM contracts WHERE id=?", (contract_id,)).fetchone()
    dias = int(linha[0]) if linha is not None else 3
    prazo = (date.today() + timedelta(days=dias)).isoformat()
    status = (StatusPendencia.ABERTA if categoria is CategoriaPendencia.DOCUMENTO_AUSENTE
              else StatusPendencia.NOTIFICADA)
    agora = db.agora()
    historico = [{"status": status.value, "em": agora, "motivo": "pendência registrada"}]
    cur = conn.execute(
        "INSERT INTO issues (contract_id, document_id, worker_id, competencia, tipo_documento, categoria,"
        " motivo, evidencia, acao, status, prazo, created_at, updated_at, historico_json)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (contract_id, document_id, worker_id, competencia, tipo_documento, categoria.value,
         motivo[:1000], evidencia[:500], acao[:500], status.value, prazo, agora, agora,
         json.dumps(historico, ensure_ascii=False)))
    return int(cur.lastrowid)


def atualizar_por_nova_versao(conn: sqlite3.Connection, documento_antigo_id: int,
                              novo_status: StatusDocumento) -> None:
    """Chamada quando um reenvio substitui um documento: pendências abertas do antigo
    viram RESOLVIDA (novo APTO) ou REABERTA (novo com problema), com histórico.

    Novo documento em REVISAO_HUMANA: a pendência fica REENVIADA e passa a apontar para a
    nova versão; ela é resolvida quando a Bernhoeft aprova essa versão na revisão.
    Em REABERTA a pendência também passa a apontar para a nova versão (próximo reenvio).
    """
    novo_status = StatusDocumento(novo_status)
    novo = conn.execute("SELECT id, versao FROM documents WHERE substitui_id=? ORDER BY id DESC LIMIT 1",
                        (documento_antigo_id,)).fetchone()
    novo_id = int(novo["id"]) if novo is not None else None
    marcas = ",".join("?" * len(STATUS_EM_ABERTO))
    pendencias = conn.execute(
        f"SELECT * FROM issues WHERE document_id=? AND status IN ({marcas})",
        (documento_antigo_id, *STATUS_EM_ABERTO)).fetchall()
    for issue in pendencias:
        extra = {"documento": novo_id, "versao": int(novo["versao"])} if novo is not None else {}
        if novo_status is StatusDocumento.APTO:
            _mudar_status(conn, issue, StatusPendencia.RESOLVIDA, "nova versão recebida e apta", **extra)
        elif novo_status is StatusDocumento.REVISAO_HUMANA:
            _mudar_status(conn, issue, StatusPendencia.REENVIADA,
                          "nova versão recebida; em conferência pela Bernhoeft", **extra)
        else:
            _mudar_status(conn, issue, StatusPendencia.REABERTA,
                          "nova versão recebida ainda com problema objetivo", **extra)
        if novo_id is not None and novo_status is not StatusDocumento.APTO:
            conn.execute("UPDATE issues SET document_id=? WHERE id=?", (novo_id, issue["id"]))


def resolver_ausencia(conn: sqlite3.Connection, contract_id: str, worker_id: str,
                      competencia: str, tipo_documento: str) -> None:
    """Documento que estava ausente chegou -> pendência DOCUMENTO_AUSENTE vira RESOLVIDA."""
    marcas = ",".join("?" * len(STATUS_EM_ABERTO))
    pendencias = conn.execute(
        f"SELECT * FROM issues WHERE contract_id=? AND worker_id=? AND competencia=? AND tipo_documento=?"
        f" AND categoria=? AND status IN ({marcas})",
        (contract_id, worker_id, competencia, tipo_documento,
         CategoriaPendencia.DOCUMENTO_AUSENTE.value, *STATUS_EM_ABERTO)).fetchall()
    for issue in pendencias:
        _mudar_status(conn, issue, StatusPendencia.RESOLVIDA, "documento recebido")


def resolver_do_documento(conn: sqlite3.Connection, document_id: int, motivo: str) -> int:
    """Resolve todas as pendências em aberto de um documento (ex.: aprovado na revisão)."""
    marcas = ",".join("?" * len(STATUS_EM_ABERTO))
    pendencias = conn.execute(f"SELECT * FROM issues WHERE document_id=? AND status IN ({marcas})",
                              (document_id, *STATUS_EM_ABERTO)).fetchall()
    for issue in pendencias:
        _mudar_status(conn, issue, StatusPendencia.RESOLVIDA, motivo)
    return len(pendencias)
