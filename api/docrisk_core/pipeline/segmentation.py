"""Páginas -> documentos (fronteiras e agrupamento multipágina). Dono: FRENTE 2.

Substitui documents.group_pages do sprint01, corrigindo:
- needs_review forçado para todos (aqui só vai à revisão o que tiver motivo)
- numeração só procurada no topo (aqui vem do campo pagina_x/pagina_de da análise)
- página desconhecida grudando no documento anterior
- troca de trabalhador/competência ignorada
"""
from __future__ import annotations

from ..contracts import AnalisePagina, SegmentoDocumento


def segmentar(analises: list[AnalisePagina], ordens: list[int] | None = None) -> list[SegmentoDocumento]:
    """Agrupa páginas consecutivas em documentos. Função PURA (testável sem banco).

    `ordens[i]` = número da página i no lote (padrão: 1..N).

    Abre documento novo quando:
    - pagina_x == 1, ou inicio_documento sem numeração de continuação;
    - trabalhador, competência ou tipo (ambos conhecidos) mudam em relação ao grupo.
    Mantém no mesmo documento quando pagina_x > 1 sem conflito.
    Página DESCONHECIDA sem numeração -> grupo próprio + alerta "fronteira incerta".

    Por documento: tipo = mais frequente entre páginas classificadas; confiança = menor
    confianca_tipo das páginas classificadas (<= 0.6 se houver alerta); campos = da página
    que os contém; paginas_faltantes pelo "de Y"; paginas_ilegiveis por legivel/qualidade.

    Aceite: bate 100% com o gabarito do lote de demo no modo textlayer.
    """
    raise NotImplementedError("Frente 2: segmentar")
