"""Fila, processamento em segundo plano e retomada. Dono: FRENTE 2.

O upload só registra; o worker lê página por página e grava o estado de cada uma,
para que uma queda nunca obrigue a recomeçar (diferencial "retomada após falha").
"""
from __future__ import annotations

import sqlite3

from ..auth import Usuario


def criar_lote(usuario: Usuario, contract_id: str, filename: str, data: bytes,
               issue_id: int | None = None) -> int:
    """Valida, salva o arquivo em DATA_DIR/uploads, renderiza e grava batches + pages.

    Retorna batch_id com status RECEBIDO. Erro objetivo -> render.ArquivoInvalido.
    Chamado pela rota POST /api/supplier/batches e pelo reenvio de pendência (issue_id).
    """
    raise NotImplementedError("Frente 2: criar_lote")


def enfileirar(batch_id: int) -> None:
    """Coloca o lote na fila. Com config.SYNC=1 processa na hora (testes)."""
    raise NotImplementedError("Frente 2: enfileirar")


def iniciar_worker() -> None:
    """Sobe a thread do worker e recoloca na fila lotes RECEBIDO/PROCESSANDO (retomada)."""
    raise NotImplementedError("Frente 2: iniciar_worker")


def processar_lote(batch_id: int) -> None:
    """Lê cada página ainda não OK (com cache em ai_cache), indexa em page_fts e grava ms.

    Alguma página com ERRO -> lote FALHA_PROCESSAMENTO (reprocessar depois reaproveita
    as páginas OK). Todas OK -> consolidar_lote + status CONCLUIDO.
    """
    raise NotImplementedError("Frente 2: processar_lote")


def consolidar_lote(conn: sqlite3.Connection, batch_id: int) -> set[tuple[str, str]]:
    """segmentar + rotear + gravar documents/doc_pages, de forma IDEMPOTENTE.

    Para cada documento de foco com trabalhador+competência:
    - se já existe versão vigente do mesmo tipo/trabalhador/competência -> a antiga vira
      SUBSTITUIDO e a nova recebe versao+1 (rules.pendencias.atualizar_por_nova_versao);
    - PENDENTE_CORRECAO -> rules.pendencias.criar_pendencia.
    Depois chama rules.conciliacao.conciliar para cada par afetado e devolve esses pares.
    """
    raise NotImplementedError("Frente 2: consolidar_lote")
