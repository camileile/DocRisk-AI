"""F2 — TextLayerProvider (regras sobre texto, sem internet) e seleção de provedor."""
import shutil

import pytest

from docrisk_core import ai, config
from docrisk_core.ai.textlayer import TextLayerProvider, analisar_texto
from docrisk_core.contracts import TipoDocumento as T

PONTO_P1 = """ESPELHO DE PONTO
Empregador: Fornecedora Beta Serviços (fictícia)
Trabalhador: Trabalhador Fictício 001   Matrícula: T001
Competência: 10/2026
Data | Entrada | Saída almoço | Retorno | Saída | Extras
01/10 | 08:00 | 12:00 | 13:00 | 19:00 | 2,00 h
DOCUMENTO FICTÍCIO
Página 1 de 2"""

PONTO_P2 = """Matrícula: T001
16/10 | 08:00 | 12:00 | 13:00 | 17:00 |
TOTAL DE HORAS EXTRAS: 12,00 h
Assinatura do trabalhador: ________
Página 2 de 2"""

HOLERITE = """DEMONSTRATIVO DE PAGAMENTO DE SALÁRIO
Trabalhador: Trabalhador Fictício 001    Matrícula: T001
Competência: 10/2026
Código | Descrição | Referência | Proventos | Descontos
001 Salário base | 30 dias | R$ 1.800,00
002 Horas extras 50% | Ref.: 8,00 h | R$ 160,00
Líquido a receber: R$ 1.802,70
Página 1 de 1"""

HOLERITE_SO_REAIS = HOLERITE.replace("Ref.: 8,00 h | ", "").replace("8,00 h", "")

HOLERITE_ILEGIVEL = """DEMONSTRATIVO DE PAGAMENTO DE SALÁRIO
Matrícula: T002   Competência: 10/2026
Página 1 de 1"""

COMPROVANTE = """COMPROVANTE DE PAGAMENTO — TRANSFERÊNCIA
Favorecido: Trabalhador Fictício 001   Matrícula: T001
Competência: 10/2026
Valor pago: R$ 1.802,70
Data do pagamento: 05/11/2026
Página 1 de 1"""


def test_titulo_define_tipo():
    assert analisar_texto(PONTO_P1).tipo is T.ESPELHO_PONTO
    assert analisar_texto(HOLERITE).tipo is T.HOLERITE
    assert analisar_texto(COMPROVANTE).tipo is T.COMPROVANTE_PAGAMENTO
    assert analisar_texto("CONTRATO DE PRESTAÇÃO DE SERVIÇOS Nº 001/2026\nCláusula 1...").tipo is T.CONTRATO


def test_titulo_so_nos_primeiros_300_caracteres():
    longo = "CONTRATO DE PRESTAÇÃO DE SERVIÇOS\n" + ("cláusula genérica " * 30) + "\nespelho de ponto mensal"
    assert analisar_texto(longo).tipo is T.CONTRATO
    corpo_apenas = ("texto qualquer " * 30) + "\nESPELHO DE PONTO"
    assert analisar_texto(corpo_apenas).tipo is T.DESCONHECIDO


def test_paginacao_no_rodape_e_encontrada():
    a = analisar_texto(PONTO_P2)
    assert (a.pagina_x, a.pagina_de) == (2, 2)
    assert a.tipo is T.DESCONHECIDO  # continuação sem título não ganha tipo inventado
    assert a.inicio_documento is False


def test_matricula_competencia_e_nome():
    a = analisar_texto(PONTO_P1)
    assert a.trabalhador_id == "T001" and a.competencia == "10/2026"
    assert a.trabalhador_nome == "Trabalhador Fictício 001"
    assert a.inicio_documento is True and a.origem == "TEXTO_PDF"


def test_horas_extras_do_ponto_e_da_folha():
    assert analisar_texto(PONTO_P2).campos.horas_extras_h == 12.0
    h = analisar_texto(HOLERITE).campos
    assert h.horas_extras_h == 8.0 and h.horas_extras_valor == 160.0 and h.valor_liquido == 1802.7
    assert analisar_texto("TOTAL DE HORAS EXTRAS: 10:30\nPágina 2 de 2").campos.horas_extras_h == 10.5


def test_folha_so_em_reais_nao_inventa_horas():
    c = analisar_texto(HOLERITE_SO_REAIS).campos
    assert c.horas_extras_h is None and c.horas_extras_valor == 160.0


def test_comprovante_valor_e_data():
    c = analisar_texto(COMPROVANTE).campos
    assert c.valor_pago == 1802.7 and c.data_pagamento == "05/11/2026"


def test_pagina_prioritaria_so_com_titulo_e_ilegivel():
    a = analisar_texto(HOLERITE_ILEGIVEL)
    assert a.tipo is T.HOLERITE and a.legivel is False and a.qualidade < 0.5
    assert a.trabalhador_id == "T002"  # o que é legível continua sendo extraído


def test_documento_nao_reconhecido():
    a = analisar_texto("anotações — conferir com o RH\nligar para o setor pessoal sobre o lote")
    assert a.tipo is T.DESCONHECIDO and a.confianca_tipo <= 0.3 and a.legivel is True


def test_pagina_sem_texto():
    a = analisar_texto("   ")
    assert a.tipo is T.DESCONHECIDO and a.legivel is False and a.qualidade == 0.0


def test_provider_usa_camada_de_texto():
    a = TextLayerProvider().analisar(b"png", HOLERITE)
    assert a.tipo is T.HOLERITE


def test_get_provider_por_ai_provider(monkeypatch):
    ai.redefinir_provider()
    monkeypatch.setattr(config, "AI_PROVIDER", "textlayer")
    p = ai.get_provider()
    assert isinstance(p, TextLayerProvider) and ai.get_provider() is p
    ai.redefinir_provider()


@pytest.mark.skipif(shutil.which("tesseract") is not None, reason="só quando o Tesseract falta")
def test_tesseract_ausente_da_erro_claro():
    ai.redefinir_provider()
    with pytest.raises(ai.ErroConfiguracaoIA, match="Tesseract"):
        ai.get_provider("tesseract")
    ai.redefinir_provider()
