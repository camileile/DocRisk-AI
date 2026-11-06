"""H03: provisiona trabalhadores sintéticos por contrato no banco operacional.

Executar SOMENTE em ambiente controlado com acesso ao volume da API e um
ADMIN_BH previamente ativado por convite Clerk. Não recebe credenciais reais
nem cria contas ou vínculos de autenticação.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from docrisk_core import config, db
from docrisk_core.auth import Usuario, auditar
from docrisk_core.contracts import Papel

WORKER_ID = re.compile(r"^[A-Z][A-Z0-9_-]{1,39}$")


def read_workers(source: Path) -> list[tuple[str, str]]:
    try:
        with source.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ["id", "nome"]:
                raise ValueError("O CSV deve ter exatamente as colunas id,nome (nessa ordem).")
            workers: list[tuple[str, str]] = []
            seen: set[str] = set()
            for number, row in enumerate(reader, start=2):
                if None in row or row.get("id") is None or row.get("nome") is None:
                    raise ValueError(f"Linha {number}: esperado id,nome.")
                ident = row["id"].strip().upper()
                name = row["nome"].strip()
                if not WORKER_ID.fullmatch(ident):
                    raise ValueError(f"Linha {number}: identificador inválido.")
                if not 2 <= len(name) <= 160:
                    raise ValueError(f"Linha {number}: nome deve conter de 2 a 160 caracteres.")
                if ident in seen:
                    raise ValueError(f"Linha {number}: identificador duplicado.")
                seen.add(ident)
                workers.append((ident, name))
    except UnicodeError as exc:
        raise ValueError("Utilize um CSV no formato UTF-8.") from exc
    if not workers:
        raise ValueError("O CSV precisa ter ao menos um trabalhador sintético.")
    if len(workers) > 1000:
        raise ValueError("Limite de 1000 trabalhadores por operação.")
    return workers


def provision(contract_id: str, actor_id: str, source: Path) -> tuple[int, int]:
    if config.AUTH_MODE != "clerk" or config.DEMO_MODE or not config.CLERK_ISSUER:
        raise ValueError("H03 exige DOCRISK_AUTH_MODE=clerk, DOCRISK_DEMO_MODE=0 e CLERK_ISSUER.")
    workers = read_workers(source)
    # Nunca semear automaticamente dados da demo ao preparar o ambiente operacional.
    db.init_db(seed=False)
    with db.tx() as conn:
        contract = conn.execute("SELECT bernhoeft_id FROM contracts WHERE id=?", (contract_id,)).fetchone()
        if contract is None:
            raise ValueError("Contrato não encontrado.")
        actor = conn.execute(
            "SELECT u.id,u.nome,u.org_id FROM users u WHERE u.id=? AND u.ativo=1 "
            "AND u.role='ADMIN_BH' AND u.org_id=? AND EXISTS ("
            " SELECT 1 FROM identity_links l WHERE l.user_id=u.id AND l.ativo=1 AND l.issuer=?)",
            (actor_id, contract["bernhoeft_id"], config.CLERK_ISSUER),
        ).fetchone()
        if actor is None:
            raise ValueError("Informe um ADMIN_BH ativo e vinculado à auditora do contrato via Clerk.")
        created = skipped = 0
        for ident, name in workers:
            existing = conn.execute("SELECT contract_id,nome FROM workers WHERE id=?", (ident,)).fetchone()
            if existing is None:
                conn.execute("INSERT INTO workers (id,nome,contract_id) VALUES (?,?,?)",
                             (ident, name, contract_id))
                created += 1
            elif existing["contract_id"] == contract_id and existing["nome"] == name:
                skipped += 1
            else:
                raise ValueError(f"Identificador {ident} já está em uso com outro cadastro.")
        user = Usuario(actor["id"], actor["nome"], actor["org_id"], "BERNHOEFT", Papel.ADMIN_BH)
        auditar(conn, user, "TRABALHADORES_SINTETICOS_PROVISIONADOS",
                f"{contract_id}:novos={created}:existentes={skipped}")
    return created, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract-id", required=True, help="Contrato operacional já criado (CT-...).")
    parser.add_argument("--admin-id", required=True, help="ID interno do ADMIN_BH vinculado à auditora.")
    parser.add_argument("--csv", type=Path, required=True, help="CSV UTF-8 com colunas id,nome.")
    parser.add_argument("--confirm-synthetic", action="store_true",
                        help="Confirma que o arquivo não contém dados de pessoas reais.")
    args = parser.parse_args()
    if not args.confirm_synthetic:
        parser.error("Confirme expressamente o uso exclusivo de dados sintéticos.")
    try:
        created, skipped = provision(args.contract_id, args.admin_id, args.csv)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f"Provisionamento concluído: {created} trabalhador(es) novo(s); {skipped} já existente(s).")


if __name__ == "__main__":
    main()
