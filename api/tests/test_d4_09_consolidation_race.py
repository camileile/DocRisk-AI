"""D4-09: força a janela entre checar idempotência e persistir doc_pages."""
import threading
from concurrent.futures import ThreadPoolExecutor

from docrisk_core import db
from docrisk_core.ai.textlayer import TextLayerProvider
from docrisk_core.pipeline import worker
from test_f2_worker import BETA, LOTE, banco, pdf  # noqa: F401


def test_consolidacoes_concorrentes_preservam_identidades_e_estado(banco, monkeypatch):
    bid = worker.criar_lote(BETA, "CT-001", "concorrencia.pdf", pdf(*LOTE))
    with db.tx() as conn:
        lote = conn.execute("SELECT * FROM batches WHERE id=?", (bid,)).fetchone()
    worker._registrar_paginas(lote)
    with db.tx() as conn:
        pages = conn.execute("SELECT * FROM pages WHERE batch_id=? ORDER BY ordem", (bid,)).fetchall()
    for page in pages:
        assert worker._analisar_pagina(page, "CT-001", TextLayerProvider())
    original_ids = [p["id"] for p in pages]
    guard = "SELECT 1 FROM documents WHERE batch_id = ? LIMIT 1"
    stale_readers = threading.Barrier(4)
    start = threading.Barrier(4)
    original_connect = db.connect
    reads = []

    class ObservedConnection:
        def __init__(self):
            self.conn = original_connect()
        def __getattr__(self, name):
            return getattr(self.conn, name)
        def execute(self, sql, parameters=()):
            cursor = self.conn.execute(sql, parameters)
            if sql == guard:
                reads.append(self.conn.in_transaction)
                # Sem transação, força quatro leituras vazias antes de qualquer INSERT.
                # Com reserva de escrita, os demais aguardam no SQLite, antes da leitura.
                if not self.conn.in_transaction:
                    stale_readers.wait(timeout=10)
            return cursor

    monkeypatch.setattr(db, "connect", ObservedConnection)
    def process():
        start.wait(timeout=10)
        worker.processar_lote(bid, provedor=TextLayerProvider())
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process) for _ in range(4)]
        errors = []
        for future in futures:
            try:
                future.result(timeout=30)
            except Exception as exc:
                errors.append(repr(exc))
    with db.tx() as conn:
        observed = dict(conn.execute("SELECT status, erro, finished_at FROM batches WHERE id=?", (bid,)).fetchone())
        observed["page_count"] = conn.execute("SELECT COUNT(*) FROM pages WHERE batch_id=?", (bid,)).fetchone()[0]
        observed["document_count"] = conn.execute("SELECT COUNT(*) FROM documents WHERE batch_id=?", (bid,)).fetchone()[0]
    assert not errors, {"errors": errors, "guard_in_transaction": reads, "batch": observed}
    assert reads and all(reads)
    with db.tx() as conn:
        assert [r[0] for r in conn.execute("SELECT id FROM pages WHERE batch_id=? ORDER BY ordem", (bid,))] == original_ids
        links = conn.execute("SELECT page_id FROM doc_pages WHERE document_id IN (SELECT id FROM documents WHERE batch_id=?) ORDER BY page_id", (bid,)).fetchall()
        assert [r[0] for r in links] == sorted(original_ids)
        assert conn.execute("SELECT COUNT(*) FROM documents WHERE batch_id=?", (bid,)).fetchone()[0] == 6
        batch = conn.execute("SELECT status, erro, finished_at FROM batches WHERE id=?", (bid,)).fetchone()
        assert batch["status"] == "CONCLUIDO" and batch["erro"] is None and batch["finished_at"]
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        identities = [r[0] for r in conn.execute("SELECT id FROM documents WHERE batch_id=? ORDER BY id", (bid,))]
    # Repetição posterior é realmente idempotente, não apenas uma exceção suprimida.
    worker.processar_lote(bid, provedor=TextLayerProvider())
    with db.tx() as conn:
        assert [r[0] for r in conn.execute("SELECT id FROM documents WHERE batch_id=? ORDER BY id", (bid,))] == identities
        assert conn.execute("SELECT finished_at FROM batches WHERE id=?", (bid,)).fetchone()[0] == batch["finished_at"]


def test_falha_na_persistencia_reverte_documentos_e_permite_retentativa(banco, monkeypatch):
    import pytest
    bid = worker.criar_lote(BETA, "CT-001", "rollback.pdf", pdf(*LOTE))
    original_connect = db.connect

    class FailingConnection:
        def __init__(self):
            self.conn = original_connect()
        def __getattr__(self, name):
            return getattr(self.conn, name)
        def executemany(self, sql, parameters):
            if sql.startswith("INSERT INTO doc_pages"):
                raise RuntimeError("falha sintética antes do vínculo")
            return self.conn.executemany(sql, parameters)

    with monkeypatch.context() as patch:
        patch.setattr(db, "connect", FailingConnection)
        with pytest.raises(RuntimeError, match="falha sintética"):
            worker.processar_lote(bid, provedor=TextLayerProvider())
    with db.tx() as conn:
        assert conn.execute("SELECT COUNT(*) FROM documents WHERE batch_id=?", (bid,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM doc_pages JOIN pages ON pages.id=doc_pages.page_id WHERE pages.batch_id=?", (bid,)).fetchone()[0] == 0
        assert conn.execute("SELECT status FROM batches WHERE id=?", (bid,)).fetchone()[0] == "FALHA_PROCESSAMENTO"
        ids = [r[0] for r in conn.execute("SELECT id FROM pages WHERE batch_id=? ORDER BY ordem", (bid,))]
    worker.processar_lote(bid, provedor=TextLayerProvider())
    with db.tx() as conn:
        assert [r[0] for r in conn.execute("SELECT id FROM pages WHERE batch_id=? ORDER BY ordem", (bid,))] == ids
        assert conn.execute("SELECT COUNT(*) FROM documents WHERE batch_id=?", (bid,)).fetchone()[0] == 6
        assert conn.execute("SELECT status, erro FROM batches WHERE id=?", (bid,)).fetchone()[:] == ("CONCLUIDO", None)
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
