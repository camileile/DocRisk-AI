"""Vínculos internos; o token do provedor não concede papéis nem contratos."""
from fastapi import HTTPException
from .auth import Usuario
from .contracts import Papel


def links(conn, principal):
    rows = conn.execute(
        "SELECT l.id,l.user_id,l.platform_account_id,u.nome,u.org_id,u.role,o.nome AS org_nome,o.tipo AS org_tipo,"
        "p.nome AS platform_nome FROM identity_links l LEFT JOIN users u ON u.id=l.user_id "
        "LEFT JOIN organizations o ON o.id=u.org_id LEFT JOIN platform_accounts p ON p.id=l.platform_account_id "
        "WHERE l.issuer=? AND l.subject=? AND l.ativo=1 AND (u.ativo=1 OR p.ativo=1) ORDER BY l.created_at,l.id",
        (principal.issuer, principal.subject)).fetchall()
    return [dict(row) for row in rows]


def resolve_link(conn, principal, link_id):
    available = links(conn, principal)
    selected = next((r for r in available if r["id"] == link_id), None)
    if selected is None:
        raise HTTPException(403, "Vínculo não autorizado ou desativado. Entre novamente.", headers={"X-DocRisk-Link-Invalid": "1"})
    if selected["platform_account_id"]:
        return Usuario(selected["platform_account_id"], selected["platform_nome"], "DOCRISK", "PLATAFORMA", Papel.ADMIN_PLATAFORMA)
    return Usuario(selected["user_id"], selected["nome"], selected["org_id"], selected["org_tipo"], Papel(selected["role"]))
