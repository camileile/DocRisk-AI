"""H03: estrutura operacional com Clerk autenticado, sem tokens de demonstração."""
from pathlib import Path
import runpy

import pytest
from fastapi.testclient import TestClient

from docrisk_core import config, db
from docrisk_core.api import app
from test_d3_07_clerk import identity  # noqa: F401 - JWT Clerk assinado e provedor simulado


@pytest.fixture
def real_environment(identity, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", False)
    return identity


def test_admin_clerk_provisions_companies_contracts_and_invites_supplier(real_environment):
    state = real_environment
    with TestClient(app) as client:
        admin = state["headers"]()
        client_org = client.post("/api/admin/companies", headers=admin, json={
            "tipo": "CONTRATANTE", "nome": "Contratante de Apresentação (sintética)",
        })
        assert client_org.status_code == 201, client_org.text
        client_id = client_org.json()["id"]

        supplier = client.post("/api/admin/companies", headers=admin, json={
            "tipo": "FORNECEDORA", "nome": "Fornecedora de Apresentação (sintética)",
            "contratante_id": client_id, "contrato_nome": "Contrato sintético de serviços",
        })
        assert supplier.status_code == 201, supplier.text
        supplier_id = supplier.json()["id"]
        contract_id = supplier.json()["contract_id"]
        assert contract_id

        listed = client.get("/api/admin/registry", headers=admin)
        assert listed.status_code == 200
        assert any(c["id"] == contract_id for c in listed.json()["contratos"])
        assert all("token" not in c for c in listed.json()["usuarios"])

        invited = client.post("/api/auth/invitations", headers=admin, json={
            "email": "person@example.test", "nome": "Gestora Fornecedora Sintética",
            "org_id": supplier_id, "role": "GESTOR_FORN",
        })
        assert invited.status_code == 201, invited.text
        invite_id = invited.json()["id"]
        visitor = {"Authorization": "Bearer " + state["token"]("new")}
        assert client.get("/api/me", headers=visitor).status_code == 403
        accepted = client.post(f"/api/auth/invitations/{invite_id}/accept", headers=visitor)
        assert accepted.status_code == 200, accepted.text
        linked = {**visitor, "X-DocRisk-Link": accepted.json()["link_id"]}
        me = client.get("/api/me", headers=linked)
        assert me.status_code == 200
        assert me.json()["org_id"] == supplier_id and me.json()["papel"] == "GESTOR_FORN"
        own_contracts = client.get("/api/contracts", headers=linked)
        assert own_contracts.status_code == 200
        assert [c["id"] for c in own_contracts.json()] == [contract_id]

        duplicate = client.post("/api/admin/companies", headers=admin, json={
            "tipo": "CONTRATANTE", "nome": "Contratante de Apresentação (sintética)",
        })
        assert duplicate.status_code == 409

    with db.tx() as conn:
        assert conn.execute("SELECT count(*) FROM contracts WHERE id=?", (contract_id,)).fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM audit WHERE acao='EMPRESA_CRIADA' AND org_id='ORG-BH'").fetchone()[0] == 2


def test_clerk_structure_write_cannot_be_used_by_other_roles(real_environment):
    state = real_environment
    with TestClient(app) as client:
        for uid in ("u-analista", "u-gestor-beta", "u-oper-beta", "u-gestor-alfa", "platform"):
            headers = state["headers"](uid)
            assert client.post("/api/admin/companies", headers=headers, json={
                "tipo": "CONTRATANTE", "nome": "Empresa Não Autorizada",
            }).status_code == 403
            assert client.post("/api/admin/contracts", headers=headers, json={
                "nome": "Contrato não autorizado", "contratante_id": "ORG-ALFA",
                "fornecedora_id": "ORG-BETA",
            }).status_code == 403
        admin = state["headers"]()
        assert client.post("/api/admin/contracts", headers=admin, json={
            "nome": "Contrato sem acesso", "contratante_id": "ORG-EXTERNA",
            "fornecedora_id": "ORG-BETA",
        }).status_code == 422
        # Produção nunca cria usuários por token, nem credenciais de operador.
        user = client.post("/api/admin/users", headers=admin, json={
            "nome": "Sem token", "org_id": "ORG-BH", "papel": "ANALISTA_BH",
        })
        assert user.status_code == 403
        assert "token_teste" not in user.text
        assert client.post("/api/supplier/operators", headers=state["headers"]("u-gestor-beta"),
                           json={"nome": "Operador sem convite"}).status_code == 403
        assert client.patch("/api/admin/users/u-analista/status", headers=admin,
                            json={"ativo": False}).status_code == 403


def test_clerk_with_demo_mode_enabled_rejects_structure_write(identity, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    with TestClient(app) as client:
        assert client.post("/api/admin/companies", headers=identity["headers"](),
                           json={"tipo": "CONTRATANTE", "nome": "Ambiente misto bloqueado"}).status_code == 403


def test_synthetic_worker_provisioning_is_scoped_audited_and_idempotent(real_environment, tmp_path):
    state = real_environment
    # Script controlado usa a mesma base persistida da aplicação e um Admin Clerk ativo.
    script = Path(__file__).resolve().parents[1] / "scripts" / "provision_synthetic_workers.py"
    provision = runpy.run_path(str(script))["provision"]
    csv_file = tmp_path / "workers.csv"
    csv_file.write_text("id,nome\nSYNW001,Trabalhador Fictício Um\nSYNW002,Trabalhador Fictício Dois\n", encoding="utf-8")
    assert provision("CT-001", "u-admin", csv_file) == (2, 0)
    assert provision("CT-001", "u-admin", csv_file) == (0, 2)
    with TestClient(app) as client:
        response = client.get("/api/contracts/CT-001/workers", headers=state["headers"]("u-oper-beta"))
        assert response.status_code == 200
        assert {"SYNW001", "SYNW002"} <= {x["id"] for x in response.json()}
        forbidden = client.get("/api/contracts/CT-001/workers", headers=state["headers"]("u-gestor-alfa"))
        assert forbidden.status_code == 403  # contratante só consulta pareceres publicados

    with db.tx() as conn:
        assert conn.execute("SELECT count(*) FROM workers WHERE id LIKE 'SYNW%'").fetchone()[0] == 2
        assert conn.execute("SELECT count(*) FROM audit WHERE acao='TRABALHADORES_SINTETICOS_PROVISIONADOS'").fetchone()[0] == 2

    bad = tmp_path / "bad.csv"
    bad.write_text("id,nome\nSYNW003,Trabalhador Terceiro\nT101,Outro Trabalhador\n", encoding="utf-8")
    with pytest.raises(ValueError, match="já está em uso"):
        provision("CT-001", "u-admin", bad)
    with db.tx() as conn:
        assert conn.execute("SELECT count(*) FROM workers WHERE id='SYNW003'").fetchone()[0] == 0
    with pytest.raises(ValueError, match="não encontrado"):
        provision("CT-404", "u-admin", csv_file)
    with pytest.raises(ValueError, match="ADMIN_BH"):
        provision("CT-001", "u-analista", csv_file)


def test_worker_csv_validation_and_no_demo_mode(identity, tmp_path, monkeypatch):
    provision = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                                  "scripts" / "provision_synthetic_workers.py"))["provision"]
    path = tmp_path / "workers.csv"
    path.write_text("id,nome\nT990,Trabalhador Sintético\nT990,Duplicado\n", encoding="utf-8")
    monkeypatch.setattr(config, "DEMO_MODE", False)
    with pytest.raises(ValueError, match="duplicado"):
        provision("CT-001", "u-admin", path)
    path.write_text("id,nome\nT990,Trabalhador Sintético\n", encoding="utf-8")
    monkeypatch.setattr(config, "DEMO_MODE", True)
    with pytest.raises(ValueError, match="exige"):
        provision("CT-001", "u-admin", path)
