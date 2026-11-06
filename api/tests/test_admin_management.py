"""Admin Bernhoeft: cadastro real de teste, relações e controles de acesso."""
from fastapi.testclient import TestClient

from docrisk_core import config, db
from docrisk_core.api import app
from test_f2_worker import banco  # noqa: F401


def _headers(uid: str) -> dict[str, str]:
    with db.tx() as conn:
        token = conn.execute("SELECT token FROM users WHERE id=?", (uid,)).fetchone()[0]
    return {"Authorization": "Bearer " + token}


def test_admin_cadastro_uma_fornecedora_varias_contratantes_sem_duplicar(banco, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    with TestClient(app) as client:
        auth = _headers("u-admin")
        registry = client.get("/api/admin/registry", headers=auth)
        assert registry.status_code == 200
        assert len([o for o in registry.json()["empresas"] if o["tipo"] == "FORNECEDORA"]) == 2
        assert len(registry.json()["contratos"]) == 2
        assert all("token" not in u for u in registry.json()["usuarios"])

        client_a = client.post("/api/admin/companies", headers=auth,
                               json={"tipo": "CONTRATANTE", "nome": "Cliente Teste A", "cnpj": "TESTEABC00000001"})
        assert client_a.status_code == 201, client_a.text
        client_b = client.post("/api/admin/companies", headers=auth,
                               json={"tipo": "CONTRATANTE", "nome": "Cliente Teste B"})
        assert client_b.status_code == 201, client_b.text
        a_id = client_a.json()["id"]
        b_id = client_b.json()["id"]

        missing_link = client.post("/api/admin/companies", headers=auth,
                                   json={"tipo": "FORNECEDORA", "nome": "Terceirizada sem contrato"})
        assert missing_link.status_code == 422
        supplier = client.post("/api/admin/companies", headers=auth,
                               json={"tipo": "FORNECEDORA", "nome": "Terceirizada Nova", "cnpj": "TESTEFORN0000001",
                                     "contratante_id": a_id, "contrato_nome": "Limpeza A"})
        assert supplier.status_code == 201, supplier.text
        supplier_id = supplier.json()["id"]
        initial_contract = supplier.json()["contract_id"]
        assert initial_contract

        extra = client.post("/api/admin/contracts", headers=auth, json={
            "nome": "Apoio B", "contratante_id": b_id, "fornecedora_id": supplier_id,
            "inicio": "2026-11-01", "fim": "2027-04-01",
        })
        assert extra.status_code == 201, extra.text
        ids = [c for c in client.get("/api/admin/registry", headers=auth).json()["contratos"]
               if c["fornecedora_id"] == supplier_id]
        assert len(ids) == 2 and {c["contratante_id"] for c in ids} == {a_id, b_id}
        assert client.post("/api/admin/companies", headers=auth, json={
            "tipo": "FORNECEDORA", "nome": "Terceirizada Nova",
            "contratante_id": b_id, "contrato_nome": "Duplicação",
        }).status_code == 409

        manager = client.post("/api/admin/users", headers=auth,
                              json={"nome": "Gestora Exemplo", "org_id": supplier_id, "papel": "GESTOR_FORN"})
        assert manager.status_code == 201, manager.text
        test_token = manager.json()["token_teste"]
        assert test_token
        users = client.get("/api/admin/registry", headers=auth).json()["usuarios"]
        assert any(u["id"] == manager.json()["id"] and "token_teste" not in u for u in users)
        assert client.get("/api/me", headers={"Authorization": "Bearer " + test_token}).status_code == 200
        deactivate = client.patch("/api/admin/users/" + manager.json()["id"] + "/status",
                                  headers=auth, json={"ativo": False})
        assert deactivate.status_code == 200
        assert client.get("/api/me", headers={"Authorization": "Bearer " + test_token}).status_code == 401

        overview = client.get("/api/admin/overview", headers=auth,
                              params={"contratante_id": a_id})
        assert overview.status_code == 200
        assert overview.json()["contratantes"] == 1
        assert overview.json()["fornecedoras"] == 1
        assert "operacao" in overview.json()
        assert "receita" not in str(overview.json()).lower()


def test_admin_papeis_invalidos_e_escopo_negados(banco, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    with TestClient(app) as client:
        for uid in ("u-analista", "u-gestor-alfa", "u-oper-beta"):
            assert client.get("/api/admin/registry", headers=_headers(uid)).status_code == 403
            assert client.post("/api/admin/companies", headers=_headers(uid),
                               json={"tipo": "CONTRATANTE", "nome": "Proibida"}).status_code == 403

        auth = _headers("u-admin")
        assert client.post("/api/admin/users", headers=auth,
                           json={"nome": "Não pode", "org_id": "ORG-BETA", "papel": "GESTOR_CONTR"}).status_code == 422
        assert client.post("/api/admin/contracts", headers=auth, json={
            "nome": "Contrato externo", "contratante_id": "ORG-EXTERNA",
            "fornecedora_id": "ORG-BETA",
        }).status_code == 422
        assert client.patch("/api/admin/users/u-admin/status", headers=auth,
                            json={"ativo": False}).status_code == 422
        assert client.patch("/api/admin/users/u-nao-existe/status", headers=auth,
                            json={"ativo": False}).status_code == 404


def test_cadastros_bloqueados_fora_do_modo_demo(banco, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", False)
    with TestClient(app) as client:
        auth = _headers("u-admin")
        assert client.get("/api/admin/registry", headers=auth).status_code == 401
        assert client.post("/api/admin/companies", headers=auth,
                           json={"tipo": "CONTRATANTE", "nome": "Não permitida"}).status_code == 401
        assert client.post("/api/admin/users", headers=auth,
                           json={"nome": "Não permitido", "org_id": "ORG-BH", "papel": "ANALISTA_BH"}).status_code == 401
