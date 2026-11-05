"""Parecer à contratante. Dono: FRENTE 3 (a rota de publicação é da frente 1).

Spec 7.2: só o Analista Bernhoeft publica; a publicação grava snapshot imutável;
correção posterior = nova versão; a contratante nunca vê rascunho.
"""
from __future__ import annotations

import sqlite3
from typing import Any


def snapshot_parecer(conn: sqlite3.Connection, contract_id: str, competencia: str) -> dict[str, Any]:
    """Monta o conteúdo do parecer a partir das análises ATUAIS do contrato/competência.

    Conteúdo mínimo: contratante, fornecedora, contrato, competência, data, regra usada,
    escopo e limitações, resumo (avaliados / bloqueados / em revisão / com divergência /
    dados insuficientes / sem divergência), itens por trabalhador com evidências.
    Bloqueados aparecem nos denominadores, nunca como regulares.
    Sem valores em R$ e sem texto de OCR.
    """
    raise NotImplementedError("Frente 3: snapshot_parecer")
