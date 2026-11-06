"""F3 — regras: conciliação, pendências, parecer, métricas e o lote sintético ponta a ponta.

O fluxo integrado usa o lote gerado por scripts/gerar_lote_demo.py, o leitor offline
(textlayer, sem IA) e a API real com tokens de cada perfil. O gabarito é só comparado,
nunca usado para produzir resultados.
"""
import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from docrisk_core import db
from docrisk_core.api import app
from docrisk_core.contracts import CamposPagina, ResultadoConciliacao
from docrisk_core.rules import conciliacao, metricas, parecer, pendencias
from test_f2_worker import banco, q  # noqa: F401  (fixture)

R = ResultadoConciliacao


# ---------------------------------------------------------------------------
# Regra pura
# ---------------------------------------------------------------------------
def test_divergencia_de_4h_e_indicio_nunca_horas_nao_pagas():
    r = conciliacao.avaliar_horas_extras(CamposPagina(horas_extras_h=12), CamposPagina(horas_extras_h=8))
    assert r["tipo"] is R.DIVERGENCIA_A_VERIFICAR and r["diferenca_h"] == 4
    assert "diferença de 4 h a conferir" in r["detalhe"]
    assert "não pag" not in r["detalhe"].lower()


def test_reais_nunca_sao_comparados_com_horas():
    r = conciliacao.avaliar_horas_extras(CamposPagina(horas_extras_h=10),
                                         CamposPagina(horas_extras_valor=230.0))
    assert r["tipo"] is R.DADOS_INSUFICIENTES and r["diferenca_h"] is None
    assert "230" not in r["detalhe"] and "R$" not in r["detalhe"]


def test_iguais_sem_divergencia_e_sem_ponto_dados_insuficientes():
    assert conciliacao.avaliar_horas_extras(CamposPagina(horas_extras_h=4), CamposPagina(horas_extras_h=4))[
        "tipo"] is R.SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS
    assert conciliacao.avaliar_horas_extras(CamposPagina(), CamposPagina(horas_extras_h=4))[
        "tipo"] is R.DADOS_INSUFICIENTES


def test_folha_acima_do_ponto_tambem_e_divergencia():
    r = conciliacao.avaliar_horas_extras(CamposPagina(horas_extras_h=2), CamposPagina(horas_extras_h=3.5))
    assert r["tipo"] is R.DIVERGENCIA_A_VERIFICAR and r["diferenca_h"] == -1.5


# ---------------------------------------------------------------------------
# Lote sintético ponta a ponta
# ---------------------------------------------------------------------------
def _gerador():
    caminho = Path(__file__).resolve().parents[1] / "scripts" / "gerar_lote_demo.py"
    spec = importlib.util.spec_from_file_location("gerar_lote_demo", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def lote(tmp_path):
    return _gerador().gerar(tmp_path / "lote")


def _h(cliente_id):
    with db.tx() as conn:
        token = conn.execute("SELECT token FROM users WHERE id=?", (cliente_id,)).fetchone()[0]
    return {"Authorization": f"Bearer {token}"}


def _enviar(client, caminho, usuario="u-oper-beta", contrato="CT-001"):
    with open(caminho, "rb") as f:
        return client.post("/api/supplier/batches", headers=_h(usuario), data={"contract_id": contrato},
                           files={"file": (Path(caminho).name, f, "application/pdf")})


def _analises(client):
    r = client.get("/api/analyses", headers=_h("u-analista"))
    assert r.status_code == 200
    return {a["worker_id"]: a for a in r.json()}


def test_lote_demo_confere_com_gabarito_e_fluxo_completo(banco, lote):  # noqa: F811
    gabarito = json.loads(lote["gabarito.json"].read_text(encoding="utf-8"))
    with TestClient(app) as client:
        # 1. upload (processamento síncrono nos testes) ----------------------
        r = _enviar(client, lote["lote_demo.pdf"])
        assert r.status_code == 202, r.text
        batch_id = r.json()["batch_id"]
        assert client.get(f"/api/batches/{batch_id}", headers=_h("u-analista")).json()["status"] == "CONCLUIDO"

        # 2. fronteiras, tipos, trabalhador e status conferem com o gabarito ---
        docs = client.get(f"/api/batches/{batch_id}/documents", headers=_h("u-analista")).json()
        obtido = [([p["ordem"] for p in d["paginas"]], d["tipo"], d["worker_id"], d["status"]) for d in docs]
        esperado = [(g["paginas"], g["tipo"], g["trabalhador_id"], g["status_esperado"])
                    for g in gabarito["documentos"]]
        assert obtido == esperado

        # 3. conciliação com bloqueio seletivo --------------------------------
        analises = _analises(client)
        for worker_id, alvo in gabarito["conciliacao"].items():
            a = analises[worker_id]
            assert a["status"] == alvo["status"], worker_id
            if a["status"] == "ANALISADA":
                assert a["resultado"]["tipo"] == alvo["resultado"], worker_id
            if "diferenca_h" in alvo:
                assert a["resultado"]["diferenca_h"] == alvo["diferenca_h"]
            assert a["regra_versao"] == "HE-CMP-v1" and a["insumos"]
        assert analises["T001"]["resultado"]["comprovante"]["presente"] is True
        assert analises["T005"]["resultado"]["comprovante"]["presente"] is False

        # 4. pendências: só erros objetivos chegam à fornecedora --------------
        sup = client.get("/api/supplier/issues", headers=_h("u-oper-beta")).json()
        assert sorted((i["worker_id"], i["categoria"], i["status"]) for i in sup) == [
            ("T002", "ILEGIVEL", "NOTIFICADA"), ("T003", "PAGINA_FALTANTE", "NOTIFICADA")]
        assert all(i["prazo"] and i["historico"] for i in sup)
        assert client.get("/api/supplier/issues", headers=_h("u-oper-gama")).json() == []

        # 5. busca textual pesquisável e isolada por contrato -----------------
        achados = client.get("/api/search", params={"q": "espelho"}, headers=_h("u-analista")).json()
        assert achados and all(a["contract_id"] == "CT-001" for a in achados)
        assert client.get("/api/search", params={"q": "espelho"}, headers=_h("u-oper-gama")).json() == []

        # 6. revisão humana: anotação desconhecida está na fila ---------------
        fila = client.get("/api/review-queue", headers=_h("u-analista")).json()
        assert [[p["ordem"] for p in d["paginas"]] for d in fila] == [[14]]

        # 7. métricas a partir dos registros ---------------------------------
        m = client.get("/api/bernhoeft/metrics", headers=_h("u-analista")).json()
        assert m["conciliacao"]["pares"] == 5 and m["conciliacao"]["bloqueados"] == 2
        assert m["conciliacao"]["divergencias_a_verificar"] == 1
        assert m["conciliacao"]["por_resultado"]["SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS"] == 1
        assert m["pendencias"]["em_aberto"] == 2 and m["paginas"]["total"] == 16

        # 8. reenvio corrigido reprocessa só o T002 ---------------------------
        issue_t002 = next(i for i in sup if i["worker_id"] == "T002")
        antes = {w: a["id"] for w, a in analises.items()}
        with open(lote["reenvio_holerite_T002.pdf"], "rb") as f:
            r = client.post(f"/api/issues/{issue_t002['id']}/resubmit", headers=_h("u-oper-beta"),
                            files={"file": ("reenvio.pdf", f, "application/pdf")})
        assert r.status_code == 202, r.text
        depois = _analises(client)
        alvo = gabarito["apos_reenvio_T002"]["T002"]
        assert depois["T002"]["status"] == alvo["status"]
        assert depois["T002"]["resultado"]["tipo"] == alvo["resultado"]
        assert depois["T002"]["id"] != antes["T002"]
        assert all(depois[w]["id"] == antes[w] for w in ("T001", "T003", "T004", "T005"))
        issue = next(i for i in client.get("/api/issues", headers=_h("u-analista")).json()
                     if i["id"] == issue_t002["id"])
        assert issue["status"] == "RESOLVIDA" and issue["resolved_at"]
        assert [h["status"] for h in issue["historico"]] == ["NOTIFICADA", "REENVIADA", "RESOLVIDA"]
        holerites = q("SELECT versao, status FROM documents WHERE worker_id='T002' AND tipo='HOLERITE' ORDER BY id")
        assert holerites == [{"versao": 1, "status": "SUBSTITUIDO"}, {"versao": 2, "status": "APTO"}]

        # 9. parecer: rascunho invisível à contratante; publicação = snapshot --
        rascunho = client.post("/api/reports", headers=_h("u-analista"),
                               json={"contract_id": "CT-001", "competencia": "10/2026"}).json()
        assert client.get("/api/client/reports", headers=_h("u-gestor-alfa")).json() == []
        assert client.post(f"/api/reports/{rascunho['id']}/publish", headers=_h("u-gestor-alfa")).status_code == 403
        pub = client.post(f"/api/reports/{rascunho['id']}/publish", headers=_h("u-analista"))
        assert pub.status_code == 200
        publicados = client.get("/api/client/reports", headers=_h("u-gestor-alfa")).json()
        assert len(publicados) == 1
        conteudo = publicados[0]["conteudo_json"]
        assert conteudo["resumo"] == {"trabalhadores": 5, "avaliados": 4, "bloqueados": 1, "em_revisao": 0,
                                      "aguardando_documentos": 0, "com_divergencia": 1,
                                      "dados_insuficientes": 1, "sem_divergencia": 2}
        texto = json.dumps(conteudo, ensure_ascii=False)
        assert "R$" not in texto and "valor_pago" not in texto and "Proventos" not in texto

        # 10. contratante não acessa páginas, documentos nem busca ------------
        page_id = docs[0]["paginas"][0]["page_id"]
        assert client.get(f"/api/pages/{page_id}/image", headers=_h("u-gestor-alfa")).status_code == 403
        assert client.get(f"/api/batches/{batch_id}/documents", headers=_h("u-gestor-alfa")).status_code == 403
        assert client.get(f"/api/batches/{batch_id}", headers=_h("u-oper-gama")).status_code == 404

        # 11. reprocessar o mesmo lote não duplica documentos nem análises -----
        from docrisk_core.pipeline import worker
        n_docs = q("SELECT COUNT(*) AS n FROM documents")[0]["n"]
        n_an = q("SELECT COUNT(*) AS n FROM analyses")[0]["n"]
        with db.tx() as conn:
            worker.consolidar_lote(conn, batch_id)
            for w in ("T001", "T004", "T005"):
                conciliacao.conciliar(conn, "CT-001", w, "10/2026")
        assert q("SELECT COUNT(*) AS n FROM documents")[0]["n"] == n_docs
        assert q("SELECT COUNT(*) AS n FROM analyses")[0]["n"] == n_an

        # 12. arquivo corrompido é recusado sem criar lote ---------------------
        n_lotes = q("SELECT COUNT(*) AS n FROM batches")[0]["n"]
        assert _enviar(client, lote["arquivo_corrompido.pdf"]).status_code == 422
        assert q("SELECT COUNT(*) AS n FROM batches")[0]["n"] == n_lotes


def test_documento_ausente_bloqueia_e_resolve_quando_chega(banco):  # noqa: F811
    with db.tx() as conn:
        aid = conciliacao.conciliar(conn, "CT-001", "T005", "10/2026")
        a = conn.execute("SELECT status FROM analyses WHERE id=?", (aid,)).fetchone()
        assert a["status"] == "BLOQUEADA_PENDENCIA"
        abertas = conn.execute("SELECT * FROM issues WHERE categoria='DOCUMENTO_AUSENTE'").fetchall()
        assert {i["tipo_documento"] for i in abertas} == {"ESPELHO_PONTO", "HOLERITE"}
        assert all(i["status"] == "ABERTA" for i in abertas)
        # idempotente: chamar de novo não duplica pendência nem análise
        assert conciliacao.conciliar(conn, "CT-001", "T005", "10/2026") == aid
        assert conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0] == 2
        pendencias.resolver_ausencia(conn, "CT-001", "T005", "10/2026", "HOLERITE")
        st = dict(conn.execute("SELECT tipo_documento, status FROM issues").fetchall())
        assert st == {"ESPELHO_PONTO": "ABERTA", "HOLERITE": "RESOLVIDA"}


def test_metricas_sem_contratos_e_parecer_de_contrato_vazio(banco):  # noqa: F811
    with db.tx() as conn:
        m = metricas.calcular_metricas(conn, [])
        assert m["documentos"]["logicos"] == 0 and m["conciliacao"]["pares"] == 0
        s = parecer.snapshot_parecer(conn, "CT-001", "10/2026")
        assert s["resumo"]["trabalhadores"] == 5 and s["resumo"]["aguardando_documentos"] == 5
        assert s["resumo"]["sem_divergencia"] == 0
