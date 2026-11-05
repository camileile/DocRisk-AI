"""Lote -> páginas PNG numeradas. Dono: FRENTE 2.

Pode reaproveitar a detecção de formato de importer.detect_type (sprint01).
"""
from __future__ import annotations

from ..contracts import PaginaRenderizada


class ArquivoInvalido(ValueError):
    """Erro OBJETIVO do arquivo (corrompido, sem páginas, formato não suportado, senha).

    A API devolve 400/422 com a mensagem — é motivo verificável para a fornecedora.
    """


def renderizar(data: bytes, tipo_arquivo: str) -> list[PaginaRenderizada]:
    """PDF / PNG / JPEG / TIFF -> uma PaginaRenderizada por página, ordem preservada.

    Aceite:
    - DPI de config.RENDER_DPI, maior lado limitado a config.MAX_LADO_PX (imagens grandes)
    - TIFF multipágina suportado (scanners geram TIFF)
    - mais de config.MAX_PAGINAS páginas -> ArquivoInvalido
    - texto_camada = page.get_text() em PDF; "" em imagem
    """
    raise NotImplementedError("Frente 2: renderizar")
