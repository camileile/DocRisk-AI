"""Garante que a base compartilhada (contratos + banco) continua de pé."""
from docrisk_core import db
from docrisk_core.contracts import AnalisePagina, TipoDocumento, TIPOS_FOCO


def test_analise_normaliza_saida_bruta_do_modelo():
    a = AnalisePagina.model_validate({
        "texto": "DEMONSTRATIVO DE PAGAMENTO",
        "tipo": "holerite",
        "pagina_x": "1", "pagina_de": 1,
        "trabalhador_id": " t001 ",
        "competencia": "Competência 10/2026",
        "legivel": "false",
        "qualidade": "1,7",
        "campos": {"horas_extras_h": "8,00 h", "horas_extras_valor": "R$ 1.160,50"},
    })
    assert a.tipo is TipoDocumento.HOLERITE
    assert a.trabalhador_id == "T001"
    assert a.competencia == "10/2026"
    assert a.legivel is False
    assert a.qualidade == 1.0
    assert a.campos.horas_extras_h == 8.0
    assert a.campos.horas_extras_valor == 1160.5


def test_analise_rejeita_lixo_sem_quebrar():
    a = AnalisePagina.model_validate({"tipo": "BOLETO", "competencia": "13/2026",
                                      "pagina_x": 3, "pagina_de": 2})
    assert a.tipo is TipoDocumento.DESCONHECIDO
    assert a.competencia is None
    assert a.pagina_x is None and a.pagina_de is None


def test_rotulos_do_sprint01_sao_traduzidos():
    assert AnalisePagina(tipo="FOLHA_PAGAMENTO").tipo is TipoDocumento.HOLERITE
    assert AnalisePagina(tipo="NAO_IDENTIFICADO").tipo is TipoDocumento.DESCONHECIDO
    assert TipoDocumento.HOLERITE in TIPOS_FOCO and TipoDocumento.CONTRATO not in TIPOS_FOCO


def test_banco_cria_esquema_e_dados_demo_idempotente():
    db.init_db()
    db.init_db()  # segunda vez não duplica nem troca tokens
    with db.tx() as conn:
        tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
        assert {"batches", "pages", "documents", "issues", "analyses", "reports",
                "audit", "ai_cache", "page_fts"} <= tabelas
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 6
        assert conn.execute("SELECT COUNT(*) FROM workers WHERE contract_id='CT-001'").fetchone()[0] == 5
        conn.execute("INSERT INTO page_fts (texto, page_id, contract_id) VALUES ('Competência outubro', 1, 'CT-001')")
        achou = conn.execute("SELECT page_id FROM page_fts WHERE page_fts MATCH 'competencia'").fetchall()
        assert len(achou) == 1  # busca ignora acento
