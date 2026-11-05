"""Destino de cada documento separado. Dono: FRENTE 2.

Separa ERRO OBJETIVO (vai à fornecedora) de INCERTEZA (vai à revisão da Bernhoeft),
como manda a spec 4.1. A fornecedora nunca recebe diagnóstico gerado pela IA.
"""
from __future__ import annotations

from ..contracts import Roteamento, SegmentoDocumento


def rotear(segmento: SegmentoDocumento, trabalhadores_do_contrato: set[str],
           limiar_confianca: float) -> Roteamento:
    """Decide o status do documento.

    PENDENTE_CORRECAO (só tipos de foco): página ilegível ou página faltante.
    REVISAO_HUMANA: tipo DESCONHECIDO; confiança < limiar; alertas de fronteira;
        documento de foco sem trabalhador/competência; trabalhador fora do contrato;
        problema objetivo em documento FORA do foco.
    APTO: o resto.
    Pendência tem precedência sobre revisão.
    """
    raise NotImplementedError("Frente 2: rotear")
