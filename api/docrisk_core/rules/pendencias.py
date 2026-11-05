"""Pendências documentais, devolução e reenvio versionado. Dono: FRENTE 3.

Spec 4.1 e 4.3. Toda devolução tem: tipo de documento, trabalhador/competência
(se identificados), motivo objetivo, evidência (lote/página) e ação solicitada.
"""
from __future__ import annotations

import sqlite3

from ..contracts import CategoriaPendencia, StatusDocumento


def criar_pendencia(conn: sqlite3.Connection, *, contract_id: str, document_id: int | None,
                    worker_id: str | None, competencia: str | None, tipo_documento: str,
                    categoria: CategoriaPendencia, motivo: str, evidencia: str,
                    acao: str) -> int:
    """Cria a pendência (NOTIFICADA; DOCUMENTO_AUSENTE nasce ABERTA) com prazo =
    hoje + contracts.prazo_correcao_dias e histórico. Não duplica pendência aberta
    do mesmo documento/categoria. Devolve o id."""
    raise NotImplementedError("Frente 3: criar_pendencia")


def atualizar_por_nova_versao(conn: sqlite3.Connection, documento_antigo_id: int,
                              novo_status: StatusDocumento) -> None:
    """Chamada quando um reenvio substitui um documento: pendências abertas do antigo
    viram RESOLVIDA (novo APTO) ou REABERTA (novo com problema), com histórico."""
    raise NotImplementedError("Frente 3: atualizar_por_nova_versao")


def resolver_ausencia(conn: sqlite3.Connection, contract_id: str, worker_id: str,
                      competencia: str, tipo_documento: str) -> None:
    """Documento que estava ausente chegou -> pendência DOCUMENTO_AUSENTE vira RESOLVIDA."""
    raise NotImplementedError("Frente 3: resolver_ausencia")
