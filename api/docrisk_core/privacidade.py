"""Anonimização de dados pessoais (LGPD). Dono: FRENTE 3. Módulo puro: sem banco, sem rede.

- mascarar_texto(texto)  -> (texto mascarado, [{"tipo", "inicio", "fim"}])  (offsets do texto ORIGINAL)
- anonimizar_pdf(bytes, paginas=None) -> bytes de um PDF com tarja preta (só as `paginas` 1-based, se
  dadas); o texto sob a tarja é apagado de verdade. Página só de imagem levanta SemCamadaDeTexto.

Mascara: CPF, RG, PIS/NIS, CTPS, data de nascimento (só com rótulo), e-mail, telefone,
agência e conta bancária (só com rótulo).
Não mascara: matrícula (T001), competência (10/2026), horas (08:00), datas de ponto e CNPJ.

Limitações (documentadas de propósito):
- PDF: só funciona com camada de texto. Em imagem escaneada a tarja precisaria das coordenadas
  devolvidas pelo Gemini (próximo passo).
- Tipos "com rótulo" exigem rótulo e valor na MESMA linha de texto ("RG: 12.345.678-9").
- 11 dígitos soltos são tratados como CPF (um telefone sem formatação seria mascarado como CPF).
"""
from __future__ import annotations

import re

import pymupdf as fitz

_E = r"[^\S\n]*"  # espaço sem quebra de linha: o rótulo e o valor ficam na mesma linha
_NUM = rf"(?:n[ºo°.]*)?{_E}[:\-]?{_E}"  # "nº", ":" ou "-" opcionais entre o rótulo e o valor

# (tipo, regex, substituto). Em tipos com rótulo, o grupo 1 é o valor: o rótulo é preservado.
_REGRAS: list[tuple[str, re.Pattern[str], str]] = [(t, re.compile(r, re.I), s) for t, r, s in [
    ("RG", rf"\b(?:RG|registro(?:{_E}geral)?)\b{_E}{_NUM}(\d{{1,2}}\.?\d{{3}}\.?\d{{3}}-?[\dX]?)(?![\w.])", "**.***.***-*"),
    ("PIS_NIS", rf"\b(?:PIS(?:/PASEP)?|NIS){_E}{_NUM}(\d{{3}}\.?\d{{5}}\.?\d{{2}}-?\d)(?!\d)"
                r"|(?<!\d)\d{3}\.\d{5}\.\d{2}-\d(?!\d)", "[PIS/NIS]"),
    ("CTPS", rf"\bCTPS\b{_E}{_NUM}(\d{{4,8}}(?:{_E}(?:/|s[ée]rie){_E}[:\-]?{_E}\d{{3,5}})?)", "[CTPS]"),
    ("DATA_NASCIMENTO", rf"\b(?:data{_E}de{_E}nascimento|nascimento|nasc\.?|DN){_E}[:\-]?{_E}(\d{{2}}/\d{{2}}/\d{{4}})",
     "[DATA NASC.]"),
    ("EMAIL", r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "[E-MAIL]"),
    ("TELEFONE", r"(?<!\d)(?:\+55[\s-]?)?(?:\(\d{2}\)[^\S\n]?|\d{2}[^\S\n])9?\d{4}-?\d{4}(?!\d)", "[TELEFONE]"),
    ("AGENCIA", rf"\bag(?:[êe]ncia|\.){_E}{_NUM}(\d{{1,6}}(?:-[\dX])?)(?![\w])", "[AGÊNCIA]"),
    ("CONTA", rf"(?:\bconta(?:{_E}(?:corrente|poupan[çc]a))?|\bc/c){_E}{_NUM}(\d{{1,12}}(?:-[\dX])?)(?![\w])",
     "[CONTA]"),
    # CPF por último: num empate (11 dígitos depois de "NIS"), o tipo com rótulo vence.
    ("CPF", r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)|(?<!\d)\d{11}(?!\d)", "***.***.***-**"),
]]


def _detectar(texto: str) -> list[tuple[str, int, int, str]]:
    """Achados (tipo, inicio, fim, substituto) sem sobreposição; só o valor, nunca o rótulo."""
    achados = []
    for tipo, rx, subst in _REGRAS:
        for m in rx.finditer(texto):
            g = 1 if rx.groups and m.group(1) else 0
            achados.append((tipo, m.start(g), m.end(g), subst))
    achados.sort(key=lambda a: (a[1], a[1] - a[2]))
    final: list[tuple[str, int, int, str]] = []
    for a in achados:
        if not final or a[1] >= final[-1][2]:
            final.append(a)
    return final


def mascarar_texto(texto: str) -> tuple[str, list[dict]]:
    """Texto mascarado + o que foi mascarado, sem o valor original: [{"tipo", "inicio", "fim"}]."""
    achados = _detectar(texto)
    saida, pos = [], 0
    for _, ini, fim, subst in achados:
        saida += [texto[pos:ini], subst]
        pos = fim
    saida.append(texto[pos:])
    return "".join(saida), [{"tipo": t, "inicio": i, "fim": f} for t, i, f, _ in achados]


class SemCamadaDeTexto(ValueError):
    """Página só de imagem: a tarja não teria onde achar o dado, então não devolvemos PDF "anonimizado"."""


def anonimizar_pdf(data: bytes, paginas: list[int] | None = None) -> bytes:
    """PDF com tarja preta sobre cada trecho sensível; apply_redactions apaga o texto de verdade.

    `paginas` (1-based) devolve só essas páginas, na ordem dada. Página com imagem e sem texto
    levanta SemCamadaDeTexto. Imagem dentro de página que também tem texto NÃO é coberta
    (shortcut: dado pessoal dentro de imagem exige as coordenadas do Gemini).
    """
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        if paginas is not None:
            doc.select([n - 1 for n in paginas])
        for page in doc:
            texto = page.get_text()
            if not texto.strip() and page.get_images():
                raise SemCamadaDeTexto(f"página {page.number + 1} é só imagem")
            valores = {texto[i:f] for _, i, f, _ in _detectar(texto)}
            for valor in valores:
                for rect in page.search_for(valor):
                    page.add_redact_annot(rect, fill=(0, 0, 0))
            page.apply_redactions()
        doc.set_metadata({})
        return doc.tobytes(garbage=4, deflate=True)
    finally:
        doc.close()