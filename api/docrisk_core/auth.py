"""Autenticação e autorização. Dono: FRENTE 1 (API, banco e segurança).

Regra de ouro (spec 2.2 e 8.1): toda rota confere organização + vínculo com o
contrato + papel, no back-end. Esconder botão no front não é proteção.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterable

from fastapi import Header

from .contracts import Papel


@dataclass(frozen=True)
class Usuario:
    id: str
    nome: str
    org_id: str
    org_tipo: str  # BERNHOEFT | CONTRATANTE | FORNECEDORA
    papel: Papel


def usuario_atual(authorization: str = Header(default="")) -> Usuario:
    """Dependência FastAPI: lê 'Bearer <token>' e carrega o usuário ativo.

    Aceite: sem token ou token inválido -> HTTP 401.
    """
    raise NotImplementedError("Frente 1: usuario_atual")


def contratos_do_usuario(conn: sqlite3.Connection, usuario: Usuario) -> list[str]:
    """IDs de contrato que a ORGANIZAÇÃO do usuário pode ver.

    BERNHOEFT -> contracts.bernhoeft_id; FORNECEDORA -> fornecedora_id;
    CONTRATANTE -> contratante_id.
    """
    raise NotImplementedError("Frente 1: contratos_do_usuario")


def exigir_contrato(conn: sqlite3.Connection, usuario: Usuario, contract_id: str) -> None:
    """Recurso de contrato alheio -> HTTP 404 (não revela que existe) + auditoria NEGADO."""
    raise NotImplementedError("Frente 1: exigir_contrato")


def exigir_papel(usuario: Usuario, papeis: Iterable[Papel]) -> None:
    """Papel fora da lista -> HTTP 403."""
    raise NotImplementedError("Frente 1: exigir_papel")


def auditar(conn: sqlite3.Connection, usuario: Usuario | None, acao: str, alvo: str,
            resultado: str = "OK") -> None:
    """Grava em `audit` QUEM fez O QUÊ e QUANDO — nunca conteúdo de documento."""
    raise NotImplementedError("Frente 1: auditar")
