"""D4-01 — matriz dos seis papéis reais e ciclo desativação/reativação.

Complementa test_profiles_integration.py (PR #22) sem repetir o fluxo completo:
aqui cada papel recebe uma operação permitida e uma proibida, e os três caminhos
reais de reativação (Admin Geral -> Admin da auditora, Admin BH -> usuários da
auditora, Gestor da fornecedora -> operadores) são exercitados com tentativa sem
privilégio e verificação de persistência após reiniciar a aplicação.

Somente dados sintéticos do seed demo. Nenhuma chamada externa (leitor textlayer).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from docrisk_core import config, db
from docrisk_core.api import app
from test_f2_worker import banco  # noqa: F401  (fixture de banco isolado)

PAPEIS_REAIS = {
    "u-plataforma": "ADMIN_PLATAFORMA",
    "u-admin": "ADMIN_BH",
    "u-analista": "ANALISTA_BH",
    "u-gestor-beta": "GESTOR_FORN",
    "u-oper-beta": "OPERADOR_FORN",
    "u-gestor-alfa": "GESTOR_CONTR",
}


def _h(uid: str) -> dict[str, str]:
    with db.tx() as conn:
        row = conn.execute("SELECT token FROM users WHERE id=?", (uid,)).fetchone()
        if row is None:
            row = conn.execute("SELECT token FROM platform_accounts WHERE id=?", (uid,)).fetchone()
    assert row is not None, uid
    return {"Authorization": "Bearer " + row[0]}


@pytest.fixture
def demo(banco, monkeypatch):  # noqa: F811
    monkeypatch.setattr(config, "DEMO_MODE", True)
    db.init_db()  # cria a conta da plataforma (só existe em modo demo)
    return banco


# Uma operação permitida e uma proibida por papel. Rotas e respostas reais.
MATRIZ = [
    ("u-plataforma", ("GET", "/api/platform/registry"), ("GET", "/api/batches"), 403),
    ("u-admin", ("GET", "/api/admin/registry"), ("GET", "/api/platform/registry"), 403),
    ("u-analista", ("GET", "/api/review-queue"), ("GET", "/api/admin/registry"), 403),
    ("u-gestor-beta", ("GET", "/api/supplier/operators"), ("GET", "/api/review-queue"), 403),
    ("u-oper-beta", ("GET", "/api/batches"), ("GET", "/api/supplier/operators"), 403),
    ("u-gestor-alfa", ("GET", "/api/client/reports"), ("GET", "/api/batches"), 403),
]


def test_seed_tem_exatamente_os_seis_papeis_do_contrato(demo):
    from docrisk_core.contracts import Papel
    assert set(PAPEIS_REAIS.values()) == {p.value for p in Papel}
    with TestClient(app) as client:
        for uid, papel in PAPEIS_REAIS.items():
            me = client.get("/api/me", headers=_h(uid))
            assert me.status_code == 200, uid
            assert me.json()["papel"] == papel
            assert "token" not in me.json()


@pytest.mark.parametrize("uid,permitida,proibida,codigo", MATRIZ, ids=[m[0] for m in MATRIZ])
def test_cada_papel_operacao_permitida_e_proibida(demo, uid, permitida, proibida, codigo):
    with TestClient(app) as client:
        ok = client.request(permitida[0], permitida[1], headers=_h(uid))
        assert ok.status_code == 200, (uid, permitida, ok.text)
        negado = client.request(proibida[0], proibida[1], headers=_h(uid))
        assert negado.status_code == codigo, (uid, proibida, negado.status_code)


@pytest.mark.parametrize("header", [
    None, "", "Bearer", "Bearer   ", "Basic dXNlcjpwYXNz", "token-sem-esquema",
    "Bearer token-inexistente-0000", "Bearer " + "x" * 4096,
])
def test_sem_autenticacao_ou_token_invalido_retorna_401(demo, header):
    headers = {} if header is None else {"Authorization": header}
    with TestClient(app) as client:
        for path in ["/api/me", "/api/batches", "/api/admin/registry",
                     "/api/platform/registry", "/api/supplier/operators", "/api/client/reports"]:
            r = client.get(path, headers=headers)
            assert r.status_code == 401, (header, path, r.status_code)
            assert r.headers.get("www-authenticate") == "Bearer"


def _ciclo(client, ator, path_status, alvo, alvo_permitido, sem_privilegio):
    """Desativa, confirma bloqueio total, tenta reativar sem privilégio, reativa."""
    alvo_h = _h(alvo)
    metodo, rota_alvo = alvo_permitido
    assert client.request(metodo, rota_alvo, headers=alvo_h).status_code == 200
    assert client.patch(path_status, headers=_h(ator), json={"ativo": False}).status_code == 200

    # Usuário desativado: nenhuma rota aceita o token, nem para se reativar.
    for path in ["/api/me", rota_alvo]:
        assert client.get(path, headers=alvo_h).status_code == 401
    assert client.patch(path_status, headers=alvo_h, json={"ativo": True}).status_code == 401

    # Reativação sem privilégio: papel errado ou outra organização.
    for uid, esperado in sem_privilegio:
        r = client.patch(path_status, headers=_h(uid), json={"ativo": True})
        assert r.status_code == esperado, (uid, r.status_code, r.text)
    assert client.get("/api/me", headers=alvo_h).status_code == 401

    # Payload não-booleano não reativa (strict).
    assert client.patch(path_status, headers=_h(ator), json={"ativo": "1"}).status_code == 422

    r = client.patch(path_status, headers=_h(ator), json={"ativo": True})
    assert r.status_code == 200 and r.json() == {"id": alvo, "ativo": True}
    assert client.request(metodo, rota_alvo, headers=alvo_h).status_code == 200


CAMINHOS = [
    # ator, rota de status, alvo, rota permitida ao alvo, tentativas sem privilégio
    ("u-plataforma", "/api/platform/administrators/u-admin/status", "u-admin",
     ("GET", "/api/admin/registry"),
     [("u-analista", 403), ("u-gestor-beta", 403), ("u-oper-beta", 403), ("u-gestor-alfa", 403)]),
    ("u-admin", "/api/admin/users/u-analista/status", "u-analista",
     ("GET", "/api/review-queue"),
     [("u-plataforma", 403), ("u-gestor-beta", 403), ("u-oper-beta", 403), ("u-gestor-alfa", 403)]),
    ("u-gestor-beta", "/api/supplier/operators/u-oper-beta/status", "u-oper-beta",
     ("GET", "/api/batches"),
     [("u-plataforma", 403), ("u-admin", 403), ("u-analista", 403), ("u-gestor-alfa", 403),
      ("u-oper-gama", 403)]),
]


@pytest.mark.parametrize("ator,path_status,alvo,permitida,sem_priv", CAMINHOS,
                         ids=["plataforma->admin_bh", "admin_bh->analista", "gestor_forn->operador"])
def test_reativacao_autorizada_e_negada_sem_privilegio(demo, ator, path_status, alvo, permitida, sem_priv):
    with TestClient(app) as client:
        _ciclo(client, ator, path_status, alvo, permitida, sem_priv)
    with db.tx() as conn:
        eventos = [r[0] for r in conn.execute(
            "SELECT resultado FROM audit WHERE alvo=? AND user_id=? ORDER BY id", (alvo, ator))]
    assert len(eventos) >= 2  # desativação e reativação auditadas pelo ator


def test_gestor_de_outra_fornecedora_nao_ve_nem_reativa_operador(demo):
    with TestClient(app) as client:
        h = _h("u-gestor-beta")
        assert client.patch("/api/supplier/operators/u-oper-beta/status", headers=h,
                            json={"ativo": False}).status_code == 200
        with db.tx() as conn:
            conn.execute("INSERT INTO users (id,nome,org_id,role,token) VALUES "
                         "('u-gestor-gama','Gestor Gama (teste)','ORG-GAMA','GESTOR_FORN','tok-gestor-gama-sintetico')")
        r = client.patch("/api/supplier/operators/u-oper-beta/status",
                         headers={"Authorization": "Bearer tok-gestor-gama-sintetico"}, json={"ativo": True})
        assert r.status_code == 404  # não revela existência fora da organização
        assert client.get("/api/me", headers=_h("u-oper-beta")).status_code == 401


def test_estado_persiste_apos_reiniciar_a_aplicacao(demo):
    alvo = "u-oper-beta"
    path = f"/api/supplier/operators/{alvo}/status"
    with TestClient(app) as client:
        assert client.patch(path, headers=_h("u-gestor-beta"), json={"ativo": False}).status_code == 200
    # Novo ciclo de vida (lifespan): init_db idempotente não reativa o usuário.
    with TestClient(app) as client:
        assert client.get("/api/me", headers=_h(alvo)).status_code == 401
        assert client.patch(path, headers=_h("u-gestor-beta"), json={"ativo": True}).status_code == 200
    with TestClient(app) as client:
        me = client.get("/api/me", headers=_h(alvo))
        assert me.status_code == 200
        # Reativação restaura o MESMO papel e escopo, sem escalada.
        assert me.json()["papel"] == "OPERADOR_FORN" and me.json()["org_id"] == "ORG-BETA"
        assert client.get("/api/supplier/operators", headers=_h(alvo)).status_code == 403
        contratos = [c["id"] for c in client.get("/api/contracts", headers=_h(alvo)).json()]
        assert contratos == ["CT-001"]


def test_mutacoes_de_status_bloqueadas_fora_do_modo_demo(demo, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", False)
    with TestClient(app) as client:
        for ator, path, _alvo, _p, _s in CAMINHOS:
            if ator == "u-plataforma":
                continue  # conta da plataforma só existe no seed demo
            r = client.patch(path, headers=_h(ator), json={"ativo": False})
            assert r.status_code == 403, (ator, path)
