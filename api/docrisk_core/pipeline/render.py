"""Lote -> páginas PNG numeradas. Dono: FRENTE 2.

Detecta o formato pelo CONTEÚDO (reaproveita importer.detect_type do sprint01 e
acrescenta TIFF), valida sem renderizar (`inspecionar_arquivo`) e renderiza uma
página por vez (`iterar_paginas`), para não manter o lote inteiro em memória.
"""
from __future__ import annotations

import io
from collections.abc import Iterator
from dataclasses import dataclass

import fitz
from PIL import Image, ImageSequence, UnidentifiedImageError

from .. import config
from ..contracts import PaginaRenderizada
from ..importer import UnsupportedFile, detect_type

#: Limite de pixels por imagem de entrada (protege contra "decompression bomb").
MAX_PIXELS_IMAGEM = 60_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS_IMAGEM

_TIFF_MAGIC = (b"II*\x00", b"MM\x00*")
EXTENSAO_POR_TIPO = {"PDF": ".pdf", "PNG": ".png", "JPEG": ".jpg", "TIFF": ".tif"}


class ArquivoInvalido(ValueError):
    """Erro OBJETIVO do arquivo (corrompido, sem páginas, formato não suportado, senha).

    A API devolve 400/422 com a mensagem — é motivo verificável para a fornecedora.
    A mensagem nunca contém caminhos internos.
    """


@dataclass(frozen=True)
class InfoArquivo:
    tipo: str  # PDF | PNG | JPEG | TIFF
    paginas: int


def detectar_formato(filename: str, data: bytes) -> str:
    """Formato real pelo conteúdo: PDF, PNG, JPEG ou TIFF."""
    if not data:
        raise ArquivoInvalido("Arquivo vazio.")
    if data.startswith(_TIFF_MAGIC):
        return "TIFF"
    try:
        tipo = detect_type(filename or "arquivo", data)
    except UnsupportedFile as exc:
        raise ArquivoInvalido("Formato não suportado. Envie PDF, PNG, JPEG ou TIFF.") from exc
    if tipo == "PDF":
        return "PDF"
    if tipo == "IMAGE":
        return "PNG" if data.startswith(b"\x89PNG") else "JPEG"
    # AEJ é estruturado (texto), não passa pelo motor de imagem.
    raise ArquivoInvalido("Arquivo AEJ não é aceito neste envio; use o fluxo de jornada eletrônica.")


def _checar_tamanho(data: bytes) -> None:
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise ArquivoInvalido(f"Arquivo acima do limite de {config.MAX_UPLOAD_MB} MB.")


def _checar_paginas(n: int) -> None:
    if n <= 0:
        raise ArquivoInvalido("Arquivo sem páginas.")
    if n > config.MAX_PAGINAS:
        raise ArquivoInvalido(f"Arquivo com {n} páginas; o limite é {config.MAX_PAGINAS}.")


def _abrir_pdf(data: bytes) -> fitz.Document:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # PyMuPDF levanta tipos variados para PDF quebrado
        raise ArquivoInvalido("PDF corrompido ou ilegível.") from exc
    if doc.needs_pass or doc.is_encrypted:
        doc.close()
        raise ArquivoInvalido("PDF protegido por senha não é suportado. Envie sem senha.")
    return doc


def _abrir_imagem(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()  # checa integridade sem decodificar tudo
        img = Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ArquivoInvalido("Imagem corrompida, ilegível ou grande demais.") from exc
    if img.width * img.height > MAX_PIXELS_IMAGEM:
        raise ArquivoInvalido("Imagem grande demais (limite de pixels excedido).")
    return img


def inspecionar_arquivo(data: bytes, filename: str = "arquivo") -> InfoArquivo:
    """Valida o arquivo SEM renderizar: formato, tamanho, integridade e nº de páginas."""
    _checar_tamanho(data)
    tipo = detectar_formato(filename, data)
    if tipo == "PDF":
        doc = _abrir_pdf(data)
        try:
            n = doc.page_count
        finally:
            doc.close()
    else:
        img = _abrir_imagem(data)
        try:
            n = getattr(img, "n_frames", 1) if tipo == "TIFF" else 1
        finally:
            img.close()
    _checar_paginas(n)
    return InfoArquivo(tipo=tipo, paginas=n)


def _limitar(img: Image.Image) -> Image.Image:
    """Converte para RGB e reduz o maior lado a MAX_LADO_PX, mantendo a proporção."""
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    maior = max(img.width, img.height)
    if maior > config.MAX_LADO_PX:
        fator = config.MAX_LADO_PX / maior
        img = img.resize((max(1, round(img.width * fator)), max(1, round(img.height * fator))),
                         Image.Resampling.LANCZOS)
    return img


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def _iterar_pdf(data: bytes) -> Iterator[PaginaRenderizada]:
    doc = _abrir_pdf(data)
    try:
        _checar_paginas(doc.page_count)
        for indice, page in enumerate(doc):
            zoom = config.RENDER_DPI / 72
            maior_px = max(page.rect.width, page.rect.height) * zoom
            if maior_px > config.MAX_LADO_PX:
                zoom *= config.MAX_LADO_PX / maior_px
            try:
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                png = pix.tobytes("png")
                texto = page.get_text("text") or ""
            except Exception as exc:
                raise ArquivoInvalido(f"Falha ao ler a página {indice + 1} do PDF.") from exc
            yield PaginaRenderizada(ordem=indice + 1, png=png, texto_camada=texto)
    finally:
        doc.close()


def _iterar_imagem(data: bytes, tipo: str) -> Iterator[PaginaRenderizada]:
    img = _abrir_imagem(data)
    try:
        quadros = ImageSequence.Iterator(img) if tipo == "TIFF" else [img]
        ordem = 0
        for quadro in quadros:
            ordem += 1
            if ordem > config.MAX_PAGINAS:
                _checar_paginas(ordem)
            try:
                png = _png(_limitar(quadro.copy()))
            except (OSError, ValueError) as exc:
                raise ArquivoInvalido(f"Falha ao ler a página {ordem} da imagem.") from exc
            yield PaginaRenderizada(ordem=ordem, png=png, texto_camada="")
        if ordem == 0:
            raise ArquivoInvalido("Arquivo sem páginas.")
    finally:
        img.close()


def iterar_paginas(data: bytes, tipo_arquivo: str | None = None,
                   filename: str = "arquivo") -> Iterator[PaginaRenderizada]:
    """Gera uma PaginaRenderizada por vez, na ordem original (1..N)."""
    _checar_tamanho(data)
    tipo = (tipo_arquivo or "").upper() or detectar_formato(filename, data)
    if tipo == "IMAGE":  # rótulo do sprint01
        tipo = "PNG" if data.startswith(b"\x89PNG") else "JPEG"
    if tipo == "PDF":
        yield from _iterar_pdf(data)
    elif tipo in ("PNG", "JPEG", "TIFF"):
        yield from _iterar_imagem(data, tipo)
    else:
        raise ArquivoInvalido("Formato não suportado. Envie PDF, PNG, JPEG ou TIFF.")


def renderizar(data: bytes, tipo_arquivo: str) -> list[PaginaRenderizada]:
    """PDF / PNG / JPEG / TIFF -> uma PaginaRenderizada por página, ordem preservada.

    - DPI de config.RENDER_DPI, maior lado limitado a config.MAX_LADO_PX
    - TIFF multipágina suportado
    - mais de config.MAX_PAGINAS páginas, senha, corrompido ou vazio -> ArquivoInvalido
    - texto_camada = texto digital do PDF; "" em imagem
    Para lotes grandes prefira `iterar_paginas` (uma página por vez).
    """
    return list(iterar_paginas(data, tipo_arquivo))
