"""Revisão D4-09: limites transacionais, contenção e interrupção real."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from docrisk_core import config, db
from docrisk_core.ai.textlayer import TextLayerProvider
from docrisk_core.pipeline import worker
from test_f2_worker import BETA, LOTE, banco, pdf  # noqa: F401


def ready_batch():
    bid = worker.criar_lote(BETA, "CT-001", "review.pdf", pdf(*LOTE))
    with db.tx() as conn:
        batch = conn.execute("SELECT * FROM batches WHERE id=?", (bid,)).fetchone()
    worker._registrar_paginas(batch)
    with db.tx() as conn:
        pages = conn.execute("SELECT * FROM pages WHERE batch_id=? ORDER BY ordem", (bid,)).fetchall()
    for page in pages:
        assert worker._analisar_pagina(page, "CT-001", TextLayerProvider())
    return bid


def test_existing_writer_transaction_keeps_ownership_and_rolls_back(banco):
    bid = ready_batch()
    conn = db.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        first = worker.consolidar_lote(conn, bid)
        second = worker.consolidar_lote(conn, bid)
        assert first == second and conn.in_transaction
        assert conn.execute("SELECT COUNT(*) FROM documents WHERE batch_id=?", (bid,)).fetchone()[0] == 6
        conn.rollback()
    finally:
        conn.close()
    with db.tx() as conn:
        assert conn.execute("SELECT COUNT(*) FROM documents WHERE batch_id=?", (bid,)).fetchone()[0] == 0
    worker.processar_lote(bid, TextLayerProvider())
    with db.tx() as conn:
        assert conn.execute("SELECT status FROM batches WHERE id=?", (bid,)).fetchone()[0] == "CONCLUIDO"


def test_deferred_stale_snapshot_requires_caller_rollback_and_retry(banco):
    bid = ready_batch()
    conn = db.connect()
    try:
        conn.execute("BEGIN DEFERRED")
        conn.execute("SELECT COUNT(*) FROM documents").fetchone()
        with db.tx() as other:
            other.execute("UPDATE batches SET filename='snapshot-changed.pdf' WHERE id=?", (bid,))
        with pytest.raises(sqlite3.OperationalError) as error:
            worker.consolidar_lote(conn, bid)
        assert error.value.sqlite_errorcode == sqlite3.SQLITE_BUSY_SNAPSHOT
        assert conn.in_transaction  # o callee não confirma nem reabre a transação do dono
        conn.rollback()
        worker.consolidar_lote(conn, bid)
        assert conn.in_transaction
        conn.commit()
    finally:
        conn.close()
    with db.tx() as conn:
        assert conn.execute("SELECT COUNT(*) FROM documents WHERE batch_id=?", (bid,)).fetchone()[0] == 6
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()


def test_writer_timeout_is_visible_and_does_not_corrupt_batch(banco, monkeypatch):
    bid = ready_batch()
    holder = db.connect()
    original = db.connect
    def bounded_connect():
        conn = original()
        conn.execute("PRAGMA busy_timeout=100")
        return conn
    holder.execute("BEGIN IMMEDIATE")
    try:
        with monkeypatch.context() as patch:
            patch.setattr(db, "connect", bounded_connect)
            start = time.monotonic()
            with pytest.raises(sqlite3.OperationalError) as error:
                worker.processar_lote(bid, TextLayerProvider())
            assert error.value.sqlite_errorcode == sqlite3.SQLITE_BUSY
            assert time.monotonic() - start < 5
    finally:
        holder.rollback()
        holder.close()
    with db.tx() as conn:
        assert conn.execute("SELECT status FROM batches WHERE id=?", (bid,)).fetchone()[0] == "RECEBIDO"
        assert conn.execute("SELECT COUNT(*) FROM documents WHERE batch_id=?", (bid,)).fetchone()[0] == 0
    worker.processar_lote(bid, TextLayerProvider())
    with db.tx() as conn:
        assert conn.execute("SELECT status, erro FROM batches WHERE id=?", (bid,)).fetchone()[:] == ("CONCLUIDO", None)


def test_killed_writer_rolls_back_and_processing_resumes(banco):
    bid = ready_batch()
    marker = banco / "writer-ready.txt"
    code = r'''
import sys, threading
from pathlib import Path
from docrisk_core import config, db
from docrisk_core.pipeline import worker
from docrisk_core.ai.textlayer import TextLayerProvider
config.DATA_DIR=Path(sys.argv[1]); config.DB_PATH=config.DATA_DIR/'teste.sqlite'
config.UPLOAD_DIR=config.DATA_DIR/'uploads'; config.PAGES_DIR=config.DATA_DIR/'pages'
original=db.connect
class Paused:
    def __init__(self): self.conn=original()
    def __getattr__(self,name): return getattr(self.conn,name)
    def execute(self,sql,parameters=()):
        result=self.conn.execute(sql,parameters)
        if sql.startswith('INSERT INTO documents'):
            Path(sys.argv[3]).write_text('uncommitted document',encoding='utf-8')
            threading.Event().wait(20)
        return result
db.connect=Paused
worker.processar_lote(int(sys.argv[2]), TextLayerProvider())
'''
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "AI_PROVIDER": "textlayer"}
    proc = subprocess.Popen([sys.executable, "-c", code, str(banco), str(bid), str(marker)], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 12
        while not marker.exists() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(.05)
        assert marker.exists(), "child did not reach uncommitted INSERT"
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.communicate(timeout=5)
    with db.tx() as conn:
        assert conn.execute("SELECT status FROM batches WHERE id=?", (bid,)).fetchone()[0] == "PROCESSANDO"
        assert conn.execute("SELECT COUNT(*) FROM documents WHERE batch_id=?", (bid,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM doc_pages").fetchone()[0] == 0
        page_ids = [r[0] for r in conn.execute("SELECT id FROM pages WHERE batch_id=? ORDER BY ordem", (bid,))]
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    worker.processar_lote(bid, TextLayerProvider())
    with db.tx() as conn:
        assert conn.execute("SELECT status, erro FROM batches WHERE id=?", (bid,)).fetchone()[:] == ("CONCLUIDO", None)
        assert [r[0] for r in conn.execute("SELECT id FROM pages WHERE batch_id=? ORDER BY ordem", (bid,))] == page_ids
        assert conn.execute("SELECT COUNT(*) FROM documents WHERE batch_id=?", (bid,)).fetchone()[0] == 6
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()


def test_same_aej_concurrently_does_not_duplicate_derived_documents(banco, monkeypatch):
    from test_f1_aej import AEJ_LIMPO
    bid = worker.criar_lote(BETA, "CT-001", "concurrent.aej", AEJ_LIMPO)
    barrier = threading.Barrier(4)
    parse = worker.parse_aej_detalhado
    def coordinated_parse(data):
        result = parse(data)
        barrier.wait(timeout=10)  # todos já passaram pela checagem de documentos do AEJ
        return result
    monkeypatch.setattr(worker, "parse_aej_detalhado", coordinated_parse)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(worker.processar_lote, bid, TextLayerProvider()) for _ in range(4)]
        for future in futures:
            future.result(timeout=30)
    with db.tx() as conn:
        docs = conn.execute("SELECT id FROM documents WHERE batch_id=?", (bid,)).fetchall()
        derived = conn.execute("SELECT COUNT(*) FROM aej_documents WHERE batch_id=?", (bid,)).fetchone()[0]
        assert len(docs) == derived == 1, {"documents": len(docs), "aej_documents": derived}
        assert conn.execute("SELECT status, erro FROM batches WHERE id=?", (bid,)).fetchone()[:] == ("CONCLUIDO", None)
