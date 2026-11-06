"""Anonimização: um caso positivo e um negativo por tipo + PDF com tarja de verdade."""
import io

import pymupdf as fitz
import pytest
from PIL import Image

from docrisk_core.privacidade import SemCamadaDeTexto, anonimizar_pdf, mascarar_texto
from test_f3_regras import _gerador

# (tipo, texto com dado pessoal FICTÍCIO, valor que não pode sobrar)
POSITIVOS = [
    ("CPF", "CPF: 123.456.789-09", "123.456.789-09"),
    ("CPF", "CPF 12345678909 no cabeçalho", "12345678909"),
    ("RG", "RG: 12.345.678-9", "12.345.678-9"),
    ("RG", "Registro: 00.000.000-0 (fictício)", "00.000.000-0"),
    ("PIS_NIS", "PIS: 123.45678.90-1", "123.45678.90-1"),
    ("PIS_NIS", "NIS 12345678901", "12345678901"),
    ("CTPS", "CTPS: 123456 série 0012", "123456 série 0012"),
    ("DATA_NASCIMENTO", "Data de nascimento: 15/03/1990", "15/03/1990"),
    ("EMAIL", "Contato: ana.ficticia@example.invalid", "ana.ficticia@example.invalid"),
    ("TELEFONE", "Fone: (87) 99999-8888", "(87) 99999-8888"),
    ("AGENCIA", "Agência: 1234-5", "1234-5"),
    ("CONTA", "Conta corrente: 98765-4", "98765-4"),
]

# Texto que NÃO pode mudar: as regras de horas extras dependem deles.
NEGATIVOS = [
    "08:00", "10/2026", "Competência: 10/2026", "Matrícula: T001", "Horas extras 50% — Ref.: 08,00 h",
    "TOTAL DE HORAS EXTRAS: 12,00 h", "15/10/2026 08:00 12:00 13:00 19:00 02:00",
    "Fornecedora Beta — CNPJ 00.000.000/0001-00", "CNPJ 12345678000190", "Autenticação: 0000.FICT.1234.5678",
    "Data do pagamento: 05/11/2026", "Data: 15/03/1990", "Valor pago: R$ 1.840,00", "Código 001 Salário base",
]


@pytest.mark.parametrize("tipo,texto,valor", POSITIVOS)
def test_mascara_cada_tipo(tipo, texto, valor):
    mascarado, achados = mascarar_texto(texto)
    assert valor not in mascarado
    assert [a["tipo"] for a in achados] == [tipo]
    a = achados[0]
    assert texto[a["inicio"]:a["fim"]] == valor  # offsets do texto original
    assert set(a) == {"tipo", "inicio", "fim"}  # nunca devolve o valor


@pytest.mark.parametrize("texto", NEGATIVOS)
def test_nao_mascara_o_que_as_regras_usam(texto):
    assert mascarar_texto(texto) == (texto, [])


def test_rotulo_e_preservado_e_cnpj_fica():
    mascarado, _ = mascarar_texto("RG: 12.345.678-9 — CNPJ 00.000.000/0001-00")
    assert mascarado.startswith("RG: ") and "00.000.000/0001-00" in mascarado


def test_rotulo_nao_atravessa_linha():
    # "Conta" sozinha no fim da linha não pode mascarar o número da linha seguinte
    texto = "Conta\n001 Salário base"
    assert mascarar_texto(texto) == (texto, [])


def _pdf(*linhas: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    for i, linha in enumerate(linhas):
        page.insert_text((50, 80 + 20 * i), linha, fontsize=11)
    return doc.tobytes()


def test_pdf_tarja_apaga_o_texto_de_verdade():
    saida = anonimizar_pdf(_pdf("CPF: 123.456.789-09", "RG: 12.345.678-9",
                                "Matrícula: T001  Competência: 10/2026  Saída 17:00"))
    texto = "".join(p.get_text() for p in fitz.open(stream=saida, filetype="pdf"))
    assert "123.456.789-09" not in texto and "12.345.678-9" not in texto
    assert "T001" in texto and "10/2026" in texto and "17:00" in texto  # o resto permanece


def test_pdf_tem_tarja_preta():
    saida = anonimizar_pdf(_pdf("CPF: 123.456.789-09"))
    page = fitz.open(stream=saida, filetype="pdf")[0]
    pix = page.get_pixmap(clip=fitz.Rect(50, 70, 200, 90), alpha=False)
    assert min(pix.samples) == 0  # há pixel preto onde estava o CPF


def test_pdf_sem_dado_pessoal_mantem_texto():
    saida = anonimizar_pdf(_pdf("Matrícula: T001", "Horas extras 08:00"))
    texto = fitz.open(stream=saida, filetype="pdf")[0].get_text()
    assert "T001" in texto and "08:00" in texto


def test_paginas_escolhe_e_mantem_a_ordem_pedida():
    doc = fitz.open()
    for n in (1, 2, 3):
        doc.new_page().insert_text((50, 80), f"pagina {n} CPF: 123.456.789-09", fontsize=11)
    saida = fitz.open(stream=anonimizar_pdf(doc.tobytes(), [3, 1]), filetype="pdf")
    assert [p.get_text().split()[1] for p in saida] == ["3", "1"]
    assert "123.456.789-09" not in "".join(p.get_text() for p in saida)


def test_pagina_so_de_imagem_e_recusada_em_vez_de_sair_sem_tarja():
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), "white").save(buf, "PNG")
    doc = fitz.open()
    doc.new_page().insert_image(fitz.Rect(50, 50, 200, 200), stream=buf.getvalue())
    with pytest.raises(SemCamadaDeTexto):
        anonimizar_pdf(doc.tobytes())


def test_lote_demo_holerites_tem_cpf_e_rg_e_saem_com_tarja(tmp_path):
    lote = _gerador().gerar(tmp_path)["lote_demo.pdf"].read_bytes()
    original = "".join(p.get_text() for p in fitz.open(stream=lote, filetype="pdf"))
    depois = "".join(p.get_text() for p in fitz.open(stream=anonimizar_pdf(lote), filetype="pdf"))
    for n in range(1, 6):
        assert f"000.000.00{n}-00" in original and f"00.000.00{n}-0" in original
        assert f"000.000.00{n}-00" not in depois and f"00.000.00{n}-0" not in depois
    assert "00.000.000-0" not in depois  # RG do documento de identidade (rótulo "Registro")
    assert depois.count("T001") == original.count("T001")  # matrícula e horas permanecem