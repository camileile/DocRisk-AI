from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterable

from fastapi import Header, HTTPException

from . import db
from .contracts import Papel


@dataclass(frozen=True)
class Usuario:
    id: str
    nome: str
    org_id: str
    org_tipo: str
    papel: Papel


def usuario_atual(authorization: str = Header(default="")) -> Usuario:
    esquema, _, token = authorization.partition(" ")
    if esquema.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Token bearer obrigatório",
                            headers={"WWW-Authenticate": "Bearer"})
    with db.tx() as conn:
        row = conn.execute(
            "SELECT u.id, u.nome, u.org_id, o.tipo AS org_tipo, u.role "
            "FROM users u JOIN organizations o ON o.id=u.org_id "
            "WHERE u.token=? AND u.ativo=1",
            (token.strip(),),
        ).fetchone()
        platform = None if row is not None else conn.execute(
            "SELECT id,nome FROM platform_accounts WHERE token=? AND ativo=1", (token.strip(),)
        ).fetchone()
    if platform is not None:
        return Usuario(platform["id"], platform["nome"], "DOCRISK", "PLATAFORMA", Papel.ADMIN_PLATAFORMA)
    if row is None:
        raise HTTPException(status_code=401, detail="Token inválido ou usuário inativo",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        papel = Papel(row["role"])
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Papel de usuário inválido") from exc
    return Usuario(row["id"], row["nome"], row["org_id"], row["org_tipo"], papel)


def contratos_do_usuario(conn: sqlite3.Connection, usuario: Usuario) -> list[str]:
    coluna_por_tipo = {
        "BERNHOEFT": "bernhoeft_id",
        "FORNECEDORA": "fornecedora_id",
        "CONTRATANTE": "contratante_id",
    }
    coluna = coluna_por_tipo.get(usuario.org_tipo)
    if coluna is None:
        return []
    rows = conn.execute(f"SELECT id FROM contracts WHERE {coluna}=? ORDER BY id",
                        (usuario.org_id,)).fetchall()
    return [row[0] for row in rows]


def exigir_contrato(conn: sqlite3.Connection, usuario: Usuario, contract_id: str) -> None:
    if contract_id not in contratos_do_usuario(conn, usuario):
        auditar(conn, usuario, "CONTRATO_NEGADO", contract_id, "NEGADO")
        conn.commit()
        raise HTTPException(status_code=404, detail="Contrato não encontrado")


def exigir_papel(usuario: Usuario, papeis: Iterable[Papel]) -> None:
    if usuario.papel not in set(papeis):
        raise HTTPException(status_code=403, detail="Ação não permitida para este perfil")


def auditar(conn: sqlite3.Connection, usuario: Usuario | None, acao: str, alvo: str,
            resultado: str = "OK") -> None:
    conn.execute(
        "INSERT INTO audit (user_id, org_id, acao, alvo, resultado, instante) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (usuario.id if usuario else None, usuario.org_id if usuario else None,
         acao[:120], alvo[:240], resultado[:20], db.agora()),
    )
