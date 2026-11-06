"""Rotas da anonimização (proposta para o dono de routes/): PDF com tarja e OCR mascarado."""
import io

import pymupdf as fitz
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from docrisk_core import config, db
from docrisk_core.api import app
from docrisk_core.routes import _trecho_busca_mascarado
from test_f2_worker import banco  # noqa: F401  (fixture)
from test_f3_regras import _enviar, _gerador, _h

CPF_T001, RG_T001 = "000.000.001-00", "00.000.001-0"


@pytest.fixture
def lote_enviado(banco, tmp_path):  # noqa: F811
    arquivo = _gerador().gerar(tmp_path)["lote_demo.pdf"]
    with TestClient(app) as client:
        assert _enviar(client, arquivo).status_code == 202
        docs = client.get("/api/documents", params={"tipo": "HOLERITE"}, headers=_h("u-analista")).json()
        yield client, next(d["id"] for d in docs if d["worker_id"] == "T001")


def _texto(resposta):
    return "".join(p.get_text() for p in fitz.open(stream=io.BytesIO(resposta.content), filetype="pdf"))


def test_ocr_inteiro_so_para_bernhoeft(lote_enviado):
    client, doc = lote_enviado
    ber = client.get(f"/api/documents/{doc}", headers=_h("u-analista")).json()
    forn = client.get(f"/api/documents/{doc}", headers=_h("u-oper-beta")).json()
    assert CPF_T001 in ber["paginas_detalhe"][0]["texto"]
    texto = forn["paginas_detalhe"][0]["texto"]
    assert CPF_T001 not in texto and RG_T001 not in texto and "***.***.***-**" in texto
    assert "T001" in texto and "08,00" in texto  # o que as regras usam não muda


def test_pdf_anonimizado_so_do_documento_e_sem_dado_pessoal(lote_enviado):
    client, doc = lote_enviado
    for usuario in ("u-oper-beta", "u-gestor-beta", "u-analista", "u-admin"):
        r = client.get(f"/api/documents/{doc}/anonimizado", headers=_h(usuario))
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf", usuario
        assert len(fitz.open(stream=io.BytesIO(r.content), filetype="pdf")) == 1
        assert CPF_T001 not in _texto(r) and RG_T001 not in _texto(r) and "T001" in _texto(r)
    with db.tx() as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit WHERE acao='DOCUMENTO_ANONIMIZADO_BAIXADO'").fetchone()[0] == 4


def test_contratante_nao_baixa_documentos_antes_ou_depois_da_publicacao(lote_enviado):
    client, doc = lote_enviado
    path = f"/api/documents/{doc}/anonimizado"
    customer = _h("u-gestor-alfa")
    assert client.get("/api/client/reports", headers=customer).json() == []
    with db.tx() as conn:
        conn.execute("UPDATE documents SET status='REVISAO_HUMANA' WHERE id=?", (doc,))
    assert client.get(path, headers=customer).status_code == 403
    assert client.get("/api/documents/999999/anonimizado", headers=customer).status_code == 403
    draft = client.post("/api/reports", headers=_h("u-analista"),
                        json={"contract_id": "CT-001", "competencia": "10/2026"})
    assert draft.status_code == 201, draft.text
    assert client.get(path, headers=customer).status_code == 403
    published = client.post(f"/api/reports/{draft.json()['id']}/publish", headers=_h("u-analista"))
    assert published.status_code == 200, published.text
    assert client.get("/api/client/reports", headers=customer).json()
    assert client.get(path, headers=customer).status_code == 403
    with db.tx() as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit WHERE acao='DOCUMENTO_ANONIMIZADO_BAIXADO'").fetchone()[0] == 0


def test_pdf_anonimizado_respeita_isolamento_por_contrato(lote_enviado):
    client, doc = lote_enviado
    assert client.get(f"/api/documents/{doc}/anonimizado", headers=_h("u-oper-gama")).status_code == 404
    assert client.get("/api/documents/999999/anonimizado", headers=_h("u-analista")).status_code == 404


def test_contratante_nao_recebe_ocr_original(lote_enviado):
    client, doc = lote_enviado
    assert client.get(f"/api/documents/{doc}", headers=_h("u-gestor-alfa")).status_code == 403


def test_trecho_da_busca_mascarado_para_fornecedora(lote_enviado):
    client, _ = lote_enviado
    forn = client.get("/api/search", params={"q": "CPF"}, headers=_h("u-oper-beta")).json()
    ber = client.get("/api/search", params={"q": "CPF"}, headers=_h("u-analista")).json()
    assert forn and not any("000.000.00" in a["trecho"] for a in forn)
    assert any("000.000.00" in a["trecho"] for a in ber)


def test_busca_corta_depois_de_mascarar_a_pagina_inteira():
    texto = "CPF: 123.456.789-09 " + ("contexto " * 20) + "termo localizado"
    trecho = _trecho_busca_mascarado(texto, "termo", contexto=20)
    assert "123.456.789-09" not in trecho
    assert "[[termo]]" in trecho


def test_pdf_com_imagem_e_texto_e_recusado(lote_enviado):
    client, doc = lote_enviado
    detalhes = client.get(f"/api/documents/{doc}", headers=_h("u-analista")).json()
    ordens = [p["ordem"] for p in detalhes["paginas"]]
    imagem = io.BytesIO()
    Image.new("RGB", (30, 30), "white").save(imagem, format="PNG")
    original = fitz.open()
    for ordem in range(1, max(ordens) + 1):
        page = original.new_page()
        if ordem == ordens[0]:
            page.insert_text((50, 50), "CPF: 123.456.789-09", fontsize=11)
            page.insert_image(fitz.Rect(50, 100, 100, 150), stream=imagem.getvalue())
    caminho = config.UPLOAD_DIR / f"pdf-com-imagem-{doc}.pdf"
    caminho.write_bytes(original.tobytes())
    original.close()
    with db.tx() as conn:
        conn.execute("UPDATE batches SET arquivo=? WHERE id=?", (str(caminho), detalhes["batch_id"]))
    response = client.get(f"/api/documents/{doc}/anonimizado", headers=_h("u-oper-beta"))
    assert response.status_code == 422
    assert "imagem" in response.json()["detail"].lower()


@pytest.mark.parametrize("conteudo", ["comentario", "formulario", "link"])
def test_pdf_com_conteudo_fora_do_texto_e_recusado(lote_enviado, conteudo):
    client, doc = lote_enviado
    with db.tx() as conn:
        batch = conn.execute(
            "SELECT b.id,b.arquivo FROM batches b JOIN documents d ON d.batch_id=b.id WHERE d.id=?",
            (doc,),
        ).fetchone()
        order = conn.execute(
            "SELECT p.ordem FROM doc_pages dp JOIN pages p ON p.id=dp.page_id WHERE dp.document_id=?",
            (doc,),
        ).fetchone()[0]
    with fitz.open(batch["arquivo"]) as original:
        page = original[order - 1]
        if conteudo == "comentario":
            page.add_text_annot((50, 50), f"CPF: {CPF_T001}")
        elif conteudo == "formulario":
            widget = fitz.Widget()
            widget.field_name = "cpf"
            widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
            widget.field_value = CPF_T001
            widget.rect = fitz.Rect(50, 50, 200, 80)
            page.add_widget(widget)
        else:
            page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(50, 50, 200, 80),
                              "uri": f"https://example.invalid/?cpf={CPF_T001}"})
        path = config.UPLOAD_DIR / f"pdf-{conteudo}-{doc}.pdf"
        original.save(path)
    with db.tx() as conn:
        conn.execute("UPDATE batches SET arquivo=? WHERE id=?", (str(path), batch["id"]))
    for user in ("u-oper-beta", "u-analista"):
        response = client.get(f"/api/documents/{doc}/anonimizado", headers=_h(user))
        assert response.status_code == 422, response.status_code
        assert "anotações" in response.json()["detail"]
        assert CPF_T001 not in response.text
    with db.tx() as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit WHERE acao='DOCUMENTO_ANONIMIZADO_BAIXADO'").fetchone()[0] == 0
