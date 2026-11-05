"""Leitura de PDFs e imagens e segmentação heurística para layouts controlados.

O OCR funciona localmente com Tesseract; o modelo multimodal e a fila
persistente de revisão NÃO estão implementados nesta primeira entrega.
"""
from __future__ import annotations
from io import BytesIO
from typing import Any
import re
import pymupdf as fitz
from PIL import Image, UnidentifiedImageError
import pytesseract

class DocumentError(ValueError):
    pass

PATTERNS = [
    ("ESPELHO_PONTO", re.compile(r"\b(espelho\s+(de\s+)?ponto|cart[aã]o\s+de\s+ponto|registro\s+de\s+ponto)\b", re.I)),
    ("FOLHA_PAGAMENTO", re.compile(r"\b(folha\s+de\s+pagamento|holerite|contracheque|demonstrativo\s+de\s+pagamento)\b", re.I)),
    ("COMPROVANTE", re.compile(r"\b(comprovante\s+de\s+pagamento|recibo\s+de\s+sal[aá]rio)\b", re.I)),
    ("CONTRATO", re.compile(r"\bcontrato\s+(de\s+trabalho|de\s+presta[cç][aã]o)\b", re.I)),
    ("IDENTIFICACAO", re.compile(r"\b(documento\s+de\s+identifica[cç][aã]o|carteira\s+de\s+identidade)\b", re.I)),
]

def classify(text: str) -> tuple[str, str]:
    # Não é uma probabilidade estatística nem confiança calibrada.
    prefix = text[:1800]
    matches = [category for category, pattern in PATTERNS if pattern.search(prefix)]
    if len(matches) == 1:
        return matches[0], "HEURISTICA_TITULO"
    return "NAO_IDENTIFICADO", "REVISAO_HUMANA"

def _ocr(image: Image.Image) -> str:
    try:
        return pytesseract.image_to_string(image, lang="por+eng")
    except pytesseract.TesseractError as exc:
        raise DocumentError("Tesseract indisponível ou pacote de idiomas ausente") from exc

def _page_text_from_pdf(data: bytes) -> list[dict[str, Any]]:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        if doc.needs_pass:
            raise DocumentError("PDF protegido por senha não suportado no protótipo")
        if not doc.page_count:
            raise DocumentError("PDF sem páginas")
        if doc.page_count > 100:
            raise DocumentError("Limite demonstrativo: 100 páginas por arquivo")
        pages: list[dict[str, Any]] = []
        for idx, page in enumerate(doc):
            text = page.get_text("text").strip()
            origin = "PDF_TEXTO"
            if len(text) < 20:
                pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
                image = Image.open(BytesIO(pix.tobytes("png"))).convert("RGB")
                text = _ocr(image).strip()
                origin = "OCR_TESSERACT"
            category, method = classify(text)
            pages.append({"page_number": idx + 1, "text": text, "origin": origin,
                          "document_type": category, "classification_method": method})
        doc.close()
        return pages
    except fitz.FileDataError as exc:
        raise DocumentError("PDF inválido ou corrompido") from exc

def _page_text_from_image(data: bytes) -> list[dict[str, Any]]:
    try:
        img = Image.open(BytesIO(data))
        img.verify()
        img = Image.open(BytesIO(data)).convert("RGB")
        if img.width * img.height > 25_000_000:
            raise DocumentError("Imagem acima do limite de pixels")
        text = _ocr(img).strip()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise DocumentError("Imagem inválida ou excessivamente grande") from exc
    category, method = classify(text)
    return [{"page_number": 1, "text": text, "origin": "OCR_TESSERACT",
             "document_type": category, "classification_method": method}]

def _page_is_continuation(text: str) -> bool:
    head = text[:450]
    match = re.search(r"\b(p[aá]gina|pag)\s*[:.]?\s*(\d+)\s*(de|/)\s*\d+", head, re.I)
    return bool(match and int(match.group(2)) > 1)

def group_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for page in pages:
        category = page["document_type"]
        # Regra CONSERVADORA: sem cabeçalho conhecido, NÃO cria novo documento.
        # A saída é provisória e fica pendente de revisão por segmentação.
        start = not groups or (category != "NAO_IDENTIFICADO"
                               and not _page_is_continuation(page["text"]))
        if start:
            groups.append({"type": category, "pages": [], "needs_review": False})
        group = groups[-1]
        group["pages"].append(page["page_number"])
        if category == "NAO_IDENTIFICADO" or (category != group["type"]
                                              and category != "NAO_IDENTIFICADO"):
            group["needs_review"] = True
        # Heurística não é segmentação automática validada; revisão obrigatória.
        group["needs_review"] = True
    return groups

def inspect_document(data: bytes, kind: str) -> dict[str, Any]:
    if kind == "PDF":
        pages = _page_text_from_pdf(data)
    elif kind == "IMAGE":
        pages = _page_text_from_image(data)
    else:
        raise DocumentError("Formato não suportado")
    groups = group_pages(pages)
    return {"file_type": kind, "pages_count": len(pages),
            "groups": groups, "review_required": True,
            "pages": [{"page_number": p["page_number"], "origin": p["origin"],
                        "document_type": p["document_type"],
                        "classification_method": p["classification_method"],
                        "searchable_characters": len(p["text"])} for p in pages],
            "validation": "HEURISTIC_PREVIEW",
            "warnings": ["Segmentação provisória: agrupamentos precisam de revisão humana",
                         "Confiança estatística ainda não calibrada; não gerar parecer a partir deste resultado"]}
