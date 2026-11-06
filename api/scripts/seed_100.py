"""Insere T006–T100 no CT-001 sem alterar o seed-base da aplicação."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docrisk_core import db


def main() -> None:
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
