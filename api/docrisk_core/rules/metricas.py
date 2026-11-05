"""Indicadores do painel Bernhoeft. Dono: FRENTE 3.

Spec 7.1: calcular a partir dos REGISTROS processados (nunca do gabarito) e dizer
a unidade de cada número (documento lógico x versão, par trabalhador+competência...).
"""
from __future__ import annotations

import sqlite3
from typing import Any


def calcular_metricas(conn: sqlite3.Connection, contratos: list[str]) -> dict[str, Any]:
    """Indicadores dos contratos informados.

    Mínimo: documentos (lógicos e versões) por status e tipo; pares aptos / bloqueados /
    em revisão; divergências sinalizadas (não são passivos); pendências abertas e
    resolvidas; reenvios; tempo médio de regularização (h); taxa de revisão humana;
    páginas processadas e tempo médio por página (ms); pareceres publicados.
    """
    raise NotImplementedError("Frente 3: calcular_metricas")
