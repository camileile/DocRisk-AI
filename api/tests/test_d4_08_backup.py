"""D4-08 — backup consistente, restauração, reconciliação e recuperação sem duplicidade.

Cenários destrutivos só em diretórios temporários do pytest. Dados sintéticos.
"""
from __future__ import annotations

import sqlite3
import threading
import time

import pytest
from fastapi.testclient import TestClient

from docrisk_core import config, db
from docrisk_core.ai.textlayer import TextLayerProvider
from docrisk_core.api import app
from docrisk_core.pipeline import worker
from scripts import backup as bk
from test_f2_worker import BETA, LOTE, banco, pdf  # noqa: F401

TEMPOS: dict[str, float] = {}


def _q(sql, *a):
    with db.tx() as conn:
        return conn.execute(sql, a).fetchall()


def _apontar(monkeypatch, pasta):
    monkeypatch.setattr(config, "DATA_DIR", pasta)
    monkeypatch.setattr(config, "DB_PATH", pasta / "docrisk.sqlite")
    monkeypatch.setattr(config, "UPLOAD_DIR", pasta / "uploads")
    monkeypatch.setattr(config, "PAGES_DIR", pasta / "pages")


@pytest.fixture
def dados(tmp_path, monkeypatch):
    origem = tmp_path / "origem"
    _apontar(monkeypatch, origem)
    monkeypatch.setattr(config, "SYNC", True)
    db.init_db()
    bid = worker.criar_lote(BETA, "CT-001", "lote.pdf", pdf(*LOTE))
    worker.processar_lote(bid, provedor=TextLayerProvider())
    return {"origem": origem, "batch": bid, "tmp": tmp_path}


def _estado():
    return {
        "lotes": _q("SELECT id, status, sha256 FROM batches ORDER BY id"),
        "docs": _q("SELECT id, tipo, worker_id, status, versao FROM documents ORDER BY id"),
        "issues": _q("SELECT id, categoria, status FROM issues ORDER BY id"),
        "analises": _q("SELECT id, worker_id, status, atual FROM analyses ORDER BY id"),
    }


def test_B07_backup_e_restauracao_reproduzem_estado_e_servem_arquivos(dados, monkeypatch):
    antes = _estado()
    t = time.monotonic()
    pasta = bk.backup(dados["origem"], dados["tmp"] / "backups")
    TEMPOS["backup"] = time.monotonic() - t
    assert bk.verify(pasta) == []
    destino = dados["tmp"] / "restaurado"
    t = time.monotonic()
    bk.restore(pasta, destino)
    TEMPOS["restore"] = time.monotonic() - t
    _apontar(monkeypatch, destino)
    assert _estado() == antes
    caminhos = [r[0] for r in _q("SELECT image_path FROM pages")] + [r[0] for r in _q("SELECT arquivo FROM batches")]
    assert all(c.startswith(str(destino.resolve())) for c in caminhos)  # remapeados
    with TestClient(app) as client:
        h = {"Authorization": "Bearer " + _q("SELECT token FROM users WHERE id='u-oper-beta'")[0][0]}
        pid = _q("SELECT id FROM pages ORDER BY id LIMIT 1")[0][0]
        assert client.get(f"/api/pages/{pid}/image", headers=h).status_code == 200
        assert client.get(f"/api/batches/{dados['batch']}/source", headers=h).status_code == 200
    print(f"\nTEMPOS backup={TEMPOS['backup']:.3f}s restore={TEMPOS['restore']:.3f}s")


def test_B07b_backup_consistente_com_escrita_concorrente(dados):
    parar = threading.Event()
    criados = []

    def escrever():
        while not parar.is_set():
            criados.append(worker.criar_lote(BETA, "CT-001", "x.pdf", pdf("Pagina 1 de 1")))

    t = threading.Thread(target=escrever)
    t.start()
    try:
        time.sleep(0.2)
        pasta = bk.backup(dados["origem"], dados["tmp"] / "backups")
    finally:
        parar.set()
        t.join()
    m = bk.json.loads((pasta / bk.MANIFESTO).read_text(encoding="utf-8"))
    assert m["problemas"] == [] and bk.verify(pasta) == []
    snap = sqlite3.connect(pasta / "docrisk.sqlite")
    n = snap.execute("SELECT COUNT(*) FROM batches").fetchone()[0]
    snap.close()
    assert m["contagens"]["lotes"] == n  # todo lote do snapshot tem seu original no backup
    assert len(criados) > 0


def test_B07c_backup_corrompido_e_recusado_na_restauracao(dados):
    pasta = bk.backup(dados["origem"], dados["tmp"] / "backups")
    alvo = next((pasta / "files" / "pages").rglob("*.png"))
    alvo.write_bytes(b"corrompido")
    assert any("corrompido" in e for e in bk.verify(pasta))
    with pytest.raises(SystemExit):
        bk.restore(pasta, dados["tmp"] / "r2")
    assert not (dados["tmp"] / "r2" / "docrisk.sqlite").exists()


def test_B07d_restauracao_nao_sobrescreve_sem_force(dados):
    pasta = bk.backup(dados["origem"], dados["tmp"] / "backups")
    with pytest.raises(SystemExit):
        bk.restore(pasta, dados["origem"])
    bk.restore(pasta, dados["origem"], force=True)
    assert list(dados["origem"].glob("docrisk.sqlite.antes-restauracao-*"))


def test_B01_perda_de_arquivo_derivado_e_recuperada_identica(dados):
    paginas = _q("SELECT id, image_path, sha256 FROM pages WHERE batch_id=? ORDER BY ordem", dados["batch"])
    for _, caminho, _ in paginas[:3]:
        bk.Path(caminho).unlink()
    rel = bk.reconcile(dados["origem"])
    assert sorted(rel["paginas_ausentes"]) == sorted(p[0] for p in paginas[:3])
    t = time.monotonic()
    rel = bk.reconcile(dados["origem"], repair=True)
    TEMPOS["recuperar_paginas"] = time.monotonic() - t
    assert sorted(rel["paginas_recuperadas"]) == sorted(p[0] for p in paginas[:3])
    for pid, caminho, sha in paginas[:3]:
        assert bk._sha(bk.Path(caminho)) == sha
    assert bk.reconcile(dados["origem"])["paginas_ausentes"] == []


def test_B01b_original_ausente_e_relatado_nao_inventado(dados):
    arquivo = _q("SELECT arquivo FROM batches WHERE id=?", dados["batch"])[0][0]
    bk.Path(arquivo).unlink()
    pid, caminho = _q("SELECT id, image_path FROM pages WHERE batch_id=? LIMIT 1", dados["batch"])[0]
    bk.Path(caminho).unlink()
    rel = bk.reconcile(dados["origem"], repair=True)
    assert dados["batch"] in rel["originais_ausentes"] and pid in rel["paginas_irrecuperaveis"]


def test_B03_crash_durante_processamento_retoma_sem_duplicar(dados):
    bid = worker.criar_lote(BETA, "CT-001", "lote2.pdf", pdf(*LOTE))
    with db.tx() as conn:
        conn.execute("DELETE FROM ai_cache")  # força leitura real para a falha ocorrer

    class Falha(TextLayerProvider):
        n = 0

        def analisar(self, png, texto):
            Falha.n += 1
            if Falha.n == 4:
                raise RuntimeError("queda simulada no meio do lote")
            return super().analisar(png, texto)

    worker.processar_lote(bid, provedor=Falha())
    assert _q("SELECT status FROM batches WHERE id=?", bid)[0][0] == "FALHA_PROCESSAMENTO"
    worker.processar_lote(bid, provedor=TextLayerProvider())   # recuperação
    worker.processar_lote(bid, provedor=TextLayerProvider())   # repetição: idempotente
    assert _q("SELECT status FROM batches WHERE id=?", bid)[0][0] == "CONCLUIDO"
    assert tuple(_q("SELECT COUNT(*), COUNT(DISTINCT ordem) FROM pages WHERE batch_id=?", bid)[0]) == (8, 8)
    assert _q("SELECT COUNT(*) FROM documents WHERE batch_id=?", bid)[0][0] == 6


def test_B06_estado_inconsistente_detectado(dados):
    with db.tx() as conn:
        conn.execute("UPDATE pages SET status='PENDENTE' WHERE batch_id=? AND ordem=1", (dados["batch"],))
    assert dados["batch"] in bk.reconcile(dados["origem"])["lotes_inconsistentes"]


def test_B04_banco_reiniciado_preserva_dados(dados):
    antes = _estado()
    with TestClient(app):
        pass
    with TestClient(app):
        assert _estado() == antes


def test_B08_restaurar_e_reprocessar_nao_duplica_resultado(dados, monkeypatch):
    pasta = bk.backup(dados["origem"], dados["tmp"] / "backups")
    destino = dados["tmp"] / "rest"
    bk.restore(pasta, destino)
    _apontar(monkeypatch, destino)
    docs = _q("SELECT COUNT(*) FROM documents")[0][0]
    worker.processar_lote(dados["batch"], provedor=TextLayerProvider())
    assert _q("SELECT COUNT(*) FROM documents")[0][0] == docs


def test_B05_storage_indisponivel_no_backup_e_relatado(dados):
    caminho = _q("SELECT image_path FROM pages LIMIT 1")[0][0]
    bk.Path(caminho).unlink()
    pasta = bk.backup(dados["origem"], dados["tmp"] / "backups")
    m = bk.json.loads((pasta / bk.MANIFESTO).read_text(encoding="utf-8"))
    assert any("ausente no armazenamento" in p for p in m["problemas"])
