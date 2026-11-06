"""Dashboard do Analista: cobertura, segurança entre organizações e filtros."""
import json

from fastapi.testclient import TestClient

from docrisk_core import db
from docrisk_core.api import app
from test_f2_worker import banco  # noqa: F401 (fixture de SQLite de testes)


def _token(uid: str) -> dict[str, str]:
    with db.tx() as conn:
        row = conn.execute("SELECT token FROM users WHERE id=?", (uid,)).fetchone()
    return {"Authorization": "Bearer " + row["token"]}


def _registrar_analise(
    conn, contrato: str, trabalhador: str, competencia: str,
    status: str, tipo: str, horas: float | None = None,
):
    conn.execute(
        "INSERT INTO analyses (contract_id, worker_id, competencia, status, "
        "resultado_json, insumos_json, regra_versao, atual, created_at) "
        "VALUES (?, ?, ?, ?, ?, '[]', 'HE-CMP-v1', 1, '2026-11-06T01:00:00')",
        (contrato, trabalhador, competencia, status,
         json.dumps({"tipo": tipo, "diferenca_h": horas})),
    )


def test_dashboard_filtros_competencia_e_metricas_sem_inventar_valores(banco):
    with db.tx() as conn:
        _registrar_analise(conn, "CT-001", "T001", "10/2026",
                           "ANALISADA", "DIVERGENCIA_A_VERIFICAR", 4)
        _registrar_analise(conn, "CT-001", "T002", "10/2026",
                           "ANALISADA", "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS", 0)
        _registrar_analise(conn, "CT-001", "T003", "10/2026",
                           "BLOQUEADA_PENDENCIA", "NAO_AVALIADO")
        _registrar_analise(conn, "CT-002", "T101", "10/2026",
                           "ANALISADA", "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS", 0)
        _registrar_analise(conn, "CT-002", "T101", "09/2026",
                           "ANALISADA", "DIVERGENCIA_A_VERIFICAR", -2)
        conn.execute(
            "INSERT INTO issues (contract_id, document_id, worker_id, competencia, "
            "tipo_documento, categoria, motivo, acao, status, created_at, updated_at) "
            "VALUES ('CT-001', NULL, 'T003', '10/2026', 'HOLERITE', 'DOCUMENTO_AUSENTE', "
            "'Ausente', 'Enviar', 'ABERTA', '2026-11-06', '2026-11-06')"
        )

    with TestClient(app) as client:
        analista = _token("u-analista")
        response = client.get("/api/analyst/overview", headers=analista)
        assert response.status_code == 200, response.text
        dashboard = response.json()
        assert dashboard["filtros"]["competencia_selecionada"] == "10/2026"
        assert dashboard["filtros"]["competencias"] == ["10/2026", "09/2026"]
        assert len(dashboard["filtros"]["contratantes"]) == 1
        assert len(dashboard["filtros"]["fornecedoras"]) == 2
        assert dashboard["resumo"] == {
            "cadastrados": 6, "avaliados": 3, "divergencias": 1,
            "taxa_divergencias": 0.3333, "cobertura": 0.5,
            "horas_divergentes": 4.0, "divergencias_sem_horas": 0,
            "pendencias_criticas": 1, "pendencias_abertas": 1,
        }
        assert [item["competencia"] for item in dashboard["evolucao"]] == [
            "09/2026", "10/2026",
        ]

        beta = client.get("/api/analyst/overview", headers=analista, params={
            "contratante_id": "ORG-ALFA", "fornecedora_id": "ORG-BETA",
            "competencia": "10/2026", "contract_id": "CT-001",
        })
        assert beta.status_code == 200
        assert beta.json()["resumo"]["cadastrados"] == 5
        assert beta.json()["resumo"]["avaliados"] == 2
        assert beta.json()["resumo"]["taxa_divergencias"] == 0.5
        assert beta.json()["resumo"]["cobertura"] == 0.4

        gama = client.get("/api/analyst/overview", headers=analista, params={
            "fornecedora_id": "ORG-GAMA", "competencia": "10/2026",
        })
        assert gama.status_code == 200
        assert gama.json()["resumo"]["cobertura"] == 1.0
        assert gama.json()["resumo"]["taxa_divergencias"] == 0.0
        assert gama.json()["resumo"]["horas_divergentes"] == 0.0

        setembro = client.get("/api/analyst/overview", headers=analista, params={
            "fornecedora_id": "ORG-GAMA", "competencia": "09/2026",
        })
        assert setembro.status_code == 200
        assert setembro.json()["resumo"]["horas_divergentes"] == 2.0
        assert setembro.json()["resumo"]["taxa_divergencias"] == 1.0


def test_dashboard_isola_papeis_e_nao_exibe_dados_ao_filtrar_empresa_inexistente(banco):
    with TestClient(app) as client:
        for role in ("u-admin", "u-oper-beta", "u-gestor-beta", "u-gestor-alfa"):
            response = client.get("/api/analyst/overview", headers=_token(role))
            assert response.status_code == 403, (role, response.text)
        assert client.get("/api/analyst/overview").status_code == 401

        analista = _token("u-analista")
        desconhecida = client.get("/api/analyst/overview", headers=analista, params={
            "contratante_id": "ORG-EXTERNA",
        })
        assert desconhecida.status_code == 200
        assert desconhecida.json()["resumo"]["cadastrados"] == 0
        assert desconhecida.json()["resumo"]["taxa_divergencias"] is None
        assert desconhecida.json()["resumo"]["cobertura"] is None
        assert desconhecida.json()["filtros"]["contratos"] == []

        assert client.get("/api/analyst/overview", headers=analista, params={
            "competencia": "13/2026",
        }).status_code == 422
