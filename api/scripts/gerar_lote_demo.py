"""Gera o lote SINTÉTICO de demonstração + gabarito. Dono: FRENTE 3.

Uso: python scripts/gerar_lote_demo.py [pasta_saida]   (padrão: scripts/lote_demo)

Saídas:
- lote_demo.pdf              16 páginas, 14 documentos, competência 10/2026
- reenvio_holerite_T002.pdf  holerite legível do T002 (6 h extras)
- arquivo_corrompido.pdf     para o teste de recusa
- gabarito.json              fronteiras, tipos, trabalhador, competência, campos e
                             resultado esperado da conciliação por trabalhador

Cenários (todos com o aviso "DOCUMENTO FICTÍCIO" no rodapé):
| Páginas | Documento                                  | Esperado                          |
| 1-2     | Contrato de prestação (2 págs)             | organizado, sem análise           |
| 3-4     | Espelho de ponto T001, 12 h extras (2 págs)| —                                 |
| 5       | Holerite T001, 8 h extras                  | T001: divergência de 4 h a conferir |
| 6       | Espelho de ponto T002, 6 h                 | —                                 |
| 7       | Holerite T002 com corpo ilegível           | pendência à fornecedora; T002 bloqueado |
| 8       | Comprovante de pagamento T001              | evidência presente                |
| 9       | Espelho de ponto T003 "Página 1 de 2" só   | página faltante; T003 bloqueado   |
| 10      | Holerite T003, 2 h                         | —                                 |
| 11      | Documento de identidade FICTÍCIO           | organizado                        |
| 12      | Espelho de ponto T004, 10 h                | —                                 |
| 13      | Holerite T004 com horas extras só em R$    | T004: dados insuficientes         |
| 14      | Anotação solta sem título                  | desconhecido -> revisão humana    |
| 15-16   | Ponto e holerite T005, 4 h e 4 h           | T005: sem divergência             |

"Página X de Y" no RODAPÉ (como em documento real). O corpo do holerite ilegível do
T002 é uma IMAGEM borrada (ilegível para a IA visual e sem texto digital para o
leitor offline). A base de 100 trabalhadores (spec seção 10) vem depois, com o
mesmo gerador parametrizado.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFilter

COMPETENCIA = "10/2026"
LARGURA, ALTURA = 595, 842
AVISO = "DOCUMENTO FICTÍCIO — dados sintéticos para demonstração (Hack Garanhuns Tech 2026)"
EMPRESA = "Fornecedora Beta Serviços (fictícia) — CNPJ 00.000.000/0001-00 (fictício)"
NOMES = {"T001": "Ana Fictícia Souza", "T002": "Bruno Fictício Lima", "T003": "Carla Fictícia Rocha",
         "T004": "Diego Fictício Alves", "T005": "Elisa Fictícia Melo"}
# CPF/RG FICTÍCIOS (inválidos de propósito) só para exercitar a anonimização; ficam no cabeçalho do
# holerite, em campo que a classificação e as regras não leem.
CPFS = {t: f"000.000.00{i}-00" for i, t in enumerate(NOMES, 1)}
RGS = {t: f"00.000.00{i}-0" for i, t in enumerate(NOMES, 1)}


# ---------------------------------------------------------------------------
# Desenho das páginas
# ---------------------------------------------------------------------------
class Pagina:
    def __init__(self, doc: fitz.Document) -> None:
        self.p = doc.new_page(width=LARGURA, height=ALTURA)
        self.y = 60.0

    def titulo(self, texto: str) -> "Pagina":
        self.p.draw_rect(fitz.Rect(40, 40, LARGURA - 40, 72), color=(0.1, 0.25, 0.45), fill=(0.1, 0.25, 0.45))
        self.p.insert_text((50, 61), texto, fontsize=13, fontname="hebo", color=(1, 1, 1))
        self.y = 92
        return self

    def linha(self, texto: str = "", tamanho: float = 10, negrito: bool = False) -> "Pagina":
        self.p.insert_text((50, self.y), texto, fontsize=tamanho, fontname="hebo" if negrito else "helv")
        self.y += tamanho + 6
        return self

    def tabela(self, linhas: list[tuple[str, ...]], larguras: list[int]) -> "Pagina":
        for i, cols in enumerate(linhas):
            x = 50
            for col, w in zip(cols, larguras):
                self.p.insert_text((x, self.y), col, fontsize=9.5, fontname="hebo" if i == 0 else "helv")
                x += w
            self.y += 15
        self.y += 6
        return self

    def imagem(self, png: bytes, altura: float) -> "Pagina":
        self.p.insert_image(fitz.Rect(50, self.y, LARGURA - 50, self.y + altura), stream=png)
        self.y += altura + 10
        return self

    def rodape(self, pagina: str | None = None) -> None:
        self.p.draw_line((40, ALTURA - 60), (LARGURA - 40, ALTURA - 60), color=(0.6, 0.6, 0.6))
        self.p.insert_text((50, ALTURA - 44), AVISO, fontsize=7.5, color=(0.4, 0.4, 0.4))
        if pagina:
            self.p.insert_text((LARGURA - 120, ALTURA - 30), pagina, fontsize=9)


def _cabecalho(pg: Pagina, trabalhador: str) -> Pagina:
    return (pg.linha(EMPRESA, 9)
              .linha(f"Trabalhador: {NOMES[trabalhador]}    Matrícula: {trabalhador}", 10)
              .linha(f"Competência: {COMPETENCIA}", 10).linha())


def _dias_ponto(inicio: int, fim: int, extra_por_dia: dict[int, int]) -> list[tuple[str, ...]]:
    linhas = [("Data", "Entrada", "Saída almoço", "Retorno", "Saída", "Extras")]
    for dia in range(inicio, fim + 1):
        extra = extra_por_dia.get(dia, 0)
        saida = f"{17 + extra:02d}:00"
        linhas.append((f"{dia:02d}/10/2026", "08:00", "12:00", "13:00", saida, f"{extra:02d}:00" if extra else "-"))
    return linhas


def _extras(total: int, dias: range) -> dict[int, int]:
    """Distribui `total` horas extras (inteiras) nos primeiros dias úteis do intervalo."""
    resultado, restante = {}, total
    for dia in dias:
        if restante <= 0:
            break
        h = min(2, restante)
        resultado[dia] = h
        restante -= h
    return resultado


def ponto(doc: fitz.Document, t: str, horas: int, paginas: int = 1, so_primeira: bool = False) -> None:
    extras = _extras(horas, range(1, 23))
    if paginas == 1:
        pg = _cabecalho(Pagina(doc).titulo("ESPELHO DE PONTO"), t)
        pg.tabela(_dias_ponto(1, 22, extras), [80, 70, 90, 70, 70, 60])
        pg.linha(f"TOTAL DE HORAS EXTRAS: {horas:02d},00 h", 11, negrito=True)
        pg.linha("Jornada contratual: 44 h semanais. Marcações eletrônicas.", 9)
        pg.rodape("Página 1 de 1")
        return
    pg = _cabecalho(Pagina(doc).titulo("ESPELHO DE PONTO"), t)
    pg.tabela(_dias_ponto(1, 15, extras), [80, 70, 90, 70, 70, 60])
    pg.linha("Continua na próxima página.", 9)
    pg.rodape(f"Página 1 de {paginas}")
    if so_primeira:
        return
    pg = Pagina(doc).linha(f"Espelho de ponto — Matrícula: {t} — Competência: {COMPETENCIA}", 10, negrito=True).linha()
    pg.tabela(_dias_ponto(16, 31, extras), [80, 70, 90, 70, 70, 60])
    pg.linha(f"TOTAL DE HORAS EXTRAS: {horas:02d},00 h", 11, negrito=True)
    pg.linha("Assinatura do trabalhador: ____________________", 9)
    pg.rodape(f"Página 2 de {paginas}")


def _corpo_holerite(horas: int | None, valor_he: str, base: str, liquido: str) -> list[tuple[str, ...]]:
    ref = f"Ref.: {horas:02d},00 h" if horas is not None else ""
    return [
        ("Código", "Descrição", "Referência", "Proventos", "Descontos"),
        ("001", "Salário base", "30 dias", f"R$ {base}", ""),
        ("050", "Horas extras 50%", ref, f"R$ {valor_he}", ""),
        ("901", "INSS", "", "", "R$ 160,00"),
        ("", "", "", "", ""),
    ]


def holerite(doc: fitz.Document, t: str, horas: int | None, valor_he: str, liquido: str,
             ilegivel: bool = False, base: str = "1.800,00") -> None:
    pg = _cabecalho(Pagina(doc).titulo("DEMONSTRATIVO DE PAGAMENTO DE SALÁRIO"), t)
    pg.linha(f"CPF: {CPFS[t]}    RG: {RGS[t]}", 9)
    linhas = _corpo_holerite(horas, valor_he, base, liquido)
    if ilegivel:
        pg.imagem(_corpo_borrado(linhas + [("", "Líquido a receber", "", f"R$ {liquido}", "")]), 220)
        pg.rodape("Página 1 de 1")
        return
    pg.tabela(linhas, [60, 150, 90, 100, 90])
    if horas is not None:
        pg.linha(f"Horas extras 50% — Ref.: {horas:02d},00 h — R$ {valor_he}", 9)
    else:
        pg.linha(f"Horas extras 50% — R$ {valor_he}", 9)
    pg.linha(f"Líquido a receber: R$ {liquido}", 11, negrito=True)
    pg.rodape("Página 1 de 1")


def _corpo_borrado(linhas: list[tuple[str, ...]]) -> bytes:
    """Tabela renderizada em baixa resolução e borrada: o conteúdo existe, mas não se lê."""
    img = Image.new("L", (240, 90), 255)
    d = ImageDraw.Draw(img)
    for i, cols in enumerate(linhas):
        d.text((4, 4 + i * 13), "  ".join(c for c in cols if c), fill=40)
    img = img.filter(ImageFilter.GaussianBlur(3.2)).resize((960, 360), Image.Resampling.BILINEAR)
    img = img.filter(ImageFilter.GaussianBlur(6))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def comprovante(doc: fitz.Document, t: str, valor: str, data: str) -> None:
    pg = Pagina(doc).titulo("COMPROVANTE DE PAGAMENTO")
    pg.linha("Banco Fictício S.A. — transferência eletrônica", 9).linha()
    pg.linha(f"Favorecido: {NOMES[t]}    Matrícula: {t}", 10)
    pg.linha(f"Competência: {COMPETENCIA}", 10)
    pg.linha(f"Valor pago: R$ {valor}", 11, negrito=True)
    pg.linha(f"Data do pagamento: {data}", 10)
    pg.linha("Autenticação: 0000.FICT.1234.5678", 9)
    pg.rodape("Página 1 de 1")


def contrato(doc: fitz.Document) -> None:
    pg = Pagina(doc).titulo("CONTRATO DE PRESTAÇÃO DE SERVIÇOS Nº 001/2026")
    pg.linha("Contratante: Contratante Alfa S.A. (fictícia)", 10)
    pg.linha("Contratada: Fornecedora Beta Serviços (fictícia)", 10).linha()
    for c in ("Cláusula 1 — Objeto: serviços de limpeza e conservação.",
              "Cláusula 2 — Vigência: 12 meses a partir de 01/01/2026.",
              "Cláusula 3 — A contratada enviará mensalmente ponto, holerite e comprovantes.",
              "Cláusula 4 — Prazo de correção documental: 3 dias úteis."):
        pg.linha(c, 10)
    pg.rodape("Página 1 de 2")
    pg = Pagina(doc).linha("Cláusula 5 — Confidencialidade dos dados dos trabalhadores.", 10)
    pg.linha("Cláusula 9 — Foro da comarca de Garanhuns/PE.", 10).linha()
    pg.linha("Assinaturas das partes: ____________________   ____________________", 10)
    pg.rodape("Página 2 de 2")


def identidade(doc: fitz.Document) -> None:
    pg = Pagina(doc).titulo("DOCUMENTO DE IDENTIFICAÇÃO (FICTÍCIO)")
    pg.linha("Nome: Elisa Fictícia Melo", 10).linha("Registro: 00.000.000-0 (fictício)", 10)
    pg.linha("Data de nascimento: 01/01/1990", 10).linha("Órgão emissor: SSP-XX (fictício)", 10)
    pg.rodape("Página 1 de 1")


def anotacao(doc: fitz.Document) -> None:
    pg = Pagina(doc)
    pg.y = 120
    pg.linha("anotações — conferir com o RH", 12)
    pg.linha("ligar para o setor pessoal sobre o lote de outubro", 12)
    pg.linha("ver escala da equipe da noite", 12)
    pg.rodape()


# ---------------------------------------------------------------------------
# Gabarito
# ---------------------------------------------------------------------------
def _doc(paginas, tipo, trabalhador=None, status="APTO", horas=None, horas_valor=False, obs=""):
    return {"paginas": paginas, "tipo": tipo, "trabalhador_id": trabalhador,
            "competencia": COMPETENCIA if trabalhador else None, "status_esperado": status,
            "horas_extras_h": horas, "horas_extras_so_em_reais": horas_valor, "observacao": obs}


GABARITO = {
    "competencia": COMPETENCIA,
    "contrato": "CT-001",
    "paginas": 16,
    "documentos": [
        _doc([1, 2], "CONTRATO"),
        _doc([3, 4], "ESPELHO_PONTO", "T001", horas=12),
        _doc([5], "HOLERITE", "T001", horas=8),
        _doc([6], "ESPELHO_PONTO", "T002", horas=6),
        _doc([7], "HOLERITE", "T002", "PENDENTE_CORRECAO", obs="corpo ilegível -> pendência ILEGIVEL"),
        _doc([8], "COMPROVANTE_PAGAMENTO", "T001"),
        _doc([9], "ESPELHO_PONTO", "T003", "PENDENTE_CORRECAO", obs="página 2 de 2 faltante"),
        _doc([10], "HOLERITE", "T003", horas=2),
        _doc([11], "DOCUMENTO_IDENTIFICACAO"),
        _doc([12], "ESPELHO_PONTO", "T004", horas=10),
        _doc([13], "HOLERITE", "T004", horas_valor=True),
        _doc([14], "DESCONHECIDO", status="REVISAO_HUMANA", obs="anotação solta"),
        _doc([15], "ESPELHO_PONTO", "T005", horas=4),
        _doc([16], "HOLERITE", "T005", horas=4),
    ],
    "conciliacao": {
        "T001": {"status": "ANALISADA", "resultado": "DIVERGENCIA_A_VERIFICAR", "diferenca_h": 4},
        "T002": {"status": "BLOQUEADA_PENDENCIA", "resultado": "NAO_AVALIADO"},
        "T003": {"status": "BLOQUEADA_PENDENCIA", "resultado": "NAO_AVALIADO"},
        "T004": {"status": "ANALISADA", "resultado": "DADOS_INSUFICIENTES"},
        "T005": {"status": "ANALISADA", "resultado": "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS", "diferenca_h": 0},
    },
    "apos_reenvio_T002": {
        "T002": {"status": "ANALISADA", "resultado": "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS", "diferenca_h": 0},
        "pendencia_holerite_T002": "RESOLVIDA",
        "versao_holerite_T002": 2,
    },
}


def gerar(saida: Path) -> dict[str, Path]:
    """Cria os arquivos acima em `saida` e devolve {nome: caminho}."""
    saida.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    contrato(doc)                                                     # 1-2
    ponto(doc, "T001", 12, paginas=2)                                 # 3-4
    holerite(doc, "T001", 8, "160,00", "1.800,00")                    # 5
    ponto(doc, "T002", 6)                                             # 6
    holerite(doc, "T002", 6, "120,00", "1.760,00", ilegivel=True)     # 7
    comprovante(doc, "T001", "1.800,00", "05/11/2026")                # 8
    ponto(doc, "T003", 4, paginas=2, so_primeira=True)                # 9
    holerite(doc, "T003", 2, "40,00", "1.680,00")                     # 10
    identidade(doc)                                                   # 11
    ponto(doc, "T004", 10)                                            # 12
    holerite(doc, "T004", None, "230,00", "1.870,00")                 # 13
    anotacao(doc)                                                     # 14
    ponto(doc, "T005", 4)                                             # 15
    holerite(doc, "T005", 4, "80,00", "1.720,00")                     # 16
    assert doc.page_count == GABARITO["paginas"], doc.page_count
    caminhos = {"lote_demo.pdf": saida / "lote_demo.pdf"}
    doc.save(caminhos["lote_demo.pdf"])
    doc.close()

    reenvio = fitz.open()
    holerite(reenvio, "T002", 6, "120,00", "1.760,00")
    caminhos["reenvio_holerite_T002.pdf"] = saida / "reenvio_holerite_T002.pdf"
    reenvio.save(caminhos["reenvio_holerite_T002.pdf"])
    reenvio.close()

    caminhos["arquivo_corrompido.pdf"] = saida / "arquivo_corrompido.pdf"
    caminhos["arquivo_corrompido.pdf"].write_bytes(b"%PDF-1.7\n1 0 obj << /Type /Catalog >>\ntruncado\x00\xff")

    caminhos["gabarito.json"] = saida / "gabarito.json"
    caminhos["gabarito.json"].write_text(json.dumps(GABARITO, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminhos


if __name__ == "__main__":
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("lote_demo")
    for nome, caminho in gerar(destino).items():
        print(f"{nome}: {caminho}")