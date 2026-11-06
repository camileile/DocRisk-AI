"""Páginas -> documentos (fronteiras e agrupamento multipágina). Dono: FRENTE 2.

Substitui documents.group_pages do sprint01. Bugs do sprint01 corrigidos aqui
(cada um tem teste de regressão em tests/test_f2_segmentation.py):

1. needs_review forçado em todo grupo (documents.py, linha 100): aqui só vai à
   revisão o que tem motivo registrado em `alertas`.
2. "Página X de Y" só procurado nos primeiros 450 caracteres (linha 80): a
   numeração vem de AnalisePagina.pagina_x/pagina_de, extraída do texto inteiro.
3. Página sem tipo nunca abria documento novo (linhas 90-91), grudando anotações
   soltas no documento anterior: aqui vira grupo próprio com alerta.
4. Troca de trabalhador/competência ignorada numa página de continuação: aqui
   trabalhador, competência ou tipo divergentes abrem documento novo.

Função pura: sem banco, sem rede, sem alterar a entrada; mesma entrada -> mesma saída.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Any

from .. import config
from ..contracts import AnalisePagina, CamposPagina, SegmentoDocumento, TipoDocumento

_DESC = TipoDocumento.DESCONHECIDO
_CAMPOS = ("horas_extras_h", "horas_extras_valor", "valor_liquido", "valor_pago", "data_pagamento")


def _tipo(membros: Sequence[AnalisePagina]) -> TipoDocumento:
    conhecidos = [a.tipo for a in membros if a.tipo is not _DESC]
    return Counter(conhecidos).most_common(1)[0][0] if conhecidos else _DESC


def _distintos(valores: list[Any]) -> list[Any]:
    vistos: list[Any] = []
    for v in valores:
        if v is not None and v not in vistos:
            vistos.append(v)
    return vistos


def _unico(membros: Sequence[AnalisePagina], attr: str) -> Any:
    valores = _distintos([getattr(a, attr) for a in membros])
    return valores[0] if len(valores) == 1 else None


def _decidir(membros: Sequence[AnalisePagina], a: AnalisePagina, ordem: int) -> tuple[bool, str | None]:
    """(abre documento novo?, alerta). Só olha o grupo atual e a página nova."""
    ult = membros[-1]
    tipo_g = _tipo(membros)
    trab_g = _unico(membros, "trabalhador_id")
    comp_g = _unico(membros, "competencia")

    conflitos = []
    if a.trabalhador_id and trab_g and a.trabalhador_id != trab_g:
        conflitos.append("trabalhador")
    if a.competencia and comp_g and a.competencia != comp_g:
        conflitos.append("competência")
    if a.tipo is not _DESC and tipo_g is not _DESC and a.tipo is not tipo_g:
        conflitos.append("tipo")

    if a.pagina_x == 1:
        return True, None

    if a.pagina_x and a.pagina_x > 1:
        totais = _distintos([m.pagina_de for m in membros])
        if a.pagina_de and totais and a.pagina_de not in totais:
            conflitos.append("total de páginas")
        if ult.pagina_x and a.pagina_x <= ult.pagina_x:
            conflitos.append("ordem da numeração")
        if conflitos:
            return True, (f"Página {ordem}: numeração indica continuação, mas "
                          f"{', '.join(conflitos)} não confere com o documento anterior")
        return False, None  # lacunas (1 -> 3) são apuradas no resumo como página faltante

    # Página sem numeração.
    if conflitos or a.inicio_documento:
        return True, None
    anterior_completo = bool(ult.pagina_x and ult.pagina_de and ult.pagina_x >= ult.pagina_de)
    if a.tipo is _DESC or anterior_completo:
        return True, f"Página {ordem}: fronteira incerta (sem numeração, sem título e sem vínculo seguro)"
    if a.trabalhador_id and a.trabalhador_id == trab_g:
        return False, None  # mesmo tipo e mesmo trabalhador explícito: continuação segura
    return False, f"Página {ordem}: continuação inferida sem numeração nem identificação"


def _resumir(membros: list[AnalisePagina], ordens: list[int], alertas: list[str],
             limiar_legibilidade: float) -> SegmentoDocumento:
    alertas = list(alertas)
    tipo = _tipo(membros)

    trabs = _distintos([a.trabalhador_id for a in membros])
    comps = _distintos([a.competencia for a in membros])
    if len(trabs) > 1:
        alertas.append(f"Trabalhadores diferentes no mesmo documento: {', '.join(trabs)}")
    if len(comps) > 1:
        alertas.append(f"Competências diferentes no mesmo documento: {', '.join(comps)}")

    campos: dict[str, Any] = {}
    for campo in _CAMPOS:
        valores = _distintos([getattr(a.campos, campo) for a in membros])
        if len(valores) == 1:
            campos[campo] = valores[0]
        elif len(valores) > 1:
            alertas.append(f"Valores divergentes para {campo} entre as páginas {ordens[0]}–{ordens[-1]}")

    faltantes: list[int] = []
    totais = _distintos([a.pagina_de for a in membros])
    numeradas = [a.pagina_x for a in membros if a.pagina_x]
    if len(totais) > 1:
        alertas.append(f"Totais de páginas divergentes ({', '.join(map(str, totais))})")
    if totais:
        total = max(totais)
        if len(numeradas) == len(membros):
            faltantes = sorted(set(range(1, total + 1)) - set(numeradas))
        elif len(membros) < total:
            alertas.append(f"Documento indica {total} páginas e {len(membros)} foram recebidas; "
                           "a numeração incompleta impede confirmar quais faltam")
    if len(set(numeradas)) != len(numeradas):
        alertas.append("Numeração de página repetida no mesmo documento")

    confs = [a.confianca_tipo for a in membros if a.tipo is not _DESC]
    confianca = min(confs) if confs else 0.0
    if tipo is _DESC:
        confianca = min(confianca, 0.3)
    if alertas:
        confianca = min(confianca, 0.6)

    ilegiveis = [o for a, o in zip(membros, ordens) if not a.legivel or a.qualidade < limiar_legibilidade]

    return SegmentoDocumento(
        paginas=list(ordens),
        tipo=tipo,
        trabalhador_id=trabs[0] if len(trabs) == 1 else None,
        competencia=comps[0] if len(comps) == 1 else None,
        confianca=round(confianca, 4),
        campos=CamposPagina(**campos),
        paginas_ilegiveis=ilegiveis,
        paginas_faltantes=faltantes,
        alertas=alertas,
    )


def resumir_paginas(analises: list[AnalisePagina], ordens: list[int], alertas: list[str] | None = None,
                    limiar_legibilidade: float | None = None) -> SegmentoDocumento:
    """Resume páginas JÁ AGRUPADAS (ex.: por decisão humana na revisão) num documento,
    com as mesmas regras de tipo, campos, faltantes e ilegíveis da segmentação."""
    if not analises or len(analises) != len(ordens):
        raise ValueError("Informe ao menos uma página e uma ordem por página.")
    limiar = config.LIMIAR_LEGIBILIDADE if limiar_legibilidade is None else limiar_legibilidade
    return _resumir(list(analises), list(ordens), list(alertas or []), limiar)


def segmentar(analises: list[AnalisePagina], ordens: list[int] | None = None,
              limiar_legibilidade: float | None = None) -> list[SegmentoDocumento]:
    """Agrupa páginas consecutivas em documentos.

    `ordens[i]` = número da página i no lote (padrão: 1..N). Lista vazia -> [].

    Abre documento novo quando:
    - pagina_x == 1, ou inicio_documento sem numeração de continuação;
    - trabalhador, competência ou tipo (ambos conhecidos) mudam em relação ao grupo;
    - página DESCONHECIDA sem numeração (grupo próprio + alerta "fronteira incerta").
    Mantém no mesmo documento quando pagina_x > 1 sem conflito, ou mesmo tipo e
    mesmo trabalhador explícito sem numeração.

    Por documento: tipo = mais frequente entre páginas classificadas; confiança = menor
    confianca_tipo das páginas classificadas (<= 0.6 com alerta, <= 0.3 se DESCONHECIDO);
    campos = valor único entre as páginas (divergência vira alerta, nunca escolha);
    paginas_faltantes pela numeração impressa; paginas_ilegiveis por legivel/qualidade.
    """
    if ordens is None:
        ordens = list(range(1, len(analises) + 1))
    if len(ordens) != len(analises):
        raise ValueError("`ordens` precisa ter o mesmo tamanho de `analises`.")
    limiar = config.LIMIAR_LEGIBILIDADE if limiar_legibilidade is None else limiar_legibilidade

    grupos: list[tuple[list[int], list[str]]] = []
    for i, analise in enumerate(analises):
        if not grupos:
            grupos.append(([i], []))
            continue
        indices, alertas = grupos[-1]
        novo, alerta = _decidir([analises[j] for j in indices], analise, ordens[i])
        if novo:
            grupos.append(([i], [alerta] if alerta else []))
        else:
            indices.append(i)
            if alerta:
                alertas.append(alerta)

    return [
        _resumir([analises[j] for j in indices], [ordens[j] for j in indices], alertas, limiar)
        for indices, alertas in grupos
    ]
