"""Um fluxo integrado dos seis perfis, com dados sintéticos e SQLite efêmero."""
from fastapi.testclient import TestClient
from docrisk_core import config, db
from docrisk_core.api import app
from test_f2_worker import banco, pdf, HOLERITE  # noqa: F401
from test_f1_security import headers


def test_six_profiles_from_auditor_registration_to_published_report(banco, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    db.init_db()
    with db.tx() as conn:
        token = conn.execute("SELECT token FROM platform_accounts WHERE id='u-plataforma'").fetchone()[0]
    general = {"Authorization": "Bearer " + token}

    def auth(result):
        return {"Authorization": "Bearer " + result["token_teste"]}

    with TestClient(app) as client:
        def post(path, actor, payload):
            response = client.post(path, headers=actor, json=payload)
            assert response.status_code == 201, (path, response.status_code, response.text)
            return response.json()

        # 1. Admin Geral provisiona uma auditora isolada da Bernhoeft demo.
        auditor = post("/api/platform/auditors", general,
                       {"nome": "Auditora Integração", "administrador": "Admin Integração"})
        admin = auth(auditor)
        # 2. Admin da auditora cria a estrutura e os gestores com contratos próprios.
        contractor = post("/api/admin/companies", admin, {"tipo": "CONTRATANTE", "nome": "Contratante Integração"})
        supplier = post("/api/admin/companies", admin, {
            "tipo": "FORNECEDORA", "nome": "Fornecedora Integração",
            "contratante_id": contractor["id"], "contrato_nome": "Contrato Integração",
        })
        contract = supplier["contract_id"]
        analyst = auth(post("/api/admin/users", admin, {"nome": "Analista Integração", "org_id": auditor["id"], "papel": "ANALISTA_BH"}))
        manager = auth(post("/api/admin/users", admin, {"nome": "Gestor Fornecedora", "org_id": supplier["id"], "papel": "GESTOR_FORN"}))
        customer = auth(post("/api/admin/users", admin, {"nome": "Gestor Contratante", "org_id": contractor["id"], "papel": "GESTOR_CONTR"}))
        # 3. Gestor da fornecedora cadastra operador na mesma organização.
        operator_result = post("/api/supplier/operators", manager, {"nome": "Operador Integração"})
        operator = auth(operator_result)
        assert operator_result["org_id"] == supplier["id"]
        # Preparação do cadastro sintético de trabalhador (ainda sem tela própria no MVP).
        with db.tx() as conn:
            conn.execute("INSERT INTO workers (id,nome,contract_id) VALUES ('T900','Trabalhador Sintético',?)", (contract,))
        # 4. Operador envia PDF sintético; F2 e conciliação são reais, via leitor offline.
        point = "ESPELHO DE PONTO\nMatricula: T900\nCompetencia: 10/2026\nTOTAL DE HORAS EXTRAS: 12,00 h\nPagina 1 de 1"
        content = pdf(point, HOLERITE.format(t="T900", h="8,00"))
        upload = client.post("/api/supplier/batches", headers=operator, data={"contract_id": contract},
                             files={"file": ("integracao-seis-perfis.pdf", content, "application/pdf")})
        assert upload.status_code == 202, upload.text
        batch = upload.json()["batch_id"]
        assert client.get(f"/api/batches/{batch}", headers=manager).status_code == 200
        # Outro operador da mesma empresa pode consultar o envio.
        colleague = auth(post("/api/supplier/operators", manager, {"nome": "Colega Integração"}))
        assert len(client.get(f"/api/batches/{batch}/documents", headers=colleague).json()) == 2
        # 5. Analista publica; antes disso nada chega à contratante.
        assert client.get("/api/client/reports", headers=customer).json() == []
        analyses = client.get("/api/analyses", headers=analyst).json()
        assert len(analyses) == 1
        assert analyses[0]["resultado"]["tipo"] == "DIVERGENCIA_A_VERIFICAR"
        report = post("/api/reports", analyst, {"contract_id": contract, "competencia": "10/2026"})
        assert client.post(f"/api/reports/{report['id']}/publish", headers=analyst).status_code == 200
        # 6. Contratante recebe apenas a publicação do seu contrato.
        published = client.get("/api/client/reports", headers=customer).json()
        assert [r["id"] for r in published] == [report["id"]]
        assert published[0]["conteudo_json"]["resumo"]["com_divergencia"] == 1
        assert client.get("/api/client/overview", headers=customer).json()["resumo"]["taxa_divergencias"] == 1.0
        assert client.get(f"/api/batches/{batch}", headers=customer).status_code == 403
        # A Bernhoeft demo, outra empresa e a administração geral não recebem os documentos.
        assert client.get(f"/api/batches/{batch}", headers=headers("u-admin")).status_code == 403
        assert client.get(f"/api/batches/{batch}", headers=headers("u-oper-beta")).status_code == 404
        assert client.get(f"/api/batches/{batch}", headers=general).status_code == 403
        assert client.post(f"/api/reports/{report['id']}/publish", headers=operator).status_code == 403
        assert client.get("/api/platform/registry", headers=admin).status_code == 403
        assert client.get("/api/supplier/operators", headers=operator).status_code == 403
        assert client.get("/api/admin/registry", headers=manager).status_code == 403
        # Revogação pelo gestor encerra o acesso sem remover evidências.
        status = client.patch(f"/api/supplier/operators/{operator_result['id']}/status", headers=manager, json={"ativo": False})
        assert status.status_code == 200
        assert client.get("/api/me", headers=operator).status_code == 401
        assert client.get(f"/api/batches/{batch}", headers=colleague).status_code == 200
