"""Concessão individual: Admin BH → analistas; Gestor Forn → operadores."""
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from .. import db
from ..auth import Usuario, auditar, exigir_papel, usuario_atual
from ..contracts import Papel

router = APIRouter(prefix="/api/contract-access", tags=["contract-access"])


def connection():
    with db.tx() as conn:
        yield conn


def target_user(conn: sqlite3.Connection, manager: Usuario, user_id: str):
    exigir_papel(manager, [Papel.ADMIN_BH, Papel.GESTOR_FORN])
    expected = {Papel.ADMIN_BH: ("BERNHOEFT", Papel.ANALISTA_BH),
                Papel.GESTOR_FORN: ("FORNECEDORA", Papel.OPERADOR_FORN)}[manager.papel]
    if manager.org_tipo != expected[0]:
        raise HTTPException(403, "Perfil incompatível com a organização.")
    target = conn.execute("SELECT id,nome,org_id,role FROM users WHERE id=? AND org_id=? AND role=?",
                          (user_id, manager.org_id, expected[1].value)).fetchone()
    if target is None:
        raise HTTPException(404, "Usuário não encontrado para gestão de contratos.")
    return target


def managed_contracts(conn, manager):
    column = "bernhoeft_id" if manager.papel == Papel.ADMIN_BH else "fornecedora_id"
    return conn.execute(f"SELECT id,nome FROM contracts WHERE {column}=? ORDER BY nome,id",
                        (manager.org_id,)).fetchall()


def view(conn, user_id, contracts):
    now = datetime.now(timezone.utc).isoformat()
    grants = {r["contract_id"]: r for r in conn.execute(
        "SELECT * FROM user_contract_grants WHERE user_id=? AND revoked_at IS NULL", (user_id,))}
    return [{"id": c["id"], "nome": c["nome"],
             "ativo": c["id"] in grants and (grants[c["id"]]["expires_at"] is None or
                                               grants[c["id"]]["expires_at"] > now),
             "expires_at": grants[c["id"]]["expires_at"] if c["id"] in grants else None}
            for c in contracts]


class GrantInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ativo: bool = Field(strict=True)
    expires_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def valid_expiry(self):
        if not self.ativo and self.expires_at is not None:
            raise ValueError("Revogação não aceita data de expiração.")
        if self.expires_at is not None and self.expires_at <= datetime.now(timezone.utc):
            raise ValueError("A expiração deve estar no futuro e indicar o fuso horário.")
        return self


@router.get("/users/{user_id}")
def list_access(user_id: str, manager: Usuario = Depends(usuario_atual),
                conn: sqlite3.Connection = Depends(connection)):
    target = target_user(conn, manager, user_id)
    return {"user_id": target["id"], "nome": target["nome"],
            "contratos": view(conn, user_id, managed_contracts(conn, manager))}


@router.put("/users/{user_id}/contracts/{contract_id}")
def set_access(user_id: str, contract_id: str, payload: GrantInput,
               manager: Usuario = Depends(usuario_atual),
               conn: sqlite3.Connection = Depends(connection)):
    conn.execute("BEGIN IMMEDIATE")
    target_user(conn, manager, user_id)
    contracts = managed_contracts(conn, manager)
    if contract_id not in {c["id"] for c in contracts}:
        raise HTTPException(404, "Contrato não encontrado para gestão de acesso.")
    now = datetime.now(timezone.utc).isoformat()
    expiry = payload.expires_at.astimezone(timezone.utc).isoformat() if payload.expires_at else None
    current = conn.execute(
        "SELECT * FROM user_contract_grants WHERE user_id=? AND contract_id=? AND revoked_at IS NULL",
        (user_id, contract_id)).fetchone()
    # Repetir o mesmo PUT não duplica concessão ou auditoria. Renovar a validade
    # encerra a concessão anterior e preserva o histórico.
    unchanged = current is not None and payload.ativo and current["expires_at"] == expiry
    if not unchanged:
        if current is not None:
            conn.execute("UPDATE user_contract_grants SET revoked_at=?,revoked_by=? WHERE id=?",
                         (now, manager.id, current["id"]))
        if payload.ativo:
            conn.execute("INSERT INTO user_contract_grants (user_id,contract_id,granted_by,granted_at,expires_at) "
                         "VALUES (?,?,?,?,?)", (user_id, contract_id, manager.id, now, expiry))
        if current is not None or payload.ativo:
            auditar(conn, manager, "CONTRATO_ACESSO_CONCEDIDO" if payload.ativo else
                    "CONTRATO_ACESSO_REVOGADO", f"{user_id}:{contract_id}")
    result = next(c for c in view(conn, user_id, contracts) if c["id"] == contract_id)
    conn.commit()
    return result
