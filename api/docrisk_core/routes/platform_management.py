"""Administração estrutural independente da operação documental Bernhoeft."""
import secrets
import sqlite3
import re
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .. import config, db
from ..auth import Usuario, auditar, exigir_papel, usuario_atual
from ..contracts import Papel
from .identity import InvitationInput, issue_invitation

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
    email: str | None = Field(default=None, max_length=254)

    @field_validator("nome", "administrador")
    @classmethod
    def clean(cls, v):
        if len(v.strip()) < 2:
            raise ValueError("Nome obrigatório.")
        return v.strip()

    @field_validator("email")
    @classmethod
    def clean_email(cls, v):
        if v is None:
            return None
        v = v.strip().casefold()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", v):
            raise ValueError("E-mail inválido.")
        return v

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
    initial_invites = [dict(r) for r in conn.execute(
        "SELECT i.id,i.org_id,i.nome,i.email,i.status,i.expires_at "
        "FROM identity_invitations i JOIN platform_accounts p ON p.id=i.invited_by "
        "WHERE i.role='ADMIN_BH' ORDER BY i.created_at DESC")]
    events = [dict(r) for r in conn.execute(
        "SELECT id,acao,alvo,resultado,instante FROM audit WHERE org_id='DOCRISK' ORDER BY id DESC LIMIT 30")]
    return {"auditoras": auditors, "administradores": admins, "convites_iniciais": initial_invites, "modulos": MODULES,
            "configuracoes": dict(conn.execute("SELECT nome,contato FROM platform_settings WHERE id=1").fetchone()),
            "auditoria": events}


@router.post("/auditors", status_code=201)
def create_auditor(payload: AuditorInput, x_docrisk_link: str = Header(default=""),
                   user: Usuario = Depends(usuario_atual), conn: sqlite3.Connection = Depends(connection)):
    authorize(user)
    # O modo demonstrativo mantém o cadastro com token, isolado do login real.
    clerk_mode = config.AUTH_MODE == "clerk" and not config.DEMO_MODE
    demo_mode = config.AUTH_MODE == "token" and config.DEMO_MODE
    if not clerk_mode and not demo_mode:
        raise HTTPException(403, "Configure o modo de autenticação antes de cadastrar auditoras.")
    if clerk_mode and not payload.email:
        raise HTTPException(422, "Informe o e-mail do administrador inicial para enviar o convite.")

    # Serializar cadastros com o mesmo nome antes de criar a organização.
    conn.execute("BEGIN IMMEDIATE")
    names = [r[0].casefold() for r in conn.execute("SELECT nome FROM organizations WHERE tipo='BERNHOEFT'")]
    if payload.nome.casefold() in names:
        raise HTTPException(409, "Organização auditora já cadastrada.")
    org = "ORG-" + secrets.token_hex(6).upper()
    conn.execute("INSERT INTO organizations (id,nome,tipo) VALUES (?,?,'BERNHOEFT')", (org, payload.nome))

    if clerk_mode:
        # A conta ADMIN_BH só é criada após o destinatário confirmar o e-mail e
        # aceitar o convite. Não provisionar um usuário com token de demonstração.
        invitation = InvitationInput(email=payload.email, nome=payload.administrador,
                                     org_id=org, role=Papel.ADMIN_BH)
        conn.commit()  # A emissão usa sua própria transação antes da chamada ao Clerk.
        try:
            issued = issue_invitation(conn, user, x_docrisk_link, invitation)
        except Exception:
            # Falha no convite => não deixar auditora sem responsável inicial.
            # Uma eventual mensagem externa sem registro local não concede acesso.
            conn.execute("DELETE FROM identity_invitations WHERE org_id=?", (org,))
            conn.execute("DELETE FROM organizations WHERE id=?", (org,))
            conn.commit()
            raise
        auditar(conn, user, "AUDITORA_CRIADA", org)
        conn.commit()
        return {"id": org, "convite_id": issued["id"], "convite_status": issued["status"]}

    uid, token = "u-" + secrets.token_hex(6), secrets.token_urlsafe(24)
    conn.execute("INSERT INTO users (id,nome,org_id,role,token) VALUES (?,?,?,'ADMIN_BH',?)",
                 (uid, payload.administrador, org, token))
    auditar(conn, user, "AUDITORA_CRIADA", org)
    conn.commit()
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
    # Persistir antes da resposta: a interface consulta novamente imediatamente.
    conn.commit()
    return {"id": uid, "ativo": payload.ativo}


@router.patch("/settings")
def update_settings(payload: SettingsInput, user: Usuario = Depends(usuario_atual), conn: sqlite3.Connection = Depends(connection)):
    authorize(user, write=True)
    conn.execute("UPDATE platform_settings SET nome=?,contato=? WHERE id=1", (payload.nome, payload.contato.strip()))
    auditar(conn, user, "CONFIGURACAO_PLATAFORMA_ATUALIZADA", "dados-institucionais")
    # Persistir antes da resposta: a interface consulta novamente imediatamente.
    conn.commit()
    return {"nome": payload.nome, "contato": payload.contato.strip()}
