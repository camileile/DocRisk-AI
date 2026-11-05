"""Destino de cada documento separado. Dono: FRENTE 2.

Separa ERRO OBJETIVO (vai à fornecedora) de INCERTEZA (vai à revisão da Bernhoeft),
como manda a spec 4.1. A fornecedora nunca recebe diagnóstico gerado pela IA, e
nada aqui avalia horas extras: suspeita trabalhista não é rejeição documental.
(Arquivo corrompido ou incompatível é recusado antes, em render.ArquivoInvalido.)
"""
from __future__ import annotations

from ..contracts import TIPOS_FOCO, Roteamento, SegmentoDocumento, StatusDocumento, TipoDocumento


def _lista(numeros: list[int]) -> str:
    return ", ".join(str(n) for n in numeros)


def rotear(segmento: SegmentoDocumento, trabalhadores_do_contrato: set[str],
           limiar_confianca: float) -> Roteamento:
    """Decide o status do documento.

    PENDENTE_CORRECAO (só tipos de foco): página ilegível ou página faltante comprovada.
    REVISAO_HUMANA: tipo DESCONHECIDO; confiança < limiar; alertas da segmentação;
        documento de foco sem trabalhador/competência; trabalhador fora do contrato;
        problema objetivo em documento FORA do foco.
    APTO: o resto. Pendência tem precedência sobre revisão.
    """
    foco = segmento.tipo in TIPOS_FOCO
    objetivos: list[str] = []
    if segmento.paginas_ilegiveis:
        objetivos.append(f"Página(s) {_lista(segmento.paginas_ilegiveis)} do lote com legibilidade insuficiente")
    if segmento.paginas_faltantes:
        objetivos.append(
            f"Página(s) {_lista(segmento.paginas_faltantes)} do documento (numeração impressa) não recebida(s)")

    pendencia = list(objetivos) if foco else []
    revisao: list[str] = [] if foco else list(objetivos)

    if segmento.tipo is TipoDocumento.DESCONHECIDO:
        revisao.append("Tipo documental não identificado")
    elif segmento.confianca < limiar_confianca:
        revisao.append(f"Confiança de classificação baixa ({segmento.confianca:.2f} < {limiar_confianca:.2f})")
    revisao.extend(segmento.alertas)

    if foco:
        if not segmento.trabalhador_id:
            revisao.append("Trabalhador não identificado com segurança")
        elif segmento.trabalhador_id not in trabalhadores_do_contrato:
            revisao.append(f"Trabalhador {segmento.trabalhador_id} não cadastrado neste contrato")
        if not segmento.competencia:
            revisao.append("Competência não identificada")

    revisao = list(dict.fromkeys(revisao))  # sem duplicatas, ordem preservada
    if pendencia:
        status = StatusDocumento.PENDENTE_CORRECAO
    elif revisao:
        status = StatusDocumento.REVISAO_HUMANA
    else:
        status = StatusDocumento.APTO
    return Roteamento(status=status, motivos_pendencia=pendencia, motivos_revisao=revisao)
