"""D4-04 — validação de configuração, CORS e instância única do processo da API."""
from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest
from fastapi.testclient import TestClient

from docrisk_core import config, runtime
from docrisk_core.api import app
from test_f2_worker import banco  # noqa: F401


def test_configuracao_padrao_de_teste_e_valida(banco):  # noqa: F811
    assert runtime.validar_configuracao() == []


@pytest.mark.parametrize("ajuste,trecho", [
    ({"AI_PROVIDER": "xyz"}, "AI_PROVIDER='xyz' inválido"),
    ({"AI_PROVIDER": "gemini", "GEMINI_API_KEY": ""}, "exige GEMINI_API_KEY"),
    ({"GEMINI_RPM": 0}, "GEMINI_RPM deve ser maior que zero"),
    ({"MAX_UPLOAD_MB": -1}, "MAX_UPLOAD_MB deve ser maior que zero"),
    ({"LIMIAR_CONFIANCA": 1.5}, "LIMIAR_CONFIANCA deve estar entre 0 e 1"),
])
def test_valores_invalidos_geram_mensagem_clara(banco, monkeypatch, ajuste, trecho):  # noqa: F811
    for nome, valor in ajuste.items():
        monkeypatch.setattr(config, nome, valor)
    problemas = runtime.validar_configuracao()
    assert any(trecho in p for p in problemas), problemas
    # Nenhuma mensagem pode conter o valor de uma chave.
    assert all("GEMINI_API_KEY=" not in p for p in problemas)


def test_todos_os_problemas_sao_reunidos(banco, monkeypatch):  # noqa: F811
    monkeypatch.setattr(config, "AI_PROVIDER", "xyz")
    monkeypatch.setattr(config, "GEMINI_RPM", 0)
    monkeypatch.setenv("CORS_ORIGINS", "*")
    assert len(runtime.validar_configuracao()) == 3


@pytest.mark.parametrize("origens,ok", [
    ("http://localhost:3000,http://127.0.0.1:3000", True),
    ("https://piloto.example.com", True),
    ("http://[::1]:4173", True),
    ("*", False),
    ("null", False),
    ("", False),
    ("http://piloto.example.com", False),          # HTTP fora de loopback
    ("https://piloto.example.com/app", False),     # caminho
    ("ftp://localhost", False),
    ("https://user:pw@piloto.example.com", False),
])
def test_cors_somente_origens_explicitas(banco, monkeypatch, origens, ok):  # noqa: F811
    monkeypatch.setenv("CORS_ORIGINS", origens)
    problemas = [p for p in runtime.validar_configuracao() if "CORS" in p]
    assert (problemas == []) is ok, problemas


def test_demo_mode_recusa_origem_publica(banco, monkeypatch):  # noqa: F811
    monkeypatch.setattr(config, "DEMO_MODE", True)
    monkeypatch.setenv("CORS_ORIGINS", "https://piloto.example.com")
    assert any("DOCRISK_DEMO_MODE=1 expõe tokens" in p for p in runtime.validar_configuracao())


def test_data_dir_que_e_arquivo_e_recusado(banco, monkeypatch, tmp_path):  # noqa: F811
    arquivo = tmp_path / "nao-e-pasta"
    arquivo.write_text("x")
    monkeypatch.setattr(config, "DATA_DIR", arquivo)
    assert any("DOCRISK_DATA_DIR" in p for p in runtime.validar_configuracao())


def test_banco_corrompido_e_recusado_sem_ser_alterado(banco, monkeypatch, tmp_path):  # noqa: F811
    corrompido = tmp_path / "corrompido.sqlite"
    corrompido.write_bytes(b"isto nao e um banco sqlite" * 100)
    monkeypatch.setattr(config, "DB_PATH", corrompido)
    problemas = runtime.validar_configuracao()
    assert any("ilegível" in p for p in problemas), problemas
    assert corrompido.read_bytes().startswith(b"isto nao e um banco")


def test_inicializacao_recusada_com_configuracao_invalida(banco, monkeypatch):  # noqa: F811
    monkeypatch.setattr(config, "AI_PROVIDER", "xyz")
    with pytest.raises(runtime.ConfiguracaoInvalida) as erro:
        with TestClient(app):
            pass
    assert "AI_PROVIDER" in str(erro.value) and ".env.example" in str(erro.value)
    # A trava não fica presa após a falha: nova inicialização válida funciona.
    monkeypatch.setattr(config, "AI_PROVIDER", "textlayer")
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200


def test_numero_invalido_no_ambiente_tem_mensagem_clara():
    codigo = "import docrisk_core.config"
    r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, encoding="utf-8",
                       env={**_env_base(), "GEMINI_RPM": "abc"}, cwd=_api_dir())
    assert r.returncode != 0
    assert "Variável GEMINI_RPM deve ser inteiro; recebido 'abc'" in r.stderr


def test_cors_permitido_e_negado(banco):  # noqa: F811
    with TestClient(app) as client:
        ok = client.options("/api/me", headers={"Origin": "http://127.0.0.1:3000",
                                                "Access-Control-Request-Method": "GET"})
        assert ok.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"
        negado = client.options("/api/me", headers={"Origin": "https://atacante.example",
                                                    "Access-Control-Request-Method": "GET"})
        assert negado.status_code == 400
        assert "access-control-allow-origin" not in negado.headers
        simples = client.get("/health", headers={"Origin": "https://atacante.example"})
        assert "access-control-allow-origin" not in simples.headers


def test_trava_reentrante_no_mesmo_processo(banco):  # noqa: F811
    with TestClient(app) as a:
        with TestClient(app) as b:
            assert a.get("/health").status_code == b.get("/health").status_code == 200
        assert a.get("/health").status_code == 200


def test_segundo_processo_no_mesmo_data_dir_e_recusado(banco):  # noqa: F811
    script = textwrap.dedent("""
        import sys
        from docrisk_core import runtime
        try:
            runtime.adquirir_instancia()
        except runtime.InstanciaDuplicada as exc:
            print(exc); sys.exit(3)
        print("adquiriu"); sys.exit(0)
    """)
    env = {**_env_base(), "DOCRISK_DATA_DIR": str(config.DATA_DIR)}
    with TestClient(app):  # este processo detém a trava
        r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, encoding="utf-8", env=env, cwd=_api_dir())
        assert r.returncode == 3, r.stdout + r.stderr
        assert "Já existe uma instância da API" in r.stdout
    # Liberada no encerramento: outro processo consegue.
    r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, encoding="utf-8", env=env, cwd=_api_dir())
    assert r.returncode == 0 and "adquiriu" in r.stdout


def _api_dir() -> str:
    return str(config.API_DIR)


def _env_base() -> dict[str, str]:
    import os
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GEMINI", "DOCRISK", "CORS"))}
    env.update({"AI_PROVIDER": "textlayer", "GEMINI_API_KEY": "", "PYTHONIOENCODING": "utf-8"})
    return env
