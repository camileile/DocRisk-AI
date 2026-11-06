"""Acesso ao SQLite. Dono: frente 1.

Uso:
    from docrisk_core import db
    db.init_db()
    with db.tx() as conn:
        conn.execute("SELECT ...")
"""
from __future__ import annotations

import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .. import config

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
MIGRATIONS_PATH = Path(__file__).with_name("migrations")


def agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    """Uma transação: commit no fim, rollback em erro."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(seed: bool = True) -> None:
    for pasta in (config.DATA_DIR, config.UPLOAD_DIR, config.PAGES_DIR):
        pasta.mkdir(parents=True, exist_ok=True)
    conn = connect()
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _apply_migrations(conn)
        if seed:
            seed_demo(conn)
        conn.commit()
    finally:
        conn.close()


def _apply_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    for migration in sorted(MIGRATIONS_PATH.glob("*.sql")):
        version = migration.name
        if conn.execute("SELECT 1 FROM schema_migrations WHERE version=?", (version,)).fetchone():
            continue
        conn.executescript(migration.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                     (version, agora()))


# ---------------------------------------------------------------------------
# Dados fictícios de demonstração (organizações, perfis, contratos, trabalhadores)
# ---------------------------------------------------------------------------
ORGANIZACOES = [
    ("ORG-BH", "Bernhoeft (demo)", "BERNHOEFT"),
    ("ORG-ALFA", "Contratante Alfa S.A. (fictícia)", "CONTRATANTE"),
    ("ORG-BETA", "Fornecedora Beta Serviços (fictícia)", "FORNECEDORA"),
    ("ORG-GAMA", "Fornecedora Gama Facilities (fictícia)", "FORNECEDORA"),
]
USUARIOS = [
    ("u-admin", "Admin Bernhoeft (demo)", "ORG-BH", "ADMIN_BH"),
    ("u-analista", "Analista Bernhoeft (demo)", "ORG-BH", "ANALISTA_BH"),
    ("u-gestor-beta", "Gestor Beta (demo)", "ORG-BETA", "GESTOR_FORN"),
    ("u-oper-beta", "Operador Beta (demo)", "ORG-BETA", "OPERADOR_FORN"),
    ("u-oper-gama", "Operador Gama (demo)", "ORG-GAMA", "OPERADOR_FORN"),
    ("u-gestor-alfa", "Gestor Alfa (demo)", "ORG-ALFA", "GESTOR_CONTR"),
]
CONTRATOS = [
    ("CT-001", "Limpeza e conservação — Alfa × Beta", "ORG-ALFA", "ORG-BETA", "ORG-BH"),
    ("CT-002", "Facilities — Alfa × Gama", "ORG-ALFA", "ORG-GAMA", "ORG-BH"),
]
TRABALHADORES = [
    *[(f"T00{i}", f"Trabalhador Fictício 00{i}", "CT-001") for i in range(1, 6)],
    ("T101", "Trabalhador Fictício 101", "CT-002"),
]


def seed_demo(conn: sqlite3.Connection) -> None:
    """Cria dados fictícios somente quando o modo de demonstração está ativo."""
    if not config.DEMO_MODE:
        return

    conn.execute("INSERT OR IGNORE INTO platform_accounts (id,nome,token) VALUES (?,?,?)",
                 ("u-plataforma", "Admin Geral (demo)", secrets.token_urlsafe(32)))
    conn.executemany("INSERT OR IGNORE INTO organizations VALUES (?, ?, ?)", ORGANIZACOES)
    for uid, nome, org, papel in USUARIOS:
        conn.execute(
            "INSERT OR IGNORE INTO users (id, nome, org_id, role, token) VALUES (?, ?, ?, ?, ?)",
            (uid, nome, org, papel, secrets.token_urlsafe(24)),
        )
    conn.executemany(
        "INSERT OR IGNORE INTO contracts (id, nome, contratante_id, fornecedora_id, bernhoeft_id)"
        " VALUES (?, ?, ?, ?, ?)",
        CONTRATOS,
    )
    conn.executemany("INSERT OR IGNORE INTO workers VALUES (?, ?, ?)", TRABALHADORES)
