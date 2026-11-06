"""Administração de uma organização auditora no MVP.

Todas as leituras e alterações são limitadas ao auditor do token. Cadastros
mutáveis só funcionam no ambiente de testes, que ainda usa tokens Bearer de demo.
"""
from __future__ import annotations

import secrets
import sqlite3
from datetime import date, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import config, db
from ..auth import Usuario, auditar, contratos_do_usuario, exigir_papel, usuario_atual
from ..contracts import Papel
from ..rules import metricas

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _conn():
    conn = db.connect()
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _authorize(user: Usuario) -> None:
    exigir_papel(user, [Papel.ADMIN_BH])


def _write_allowed(user: Usuario) -> None:
    _authorize(user)
    if not config.DEMO_MODE:
        raise HTTPException(403, "Cadastros de teste indisponíveis fora do ambiente demo; configurar autenticação de produção.")


def _organizations(conn: sqlite3.Connection, user: Usuario) -> list[dict[str, Any]]:
    """As organizações acessíveis são as de contratos do auditor OU suas inscrições explícitas."""
    rows = conn.execute(
        "SELECT DISTINCT o.id, o.nome, o.tipo, p.cnpj FROM organizations o "
        "LEFT JOIN organization_profiles p ON p.org_id=o.id "
        "WHERE o.id IN ("
        " SELECT contratante_id FROM contracts WHERE bernhoeft_id=?"
        " UNION SELECT fornecedora_id FROM contracts WHERE bernhoeft_id=?"
        " UNION SELECT org_id FROM organization_auditors WHERE auditor_id=?"
        ") ORDER BY o.tipo, o.nome",
        (user.org_id, user.org_id, user.org_id),
    ).fetchall()
    return [dict(row) for row in rows]


def _available(conn: sqlite3.Connection, user: Usuario, org_id: str, kind: str) -> bool:
    return any(row["id"] == org_id and row["tipo"] == kind for row in _organizations(conn, user))


def _contracts(conn: sqlite3.Connection, user: Usuario) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT c.id, c.nome, c.contratante_id, c.fornecedora_id, "
        "ct.nome AS contratante_nome, fn.nome AS fornecedora_nome, "
        "c.prazo_correcao_dias, m.inicio, m.fim, COALESCE(m.status, 'ATIVO') AS status "
        "FROM contracts c "
        "JOIN organizations ct ON ct.id=c.contratante_id "
        "JOIN organizations fn ON fn.id=c.fornecedora_id "
        "LEFT JOIN contract_metadata m ON m.contract_id=c.id "
        "WHERE c.bernhoeft_id=? ORDER BY c.nome", (user.org_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _users(conn: sqlite3.Connection, user: Usuario, orgs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ids = [user.org_id, *(org["id"] for org in orgs)]
    marks = ",".join("?" for _ in ids)
    rows = conn.execute(
        "SELECT u.id, u.nome, u.org_id, o.nome AS org_nome, u.role AS papel, u.ativo "
        f"FROM users u JOIN organizations o ON o.id=u.org_id WHERE u.org_id IN ({marks}) "
        "AND u.role IN ('ADMIN_BH','ANALISTA_BH','GESTOR_CONTR','GESTOR_FORN') ORDER BY o.nome, u.nome",
        ids,
    ).fetchall()
    # Não transmitir tokens, hashes ou informações de documentos.
    return [dict(row) for row in rows]


class CompanyInput(BaseModel):
    tipo: Literal["CONTRATANTE", "FORNECEDORA"]
    nome: str = Field(min_length=2, max_length=160)
    cnpj: str | None = Field(default=None, max_length=32)
    contratante_id: str | None = None
    contrato_nome: str | None = None


class ContractInput(BaseModel):
    nome: str = Field(min_length=3, max_length=160)
    contratante_id: str
    fornecedora_id: str
    inicio: date | None = None
    fim: date | None = None


class UserInput(BaseModel):
    nome: str = Field(min_length=2, max_length=140)
    org_id: str
    papel: Literal["ADMIN_BH", "ANALISTA_BH", "GESTOR_CONTR", "GESTOR_FORN"]


class StatusInput(BaseModel):
    ativo: bool


def _create_contract(conn: sqlite3.Connection, user: Usuario, payload: ContractInput) -> str:
    if not _available(conn, user, payload.contratante_id, "CONTRATANTE"):
        raise HTTPException(422, "Contratante não cadastrada neste ambiente.")
    if not _available(conn, user, payload.fornecedora_id, "FORNECEDORA"):
        raise HTTPException(422, "Fornecedora não cadastrada neste ambiente.")
    if payload.inicio and payload.fim and payload.inicio > payload.fim:
        raise HTTPException(422, "O fim do contrato não pode preceder seu início.")
    contract_id = "CT-" + secrets.token_hex(6).upper()
    conn.execute(
        "INSERT INTO contracts (id, nome, contratante_id, fornecedora_id, bernhoeft_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (contract_id, payload.nome.strip(), payload.contratante_id, payload.fornecedora_id, user.org_id),
    )
    conn.execute(
        "INSERT INTO contract_metadata (contract_id, inicio, fim) VALUES (?, ?, ?)",
        (contract_id, payload.inicio.isoformat() if payload.inicio else None,
         payload.fim.isoformat() if payload.fim else None),
    )
    auditar(conn, user, "CONTRATO_CRIADO", contract_id)
    return contract_id


@router.get("/registry")
def registry(user: Usuario = Depends(usuario_atual),
             conn: sqlite3.Connection = Depends(_conn)) -> dict[str, Any]:
    _authorize(user)
    orgs = _organizations(conn, user)
    return {"empresas": orgs, "contratos": _contracts(conn, user),
            "usuarios": _users(conn, user, orgs)}


@router.get("/overview")
def overview(contratante_id: str | None = None, user: Usuario = Depends(usuario_atual),
             conn: sqlite3.Connection = Depends(_conn)) -> dict[str, Any]:
    _authorize(user)
    all_contracts = _contracts(conn, user)
    contracts = [c for c in all_contracts if not contratante_id or c["contratante_id"] == contratante_id]
    ids = [c["id"] for c in contracts]
    operacao = metricas.calcular_metricas(conn, ids)
    hoje = date.today()
    limite = hoje + timedelta(days=30)
    return {
        "contratantes": len({c["contratante_id"] for c in contracts}),
        "fornecedoras": len({c["fornecedora_id"] for c in contracts}),
        "contratos_ativos": sum(c["status"] == "ATIVO" for c in contracts),
        "contratos_vencendo_30d": sum(c["status"] == "ATIVO" and c["fim"] is not None and
                                     hoje <= date.fromisoformat(c["fim"]) <= limite for c in contracts),
        "contratos_sem_prazo": sum(c["fim"] is None for c in contracts),
        "operacao": operacao,
    }


@router.post("/companies", status_code=201)
def create_company(payload: CompanyInput, user: Usuario = Depends(usuario_atual),
                   conn: sqlite3.Connection = Depends(_conn)) -> dict[str, Any]:
    _write_allowed(user)
    nome = payload.nome.strip()
    if not nome:
        raise HTTPException(422, "Nome da empresa obrigatório.")
    cnpj = (payload.cnpj or "").strip().upper() or None
    if cnpj and len(cnpj) > 32:
        raise HTTPException(422, "Identificação empresarial inválida.")
    # Impedir dupla identidade dentro de uma organização, inclusive quando CNPJ não foi informado.
    existing = [o for o in _organizations(conn, user)
                if o["tipo"] == payload.tipo and
                (o["nome"].casefold() == nome.casefold() or (cnpj and o.get("cnpj") == cnpj))]
    if existing:
        raise HTTPException(409, "Empresa já cadastrada. Vincule-a a outra contratante sem duplicar o cadastro.")
    if cnpj and conn.execute("SELECT 1 FROM organization_profiles WHERE cnpj=?", (cnpj,)).fetchone():
        raise HTTPException(409, "Identificação empresarial já cadastrada.")
    if payload.tipo == "FORNECEDORA":
        if not payload.contratante_id or not _available(conn, user, payload.contratante_id, "CONTRATANTE"):
            raise HTTPException(422, "A fornecedora precisa ser vinculada a uma contratante cadastrada.")
        if not (payload.contrato_nome or "").strip():
            raise HTTPException(422, "Informe o nome do contrato inicial da fornecedora.")
    org_id = "ORG-" + secrets.token_hex(6).upper()
    conn.execute("INSERT INTO organizations (id, nome, tipo) VALUES (?, ?, ?)", (org_id, nome, payload.tipo))
    conn.execute(
        "INSERT INTO organization_profiles (org_id, cnpj, criado_em) VALUES (?, ?, ?)",
        (org_id, cnpj, db.agora()),
    )
    conn.execute(
        "INSERT INTO organization_auditors (org_id, auditor_id) VALUES (?, ?)",
        (org_id, user.org_id),
    )
    audit_target = org_id
    contract_id = None
    if payload.tipo == "FORNECEDORA":
        contract_id = _create_contract(conn, user, ContractInput(
            nome=(payload.contrato_nome or "").strip(),
            contratante_id=payload.contratante_id or "",
            fornecedora_id=org_id,
        ))
    auditar(conn, user, "EMPRESA_CRIADA", audit_target)
    return {"id": org_id, "nome": nome, "tipo": payload.tipo, "cnpj": cnpj, "contract_id": contract_id}


@router.post("/contracts", status_code=201)
def create_contract(payload: ContractInput, user: Usuario = Depends(usuario_atual),
                    conn: sqlite3.Connection = Depends(_conn)) -> dict[str, str]:
    _write_allowed(user)
    return {"id": _create_contract(conn, user, payload)}


@router.post("/users", status_code=201)
def create_user(payload: UserInput, user: Usuario = Depends(usuario_atual),
                conn: sqlite3.Connection = Depends(_conn)) -> dict[str, Any]:
    _write_allowed(user)
    if payload.papel in ("ADMIN_BH", "ANALISTA_BH"):
        if payload.org_id != user.org_id:
            raise HTTPException(422, "Perfil interno pertence à organização auditora.")
    else:
        expected = "CONTRATANTE" if payload.papel == "GESTOR_CONTR" else "FORNECEDORA"
        if not _available(conn, user, payload.org_id, expected):
            raise HTTPException(422, "Empresa incompatível ou não vinculada à organização.")
    uid = "u-" + secrets.token_hex(6)
    token = secrets.token_urlsafe(24)
    conn.execute(
        "INSERT INTO users (id, nome, org_id, role, token) VALUES (?, ?, ?, ?, ?)",
        (uid, payload.nome.strip(), payload.org_id, payload.papel, token),
    )
    auditar(conn, user, "USUARIO_CRIADO", uid)
    # Token só é mostrado no momento do cadastro, no ambiente de testes.
    return {"id": uid, "nome": payload.nome.strip(), "org_id": payload.org_id,
            "papel": payload.papel, "ativo": 1, "token_teste": token}


@router.patch("/users/{uid}/status")
def update_user_status(uid: str, payload: StatusInput,
                       user: Usuario = Depends(usuario_atual),
                       conn: sqlite3.Connection = Depends(_conn)) -> dict[str, Any]:
    _write_allowed(user)
    if uid == user.id and not payload.ativo:
        raise HTTPException(422, "Não é possível desativar seu próprio acesso.")
    visible = {u["id"] for u in _users(conn, user, _organizations(conn, user))}
    if uid not in visible:
        raise HTTPException(404, "Usuário não encontrado.")
    conn.execute("UPDATE users SET ativo=? WHERE id=?", (int(payload.ativo), uid))
    auditar(conn, user, "USUARIO_STATUS_ALTERADO", uid)
    return {"id": uid, "ativo": payload.ativo}
