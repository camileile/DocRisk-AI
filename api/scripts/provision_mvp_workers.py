"""Provisionamento controlado de trabalhadores SINTÉTICOS de um contrato do MVP.

Execução no ambiente da API (sem endpoint público, sem tokens de demonstração).
Requer DOCRISK_AUTH_MODE=clerk, DOCRISK_DEMO_MODE=0 e confirmação explícita.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from docrisk_core import config, db

WORKER_ID = re.compile(r"T[0-9]{3,8}\Z")
MAX_WORKERS = 500


def load_csv(path: Path) -> list[tuple[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ["id", "nome"]:
                raise ValueError("O CSV deve conter exatamente as colunas id,nome.")
            rows = []
            for line, item in enumerate(reader, start=2):
                wid = str(item["id"] or "").strip().upper()
                name = str(item["nome"] or "").strip()
                if not WORKER_ID.fullmatch(wid) or not 2 <= len(name) <= 120:
                    raise ValueError(f"Linha {line}: identificador (T001...) ou nome sintético inválido.")
                rows.append((wid, name))
                if len(rows) > MAX_WORKERS:
                    raise ValueError(f"Máximo de {MAX_WORKERS} trabalhadores por execução.")
    except OSError as exc:
        raise ValueError("CSV não pôde ser lido no ambiente de execução.") from exc
    if not rows or len({wid for wid, _ in rows}) != len(rows):
        raise ValueError("CSV vazio ou com identificadores de trabalhador repetidos.")
    return rows


def provision(contract_id: str, records: list[tuple[str, str]], apply: bool) -> tuple[int, int]:
    """Verifica todas as linhas antes de gravar; rejeita colisão entre contratos."""
    with db.tx() as conn:
        contract = conn.execute("SELECT bernhoeft_id FROM contracts WHERE id=?", (contract_id,)).fetchone()
        if contract is None:
            raise ValueError("Contrato não encontrado. Cadastre-o pelo Administrador Bernhoeft.")
        existing = conn.execute(
            "SELECT id, nome, contract_id FROM workers WHERE id IN (" +
            ",".join("?" for _ in records) + ")",
            [wid for wid, _ in records],
        ).fetchall()
        indexed = {item["id"]: item for item in existing}
        to_create: list[tuple[str, str, str]] = []
        already = 0
        for wid, name in records:
            before = indexed.get(wid)
            if before is not None:
                if before["contract_id"] != contract_id:
                    raise ValueError(f"{wid}: identificador já pertence a outro contrato.")
                if before["nome"] != name:
                    raise ValueError(f"{wid}: nome previamente cadastrado é diferente; ajuste manual obrigatório.")
                already += 1
            else:
                to_create.append((wid, name, contract_id))
        if apply and to_create:
            conn.executemany("INSERT INTO workers (id,nome,contract_id) VALUES (?,?,?)", to_create)
            conn.execute(
                "INSERT INTO audit (org_id,acao,alvo,resultado,instante) VALUES (?,?,?,?,?)",
                (contract["bernhoeft_id"], "TRABALHADORES_SINTETICOS_PROVISIONADOS",
                 contract_id, "OK", db.agora()),
            )
        return len(to_create), already


def main() -> int:
    parser = argparse.ArgumentParser(description="Preparar trabalhadores inteiramente sintéticos para o MVP Clerk.")
    parser.add_argument("--contract-id", required=True, help="Contrato existente, autorizado pela organização auditora.")
    parser.add_argument("--csv", required=True, type=Path, help="CSV id,nome com trabalhadores fictícios.")
    parser.add_argument("--apply", action="store_true", help="Confirma a gravação; sem esta opção faz apenas simulação.")
    parser.add_argument("--confirm-synthetic", action="store_true", help="Confirma que não há dados pessoais reais.")
    args = parser.parse_args()

    if config.AUTH_MODE != "clerk" or config.DEMO_MODE:
        parser.error("Execute somente no modo Clerk com DOCRISK_DEMO_MODE=0.")
    if args.apply and not args.confirm_synthetic:
        parser.error("Para gravar, confirme que o arquivo contém apenas dados inteiramente sintéticos.")
    try:
        records = load_csv(args.csv)
        created, existing = provision(args.contract_id, records, args.apply)
    except ValueError as exc:
        parser.error(str(exc))
    action = "GRAVADOS" if args.apply else "SIMULAÇÃO"
    print(f"{action}: {created} novos, {existing} já existentes, contrato {args.contract_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
