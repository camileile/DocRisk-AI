"""Adaptador PROVISÓRIO para as regras da Frente 3. Dono: FRENTE 2.

Enquanto rules.pendencias / rules.conciliacao ainda levantam NotImplementedError,
o motor documental segue funcionando: a etapa da F3 NÃO é executada (nada é
simulado) e um aviso "Integração F3 pendente" vai para o log uma vez por função.
Qualquer outro erro vindo da F3 sobe normalmente — não é escondido.

Quando a F3 estiver pronta este arquivo continua válido (só repassa as chamadas).
"""
from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from typing import Any

from ..contracts import StatusDocumento

log = logging.getLogger("docrisk.pipeline.f3")
_avisados: set[str] = set()


def _chamar(nome: str, funcao: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return funcao(*args, **kwargs)
    except NotImplementedError:
        if nome not in _avisados:
            _avisados.add(nome)
            log.warning("Integração F3 pendente: %s ainda não implementada; etapa NÃO executada.", nome)
        return None


def criar_pendencia(conn: sqlite3.Connection, **kwargs: Any) -> int | None:
    from ..rules import pendencias
    return _chamar("rules.pendencias.criar_pendencia", pendencias.criar_pendencia, conn, **kwargs)


def atualizar_por_nova_versao(conn: sqlite3.Connection, documento_antigo_id: int,
                              novo_status: StatusDocumento) -> None:
    from ..rules import pendencias
    _chamar("rules.pendencias.atualizar_por_nova_versao", pendencias.atualizar_por_nova_versao,
            conn, documento_antigo_id, novo_status)


def conciliar(conn: sqlite3.Connection, contract_id: str, worker_id: str, competencia: str) -> int | None:
    from ..rules import conciliacao
    return _chamar("rules.conciliacao.conciliar", conciliacao.conciliar,
                   conn, contract_id, worker_id, competencia)
