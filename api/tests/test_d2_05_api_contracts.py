from fastapi.testclient import TestClient

from docrisk_core.api import app
from test_analyst_overview import _token
from test_f2_worker import banco  # noqa: F401


def test_report_routes_validate_competence_and_return_content_as_object(banco):
    analyst = _token("u-analista")
    contractor = _token("u-gestor-alfa")
    payload = {"contract_id": "CT-001", "competencia": "10/2026", "observacoes": "Conferido"}

    with TestClient(app) as client:
        for competencia in ("1/2026", "13/2026", "10-2026", "00/2026"):
            invalid = client.post(
                "/api/reports", headers=analyst,
                json={**payload, "competencia": competencia},
            )
            assert invalid.status_code == 422, competencia

        invalid_id = client.post(
            "/api/reports", headers=analyst,
            json={**payload, "contract_id": "contrato-001"},
        )
        assert invalid_id.status_code == 422

        created = client.post("/api/reports", headers=analyst, json=payload)
        assert created.status_code == 201, created.text
        draft = created.json()
        assert draft["status"] == "RASCUNHO"
        assert draft["conteudo_json"] == {}

        preview = client.get(f"/api/reports/{draft['id']}/preview", headers=analyst)
        published = client.post(f"/api/reports/{draft['id']}/publish", headers=analyst,
                                json={"conteudo_sha256": preview.json()["conteudo_sha256"]})
        assert published.status_code == 200, published.text
        result = published.json()
        assert result["status"] == "APROVADO_PUBLICADO"
        assert isinstance(result["conteudo_json"], dict)
        assert {"contrato", "contratante", "fornecedora", "competencia", "resumo", "itens"} <= result["conteudo_json"].keys()

        analyst_list = client.get("/api/reports", headers=analyst)
        client_list = client.get("/api/client/reports", headers=contractor)

    assert isinstance(analyst_list.json()[0]["conteudo_json"], dict)
    assert isinstance(client_list.json()[0]["conteudo_json"], dict)


def test_report_openapi_advertises_the_same_response_model():
    openapi = app.openapi()
    paths = openapi["paths"]
    expected_ref = "#/components/schemas/ReportResponse"

    assert paths["/api/reports"]["post"]["responses"]["201"]["content"]["application/json"]["schema"]["$ref"] == expected_ref
    assert paths["/api/reports/{report_id}/publish"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] == expected_ref
    assert paths["/api/reports"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["items"]["$ref"] == expected_ref
