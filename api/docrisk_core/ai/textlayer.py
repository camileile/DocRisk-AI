"""Leitor offline: regras sobre o TEXTO DIGITAL do PDF. Dono: FRENTE 2.

Serve para testes automáticos (determinístico, sem internet) e como plano B da demo.
Não é OCR e não deve ser apresentado como IA. As mesmas regras são reaproveitadas
pelo TesseractProvider sobre o texto do OCR (`analisar_texto`).

- tipo pelo título nos primeiros ~300 caracteres (evita falsos positivos no corpo)
- "Página X de Y" procurado no texto INTEIRO (numeração costuma estar no rodapé)
- matrícula, competência e horas extras por expressão regular — só com unidade explícita
- página de foco com título mas sem os marcadores do corpo -> legivel=False
"""
from __future__ import annotations

import re
import unicodedata

from ..contracts import AnalisePagina, CamposPagina, TIPOS_FOCO, TipoDocumento, normalizar_duracao, numero_br

JANELA_TITULO = 300
VERSAO_REGRAS = "regras-v1"

_F = re.IGNORECASE


def _sem_acento(texto: str) -> str:
    """Remove acentos preservando o comprimento (posições continuam válidas)."""
    return "".join(
        unicodedata.normalize("NFKD", c)[0] if unicodedata.normalize("NFKD", c) else c
        for c in texto
    )


# Padrões aplicados ao texto SEM acento, em minúsculas.
TITULOS: list[tuple[TipoDocumento, re.Pattern[str]]] = [
    (TipoDocumento.ESPELHO_PONTO, re.compile(
        r"\b(espelho\s+de\s+ponto|registro\s+de\s+ponto|cartao\s+de\s+ponto|folha\s+de\s+ponto|"
        r"controle\s+de\s+jornada)\b", _F)),
    (TipoDocumento.COMPROVANTE_PAGAMENTO, re.compile(
        r"\bcomprovante\s+de\s+(pagamento|transferencia|deposito|pix)\b", _F)),
    (TipoDocumento.HOLERITE, re.compile(
        r"\b(demonstrativo\s+de\s+pagamento|holerite|contracheque|contra-cheque|"
        r"recibo\s+de\s+pagamento\s+de\s+salario|folha\s+de\s+pagamento)\b", _F)),
    (TipoDocumento.CONTRATO, re.compile(r"\bcontrato\s+de\s+(prestacao|trabalho)\b", _F)),
    (TipoDocumento.DOCUMENTO_IDENTIFICACAO, re.compile(
        r"\b(carteira\s+de\s+identidade|documento\s+de\s+identificacao|registro\s+geral|"
        r"carteira\s+nacional\s+de\s+habilitacao)\b", _F)),
    (TipoDocumento.NOTA_FISCAL, re.compile(r"\bnota\s+fiscal\b", _F)),
]

#: Marcadores que precisam aparecer no CORPO (fora do título) para a página ser considerada legível.
MARCADORES_CORPO: dict[TipoDocumento, re.Pattern[str]] = {
    TipoDocumento.ESPELHO_PONTO: re.compile(
        r"\b(entrada|saida|jornada|marcac|total\s+de\s+horas|batida)", _F),
    TipoDocumento.HOLERITE: re.compile(
        r"\b(proventos|descontos|vencimentos|salario\s+base|liquido)", _F),
    TipoDocumento.COMPROVANTE_PAGAMENTO: re.compile(
        r"\b(valor|favorecido|beneficiario|data\s+do\s+pagamento|autenticacao)", _F),
}

_NUM = r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:[.,]\d+)?)"
_DINHEIRO = r"R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})"
PAGINACAO = re.compile(r"\bp(?:agina|ag\.?|g\.?)\s*(\d{1,3})\s*(?:de|/)\s*(\d{1,3})\b", _F)
MATRICULA = re.compile(r"\bmatricula\s*(?:n[oº°.]*)?\s*[:\-]?\s*([a-z]{0,3}\s?\d{1,10})\b", _F)
COMPETENCIA = re.compile(r"\bcompetencia\s*[:\-]?\s*(\d{1,2}\s*/\s*\d{4})", _F)
NOME = re.compile(
    r"\b(?:trabalhador|funcionario|colaborador|empregado|favorecido|nome)\s*:\s*"
    r"([^\n|:]+?)(?=\s{2,}|\s+matricula\b|\s*\||\n|$)", _F)
HE_TOTAL_PONTO = re.compile(
    r"\btotal\s+(?:de\s+)?(?:horas\s+extras?|h\.?\s*e\.?)\s*[:\-]?\s*"
    r"((?:\d{1,3}\s*h\s*\d{1,2}(?:\s*m(?:in(?:utos?)?)?)?|\d{1,3}\s*h|"
    r"\d{1,3}:\d{2}|" + _NUM + r"\s*h))\b", _F)
HE_REF_FOLHA = re.compile(
    r"\bhoras?\s+extras?[^\n]*?\bref(?:erencia)?\.?\s*[:\-]?\s*"
    r"((?:\d{1,3}\s*h\s*\d{1,2}(?:\s*m(?:in(?:utos?)?)?)?|\d{1,3}\s*h|"
    r"\d{1,3}:\d{2}|" + _NUM + r"\s*h))\b", _F)
HE_HORAS_FOLHA = re.compile(
    r"\bhoras?\s+extras?[^\n%]*?\b((?:\d{1,3}\s*h\s*\d{1,2}(?:\s*m(?:in(?:utos?)?)?)?|"
    r"\d{1,3}\s*h|\d{1,3}:\d{2}|" + _NUM + r"\s*h))\b", _F)
HE_VALOR = re.compile(r"\bhoras?\s+extras?[^\n]*?R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})", _F)
LIQUIDO = re.compile(r"\bliquido(?:\s+a\s+receber)?\s*[:\-]?\s*" + _DINHEIRO, _F)
VALOR_PAGO = re.compile(
    r"\bvalor\s+(?:pago|transferido|da\s+transferencia|do\s+pagamento)\s*[:\-]?\s*" + _DINHEIRO, _F)
DATA_PAGAMENTO = re.compile(r"\bdata\s+(?:do\s+|de\s+)?pagamento\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})", _F)


def _horas(valor: str | None) -> float | None:
    if not valor:
        return None
    return normalizar_duracao(valor)


def _titulo(norm: str) -> tuple[TipoDocumento, tuple[int, int] | None]:
    janela = norm[:JANELA_TITULO]
    achados = [(m.start(), tipo, m.span()) for tipo, padrao in TITULOS if (m := padrao.search(janela))]
    if not achados:
        return TipoDocumento.DESCONHECIDO, None
    _, tipo, span = min(achados, key=lambda a: a[0])  # o título que aparece primeiro
    return tipo, span


def _ultimo(padrao: re.Pattern[str], texto: str) -> re.Match[str] | None:
    achado = None
    for achado in padrao.finditer(texto):
        pass
    return achado


def analisar_texto(texto: str, origem: str = "TEXTO_PDF") -> AnalisePagina:
    """Regras determinísticas sobre um texto de página. Nunca usa gabarito."""
    texto = texto or ""
    norm = _sem_acento(texto)
    significativo = re.sub(r"\s+", "", texto)

    tipo, span = _titulo(norm)
    pag = _ultimo(PAGINACAO, norm)  # rodapé: a última ocorrência
    pagina_x = int(pag.group(1)) if pag else None
    pagina_de = int(pag.group(2)) if pag else None

    matricula = MATRICULA.search(norm)
    competencia = COMPETENCIA.search(norm)
    nome = NOME.search(texto) or None
    nome_txt = nome.group(1).strip() if nome else None

    # Legibilidade: texto vazio/ínfimo = ilegível; foco com título e sem corpo = ilegível.
    if len(significativo) < 20:
        legivel, qualidade = False, 0.0 if not significativo else 0.1
    else:
        legivel, qualidade = True, 0.9
        if tipo in MARCADORES_CORPO:
            corpo = norm[:span[0]] + norm[span[1]:] if span else norm
            if not MARCADORES_CORPO[tipo].search(corpo):
                legivel, qualidade = False, 0.2

    campos = CamposPagina()
    avisos_validacao: list[str] = []
    if tipo is TipoDocumento.ESPELHO_PONTO or (tipo is TipoDocumento.DESCONHECIDO and pagina_x and pagina_x > 1):
        m = _ultimo(HE_TOTAL_PONTO, norm)
        if m:
            try:
                campos.horas_extras_h = _horas(m.group(1))
            except ValueError as exc:
                avisos_validacao.append(f"Campo horas_extras_h: {exc}; conferência humana necessária.")
    if tipo is TipoDocumento.HOLERITE:
        m = HE_REF_FOLHA.search(norm) or HE_HORAS_FOLHA.search(norm)
        if m:
            try:
                campos.horas_extras_h = _horas(m.group(1))
            except ValueError as exc:
                avisos_validacao.append(f"Campo horas_extras_h: {exc}; conferência humana necessária.")
        v = HE_VALOR.search(norm)
        if v:
            campos.horas_extras_valor = numero_br(v.group(1))
        liq = LIQUIDO.search(norm)
        if liq:
            campos.valor_liquido = numero_br(liq.group(1))
    if tipo is TipoDocumento.COMPROVANTE_PAGAMENTO:
        vp = VALOR_PAGO.search(norm)
        if vp:
            campos.valor_pago = numero_br(vp.group(1))
        dp = DATA_PAGAMENTO.search(norm)
        if dp:
            campos.data_pagamento = dp.group(1)

    if tipo is TipoDocumento.DESCONHECIDO:
        confianca = 0.0 if not significativo else 0.3
    else:
        confianca = 0.9 if legivel else 0.6

    return AnalisePagina.model_validate({
        "texto": texto,
        "tipo": tipo,
        "inicio_documento": span is not None or pagina_x == 1,
        "pagina_x": pagina_x,
        "pagina_de": pagina_de,
        "trabalhador_id": matricula.group(1) if matricula else None,
        "trabalhador_nome": nome_txt,
        "competencia": competencia.group(1) if competencia else None,
        "legivel": legivel,
        "qualidade": qualidade,
        "confianca_tipo": confianca,
        "campos": campos.model_dump(),
        "avisos_validacao": avisos_validacao,
        "origem": origem,
    })


class TextLayerProvider:
    nome = "textlayer"
    modelo = VERSAO_REGRAS

    def analisar(self, png: bytes, texto_camada: str | None) -> AnalisePagina:
        return analisar_texto(texto_camada or "", origem="TEXTO_PDF")


__all__ = ["TextLayerProvider", "analisar_texto", "TIPOS_FOCO"]
