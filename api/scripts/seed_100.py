"""Insere T006–T100 no CT-001 sem alterar o seed-base da aplicação.

ATENÇÃO: NÃO rode no banco da demonstração. O parecer lista TODOS os trabalhadores do
contrato, então o lote de 16 páginas passaria a aparecer como "5 avaliados de 100".
Use uma pasta de dados separada, por exemplo:  $env:DOCRISK_DATA_DIR = "data-100"
(scripts/benchmark.py já usa um banco temporário próprio e não precisa deste script).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docrisk_core import config, db


def main() -> None:
    if not config.DEMO_MODE:
        # Sem modo demo o banco não tem o contrato CT-001 (seed fictício desligado no D2-01).
        sys.exit("seed_100 só roda com DOCRISK_DEMO_MODE=1: os trabalhadores fictícios pertencem "
                 "ao contrato de demonstração CT-001. Use uma pasta de dados separada da demo.")
    db.init_db()
    with db.tx() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO workers (id, nome, contract_id) VALUES (?, ?, ?)",
            [(f"T{i:03d}", f"Trabalhador Fictício {i:03d}", "CT-001") for i in range(6, 101)],
        )
        total = conn.execute("SELECT COUNT(*) FROM workers WHERE contract_id = 'CT-001'").fetchone()[0]
    print(f"CT-001: {total} trabalhadores cadastrados (T001–T100).")


if __name__ == "__main__":
    main()
