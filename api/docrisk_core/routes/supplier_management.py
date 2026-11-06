"""Gestão da fornecedora; contas com token só são criadas no demo local."""
import secrets
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .. import config, db
from ..auth import Usuario, auditar, exigir_papel, usuario_atual
from ..contracts import Papel

router = APIRouter(prefix="/api/supplier/operators", tags=["supplier"])


def connection():
    with db.tx() as conn:
        yield conn


def authorize(user: Usuario, write: bool = False):
    exigir_papel(user, [Papel.GESTOR_FORN])
    if user.org_tipo != "FORNECEDORA":
        raise HTTPException(403, "Perfil incompatível com a organização.")
    if write and (config.AUTH_MODE != "token" or not config.DEMO_MODE):
        raise HTTPException(403, "No acesso Clerk, convide operadores e gerencie seus vínculos autenticados.")


class OperatorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str = Field(min_length=2, max_length=140)

    @field_validator("nome")
    @classmethod
    def normalized_name(cls, value: str):
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Informe o nome do operador.")
        return value


class StatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ativo: bool = Field(strict=True)


@router.get("")
def list_operators(user: Usuario = Depends(usuario_atual), conn: sqlite3.Connection = Depends(connection)):
    authorize(user)
    return [dict(r) for r in conn.execute(
        "SELECT id, nome, org_id, role AS papel, ativo FROM users "
        "WHERE org_id=? AND role='OPERADOR_FORN' ORDER BY nome,id", (user.org_id,))]


@router.post("", status_code=201)
def create_operator(payload: OperatorInput, user: Usuario = Depends(usuario_atual),
                    conn: sqlite3.Connection = Depends(connection)):
    authorize(user, write=True)
    uid, token = "u-" + secrets.token_hex(6), secrets.token_urlsafe(24)
    conn.execute("INSERT INTO users (id,nome,org_id,role,token) VALUES (?,?,?,'OPERADOR_FORN',?)",
                 (uid, payload.nome, user.org_id, token))
    auditar(conn, user, "OPERADOR_CRIADO", uid)
    # Persistir antes da resposta: a interface consulta novamente imediatamente.
    conn.commit()
    # Credencial efêmera de teste, mostrada apenas nesta resposta, nunca na lista.
    return {"id": uid, "nome": payload.nome, "org_id": user.org_id,
            "papel": "OPERADOR_FORN", "ativo": 1, "token_teste": token}


@router.patch("/{uid}/status")
def operator_status(uid: str, payload: StatusInput, user: Usuario = Depends(usuario_atual),
                    conn: sqlite3.Connection = Depends(connection)):
    authorize(user, write=True)
    target = conn.execute("SELECT id FROM users WHERE id=? AND org_id=? AND role='OPERADOR_FORN'",
                          (uid, user.org_id)).fetchone()
    if target is None:
        raise HTTPException(404, "Operador não encontrado.")
    conn.execute("UPDATE users SET ativo=? WHERE id=?", (int(payload.ativo), uid))
    auditar(conn, user, "OPERADOR_ATIVADO" if payload.ativo else "OPERADOR_DESATIVADO", uid)
    # Persistir antes da resposta: a interface consulta novamente imediatamente.
    conn.commit()
    return {"id": uid, "ativo": payload.ativo}
