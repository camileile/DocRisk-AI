"""Administração estrutural independente da operação documental Bernhoeft."""
import secrets
import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .. import config, db
from ..auth import Usuario, auditar, exigir_papel, usuario_atual
from ..contracts import Papel

router = APIRouter(prefix="/api/platform", tags=["platform"])
MODULES = [
    {"id": "trabalhista", "nome": "Trabalhista", "status": "MVP"},
    {"id": "homologacao", "nome": "Homologação de Fornecedores", "status": "PLANEJADO"},
    {"id": "sso", "nome": "Saúde e Segurança Ocupacional", "status": "PLANEJADO"},
    {"id": "ambiental", "nome": "Conformidade Ambiental", "status": "PLANEJADO"},
]


def connection():
    with db.tx() as conn:
        yield conn


def authorize(user: Usuario, write=False):
    exigir_papel(user, [Papel.ADMIN_PLATAFORMA])
    if user.org_tipo != "PLATAFORMA":
        raise HTTPException(403, "Identidade institucional obrigatória.")
    if write and not config.DEMO_MODE:
        raise HTTPException(403, "Alterações disponíveis apenas no ambiente de testes.")


class AuditorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str = Field(min_length=2, max_length=160)
    administrador: str = Field(min_length=2, max_length=140)

    @field_validator("nome", "administrador")
    @classmethod
    def clean(cls, v):
        if len(v.strip()) < 2:
            raise ValueError("Nome obrigatório.")
        return v.strip()


class SettingsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str = Field(min_length=2, max_length=160)
    contato: str = Field(max_length=160)

    @field_validator("nome")
    @classmethod
    def clean(cls, v):
        if len(v.strip()) < 2:
            raise ValueError("Nome obrigatório.")
        return v.strip()


class StatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ativo: bool = Field(strict=True)


@router.get("/registry")
def registry(user: Usuario = Depends(usuario_atual), conn: sqlite3.Connection = Depends(connection)):
    authorize(user)
    auditors = [dict(r) for r in conn.execute(
        "SELECT o.id,o.nome,(SELECT COUNT(*) FROM contracts c WHERE c.bernhoeft_id=o.id) AS contratos "
        "FROM organizations o WHERE o.tipo='BERNHOEFT' ORDER BY o.nome")]
    admins = [dict(r) for r in conn.execute(
        "SELECT u.id,u.nome,u.org_id,u.ativo FROM users u JOIN organizations o ON o.id=u.org_id "
        "WHERE o.tipo='BERNHOEFT' AND u.role='ADMIN_BH' ORDER BY u.nome")]
    events = [dict(r) for r in conn.execute(
        "SELECT id,acao,alvo,resultado,instante FROM audit WHERE org_id='DOCRISK' ORDER BY id DESC LIMIT 30")]
    return {"auditoras": auditors, "administradores": admins, "modulos": MODULES,
            "configuracoes": dict(conn.execute("SELECT nome,contato FROM platform_settings WHERE id=1").fetchone()),
            "auditoria": events}


@router.post("/auditors", status_code=201)
def create_auditor(payload: AuditorInput, user: Usuario = Depends(usuario_atual), conn: sqlite3.Connection = Depends(connection)):
    authorize(user, write=True)
    names = [r[0].casefold() for r in conn.execute("SELECT nome FROM organizations WHERE tipo='BERNHOEFT'")]
    if payload.nome.casefold() in names:
        raise HTTPException(409, "Organização auditora já cadastrada.")
    org, uid, token = "ORG-" + secrets.token_hex(6).upper(), "u-" + secrets.token_hex(6), secrets.token_urlsafe(24)
    conn.execute("INSERT INTO organizations (id,nome,tipo) VALUES (?,?,'BERNHOEFT')", (org, payload.nome))
    conn.execute("INSERT INTO users (id,nome,org_id,role,token) VALUES (?,?,?,'ADMIN_BH',?)", (uid, payload.administrador, org, token))
    auditar(conn, user, "AUDITORA_CRIADA", org)
    return {"id": org, "administrador_id": uid, "token_teste": token}


@router.patch("/administrators/{uid}/status")
def administrator_status(uid: str, payload: StatusInput, user: Usuario = Depends(usuario_atual), conn: sqlite3.Connection = Depends(connection)):
    authorize(user, write=True)
    target = conn.execute("SELECT u.id FROM users u JOIN organizations o ON o.id=u.org_id "
                          "WHERE u.id=? AND u.role='ADMIN_BH' AND o.tipo='BERNHOEFT'", (uid,)).fetchone()
    if target is None:
        raise HTTPException(404, "Administrador da auditora não encontrado.")
    conn.execute("UPDATE users SET ativo=? WHERE id=?", (int(payload.ativo), uid))
    auditar(conn, user, "ADMIN_AUDITORA_ATIVADO" if payload.ativo else "ADMIN_AUDITORA_DESATIVADO", uid)
    return {"id": uid, "ativo": payload.ativo}


@router.patch("/settings")
def update_settings(payload: SettingsInput, user: Usuario = Depends(usuario_atual), conn: sqlite3.Connection = Depends(connection)):
    authorize(user, write=True)
    conn.execute("UPDATE platform_settings SET nome=?,contato=? WHERE id=1", (payload.nome, payload.contato.strip()))
    auditar(conn, user, "CONFIGURACAO_PLATAFORMA_ATUALIZADA", "dados-institucionais")
    return {"nome": payload.nome, "contato": payload.contato.strip()}
