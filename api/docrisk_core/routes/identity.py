"""Login, vínculos e convites: API produtiva; recuperação permanece no Clerk."""
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .. import config, db, clerk_identity
from ..auth import Usuario, auditar, usuario_atual
from ..contracts import Papel
from ..identity_links import links

router = APIRouter(prefix="/api/auth", tags=["identity"])


def principal(authorization: str = Header(default="")):
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(401, "Identificação obrigatória.")
    return clerk_identity.authenticate(token.strip())


def connection():
    with db.tx() as conn:
        yield conn


def now():
    return datetime.now(timezone.utc)


def authorize_invitation(conn, user, org_id, role):
    org = conn.execute("SELECT tipo FROM organizations WHERE id=?", (org_id,)).fetchone()
    if org is None:
        raise HTTPException(404, "Organização não encontrada.")
    allowed = False
    if user.papel == Papel.ADMIN_PLATAFORMA:
        allowed = role == Papel.ADMIN_BH and org["tipo"] == "BERNHOEFT"
    elif user.papel == Papel.ADMIN_BH:
        if role in {Papel.ADMIN_BH, Papel.ANALISTA_BH}:
            allowed = org_id == user.org_id and org["tipo"] == "BERNHOEFT"
        elif role in {Papel.GESTOR_CONTR, Papel.GESTOR_FORN}:
            column = "contratante_id" if role == Papel.GESTOR_CONTR else "fornecedora_id"
            expected = "CONTRATANTE" if role == Papel.GESTOR_CONTR else "FORNECEDORA"
            allowed = org["tipo"] == expected and conn.execute(
                f"SELECT 1 FROM contracts WHERE bernhoeft_id=? AND {column}=?", (user.org_id, org_id)).fetchone() is not None
    elif user.papel == Papel.GESTOR_FORN:
        allowed = role == Papel.OPERADOR_FORN and org_id == user.org_id and org["tipo"] == "FORNECEDORA"
    if not allowed:
        raise HTTPException(403, "Seu perfil não pode conceder este acesso nesta organização.")


class InvitationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    nome: str = Field(min_length=2, max_length=140)
    org_id: str = Field(min_length=1, max_length=120)
    role: Papel

    @field_validator("email")
    @classmethod
    def email_valid(cls, value):
        import re
        value = value.strip().casefold()
        if re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value) is None:
            raise ValueError("E-mail inválido.")
        return value

    @field_validator("nome")
    @classmethod
    def nome_valid(cls, value):
        if len(value.strip()) < 2:
            raise ValueError("Nome obrigatório.")
        return value.strip()


@router.get("/links")
def available_links(identity=Depends(principal), conn=Depends(connection)):
    return [{"id": r["id"], "nome": r["platform_nome"] or r["nome"],
             "org_nome": "DocRisk AI" if r["platform_account_id"] else r["org_nome"],
             "papel": "ADMIN_PLATAFORMA" if r["platform_account_id"] else r["role"]} for r in links(conn, identity)]


@router.get("/invitations/pending")
def pending_invitations(identity=Depends(principal), conn=Depends(connection)):
    email = clerk_identity.verified_email(identity)
    return [dict(r) for r in conn.execute(
        "SELECT i.id,i.nome,i.role,i.expires_at,o.nome AS org_nome FROM identity_invitations i "
        "JOIN organizations o ON o.id=i.org_id WHERE i.email=? AND i.status='PENDING' AND i.expires_at>?",
        (email, now().isoformat()))]


@router.post("/invitations", status_code=201)
def create_invitation(payload: InvitationInput, x_docrisk_link: str = Header(default=""), identity=Depends(principal),
                      user: Usuario = Depends(usuario_atual), conn=Depends(connection)):
    authorize_invitation(conn, user, payload.org_id, payload.role)
    redirect = urlsplit(config.CLERK_INVITE_REDIRECT_URL)
    origin = f"{redirect.scheme}://{redirect.netloc}"
    if (origin not in config.CLERK_AUTHORIZED_PARTIES or redirect.scheme != "https"
            or redirect.username or redirect.password or redirect.query or redirect.fragment):
        raise HTTPException(503, "Configure o destino seguro dos convites.")
    conn.execute("BEGIN IMMEDIATE")
    conn.execute("UPDATE identity_invitations SET status='EXPIRED' WHERE email=? AND expires_at<=? AND status IN ('CREATING','PENDING')",
                 (payload.email, now().isoformat()))
    if conn.execute("SELECT 1 FROM identity_invitations WHERE email=? AND org_id=? AND role=? AND status IN ('CREATING','PENDING') AND expires_at>?",
                    (payload.email, payload.org_id, payload.role.value, now().isoformat())).fetchone():
        raise HTTPException(409, "Já existe convite pendente para este acesso.")
    invitation_id = secrets.token_urlsafe(24)
    created = now()
    conn.execute("INSERT INTO identity_invitations (id,email,nome,org_id,role,invited_by,invited_link_id,status,created_at,expires_at) VALUES (?,?,?,?,?,?,?,'CREATING',?,?)",
                 (invitation_id, payload.email, payload.nome, payload.org_id, payload.role.value, user.id, x_docrisk_link,
                  created.isoformat(), (created + timedelta(hours=72)).isoformat()))
    conn.commit()
    try:
        result = clerk_identity.clerk_api("POST", "/invitations", {"email_address": payload.email,
            "redirect_url": config.CLERK_INVITE_REDIRECT_URL, "expires_in_days": 3, "ignore_existing": True,
            "public_metadata": {"docrisk_invitation_id": invitation_id}})
        if not isinstance(result.get("id"), str):
            raise HTTPException(503, "O provedor não confirmou o convite.")
    except HTTPException:
        conn.execute("UPDATE identity_invitations SET status='FAILED' WHERE id=?", (invitation_id,))
        conn.commit()
        raise
    conn.execute("UPDATE identity_invitations SET provider_id=?,status='PENDING' WHERE id=?", (result["id"], invitation_id))
    auditar(conn, user, "CONVITE_CRIADO", invitation_id)
    return {"id": invitation_id, "expires_at": (created + timedelta(hours=72)).isoformat(), "status": "PENDING"}


@router.get("/invitations")
def list_invitations(identity=Depends(principal), user: Usuario = Depends(usuario_atual), conn=Depends(connection)):
    if user.papel not in {Papel.ADMIN_PLATAFORMA, Papel.ADMIN_BH, Papel.GESTOR_FORN}:
        raise HTTPException(403, "Seu perfil não administra convites.")
    result = []
    for row in conn.execute("SELECT id,email,nome,org_id,role,status,expires_at FROM identity_invitations ORDER BY created_at DESC"):
        try:
            authorize_invitation(conn, user, row["org_id"], Papel(row["role"]))
        except HTTPException:
            continue
        result.append(dict(row))
    return result


@router.post("/invitations/{invitation_id}/revoke")
def revoke_invitation(invitation_id: str, identity=Depends(principal), user: Usuario = Depends(usuario_atual), conn=Depends(connection)):
    row = conn.execute("SELECT * FROM identity_invitations WHERE id=?", (invitation_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Convite não encontrado.")
    authorize_invitation(conn, user, row["org_id"], Papel(row["role"]))
    if row["status"] != "PENDING":
        raise HTTPException(409, "Somente convites pendentes podem ser revogados.")
    conn.execute("UPDATE identity_invitations SET status='REVOKED' WHERE id=?", (invitation_id,))
    auditar(conn, user, "CONVITE_REVOGADO", invitation_id)
    conn.commit()  # Bloqueio local efetivo mesmo se a chamada ao provedor falhar.
    try:
        clerk_identity.clerk_api("POST", f"/invitations/{row['provider_id']}/revoke")
    except HTTPException:
        return {"status": "REVOKED", "provider_pending": True}
    return {"status": "REVOKED", "provider_pending": False}


@router.post("/invitations/{invitation_id}/accept")
def accept_invitation(invitation_id: str, identity=Depends(principal), conn=Depends(connection)):
    email = clerk_identity.verified_email(identity)
    preview = conn.execute("SELECT * FROM identity_invitations WHERE id=? AND email=?", (invitation_id, email)).fetchone()
    if preview is None:
        raise HTTPException(404, "Convite não encontrado para esta identidade.")
    if preview["status"] != "PENDING" or preview["expires_at"] <= now().isoformat():
        raise HTTPException(409, "Convite expirado, revogado ou já utilizado.")
    if not clerk_identity.invitation_active(preview["provider_id"], email):
        raise HTTPException(409, "O convite não está mais ativo no provedor.")
    # A decisão e a ativação são atômicas, inclusive em dois cliques/abas.
    conn.execute("BEGIN IMMEDIATE")
    row = conn.execute("SELECT * FROM identity_invitations WHERE id=? AND email=?", (invitation_id, email)).fetchone()
    if row is None:
        raise HTTPException(404, "Convite não encontrado para esta identidade.")
    if row["status"] != "PENDING" or row["expires_at"] <= now().isoformat():
        raise HTTPException(409, "Convite expirado, revogado ou já utilizado.")
    if conn.execute("SELECT 1 FROM identity_links WHERE id=? AND ativo=1 AND (user_id=? OR platform_account_id=?)",
                    (row["invited_link_id"], row["invited_by"], row["invited_by"])).fetchone() is None:
        raise HTTPException(403, "O vínculo do emissor não está mais autorizado.")
    # Revalidar o emissor: uma desativação posterior também invalida a concessão.
    issuer = conn.execute("SELECT u.*,o.tipo AS org_tipo FROM users u JOIN organizations o ON o.id=u.org_id WHERE u.id=? AND u.ativo=1", (row["invited_by"],)).fetchone()
    platform = conn.execute("SELECT id,nome FROM platform_accounts WHERE id=? AND ativo=1", (row["invited_by"],)).fetchone()
    if platform:
        inviter = Usuario(platform["id"], platform["nome"], "DOCRISK", "PLATAFORMA", Papel.ADMIN_PLATAFORMA)
    elif issuer:
        inviter = Usuario(issuer["id"], issuer["nome"], issuer["org_id"], issuer["org_tipo"], Papel(issuer["role"]))
    else:
        raise HTTPException(403, "O emissor não está autorizado a conceder acesso.")
    authorize_invitation(conn, inviter, row["org_id"], Papel(row["role"]))
    if conn.execute("SELECT 1 FROM identity_links WHERE issuer=? AND subject=? AND platform_account_id IS NOT NULL", (identity.issuer, identity.subject)).fetchone():
        raise HTTPException(403, "A identidade institucional da plataforma não recebe vínculo operacional.")
    if conn.execute("SELECT 1 FROM identity_links l JOIN users u ON u.id=l.user_id WHERE l.issuer=? AND l.subject=? AND u.org_id=? AND u.role=?", (identity.issuer, identity.subject, row["org_id"], row["role"])).fetchone():
        raise HTTPException(409, "Esta identidade já possui este vínculo; consulte o responsável.")
    user_id, link_id = "u-" + secrets.token_hex(12), secrets.token_urlsafe(24)
    conn.execute("INSERT INTO users (id,nome,org_id,role,token) VALUES (?,?,?,?,?)", (user_id,row["nome"],row["org_id"],row["role"],secrets.token_urlsafe(48)))
    conn.execute("INSERT INTO identity_links (id,issuer,subject,user_id,created_at) VALUES (?,?,?,?,?)", (link_id,identity.issuer,identity.subject,user_id,now().isoformat()))
    conn.execute("UPDATE identity_invitations SET status='ACCEPTED',accepted_by=?,accepted_at=? WHERE id=?", (identity.subject,now().isoformat(),invitation_id))
    org_type = conn.execute("SELECT tipo FROM organizations WHERE id=?", (row["org_id"],)).fetchone()[0]
    accepted_user = Usuario(user_id,row["nome"],row["org_id"],org_type,Papel(row["role"]))
    auditar(conn, accepted_user, "CONVITE_ACEITO", invitation_id)
    return {"link_id": link_id}


class LinkStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ativo: bool = Field(strict=True)


@router.get("/managed-links")
def managed_links(identity=Depends(principal), user: Usuario = Depends(usuario_atual), conn=Depends(connection)):
    if user.papel not in {Papel.ADMIN_PLATAFORMA, Papel.ADMIN_BH, Papel.GESTOR_FORN}:
        raise HTTPException(403, "Seu perfil não administra acessos.")
    result = []
    for row in conn.execute("SELECT l.id,l.ativo,u.id AS user_id,u.nome,u.org_id,u.role,o.nome AS org_nome FROM identity_links l JOIN users u ON u.id=l.user_id JOIN organizations o ON o.id=u.org_id"):
        try:
            authorize_invitation(conn, user, row["org_id"], Papel(row["role"]))
        except HTTPException:
            continue
        result.append(dict(row))
    return result


@router.patch("/links/{link_id}")
def change_link(link_id: str, payload: LinkStatusInput, identity=Depends(principal), user: Usuario = Depends(usuario_atual), conn=Depends(connection)):
    row = conn.execute("SELECT l.*,u.org_id,u.role FROM identity_links l JOIN users u ON u.id=l.user_id WHERE l.id=?", (link_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Vínculo não encontrado.")
    authorize_invitation(conn, user, row["org_id"], Papel(row["role"]))
    if row["user_id"] == user.id:
        raise HTTPException(409, "Não é possível alterar seu próprio acesso.")
    conn.execute("UPDATE identity_links SET ativo=? WHERE id=?", (int(payload.ativo), link_id))
    auditar(conn, user, "VINCULO_ATIVADO" if payload.ativo else "VINCULO_REVOGADO", link_id)
    return {"id": link_id, "ativo": payload.ativo}
