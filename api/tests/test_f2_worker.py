"""F2 — worker: criar_lote, processamento, cache, retomada, consolidação e versões."""
import hashlib
import logging
import time

import pymupdf as fitz
import pytest

from docrisk_core import config, db
from docrisk_core.ai import ErroIATransitorio
from docrisk_core.ai.textlayer import TextLayerProvider, analisar_texto
from docrisk_core.auth import Usuario
from docrisk_core.contracts import Papel
from docrisk_core.pipeline import worker
from docrisk_core.pipeline.render import ArquivoInvalido

BETA = Usuario("u-oper-beta", "Operador Beta", "ORG-BETA", "FORNECEDORA", Papel.OPERADOR_FORN)
GAMA = Usuario("u-oper-gama", "Operador Gama", "ORG-GAMA", "FORNECEDORA", Papel.OPERADOR_FORN)

CONTRATO_P1 = "CONTRATO DE PRESTAÇÃO DE SERVIÇOS Nº 001/2026\nCláusula 1 — objeto\nPágina 1 de 2"
CONTRATO_P2 = "Cláusula 9 — foro\nAssinaturas das partes\nPágina 2 de 2"
PONTO_T001_P1 = ("ESPELHO DE PONTO\nMatrícula: T001\nCompetência: 10/2026\n"
                 "Data | Entrada | Saída\n01/10 | 08:00 | 19:00\nPágina 1 de 2")
PONTO_T001_P2 = "Matrícula: T001\n16/10 | 08:00 | 17:00\nTOTAL DE HORAS EXTRAS: 12,00 h\nPágina 2 de 2"
HOLERITE = ("DEMONSTRATIVO DE PAGAMENTO DE SALÁRIO\nMatrícula: {t}\nCompetência: 10/2026\n"
            "Proventos | Descontos\nSalário base | R$ 1.800,00\nHoras extras 50% | Ref.: {h} h | R$ 160,00\n"
            "Página 1 de 1")
NOTA = "anotações — conferir com o RH\nligar para o setor pessoal sobre o lote"
HOLERITE_ILEGIVEL = "DEMONSTRATIVO DE PAGAMENTO DE SALÁRIO\nMatrícula: {t}\nCompetência: 10/2026\nPágina 1 de 1"
PONTO_T003_INCOMPLETO = "ESPELHO DE PONTO\nMatrícula: T003\nCompetência: 10/2026\nEntrada 08:00\nPágina 1 de 2"


def pdf(*textos):
    doc = fitz.open()
    for t in textos:
        p = doc.new_page(width=595, height=842)
        y = 60
        for linha in t.split("\n"):
            p.insert_text((50, y), linha, fontsize=10)
            y += 16
    data = doc.tobytes()
    doc.close()
    return data


LOTE = [CONTRATO_P1, CONTRATO_P2, PONTO_T001_P1, PONTO_T001_P2, HOLERITE.format(t="T001", h="8,00"),
        NOTA, HOLERITE_ILEGIVEL.format(t="T002"), PONTO_T003_INCOMPLETO]


class Contador(TextLayerProvider):
    """Provedor de teste: regras de texto + contagem de chamadas + falha programada."""
    nome = "teste"
    modelo = "v1"

    def __init__(self, falhar_em=()):
        self.chamadas = []
        self.falhar_em = list(falhar_em)

    def analisar(self, png, texto_camada):
        self.chamadas.append(hashlib.sha256(png).hexdigest())
        for marcador in list(self.falhar_em):
            if marcador in (texto_camada or ""):
                self.falhar_em.remove(marcador)
                raise ErroIATransitorio("Gemini indisponível (simulado).")
        return analisar_texto(texto_camada or "")


@pytest.fixture
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "teste.sqlite")
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(config, "PAGES_DIR", tmp_path / "pages")
    monkeypatch.setattr(config, "SYNC", True)
    db.init_db()
    return tmp_path


def q(sql, *args):
    with db.tx() as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def documentos(batch_id):
    docs = q("SELECT * FROM documents WHERE batch_id = ? ORDER BY id", batch_id)
    for d in docs:
        d["paginas"] = [r["ordem"] for r in q(
            "SELECT p.ordem FROM doc_pages dp JOIN pages p ON p.id = dp.page_id"
            " WHERE dp.document_id = ? ORDER BY dp.posicao", d["id"])]
    return docs


def test_criar_lote_preserva_original_com_nome_seguro(banco):
    data = pdf(*LOTE)
    bid = worker.criar_lote(BETA, "CT-001", "../../segredo/lote.pdf", data)
    [lote] = q("SELECT * FROM batches WHERE id = ?", bid)
    assert lote["status"] == "RECEBIDO" and lote["total_pages"] == 8 and lote["tipo_arquivo"] == "PDF"
    assert lote["filename"] == "lote.pdf" and lote["uploaded_by"] == "u-oper-beta"
    assert lote["sha256"] == hashlib.sha256(data).hexdigest()
    caminho = banco / "uploads" / f"lote-{bid:06d}.pdf"
    assert lote["arquivo"] == str(caminho) and caminho.read_bytes() == data


def test_criar_lote_invalido_nao_grava_nada(banco):
    with pytest.raises(ArquivoInvalido):
        worker.criar_lote(BETA, "CT-001", "x.pdf", b"%PDF-1.4 quebrado")
    assert q("SELECT COUNT(*) AS n FROM batches")[0]["n"] == 0


def test_reenvio_guarda_issue_id(banco):
    bid = worker.criar_lote(BETA, "CT-001", "r.pdf", pdf(HOLERITE.format(t="T002", h="6,00")), issue_id=42)
    assert q("SELECT issue_id FROM batches WHERE id = ?", bid)[0]["issue_id"] == 42


def test_fluxo_completo_textlayer(banco):
    bid = worker.criar_lote(BETA, "CT-001", "lote.pdf", pdf(*LOTE))
    worker.processar_lote(bid, provedor=TextLayerProvider())
    assert q("SELECT status FROM batches WHERE id = ?", bid)[0]["status"] == "CONCLUIDO"
    paginas = q("SELECT ordem, status, texto, ms FROM pages WHERE batch_id = ? ORDER BY ordem", bid)
    assert [p["ordem"] for p in paginas] == list(range(1, 9))
    assert all(p["status"] == "OK" and p["ms"] is not None for p in paginas)

    docs = documentos(bid)
    resumo = [(d["paginas"], d["tipo"], d["worker_id"], d["status"]) for d in docs]
    assert resumo == [
        ([1, 2], "CONTRATO", None, "APTO"),
        ([3, 4], "ESPELHO_PONTO", "T001", "APTO"),
        ([5], "HOLERITE", "T001", "APTO"),
        ([6], "DESCONHECIDO", None, "REVISAO_HUMANA"),
        ([7], "HOLERITE", "T002", "PENDENTE_CORRECAO"),
        ([8], "ESPELHO_PONTO", "T003", "PENDENTE_CORRECAO"),
    ]
    assert '"horas_extras_h":12.0' in docs[1]["campos_json"]
    assert "legibilidade" in docs[4]["motivos_pendencia"] and "não recebida" in docs[5]["motivos_pendencia"]

    with db.tx() as conn:
        achados = conn.execute("SELECT page_id FROM page_fts WHERE page_fts MATCH 'demonstrativo'"
                               " AND contract_id = 'CT-001'").fetchall()
    assert len(achados) == 2  # holerites T001 e T002 pesquisáveis


def test_cache_evita_nova_chamada(banco):
    data = pdf(*LOTE[:5])
    leitor = Contador()
    worker.processar_lote(worker.criar_lote(BETA, "CT-001", "a.pdf", data), provedor=leitor)
    assert len(leitor.chamadas) == 5
    worker.processar_lote(worker.criar_lote(BETA, "CT-001", "b.pdf", data), provedor=leitor)
    assert len(leitor.chamadas) == 5  # mesmas páginas: tudo veio de ai_cache
    telemetria = q("SELECT cache_hit, provider, model, status, estimated_cost_usd "
                   "FROM ai_telemetry ORDER BY page_id")
    assert len(telemetria) == 10
    assert all(r["provider"] == "teste" and r["model"] == "v1" and r["status"] == "OK"
               for r in telemetria)
    assert [r["cache_hit"] for r in telemetria] == [0] * 5 + [1] * 5
    assert all(r["estimated_cost_usd"] == 0 for r in telemetria)


def test_telemetria_persiste_uso_e_custo_por_pagina(banco):
    class LeitorComUso(Contador):
        nome = "gemini"
        modelo = "modelo-teste"

        def analisar_com_proveniencia(self, png, texto_camada):
            analise = self.analisar(png, texto_camada)
            return analise, {
                "input_tokens": 10,
                "output_tokens": 2,
                "total_tokens": 12,
                "input_price_usd_per_million": 2.0,
                "output_price_usd_per_million": 4.0,
                "estimated_cost_usd": 0.000028,
            }

    leitor = LeitorComUso()
    bid = worker.criar_lote(BETA, "CT-001", "uso.pdf", pdf(NOTA))
    worker.processar_lote(bid, provedor=leitor)

    [registro] = q("SELECT provider, model, prompt_version, schema_version, input_tokens, "
                   "output_tokens, total_tokens, estimated_cost_usd, cache_hit, status "
                   "FROM ai_telemetry")
    assert (registro["provider"], registro["model"]) == ("gemini", "modelo-teste")
    assert (registro["prompt_version"], registro["schema_version"]) == ("p1", "s1")
    assert (registro["input_tokens"], registro["output_tokens"], registro["total_tokens"]) == (10, 2, 12)
    assert registro["estimated_cost_usd"] == pytest.approx(0.000028)
    assert registro["cache_hit"] == 0 and registro["status"] == "OK"


def test_retomada_le_so_a_pagina_que_falhou(banco):
    leitor = Contador(falhar_em=["Cláusula 9"])
    bid = worker.criar_lote(BETA, "CT-001", "c.pdf", pdf(CONTRATO_P1, CONTRATO_P2, NOTA))
    worker.processar_lote(bid, provedor=leitor)
    [lote] = q("SELECT status, erro FROM batches WHERE id = ?", bid)
    assert lote["status"] == "FALHA_PROCESSAMENTO" and "1 página" in lote["erro"]
    estados = [p["status"] for p in q("SELECT status FROM pages WHERE batch_id = ? ORDER BY ordem", bid)]
    assert estados == ["OK", "ERRO", "OK"]
    assert q("SELECT COUNT(*) AS n FROM documents WHERE batch_id = ?", bid)[0]["n"] == 0
    primeira_rodada = list(leitor.chamadas)

    worker.processar_lote(bid, provedor=leitor)
    assert q("SELECT status FROM batches WHERE id = ?", bid)[0]["status"] == "CONCLUIDO"
    assert len(leitor.chamadas) == len(primeira_rodada) + 1  # só a página 2 voltou ao leitor
    assert leitor.chamadas[-1] == primeira_rodada[1]
    assert [d["paginas"] for d in documentos(bid)] == [[1, 2], [3]]


def test_consolidacao_idempotente(banco):
    bid = worker.criar_lote(BETA, "CT-001", "d.pdf", pdf(*LOTE))
    worker.processar_lote(bid, provedor=TextLayerProvider())
    antes = documentos(bid)
    with db.tx() as conn:
        pares = worker.consolidar_lote(conn, bid)
        pares2 = worker.consolidar_lote(conn, bid)
    assert pares == pares2 == {("T001", "10/2026"), ("T002", "10/2026"), ("T003", "10/2026")}
    assert documentos(bid) == antes
    assert q("SELECT COUNT(*) AS n FROM doc_pages")[0]["n"] == 8
    worker.processar_lote(bid, provedor=TextLayerProvider())  # lote CONCLUIDO: nada muda
    assert documentos(bid) == antes


def test_reenvio_cria_nova_versao_e_preserva_a_anterior(banco):
    b1 = worker.criar_lote(GAMA, "CT-002", "h1.pdf", pdf(HOLERITE_ILEGIVEL.format(t="T101")))
    worker.processar_lote(b1, provedor=TextLayerProvider())
    [antigo] = documentos(b1)
    assert antigo["status"] == "PENDENTE_CORRECAO"

    [issue] = q("SELECT id FROM issues WHERE document_id = ?", antigo["id"])
    with db.tx() as conn:
        conn.execute("UPDATE issues SET status='REENVIADA' WHERE id=?", (issue["id"],))
    b2 = worker.criar_lote(GAMA, "CT-002", "h2.pdf", pdf(HOLERITE.format(t="T101", h="6,00")),
                           issue_id=issue["id"])
    worker.processar_lote(b2, provedor=TextLayerProvider())
    [novo] = documentos(b2)
    [antigo_depois] = documentos(b1)
    assert antigo_depois["status"] == "SUBSTITUIDO" and antigo_depois["campos_json"] == antigo["campos_json"]
    assert novo["status"] == "APTO" and novo["versao"] == 2 and novo["substitui_id"] == antigo["id"]


def test_documento_duplicado_preserva_vigente_e_vai_para_revisao(banco):
    primeiro = worker.criar_lote(BETA, "CT-001", "h1.pdf", pdf(HOLERITE.format(t="T001", h="6,00")))
    worker.processar_lote(primeiro, provedor=TextLayerProvider())
    [vigente] = documentos(primeiro)
    assert vigente["status"] == "APTO"

    segundo = worker.criar_lote(BETA, "CT-001", "h2.pdf", pdf(HOLERITE.format(t="T001", h="7,00")))
    worker.processar_lote(segundo, provedor=TextLayerProvider())
    [duplicado] = documentos(segundo)
    [vigente_depois] = documentos(primeiro)

    assert duplicado["status"] == "REVISAO_HUMANA"
    assert duplicado["versao"] == 1 and duplicado["substitui_id"] is None
    assert "Possível duplicidade" in duplicado["motivos_revisao"]
    assert vigente_depois["status"] == "APTO" and vigente_depois["campos_json"] == vigente["campos_json"]


def test_contrato_nao_mistura_lotes_de_outra_fornecedora(banco):
    b1 = worker.criar_lote(BETA, "CT-001", "x.pdf", pdf(HOLERITE.format(t="T101", h="1,00")))
    worker.processar_lote(b1, provedor=TextLayerProvider())
    [doc] = documentos(b1)
    assert doc["contract_id"] == "CT-001" and doc["status"] == "REVISAO_HUMANA"
    assert "não cadastrado" in doc["motivos_revisao"]
    with db.tx() as conn:
        assert conn.execute("SELECT contract_id FROM page_fts").fetchone()[0] == "CT-001"


def test_integracao_f3_pendente_nao_simula_resultado(banco, caplog, monkeypatch):
    caplog.set_level(logging.WARNING, logger="docrisk.pipeline.f3")
    from docrisk_core.pipeline import integracao_f3
    from docrisk_core.rules import conciliacao, pendencias

    def stub(*_a, **_k):
        raise NotImplementedError("Frente 3")
    for modulo, nome in ((conciliacao, "conciliar"), (pendencias, "criar_pendencia"),
                         (pendencias, "atualizar_por_nova_versao")):
        monkeypatch.setattr(modulo, nome, stub)
    integracao_f3._avisados.clear()
    bid = worker.criar_lote(BETA, "CT-001", "f.pdf", pdf(*LOTE))
    worker.processar_lote(bid, provedor=TextLayerProvider())
    assert q("SELECT COUNT(*) AS n FROM analyses")[0]["n"] == 0
    assert q("SELECT COUNT(*) AS n FROM issues")[0]["n"] == 0
    assert "Integração F3 pendente" in caplog.text


def test_f3_e_chamada_quando_existir(banco, monkeypatch):
    from docrisk_core.rules import conciliacao, pendencias
    conciliados, pendentes = [], []
    monkeypatch.setattr(conciliacao, "conciliar", lambda conn, c, w, comp: conciliados.append((c, w, comp)) or 1)
    monkeypatch.setattr(pendencias, "criar_pendencia", lambda conn, **kw: pendentes.append(kw) or 1)
    bid = worker.criar_lote(BETA, "CT-001", "g.pdf", pdf(*LOTE))
    worker.processar_lote(bid, provedor=TextLayerProvider())
    assert conciliados == [("CT-001", "T001", "10/2026"), ("CT-001", "T002", "10/2026"),
                           ("CT-001", "T003", "10/2026")]
    assert [(p["worker_id"], p["categoria"].value) for p in pendentes] == [
        ("T002", "ILEGIVEL"), ("T003", "PAGINA_FALTANTE")]
    assert pendentes[0]["evidencia"] == f"Lote {bid}, página(s) 7"


def test_erro_de_f3_nao_e_escondido(banco, monkeypatch):
    from docrisk_core.rules import conciliacao

    def quebra(*a):
        raise KeyError("coluna inexistente")
    monkeypatch.setattr(conciliacao, "conciliar", quebra)
    bid = worker.criar_lote(BETA, "CT-001", "h.pdf", pdf(*LOTE[2:5]))
    with pytest.raises(KeyError):
        worker.processar_lote(bid, provedor=TextLayerProvider())
    assert q("SELECT status FROM batches WHERE id = ?", bid)[0]["status"] == "FALHA_PROCESSAMENTO"
    assert q("SELECT COUNT(*) AS n FROM documents WHERE batch_id = ?", bid)[0]["n"] == 0  # rollback


def test_enfileirar_sincrono(banco, monkeypatch):
    from docrisk_core import ai
    ai.redefinir_provider()
    monkeypatch.setattr(config, "AI_PROVIDER", "textlayer")
    bid = worker.criar_lote(BETA, "CT-001", "s.pdf", pdf(CONTRATO_P1, CONTRATO_P2))
    worker.enfileirar(bid)
    assert q("SELECT status FROM batches WHERE id = ?", bid)[0]["status"] == "CONCLUIDO"
    ai.redefinir_provider()


def test_provedor_sem_configuracao_marca_falha(banco, monkeypatch):
    from docrisk_core import ai
    ai.redefinir_provider()
    monkeypatch.setattr(config, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    bid = worker.criar_lote(BETA, "CT-001", "k.pdf", pdf(CONTRATO_P1))
    worker.processar_lote(bid)
    [lote] = q("SELECT status, erro FROM batches WHERE id = ?", bid)
    assert lote["status"] == "FALHA_PROCESSAMENTO" and "GEMINI_API_KEY" in lote["erro"]
    ai.redefinir_provider()


def test_thread_retoma_lote_pendente_e_processa_novos(banco, monkeypatch):
    from docrisk_core import ai
    ai.redefinir_provider()
    monkeypatch.setattr(config, "AI_PROVIDER", "textlayer")
    monkeypatch.setattr(config, "SYNC", False)
    interrompido = worker.criar_lote(BETA, "CT-001", "i.pdf", pdf(CONTRATO_P1, CONTRATO_P2))
    try:
        assert worker.iniciar_worker() is True
        assert worker.iniciar_worker() is False  # não sobe duas threads
        novo = worker.criar_lote(BETA, "CT-001", "j.pdf", pdf(NOTA))
        worker.enfileirar(novo)
        limite = time.monotonic() + 15
        while time.monotonic() < limite:
            estados = {r["status"] for r in q("SELECT status FROM batches WHERE id IN (?, ?)", interrompido, novo)}
            if estados == {"CONCLUIDO"}:
                break
            time.sleep(0.1)
        assert estados == {"CONCLUIDO"}
    finally:
        worker.parar_worker()
        ai.redefinir_provider()


def test_mesmo_conteudo_enviado_de_novo_vira_nova_versao_sem_revisao(banco):
    # Ex.: o mesmo PDF reenviado (demo com cache). Não é ambiguidade: as páginas são idênticas.
    dados = pdf(HOLERITE.format(t="T001", h="6,00"))
    primeiro = worker.criar_lote(BETA, "CT-001", "h1.pdf", dados)
    worker.processar_lote(primeiro, provedor=TextLayerProvider())
    segundo = worker.criar_lote(BETA, "CT-001", "h1-de-novo.pdf", dados)
    worker.processar_lote(segundo, provedor=TextLayerProvider())
    [antigo] = documentos(primeiro)
    [novo] = documentos(segundo)
    assert antigo["status"] == "SUBSTITUIDO"
    assert novo["status"] == "APTO" and novo["versao"] == 2 and novo["substitui_id"] == antigo["id"]
    assert "Possível duplicidade" not in novo["motivos_revisao"]
