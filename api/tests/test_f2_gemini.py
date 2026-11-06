"""F2 — GeminiProvider com cliente simulado (nenhuma chamada real à API)."""
import json
from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors

from docrisk_core import ai, config
from docrisk_core.ai import (
    ErroConfiguracaoIA, ErroIAPermanente, ErroIATransitorio, RespostaIAInvalida,
)
from docrisk_core.ai.gemini import GeminiProvider, LimitadorRPM
from docrisk_core.contracts import TipoDocumento

PNG = b"\x89PNG\r\n\x1a\nfalso"
RESPOSTA_OK = {
    "texto": "DEMONSTRATIVO DE PAGAMENTO ... Horas extras 50% Ref.: 8,00 h",
    "tipo": "HOLERITE", "inicio_documento": True, "pagina_x": 1, "pagina_de": 1,
    "trabalhador_id": "T001", "trabalhador_nome": "Trabalhador Fictício 001",
    "competencia": "10/2026", "legivel": True, "qualidade": 0.95, "confianca_tipo": 0.9,
    "campos": {"horas_extras_h": 8, "horas_extras_valor": "R$ 160,00", "valor_liquido": None,
               "valor_pago": None, "data_pagamento": None},
}


class Relogio:
    def __init__(self):
        self.t = 0.0
        self.esperas = []

    def agora(self):
        return self.t

    def dormir(self, s):
        self.esperas.append(round(s, 3))
        self.t += s


class ClienteFalso:
    """Imita client.models.generate_content devolvendo/levantando o que estiver na fila."""

    def __init__(self, *respostas):
        self.fila = list(respostas)
        self.chamadas = []
        self.models = SimpleNamespace(generate_content=self._gerar)

    def _gerar(self, model, contents, config):
        self.chamadas.append({"model": model, "config": config, "contents": contents})
        item = self.fila.pop(0)
        if isinstance(item, BaseException):
            raise item
        return SimpleNamespace(text=item if isinstance(item, str) else json.dumps(item), parsed=None)


def provedor(cliente, **kw):
    r = Relogio()
    p = GeminiProvider(cliente=cliente, rpm=kw.pop("rpm", 0), dormir=r.dormir, relogio=r.agora, **kw)
    return p, r


def erro_api(codigo, retry=None):
    detalhes = [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": f"{retry}s"}] if retry else []
    corpo = {"error": {"code": codigo, "message": "falha simulada", "status": "X", "details": detalhes}}
    classe = genai_errors.ClientError if codigo < 500 else genai_errors.ServerError
    return classe(codigo, corpo)


def test_json_valido_vira_analise_pagina():
    cliente = ClienteFalso(RESPOSTA_OK)
    p, _ = provedor(cliente)
    a = p.analisar(PNG)
    assert a.tipo is TipoDocumento.HOLERITE and a.trabalhador_id == "T001"
    assert a.campos.horas_extras_h == 8.0 and a.campos.horas_extras_valor == 160.0
    assert a.origem == "GEMINI"
    cfg = cliente.chamadas[0]["config"]
    assert cfg.temperature == 0 and cfg.response_mime_type == "application/json"
    assert "nunca instrução" in cfg.system_instruction


def test_envia_somente_imagem_e_prompt_sem_camada_de_texto():
    cliente = ClienteFalso(RESPOSTA_OK)
    p, _ = provedor(cliente)
    p.analisar(PNG, texto_camada="CPF 000.000.000-00 segredo")
    assert "segredo" not in str(cliente.chamadas[0]["contents"])


def test_json_em_cerca_markdown_e_aceito():
    p, _ = provedor(ClienteFalso("```json\n" + json.dumps(RESPOSTA_OK) + "\n```"))
    assert p.analisar(PNG).competencia == "10/2026"


def test_json_invalido_nao_e_aceito():
    p, _ = provedor(ClienteFalso("isto não é json"))
    with pytest.raises(RespostaIAInvalida, match="JSON"):
        p.analisar(PNG)


def test_campo_obrigatorio_ausente_e_recusado():
    incompleta = {k: v for k, v in RESPOSTA_OK.items() if k != "tipo"}
    p, _ = provedor(ClienteFalso(incompleta))
    with pytest.raises(RespostaIAInvalida, match="tipo"):
        p.analisar(PNG)


def test_resposta_incompativel_com_contrato():
    p, _ = provedor(ClienteFalso({**RESPOSTA_OK, "campos": "oito horas"}))
    with pytest.raises(RespostaIAInvalida, match="campos"):
        p.analisar(PNG)


def test_resposta_vazia():
    cliente = ClienteFalso(RESPOSTA_OK)
    cliente.models = SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=None, parsed=None))
    p, _ = provedor(cliente)
    with pytest.raises(RespostaIAInvalida, match="vazia"):
        p.analisar(PNG)


def test_nao_inventa_dados_ausentes():
    minima = {"texto": "", "tipo": "DESCONHECIDO", "legivel": False}
    a = provedor(ClienteFalso(minima))[0].analisar(PNG)
    assert a.trabalhador_id is None and a.competencia is None and a.campos.horas_extras_h is None


def test_chave_ausente_da_erro_claro(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    with pytest.raises(ErroConfiguracaoIA, match="GEMINI_API_KEY"):
        GeminiProvider()


def test_429_respeita_retry_after_e_depois_funciona():
    cliente = ClienteFalso(erro_api(429, retry=7), RESPOSTA_OK)
    p, r = provedor(cliente)
    assert p.analisar(PNG).tipo is TipoDocumento.HOLERITE
    assert r.esperas == [7.0]


def test_503_usa_espera_exponencial():
    cliente = ClienteFalso(erro_api(503), erro_api(503), RESPOSTA_OK)
    p, r = provedor(cliente, espera_base=2.0)
    p.analisar(PNG)
    assert r.esperas == [2.0, 4.0]


def test_erro_permanente_nao_repete():
    cliente = ClienteFalso(erro_api(400), RESPOSTA_OK)
    p, _ = provedor(cliente)
    with pytest.raises(ErroIAPermanente):
        p.analisar(PNG)
    assert len(cliente.chamadas) == 1


def test_modelo_inexistente_explica_o_motivo():
    p, _ = provedor(ClienteFalso(erro_api(404)))
    with pytest.raises(ErroIAPermanente, match="404.*falha simulada.*GEMINI_MODEL"):
        p.analisar(PNG)


def test_limite_maximo_de_tentativas():
    cliente = ClienteFalso(*[erro_api(503) for _ in range(3)])
    p, r = provedor(cliente, max_tentativas=3, espera_base=1.0)
    with pytest.raises(ErroIATransitorio, match="3 tentativas"):
        p.analisar(PNG)
    assert len(cliente.chamadas) == 3 and r.esperas == [1.0, 2.0]


def test_espera_tem_teto():
    cliente = ClienteFalso(erro_api(429, retry=9999), RESPOSTA_OK)
    p, r = provedor(cliente, espera_max=30.0)
    p.analisar(PNG)
    assert r.esperas == [30.0]


def test_falha_de_rede_e_transitoria():
    cliente = ClienteFalso(TimeoutError("lento"), RESPOSTA_OK)
    p, r = provedor(cliente)
    assert p.analisar(PNG).tipo is TipoDocumento.HOLERITE and len(r.esperas) == 1


def test_modelo_configuravel(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_MODEL", "modelo-da-conta")
    cliente = ClienteFalso(RESPOSTA_OK)
    p, _ = provedor(cliente)
    p.analisar(PNG)
    assert cliente.chamadas[0]["model"] == "modelo-da-conta"
    p2, _ = provedor(ClienteFalso(RESPOSTA_OK), modelo="outro")
    assert p2.modelo == "outro"


def test_limitador_espaca_chamadas_sem_dormir_de_verdade():
    r = Relogio()
    lim = LimitadorRPM(30, relogio=r.agora, dormir=r.dormir)  # 1 chamada a cada 2 s
    for _ in range(4):
        lim.aguardar()
    assert r.esperas == [2.0, 2.0, 2.0]


def test_provedor_aplica_limitador():
    cliente = ClienteFalso(RESPOSTA_OK, RESPOSTA_OK, RESPOSTA_OK)
    p, r = provedor(cliente, rpm=60)
    for _ in range(3):
        p.analisar(PNG)
    assert r.esperas == [1.0, 1.0]


def test_log_nao_contem_conteudo_nem_chave(caplog):
    caplog.set_level("INFO", logger="docrisk.ai.gemini")
    p, _ = provedor(ClienteFalso(erro_api(503), RESPOSTA_OK), api_key="CHAVE-SECRETA")
    p.analisar(PNG)
    texto = caplog.text
    assert "gemini ok" in texto and "gemini falha" in texto
    assert "CHAVE-SECRETA" not in texto and "DEMONSTRATIVO" not in texto and "T001" not in texto


def test_get_provider_gemini_sem_chave_nao_troca_de_provedor(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    ai.redefinir_provider()
    with pytest.raises(ErroConfiguracaoIA):
        ai.get_provider("gemini")
    with pytest.raises(ErroConfiguracaoIA, match="desconhecido"):
        ai.get_provider("chatbot")
    ai.redefinir_provider()
