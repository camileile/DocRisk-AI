"""Parecer à contratante. Dono: FRENTE 3 (a rota de publicação é da frente 1).

Spec 7.2: só o Analista Bernhoeft publica; a publicação grava snapshot imutável;
correção posterior = nova versão; a contratante nunca vê rascunho.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from .. import db
from ..contracts import REGRA_CONCILIACAO, ResultadoConciliacao, StatusConciliacao

ESCOPO = ("Conferência documental de espelho de ponto, holerite e comprovante de pagamento, por "
          "trabalhador e competência, com comparação da quantidade de horas extras registradas no "
          "ponto e informadas no holerite.")
LIMITACOES = [
    "Divergências são indícios a conferir, não constituem conclusão jurídica nem passivo trabalhista.",
    "Diferenças podem decorrer de compensação, banco de horas ou pagamento em outra competência.",
    "Valores em reais não são comparados com quantidades de horas.",
    "Trabalhadores com documentação bloqueada ou em revisão não foram avaliados e não contam como sem divergência.",
    "A ausência de comprovante de pagamento não comprova atraso salarial.",
    "Leitura automatizada de documentos sujeita a revisão humana; dados de demonstração são fictícios.",
]


def _evidencias(insumos_json: str) -> list[dict[str, Any]]:
    try:
        insumos = json.loads(insumos_json or "[]")
    except (TypeError, ValueError):
        return []
    return [{"tipo": i.get("tipo"), "documento": i.get("doc_id"), "versao": i.get("versao"),
             "lote": i.get("batch_id"), "paginas": i.get("paginas", [])} for i in insumos]


def snapshot_parecer(conn: sqlite3.Connection, contract_id: str, competencia: str) -> dict[str, Any]:
    """Monta o conteúdo do parecer a partir das análises ATUAIS do contrato/competência.

    Conteúdo mínimo: contratante, fornecedora, contrato, competência, data, regra usada,
    escopo e limitações, resumo (avaliados / bloqueados / em revisão / com divergência /
    dados insuficientes / sem divergência), itens por trabalhador com evidências.
    Bloqueados aparecem nos denominadores, nunca como regulares.
    Sem valores em R$ e sem texto de OCR.
    """
    contrato = conn.execute(
        "SELECT c.id, c.nome, ct.nome AS contratante, f.nome AS fornecedora FROM contracts c"
        " JOIN organizations ct ON ct.id=c.contratante_id JOIN organizations f ON f.id=c.fornecedora_id"
        " WHERE c.id=?", (contract_id,)).fetchone()
    if contrato is None:
        raise LookupError(f"Contrato {contract_id} não existe")

    analises = {r["worker_id"]: r for r in conn.execute(
        "SELECT * FROM analyses WHERE contract_id=? AND competencia=? AND atual=1",
        (contract_id, competencia))}
    trabalhadores = {r["id"]: r["nome"] for r in conn.execute(
        "SELECT id, nome FROM workers WHERE contract_id=? ORDER BY id", (contract_id,))}
    # Trabalhadores com análise mas fora do cadastro também entram (não somem do denominador).
    for worker_id in analises:
        trabalhadores.setdefault(worker_id, worker_id)

    resumo = {"trabalhadores": len(trabalhadores), "avaliados": 0, "bloqueados": 0, "em_revisao": 0,
              "aguardando_documentos": 0, "com_divergencia": 0, "dados_insuficientes": 0,
              "sem_divergencia": 0}
    itens = []
    for worker_id in sorted(trabalhadores):
        analise = analises.get(worker_id)
        if analise is None:
            resumo["aguardando_documentos"] += 1
            itens.append({"trabalhador_id": worker_id, "situacao": StatusConciliacao.AGUARDANDO_DOCUMENTOS.value,
                          "resultado": ResultadoConciliacao.NAO_AVALIADO.value,
                          "detalhe": "Nenhum documento de foco recebido para a competência.",
                          "horas_ponto": None, "horas_folha": None, "diferenca_h": None,
                          "comprovante_presente": False, "evidencias": []})
            continue
        resultado = json.loads(analise["resultado_json"] or "{}")
        status = analise["status"]
        tipo = resultado.get("tipo", ResultadoConciliacao.NAO_AVALIADO.value)
        if status == StatusConciliacao.BLOQUEADA_PENDENCIA.value:
            resumo["bloqueados"] += 1
            tipo = ResultadoConciliacao.NAO_AVALIADO.value
        elif status == StatusConciliacao.REVISAO_HUMANA.value:
            resumo["em_revisao"] += 1
            tipo = ResultadoConciliacao.NAO_AVALIADO.value
        elif status == StatusConciliacao.ANALISADA.value:
            resumo["avaliados"] += 1
            chave = {
                ResultadoConciliacao.DIVERGENCIA_A_VERIFICAR.value: "com_divergencia",
                ResultadoConciliacao.DADOS_INSUFICIENTES.value: "dados_insuficientes",
                ResultadoConciliacao.SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS.value: "sem_divergencia",
            }.get(tipo)
            if chave:
                resumo[chave] += 1
        else:
            resumo["aguardando_documentos"] += 1
        itens.append({
            "trabalhador_id": worker_id,
            "situacao": status,
            "resultado": tipo,
            "detalhe": resultado.get("detalhe", ""),
            "horas_ponto": resultado.get("horas_ponto"),
            "horas_folha": resultado.get("horas_folha"),
            "diferenca_h": resultado.get("diferenca_h"),
            "comprovante_presente": bool((resultado.get("comprovante") or {}).get("presente")),
            "evidencias": _evidencias(analise["insumos_json"]),
            "analise_id": int(analise["id"]),
        })

    return {
        "contrato": {"id": contrato["id"], "nome": contrato["nome"]},
        "contratante": contrato["contratante"],
        "fornecedora": contrato["fornecedora"],
        "competencia": competencia,
        "gerado_em": db.agora(),
        "regra": REGRA_CONCILIACAO,
        "escopo": ESCOPO,
        "limitacoes": LIMITACOES,
        "resumo": resumo,
        "itens": itens,
    }
