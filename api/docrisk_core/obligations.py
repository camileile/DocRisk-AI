from __future__ import annotations

import json
import re
import sqlite3
from datetime import date, datetime, time, timedelta
from typing import Callable, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .db import agora

ESTADOS = {
    "NAO_RECEBIDO", "RECEBIDO", "EM_REVISAO", "CONFERIDO", "INSUFICIENTE",
    "REJEITADO", "NAO_APLICAVEL",
}
EVENTOS = {"ANTES_PRAZO", "NO_PRAZO", "APOS_PRAZO"}
_COMPETENCIA = re.compile(r"^(0[1-9]|1[0-2])/\d{4}$")
_HORA = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class ObrigacaoInvalida(ValueError):
    pass


def _timezone(nome: str) -> ZoneInfo:
    try:
        return ZoneInfo(nome)
    except (ZoneInfoNotFoundError, TypeError) as exc:
        raise ObrigacaoInvalida("Fuso horário inválido.") from exc


def criar_obrigacao(
    conn: sqlite3.Connection,
    *,
    contract_id: str,
    competencia: str,
    tipo_documento: str,
    due_date: str,
    timezone_name: str,
    responsavel_id: str | None = None,
) -> int:
    if not _COMPETENCIA.fullmatch(competencia):
        raise ObrigacaoInvalida("Competência deve estar no formato MM/AAAA.")
    try:
        date.fromisoformat(due_date)
    except (TypeError, ValueError) as exc:
        raise ObrigacaoInvalida("Vencimento deve ser uma data ISO (AAAA-MM-DD).") from exc
    _timezone(timezone_name)
    if not tipo_documento.strip():
        raise ObrigacaoInvalida("Tipo de documento obrigatório.")
    now = agora()
    cursor = conn.execute(
        "INSERT INTO obligations (contract_id, competencia, tipo_documento, due_date, timezone, "
        "status, responsavel_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'NAO_RECEBIDO', ?, ?, ?)",
        (contract_id, competencia, tipo_documento.strip(), due_date, timezone_name, responsavel_id, now, now),
    )
    obligation_id = int(cursor.lastrowid)
    conn.execute(
        "INSERT INTO obligation_history (obligation_id, event, new_status, details_json, created_at) "
        "VALUES (?, 'CRIADA', 'NAO_RECEBIDO', '{}', ?)", (obligation_id, now),
    )
    return obligation_id


def atualizar_obrigacao(
    conn: sqlite3.Connection,
    obligation_id: int,
    status: str,
    *,
    actor_id: str | None = None,
    details: dict | None = None,
) -> None:
    if status not in ESTADOS:
        raise ObrigacaoInvalida("Estado de obrigação inválido.")
    row = conn.execute("SELECT status FROM obligations WHERE id=?", (obligation_id,)).fetchone()
    if row is None:
        raise ObrigacaoInvalida("Obrigação não encontrada.")
    now = agora()
    old = row["status"]
    conn.execute("UPDATE obligations SET status=?, updated_at=? WHERE id=?", (status, now, obligation_id))
    conn.execute(
        "INSERT INTO obligation_history (obligation_id, actor_id, event, old_status, new_status, details_json, created_at) "
        "VALUES (?, ?, 'STATUS_ALTERADO', ?, ?, ?, ?)",
        (obligation_id, actor_id, old, status, json.dumps(details or {}, ensure_ascii=False, sort_keys=True), now),
    )


def configurar_agendamento(
    conn: sqlite3.Connection,
    *,
    contract_id: str,
    event: str,
    timezone_name: str,
    local_time: str = "09:00",
    offset_days: int = 0,
    tipo_documento: str | None = None,
    channel: str = "SIMULADO",
) -> int:
    if event not in EVENTOS:
        raise ObrigacaoInvalida("Evento de calendário inválido.")
    if not _HORA.fullmatch(local_time):
        raise ObrigacaoInvalida("Horário local inválido; use HH:MM.")
    if offset_days < 0 or (event == "NO_PRAZO" and offset_days != 0) or (event != "NO_PRAZO" and offset_days == 0):
        raise ObrigacaoInvalida("O deslocamento deve ser positivo antes/depois do prazo e zero no vencimento.")
    _timezone(timezone_name)
    if not channel.strip():
        raise ObrigacaoInvalida("Canal de comunicação obrigatório.")
    now = agora()
    conn.execute(
        "INSERT INTO notification_schedules (contract_id, tipo_documento, event, offset_days, local_time, "
        "timezone, channel, ativo, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?) "
        "ON CONFLICT(contract_id, tipo_documento, event, offset_days) DO UPDATE SET "
        "local_time=excluded.local_time, timezone=excluded.timezone, channel=excluded.channel, ativo=1",
        (contract_id, tipo_documento or "*", event, offset_days, local_time, timezone_name, channel.strip(), now),
    )
    row = conn.execute(
        "SELECT id FROM notification_schedules WHERE contract_id=? AND tipo_documento=? AND event=? AND offset_days=?",
        (contract_id, tipo_documento or "*", event, offset_days),
    ).fetchone()
    return int(row["id"])


def agendar_alertas(
    conn: sqlite3.Connection,
    *,
    now: datetime,
    resolver_destinatarios: Callable[[dict], Iterable[str]],
    destinatario_autorizado: Callable[[str, dict], bool],
) -> int:
    if now.tzinfo is None:
        raise ObrigacaoInvalida("O relógio de agendamento precisa incluir fuso horário.")
    obligations = conn.execute(
        "SELECT * FROM obligations WHERE status NOT IN ('CONFERIDO', 'NAO_APLICAVEL')"
    ).fetchall()
    count = 0
    for obligation_row in obligations:
        obligation = dict(obligation_row)
        schedules = conn.execute(
            "SELECT * FROM notification_schedules WHERE contract_id=? AND ativo=1 "
            "AND (tipo_documento='*' OR tipo_documento=?)",
            (obligation["contract_id"], obligation["tipo_documento"]),
        ).fetchall()
        for schedule_row in schedules:
            schedule = dict(schedule_row)
            zone = _timezone(schedule["timezone"])
            due = date.fromisoformat(obligation["due_date"])
            hour, minute = map(int, schedule["local_time"].split(":"))
            due_local = datetime.combine(due, time(hour, minute), tzinfo=zone)
            if schedule["event"] == "ANTES_PRAZO":
                fire_at = due_local - timedelta(days=schedule["offset_days"])
            elif schedule["event"] == "APOS_PRAZO":
                fire_at = due_local + timedelta(days=schedule["offset_days"])
            else:
                fire_at = due_local
            if now.astimezone(zone) < fire_at:
                continue
            context = {
                "obligation_id": obligation["id"], "contract_id": obligation["contract_id"],
                "competencia": obligation["competencia"], "tipo_documento": obligation["tipo_documento"],
                "status": obligation["status"], "event": schedule["event"],
            }
            recipients = set(resolver_destinatarios(context))
            for recipient_id in recipients:
                user = conn.execute("SELECT ativo FROM users WHERE id=?", (recipient_id,)).fetchone()
                if user is None or not user["ativo"] or not destinatario_autorizado(recipient_id, context):
                    raise PermissionError("Destinatário não autorizado para este contrato e alerta.")
                key = f"obligation:{obligation['id']}:schedule:{schedule['id']}:{schedule['event']}:recipient:{recipient_id}"
                payload = json.dumps(context, ensure_ascii=False, sort_keys=True)
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO notification_outbox (obligation_id, recipient_id, channel, event, "
                    "idempotency_key, payload_json, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'PENDENTE', ?)",
                    (obligation["id"], recipient_id, schedule["channel"], schedule["event"], key, payload, agora()),
                )
                count += cursor.rowcount
    return count


def processar_simulado(conn: sqlite3.Connection, limit: int = 100) -> int:
    if limit <= 0:
        raise ValueError("limit precisa ser positivo.")
    rows = conn.execute(
        "SELECT id FROM notification_outbox WHERE status='PENDENTE' ORDER BY id LIMIT ?", (limit,)
    ).fetchall()
    now = agora()
    result = "Adaptador simulado: envio externo não realizado."
    processed = 0
    for row in rows:
        updated = conn.execute(
            "UPDATE notification_outbox SET status='SIMULADO', attempts=attempts+1, last_result=?, attempted_at=? "
            "WHERE id=? AND status='PENDENTE'", (result, now, row["id"]),
        )
        if not updated.rowcount:
            continue
        conn.execute(
            "INSERT INTO notification_attempts (outbox_id, result, detail, attempted_at) VALUES (?, 'SIMULADO', ?, ?)",
            (row["id"], result, now),
        )
        processed += 1
    return processed


def registrar_falha(conn: sqlite3.Connection, outbox_id: int, detalhe: str) -> bool:
    if not detalhe.strip():
        raise ValueError("A descrição da falha é obrigatória.")
    now = agora()
    updated = conn.execute(
        "UPDATE notification_outbox SET status='FALHA', attempts=attempts+1, last_result=?, attempted_at=? "
        "WHERE id=? AND status='PENDENTE'", (detalhe[:1000], now, outbox_id),
    )
    if not updated.rowcount:
        return False
    conn.execute(
        "INSERT INTO notification_attempts (outbox_id, result, detail, attempted_at) VALUES (?, 'FALHA', ?, ?)",
        (outbox_id, detalhe[:1000], now),
    )
    return True
