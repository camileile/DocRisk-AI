import shutil
import pymupdf as fitz
import pytest
from io import BytesIO
from PIL import Image, ImageDraw
from docrisk_core.importer import import_bytes

def make_pdf():
    doc = fitz.open()
    for text in (
        "ESPELHO DE PONTO\nFuncionário fictício\nCompetência 10/2026\nPÁGINA 1 DE 2",
        "PÁGINA 2 DE 2\nContinuação das marcações\n08:00 12:00 13:00 17:00",
        "HOLERITE\nFuncionário fictício\nCompetência 10/2026\nHoras extras: 8",
    ):
        p = doc.new_page()
        p.insert_text((60, 100), text, fontsize=14)
    content = doc.tobytes(); doc.close()
    return content

def test_pdf_has_three_pages_and_grouping():
    result = import_bytes("lote.pdf", make_pdf())
    assert result["pages_count"] == 3
    assert result["groups"][0]["pages"] == [1, 2]
    assert result["groups"][1]["pages"] == [3]
    assert result["groups"][0]["needs_review"] is True
    assert result["pages"][0]["document_type"] == "ESPELHO_PONTO"
    assert result["pages"][2]["document_type"] == "FOLHA_PAGAMENTO"

def test_bad_file_rejected():
    from docrisk_core.importer import UnsupportedFile
    import pytest
    with pytest.raises(UnsupportedFile):
        import_bytes("fake.pdf", b"texto qualquer")

@pytest.mark.skipif(shutil.which("tesseract") is None,
                    reason="Tesseract não instalado (leitor opcional; o principal é o Gemini)")
def test_image_ocr_basic():
    img = Image.new("RGB", (850, 180), "white")
    draw = ImageDraw.Draw(img)
    draw.text((40, 50), "HOLERITE", fill="black", stroke_width=1)
    buff = BytesIO(); img.save(buff, format="PNG")
    result = import_bytes("imagem.png", buff.getvalue())
    assert result["pages_count"] == 1
    assert result["file_type"] == "IMAGE"
