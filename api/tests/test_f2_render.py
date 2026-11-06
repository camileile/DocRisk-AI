"""F2 — renderização de lotes (pipeline/render.py)."""
import io

import pymupdf as fitz
import pytest
from PIL import Image

from docrisk_core import config
from docrisk_core.pipeline.render import (
    ArquivoInvalido, inspecionar_arquivo, iterar_paginas, renderizar,
)


def pdf(*textos, tamanho=(595, 842)):
    doc = fitz.open()
    for t in textos:
        p = doc.new_page(width=tamanho[0], height=tamanho[1])
        p.insert_text((50, 80), t, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


def pdf_escaneado():
    """PDF só com imagem (sem camada de texto)."""
    img = Image.new("RGB", (400, 300), "white")
    buf = io.BytesIO(); img.save(buf, format="PNG")
    doc = fitz.open()
    p = doc.new_page()
    p.insert_image(p.rect, stream=buf.getvalue())
    data = doc.tobytes(); doc.close()
    return data


def imagem(fmt, tamanho=(300, 200), cor="white"):
    buf = io.BytesIO()
    Image.new("RGB", tamanho, cor).save(buf, format=fmt)
    return buf.getvalue()


def tiff_multipagina(n=3):
    quadros = [Image.new("RGB", (200, 100), c) for c in ("red", "green", "blue")[:n]]
    buf = io.BytesIO()
    quadros[0].save(buf, format="TIFF", save_all=True, append_images=quadros[1:])
    return buf.getvalue()


def lado_maior(png):
    with Image.open(io.BytesIO(png)) as im:
        return max(im.size)


def test_pdf_uma_pagina_com_camada_de_texto():
    paginas = renderizar(pdf("HOLERITE T001"), "PDF")
    assert len(paginas) == 1
    assert paginas[0].ordem == 1
    assert paginas[0].png.startswith(b"\x89PNG")
    assert "HOLERITE T001" in paginas[0].texto_camada


def test_pdf_varias_paginas_preserva_ordem():
    textos = [f"PAGINA-{i}" for i in range(1, 6)]
    paginas = renderizar(pdf(*textos), "PDF")
    assert [p.ordem for p in paginas] == [1, 2, 3, 4, 5]
    assert [p.texto_camada.strip() for p in paginas] == textos


def test_pdf_escaneado_sem_texto():
    paginas = renderizar(pdf_escaneado(), "PDF")
    assert len(paginas) == 1 and paginas[0].texto_camada.strip() == ""


@pytest.mark.parametrize("fmt,tipo", [("PNG", "PNG"), ("JPEG", "JPEG")])
def test_imagens_simples(fmt, tipo):
    data = imagem(fmt)
    assert inspecionar_arquivo(data, f"x.{fmt.lower()}").tipo == tipo
    paginas = renderizar(data, tipo)
    assert len(paginas) == 1 and paginas[0].texto_camada == ""


def test_tiff_multipagina_todos_os_quadros_em_ordem():
    data = tiff_multipagina(3)
    info = inspecionar_arquivo(data, "lote.tif")
    assert info.tipo == "TIFF" and info.paginas == 3
    paginas = renderizar(data, "TIFF")
    assert [p.ordem for p in paginas] == [1, 2, 3]
    cores = []
    for p in paginas:
        with Image.open(io.BytesIO(p.png)) as im:
            cores.append(im.convert("RGB").getpixel((5, 5)))
    assert cores == [(255, 0, 0), (0, 128, 0), (0, 0, 255)]


def test_respeita_lado_maximo_em_pdf_e_imagem(monkeypatch):
    monkeypatch.setattr(config, "MAX_LADO_PX", 800)
    assert lado_maior(renderizar(pdf("A", tamanho=(1190, 1684)), "PDF")[0].png) <= 800
    grande = imagem("PNG", tamanho=(3000, 1500))
    png = renderizar(grande, "PNG")[0].png
    with Image.open(io.BytesIO(png)) as im:
        assert im.size == (800, 400)  # proporção preservada


def test_pdf_corrompido():
    with pytest.raises(ArquivoInvalido, match="corrompido"):
        inspecionar_arquivo(b"%PDF-1.4\n" + b"\x00lixo" * 50, "x.pdf")


def test_pdf_com_senha():
    doc = fitz.open(); doc.new_page()
    data = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="u", owner_pw="o")
    doc.close()
    with pytest.raises(ArquivoInvalido, match="senha"):
        inspecionar_arquivo(data, "x.pdf")


def test_arquivo_vazio():
    with pytest.raises(ArquivoInvalido, match="vazio"):
        inspecionar_arquivo(b"", "x.pdf")


def test_formato_nao_permitido():
    with pytest.raises(ArquivoInvalido, match="não suportado"):
        inspecionar_arquivo(b"texto qualquer", "x.docx")


def test_acima_do_tamanho(monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_MB", 0)
    with pytest.raises(ArquivoInvalido, match="limite"):
        inspecionar_arquivo(pdf("A"), "x.pdf")


def test_acima_do_maximo_de_paginas(monkeypatch):
    monkeypatch.setattr(config, "MAX_PAGINAS", 2)
    with pytest.raises(ArquivoInvalido, match="limite é 2"):
        inspecionar_arquivo(pdf("1", "2", "3"), "x.pdf")
    with pytest.raises(ArquivoInvalido):
        list(iterar_paginas(tiff_multipagina(3), "TIFF"))


def test_imagem_corrompida():
    with pytest.raises(ArquivoInvalido):
        inspecionar_arquivo(b"\x89PNG\r\n\x1a\n" + b"\x00" * 40, "x.png")


def test_mensagens_nao_expoem_caminhos():
    with pytest.raises(ArquivoInvalido) as exc:
        inspecionar_arquivo(b"%PDF-1.4 quebrado", "C:/segredo/x.pdf")
    assert "segredo" not in str(exc.value) and ":\\" not in str(exc.value)
