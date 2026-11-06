"""Conciliação de horas extras por trabalhador + competência. Dono: FRENTE 3.

Spec 4.2, 5.1 e 5.2. Bloqueio seletivo: um par com problema para, os outros seguem.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from .. import db
from ..contracts import (
    REGRA_CONCILIACAO, CamposPagina, CategoriaPendencia, ResultadoConciliacao, StatusConciliacao,
    StatusDocumento, TipoDocumento,
)
from . import pendencias

#: Diferenças menores que isto (em horas) são arredondamento, não divergência.
TOLERANCIA_H = 0.01

NOMES = {
    TipoDocumento.ESPELHO_PONTO: "espelho de ponto",
    TipoDocumento.HOLERITE: "holerite",
    TipoDocumento.COMPROVANTE_PAGAMENTO: "comprovante de pagamento",
}
NECESSARIOS = (TipoDocumento.ESPELHO_PONTO, TipoDocumento.HOLERITE)


def _h(valor: float) -> str:
    """12.0 -> '12 h'; 7.5 -> '7,5 h'."""
    texto = f"{valor:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{texto} h"


def avaliar_horas_extras(ponto: CamposPagina, folha: CamposPagina) -> dict[str, Any]:
    """Função PURA. Devolve {"tipo": ResultadoConciliacao, "detalhe", "horas_ponto",
    "horas_folha", "diferenca_h"}.

    - ponto sem horas_extras_h -> DADOS_INSUFICIENTES
    - folha só com horas_extras_valor (R$) -> DADOS_INSUFICIENTES, sem comparar R$ com h
      (o valor em R$ NÃO entra no "detalhe": o parecer da contratante não leva R$)
    - diferença != 0 -> DIVERGENCIA_A_VERIFICAR, texto de indício ("diferença de 4 h a
      conferir; pode haver compensação ou banco de horas"), nunca "horas não pagas"
    - iguais -> SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS (nunca "regular")
    """
    hp, hf = ponto.horas_extras_h, folha.horas_extras_h
    base = {"horas_ponto": hp, "horas_folha": hf, "diferenca_h": None}
    if hp is None:
        return {**base, "tipo": ResultadoConciliacao.DADOS_INSUFICIENTES,
                "detalhe": "O espelho de ponto não traz total de horas extras identificável; "
                           "comparação não realizada."}
    if hf is None:
        if folha.horas_extras_valor is not None:
            detalhe = ("O holerite informa horas extras apenas em valor monetário, sem a quantidade "
                       "de horas; valores em reais não são comparados com horas.")
        else:
            detalhe = "O holerite não traz quantidade de horas extras identificável; comparação não realizada."
        return {**base, "tipo": ResultadoConciliacao.DADOS_INSUFICIENTES, "detalhe": detalhe}

    diferenca = round(hp - hf, 2)
    base["diferenca_h"] = diferenca
    if abs(diferenca) < TOLERANCIA_H:
        return {**base, "tipo": ResultadoConciliacao.SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS,
                "detalhe": f"Ponto e holerite informam {_h(hp)} extras; sem divergência nos campos comparados."}
    if diferenca > 0:
        detalhe = (f"Ponto registra {_h(hp)} extras e o holerite {_h(hf)}: diferença de {_h(diferenca)} "
                   "a conferir; pode haver compensação, banco de horas ou pagamento em outra competência.")
    else:
        detalhe = (f"Holerite informa {_h(hf)} extras e o ponto {_h(hp)}: diferença de {_h(-diferenca)} "
                   "a conferir; pode haver pagamento de competência anterior ou erro de registro.")
    return {**base, "tipo": ResultadoConciliacao.DIVERGENCIA_A_VERIFICAR, "detalhe": detalhe}


def _vigente(conn: sqlite3.Connection, contract_id: str, worker_id: str, competencia: str,
             tipo: TipoDocumento) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM documents WHERE contract_id=? AND worker_id=? AND competencia=? AND tipo=?"
        " AND status<>? ORDER BY versao DESC, id DESC LIMIT 1",
        (contract_id, worker_id, competencia, tipo.value, StatusDocumento.SUBSTITUIDO.value)).fetchone()


def _insumo(conn: sqlite3.Connection, doc: sqlite3.Row) -> dict[str, Any]:
    paginas = [int(r[0]) for r in conn.execute(
        "SELECT p.ordem FROM doc_pages dp JOIN pages p ON p.id=dp.page_id WHERE dp.document_id=?"
        " ORDER BY dp.posicao", (doc["id"],))]
    return {"doc_id": int(doc["id"]), "tipo": doc["tipo"], "versao": int(doc["versao"]),
            "batch_id": int(doc["batch_id"]), "status": doc["status"], "paginas": paginas}


def conciliar(conn: sqlite3.Connection, contract_id: str, worker_id: str, competencia: str) -> int:
    """Recalcula a análise de UM par e devolve o id da nova linha em `analyses`.

    Usa a versão vigente (status != SUBSTITUIDO) de ESPELHO_PONTO e HOLERITE.
    - documento ausente -> BLOQUEADA_PENDENCIA + pendência DOCUMENTO_AUSENTE (status ABERTA)
    - documento PENDENTE_CORRECAO -> BLOQUEADA_PENDENCIA
    - documento REVISAO_HUMANA -> REVISAO_HUMANA
    - os dois APTO -> ANALISADA com avaliar_horas_extras
    Registra comprovante presente/ausente (ausência NÃO prova atraso salarial).
    Marca a análise anterior do par como atual=0; grava insumos e REGRA_CONCILIACAO.

    Idempotente: se o resultado e os insumos forem iguais aos da análise atual, nada é
    gravado e o id atual é devolvido (reprocessar não duplica análises).
    """
    docs = {tipo: _vigente(conn, contract_id, worker_id, competencia, tipo) for tipo in NOMES}
    motivos: list[str] = []
    bloqueado = em_revisao = False

    for tipo in NECESSARIOS:
        doc = docs[tipo]
        nome = NOMES[tipo]
        if doc is None:
            bloqueado = True
            motivos.append(f"{nome.capitalize()} da competência {competencia} não recebido")
            pendencias.criar_pendencia(
                conn, contract_id=contract_id, document_id=None, worker_id=worker_id,
                competencia=competencia, tipo_documento=tipo.value,
                categoria=CategoriaPendencia.DOCUMENTO_AUSENTE,
                motivo=f"{nome.capitalize()} do trabalhador {worker_id}, competência {competencia}, não recebido.",
                evidencia=f"Trabalhador {worker_id}, competência {competencia}",
                acao=f"Enviar o {nome} do trabalhador {worker_id} da competência {competencia}.")
            continue
        pendencias.resolver_ausencia(conn, contract_id, worker_id, competencia, tipo.value)
        if doc["status"] == StatusDocumento.PENDENTE_CORRECAO.value:
            bloqueado = True
            motivos.append(f"{nome.capitalize()} com pendência de correção pela fornecedora")
        elif doc["status"] == StatusDocumento.REVISAO_HUMANA.value:
            em_revisao = True
            motivos.append(f"{nome.capitalize()} aguardando conferência humana na Bernhoeft")

    comprovante = docs[TipoDocumento.COMPROVANTE_PAGAMENTO]
    resultado: dict[str, Any] = {
        "tipo": ResultadoConciliacao.NAO_AVALIADO.value, "detalhe": "", "horas_ponto": None,
        "horas_folha": None, "diferenca_h": None, "motivos": motivos,
        "comprovante": {
            "presente": comprovante is not None,
            "doc_id": int(comprovante["id"]) if comprovante is not None else None,
            "observacao": ("Comprovante de pagamento recebido." if comprovante is not None else
                           "Comprovante de pagamento não recebido; a ausência não comprova atraso salarial."),
        },
    }
    if bloqueado:
        status = StatusConciliacao.BLOQUEADA_PENDENCIA
        resultado["detalhe"] = "Conciliação bloqueada até a regularização documental: " + "; ".join(motivos) + "."
    elif em_revisao:
        status = StatusConciliacao.REVISAO_HUMANA
        resultado["detalhe"] = "Conciliação aguardando revisão humana: " + "; ".join(motivos) + "."
    else:
        status = StatusConciliacao.ANALISADA
        ponto = CamposPagina.model_validate_json(docs[TipoDocumento.ESPELHO_PONTO]["campos_json"] or "{}")
        folha = CamposPagina.model_validate_json(docs[TipoDocumento.HOLERITE]["campos_json"] or "{}")
        avaliacao = avaliar_horas_extras(ponto, folha)
        resultado.update({**avaliacao, "tipo": ResultadoConciliacao(avaliacao["tipo"]).value})

    insumos = [_insumo(conn, doc) for doc in docs.values() if doc is not None]
    resultado_json = json.dumps(resultado, ensure_ascii=False, sort_keys=True)
    insumos_json = json.dumps(insumos, ensure_ascii=False, sort_keys=True)

    atual = conn.execute(
        "SELECT id, status, resultado_json, insumos_json, regra_versao FROM analyses"
        " WHERE contract_id=? AND worker_id=? AND competencia=? AND atual=1 ORDER BY id DESC LIMIT 1",
        (contract_id, worker_id, competencia)).fetchone()
    if atual is not None and (atual["status"], atual["resultado_json"], atual["insumos_json"],
                              atual["regra_versao"]) == (status.value, resultado_json, insumos_json,
                                                         REGRA_CONCILIACAO):
        return int(atual["id"])

    conn.execute("UPDATE analyses SET atual=0 WHERE contract_id=? AND worker_id=? AND competencia=?",
                 (contract_id, worker_id, competencia))
    cur = conn.execute(
        "INSERT INTO analyses (contract_id, worker_id, competencia, status, resultado_json, insumos_json,"
        " regra_versao, atual, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)",
        (contract_id, worker_id, competencia, status.value, resultado_json, insumos_json,
         REGRA_CONCILIACAO, db.agora()))
    return int(cur.lastrowid)
