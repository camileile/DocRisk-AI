"""Conciliação de horas extras por trabalhador + competência. Dono: FRENTE 3.

Spec 4.2, 5.1 e 5.2. Bloqueio seletivo: um par com problema para, os outros seguem.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from ..contracts import CamposPagina


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
    raise NotImplementedError("Frente 3: avaliar_horas_extras")


def conciliar(conn: sqlite3.Connection, contract_id: str, worker_id: str, competencia: str) -> int:
    """Recalcula a análise de UM par e devolve o id da nova linha em `analyses`.

    Usa a versão vigente (status != SUBSTITUIDO) de ESPELHO_PONTO e HOLERITE.
    - documento ausente -> BLOQUEADA_PENDENCIA + pendência DOCUMENTO_AUSENTE (status ABERTA)
    - documento PENDENTE_CORRECAO -> BLOQUEADA_PENDENCIA
    - documento REVISAO_HUMANA -> REVISAO_HUMANA
    - os dois APTO -> ANALISADA com avaliar_horas_extras
    Registra comprovante presente/ausente (ausência NÃO prova atraso salarial).
    Marca a análise anterior do par como atual=0; grava insumos e REGRA_CONCILIACAO.
    """
    raise NotImplementedError("Frente 3: conciliar")
