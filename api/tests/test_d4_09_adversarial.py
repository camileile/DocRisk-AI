"""D4-09 — cenários adversos: multiempresa, uploads hostis, concorrência e privacidade.

Cada teste tem o identificador da matriz em docs/dev4/D4-09_TESTES_ADVERSOS.md.
Somente dados sintéticos; leitor offline (textlayer); nenhuma chamada externa.
"""
from __future__ import annotations

import io
import logging
import threading

import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from docrisk_core import config, db
from docrisk_core.ai.textlayer import TextLayerProvider
from docrisk_core.api import app
from docrisk_core.pipeline import worker
from test_f2_worker import BETA, LOTE, banco, pdf  # noqa: F401


def _h(uid: str) -> dict[str, str]:
    with db.tx() as conn:
        return {"Authorization": "Bearer " + conn.execute("SELECT token FROM users WHERE id=?", (uid,)).fetchone()[0]}


def _q(sql, *a):
    with db.tx() as conn:
        return conn.execute(sql, a).fetchall()


@pytest.fixture
def lote_beta(banco):  # noqa: F811
    bid = worker.criar_lote(BETA, "CT-001", "lote.pdf", pdf(*LOTE))
    worker.processar_lote(bid, provedor=TextLayerProvider())
    doc = _q("SELECT id FROM documents WHERE batch_id=? ORDER BY id LIMIT 1", bid)[0][0]
    page = _q("SELECT id FROM pages WHERE batch_id=? ORDER BY id LIMIT 1", bid)[0][0]
    issue = _q("SELECT id FROM issues WHERE contract_id='CT-001' ORDER BY id LIMIT 1")
    return {"batch": bid, "doc": doc, "page": page, "issue": issue[0][0] if issue else None}


# --------------------------------------------------------------- MT: multiempresa
ROTAS_POR_ID = [
    ("GET", "/api/batches/{batch}"), ("GET", "/api/batches/{batch}/documents"),
    ("GET", "/api/batches/{batch}/source"), ("POST", "/api/batches/{batch}/reprocess"),
    ("GET", "/api/documents/{doc}"), ("GET", "/api/documents/{doc}/anonimizado"),
    ("GET", "/api/pages/{page}/image"),
]


@pytest.mark.parametrize("metodo,rota", ROTAS_POR_ID)
def test_MT01_outra_fornecedora_nao_acessa_recurso_por_id(lote_beta, metodo, rota):
    with TestClient(app) as client:
        r = client.request(metodo, rota.format(**lote_beta), headers=_h("u-oper-gama"))
        assert r.status_code in (403, 404), (rota, r.status_code)
        assert "T001" not in r.text and "lote.pdf" not in r.text


def test_MT02_ids_vizinhos_e_invalidos_nao_vazam(lote_beta):
    h = _h("u-oper-gama")
    with TestClient(app) as client:
        for valor in [0, -1, lote_beta["batch"] + 1, 2**31, 2**63 - 1, "1;DROP TABLE batches", "../1", "1e3"]:
            r = client.get(f"/api/batches/{valor}", headers=h)
            assert r.status_code in (403, 404, 422), (valor, r.status_code)
    assert _q("SELECT COUNT(*) FROM batches")[0][0] >= 1  # tabela intacta


def test_MT03_listagens_e_busca_respeitam_isolamento(lote_beta):
    h = _h("u-oper-gama")
    with TestClient(app) as client:
        assert all(b["contract_id"] == "CT-002" for b in client.get("/api/batches", headers=h).json())
        docs = client.get("/api/documents", headers=h)
        assert docs.status_code in (200, 403)
        if docs.status_code == 200:
            assert all(d["contract_id"] == "CT-002" for d in docs.json())
        busca = client.get("/api/search", params={"q": "demonstrativo"}, headers=_h("u-analista"))
        assert busca.status_code == 200
        busca_gama = client.get("/api/search", params={"q": "demonstrativo", "contract_id": "CT-001"}, headers=h)
        assert busca_gama.status_code in (403, 404)


def test_MT04_contrato_alheio_no_upload_e_negado_sem_criar_lote(banco):  # noqa: F811
    antes = _q("SELECT COUNT(*) FROM batches")[0][0]
    with TestClient(app) as client:
        r = client.post("/api/supplier/batches", headers=_h("u-oper-gama"), data={"contract_id": "CT-001"},
                        files={"file": ("x.pdf", pdf("Pagina 1 de 1"), "application/pdf")})
        assert r.status_code == 404
    assert _q("SELECT COUNT(*) FROM batches")[0][0] == antes


# --------------------------------------------------------------- UP: uploads
def _png() -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (40, 40), "white").save(b, format="PNG")
    return b.getvalue()


UPLOADS_HOSTIS = [
    ("UP01 vazio", "vazio.pdf", b""),
    ("UP02 corrompido", "c.pdf", b"%PDF-1.4\n" + b"\x00\xff" * 500),
    ("UP03 tipo nao suportado", "x.exe", b"MZ\x90\x00" + b"\x00" * 200),
    ("UP04 extensao pdf com conteudo zip", "doc.pdf", b"PK\x03\x04" + b"\x00" * 200),
    ("UP05 html disfarçado", "doc.png", b"<html><script>alert(1)</script></html>"),
    ("UP06 png truncado", "img.png", _png()[:30]),
    ("UP07 tiff com cabeçalho e lixo", "a.tif", b"II*\x00" + b"\xff" * 64),
    ("UP08 svg", "a.svg", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"),
]


@pytest.mark.parametrize("cid,nome,dados", UPLOADS_HOSTIS, ids=[u[0] for u in UPLOADS_HOSTIS])
def test_UP_arquivos_hostis_sao_recusados_sem_efeito(banco, cid, nome, dados):  # noqa: F811
    with TestClient(app) as client:
        r = client.post("/api/supplier/batches", headers=_h("u-oper-beta"), data={"contract_id": "CT-001"},
                        files={"file": (nome, dados, "application/octet-stream")})
    assert r.status_code == 422, (cid, r.status_code, r.text[:200])
    assert "Traceback" not in r.text and str(config.DATA_DIR) not in r.text
    assert _q("SELECT COUNT(*) FROM batches")[0][0] == 0
    assert not any(config.UPLOAD_DIR.glob("*")) if config.UPLOAD_DIR.exists() else True


@pytest.mark.parametrize("nome", [
    "../../../../etc/passwd.pdf", "..\\..\\windows\\system32\\x.pdf", "/abs/path.pdf",
    "C:\\x\\y.pdf", "nome\x00oculto.pdf", "a" * 500 + ".pdf", "<script>.pdf", "CON.pdf",
])
def test_UP09_nome_malicioso_nao_controla_caminho(banco, nome):  # noqa: F811
    with TestClient(app) as client:
        r = client.post("/api/supplier/batches", headers=_h("u-oper-beta"), data={"contract_id": "CT-001"},
                        files={"file": (nome, pdf("Pagina 1 de 1"), "application/pdf")})
    if r.status_code != 202:
        assert r.status_code == 422
        return
    arquivo, exibicao = _q("SELECT arquivo, filename FROM batches WHERE id=?", r.json()["batch_id"])[0]
    caminho = config.UPLOAD_DIR.resolve()
    from pathlib import Path
    assert Path(arquivo).resolve().parent == caminho
    assert Path(arquivo).name.startswith("lote-")
    assert "/" not in exibicao and "\\" not in exibicao and len(exibicao) <= 200


def test_UP10_pdf_com_estrutura_adversa_nao_derruba_o_worker(banco):  # noqa: F811
    doc = fitz.open()
    for _ in range(3):
        doc.new_page()
    dados = doc.tobytes()
    bid = worker.criar_lote(BETA, "CT-001", "branco.pdf", dados)  # páginas sem texto
    worker.processar_lote(bid, provedor=TextLayerProvider())
    status = _q("SELECT status FROM batches WHERE id=?", bid)[0][0]
    assert status in ("CONCLUIDO", "FALHA_PROCESSAMENTO")


# --------------------------------------------------------------- CC: concorrência
def test_CC01_processamento_concorrente_do_mesmo_lote_nao_duplica(banco):  # noqa: F811
    bid = worker.criar_lote(BETA, "CT-001", "lote.pdf", pdf(*LOTE))
    barreira = threading.Barrier(4)
    erros: list[BaseException] = []

    def rodar():
        barreira.wait()
        try:
            worker.processar_lote(bid, provedor=TextLayerProvider())
        except BaseException as exc:  # registra e deixa o teste decidir
            erros.append(exc)

    threads = [threading.Thread(target=rodar) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    docs = _q("SELECT COUNT(*) FROM documents WHERE batch_id=?", bid)[0][0]
    paginas = _q("SELECT COUNT(*), COUNT(DISTINCT ordem) FROM pages WHERE batch_id=?", bid)[0]
    pend = _q("SELECT COUNT(*), COUNT(DISTINCT COALESCE(document_id,'')||'|'||categoria||'|'||"
              "COALESCE(worker_id,'')||'|'||COALESCE(competencia,'')) FROM issues WHERE contract_id='CT-001'")[0]
    analises = _q("SELECT COUNT(*) FROM analyses WHERE contract_id='CT-001' AND atual=1")[0][0]
    status = _q("SELECT status FROM batches WHERE id=?", bid)[0][0]
    assert not erros, [repr(e)[:120] for e in erros]
    assert paginas[0] == paginas[1] == 8, paginas
    assert docs == 6, docs                       # mesmo resultado do processamento único
    assert pend[0] == pend[1] == 4, pend         # pendências sem duplicata (referência sequencial = 4)
    assert analises == 3, analises               # uma análise vigente por trabalhador/competência
    assert status == "CONCLUIDO"


def test_CC02_uploads_simultaneos_geram_lotes_distintos(banco):  # noqa: F811
    resultados = []
    with TestClient(app) as client:
        h = _h("u-oper-beta")

        def enviar(i):
            r = client.post("/api/supplier/batches", headers=h, data={"contract_id": "CT-001"},
                            files={"file": (f"l{i}.pdf", pdf(f"Holerite {i}", "Pagina 1 de 1"), "application/pdf")})
            resultados.append(r.status_code)

        threads = [threading.Thread(target=enviar, args=(i,)) for i in range(16)]
        [t.start() for t in threads]
        [t.join(60) for t in threads]
    assert resultados.count(202) == 16, resultados
    ids = [r[0] for r in _q("SELECT id FROM batches")]
    assert len(ids) == len(set(ids)) == 16
    arquivos = {r[0] for r in _q("SELECT arquivo FROM batches")}
    assert len(arquivos) == 16


def test_CC03_enfileirar_repetido_nao_duplica_na_fila(banco, monkeypatch):  # noqa: F811
    monkeypatch.setattr(config, "SYNC", False)
    worker._na_fila.clear()
    while not worker._fila.empty():
        worker._fila.get_nowait()
    for _ in range(5):
        worker.enfileirar(4242)
    assert worker._fila.qsize() == 1
    worker._fila.get_nowait()
    worker._na_fila.clear()


# --------------------------------------------------------------- PV: privacidade
def test_PV01_logs_nao_contem_tokens_nem_texto_de_documento(banco, caplog):  # noqa: F811
    caplog.set_level(logging.DEBUG)
    with TestClient(app) as client:
        h = _h("u-oper-beta")
        r = client.post("/api/supplier/batches", headers=h, data={"contract_id": "CT-001"},
                        files={"file": ("lote.pdf", pdf(*LOTE), "application/pdf")})
        assert r.status_code == 202
        client.get("/api/me", headers={"Authorization": "Bearer token-invalido-xyz"})
    texto = caplog.text
    token = h["Authorization"].split()[1]
    assert token not in texto and "token-invalido-xyz" not in texto
    for trecho in LOTE[2:4]:  # conteúdo textual das páginas sintéticas
        primeira_linha = trecho.splitlines()[0]
        assert primeira_linha not in texto, primeira_linha


def test_PV02_respostas_nao_expoem_tokens_nem_caminhos(lote_beta):
    with TestClient(app) as client:
        for uid in ["u-oper-beta", "u-analista", "u-gestor-alfa"]:
            h = _h(uid)
            token = h["Authorization"].split()[1]
            for rota in ["/api/me", "/api/batches", "/api/documents", f"/api/batches/{lote_beta['batch']}",
                         "/api/contracts", "/api/client/reports"]:
                r = client.get(rota, headers=h)
                assert token not in r.text, (uid, rota)
                assert str(config.DATA_DIR) not in r.text and "uploads" not in r.text.lower(), (uid, rota)


def test_PV03_demo_users_indisponivel_fora_do_modo_demo(banco, monkeypatch):  # noqa: F811
    monkeypatch.setattr(config, "DEMO_MODE", False)
    with TestClient(app) as client:
        r = client.get("/api/demo/users")
        assert r.status_code in (403, 404)
        assert "token" not in r.text.lower() or r.status_code != 200
