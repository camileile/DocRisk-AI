import json
from datetime import datetime, timezone

import pytest

from docrisk_core import config, db
from docrisk_core.obligations import (
    ObrigacaoInvalida,
    agendar_alertas,
    atualizar_obrigacao,
    configurar_agendamento,
    criar_obrigacao,
    processar_simulado,
    registrar_falha,
)


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(config, "PAGES_DIR", tmp_path / "pages")
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.sqlite")
    db.init_db(seed=True)
    connection = db.connect()
    yield connection
    connection.close()


def test_obligation_is_created_with_history_and_calendar_configuration(conn):
    obligation_id = criar_obrigacao(
        conn, contract_id="CT-001", competencia="11/2026", tipo_documento="HOLERITE",
        due_date="2026-11-10", timezone_name="America/Recife", responsavel_id="u-gestor-beta",
    )
    schedule_id = configurar_agendamento(
        conn, contract_id="CT-001", tipo_documento="HOLERITE", event="ANTES_PRAZO",
        offset_days=2, local_time="08:30", timezone_name="America/Recife", channel="email",
    )
    obligation = conn.execute("SELECT * FROM obligations WHERE id=?", (obligation_id,)).fetchone()
    history = conn.execute("SELECT * FROM obligation_history WHERE obligation_id=?", (obligation_id,)).fetchall()
    schedule = conn.execute("SELECT * FROM notification_schedules WHERE id=?", (schedule_id,)).fetchone()

    assert obligation["status"] == "NAO_RECEBIDO"
    assert obligation["timezone"] == "America/Recife"
    assert len(history) == 1 and history[0]["event"] == "CRIADA"
    assert schedule["local_time"] == "08:30"
    assert schedule["channel"] == "email"


@pytest.mark.parametrize("competencia", ["00/2026", "13/2026", "11-2026", "1/2026"])
def test_invalid_competence_is_rejected(conn, competencia):
    with pytest.raises(ObrigacaoInvalida):
        criar_obrigacao(
            conn, contract_id="CT-001", competencia=competencia, tipo_documento="HOLERITE",
            due_date="2026-11-10", timezone_name="America/Recife",
        )


def test_calendar_enqueue_is_idempotent_authorized_and_contains_no_document_text(conn):
    obligation_id = criar_obrigacao(
        conn, contract_id="CT-001", competencia="11/2026", tipo_documento="HOLERITE",
        due_date="2026-11-07", timezone_name="America/Recife",
    )
    configurar_agendamento(
        conn, contract_id="CT-001", tipo_documento="HOLERITE", event="ANTES_PRAZO",
        offset_days=1, local_time="09:00", timezone_name="America/Recife", channel="email",
    )
    now = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
    resolver = lambda context: ["u-gestor-beta", "u-oper-beta"]
    autorizado = lambda user_id, context: user_id in {"u-gestor-beta", "u-oper-beta"} and context["contract_id"] == "CT-001"

    assert agendar_alertas(conn, now=now, resolver_destinatarios=resolver,
                           destinatario_autorizado=autorizado) == 2
    assert agendar_alertas(conn, now=now, resolver_destinatarios=resolver,
                           destinatario_autorizado=autorizado) == 0
    events = conn.execute("SELECT * FROM notification_outbox ORDER BY id").fetchall()
    assert len(events) == 2
    payload = json.loads(events[0]["payload_json"])
    assert payload == {
        "obligation_id": obligation_id, "contract_id": "CT-001", "competencia": "11/2026",
        "tipo_documento": "HOLERITE", "status": "NAO_RECEBIDO", "event": "ANTES_PRAZO",
    }
    assert "document_text" not in payload and events[0]["status"] == "PENDENTE"


def test_notification_requires_authorized_active_recipient(conn):
    criar_obrigacao(
        conn, contract_id="CT-001", competencia="11/2026", tipo_documento="HOLERITE",
        due_date="2026-11-07", timezone_name="America/Recife",
    )
    configurar_agendamento(
        conn, contract_id="CT-001", tipo_documento="HOLERITE", event="NO_PRAZO",
        timezone_name="America/Recife",
    )
    with pytest.raises(PermissionError):
        agendar_alertas(
            conn, now=datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc),
            resolver_destinatarios=lambda context: ["u-gestor-alfa"],
            destinatario_autorizado=lambda user_id, context: False,
        )
    assert conn.execute("SELECT COUNT(*) FROM notification_outbox").fetchone()[0] == 0


def test_simulated_dispatch_records_attempt_without_changing_obligation(conn):
    obligation_id = criar_obrigacao(
        conn, contract_id="CT-001", competencia="11/2026", tipo_documento="HOLERITE",
        due_date="2026-11-07", timezone_name="America/Recife",
    )
    conn.execute(
        "INSERT INTO notification_outbox (obligation_id, recipient_id, channel, event, idempotency_key, "
        "payload_json, status, created_at) VALUES (?, ?, 'email', 'NO_PRAZO', 'test-key', '{}', 'PENDENTE', ?)",
        (obligation_id, "u-gestor-beta", db.agora()),
    )

    assert processar_simulado(conn) == 1
    event = conn.execute("SELECT * FROM notification_outbox WHERE id=1").fetchone()
    attempt = conn.execute("SELECT * FROM notification_attempts WHERE outbox_id=1").fetchone()
    obligation = conn.execute("SELECT status FROM obligations WHERE id=?", (obligation_id,)).fetchone()
    assert event["status"] == "SIMULADO" and event["attempts"] == 1
    assert "não realizado" in attempt["detail"]
    assert obligation["status"] == "NAO_RECEBIDO"


def test_delivery_failure_is_recorded_without_changing_obligation(conn):
    obligation_id = criar_obrigacao(
        conn, contract_id="CT-001", competencia="11/2026", tipo_documento="HOLERITE",
        due_date="2026-11-07", timezone_name="America/Recife",
    )
    conn.execute(
        "INSERT INTO notification_outbox (obligation_id, recipient_id, channel, event, idempotency_key, "
        "payload_json, status, created_at) VALUES (?, ?, 'email', 'NO_PRAZO', 'failure-key', '{}', 'PENDENTE', ?)",
        (obligation_id, "u-gestor-beta", db.agora()),
    )

    assert registrar_falha(conn, 1, "adaptador indisponível")
    assert not registrar_falha(conn, 1, "tentativa duplicada")
    event = conn.execute("SELECT status, attempts FROM notification_outbox WHERE id=1").fetchone()
    attempts = conn.execute("SELECT result, detail FROM notification_attempts WHERE outbox_id=1").fetchall()
    obligation = conn.execute("SELECT status FROM obligations WHERE id=?", (obligation_id,)).fetchone()
    assert tuple(event) == ("FALHA", 1)
    assert len(attempts) == 1 and attempts[0]["result"] == "FALHA"
    assert obligation["status"] == "NAO_RECEBIDO"


def test_satisfied_obligations_are_not_scheduled_again(conn):
    obligation_id = criar_obrigacao(
        conn, contract_id="CT-001", competencia="11/2026", tipo_documento="HOLERITE",
        due_date="2026-11-07", timezone_name="America/Recife",
    )
    configurar_agendamento(
        conn, contract_id="CT-001", tipo_documento="HOLERITE", event="NO_PRAZO",
        timezone_name="America/Recife",
    )
    atualizar_obrigacao(conn, obligation_id, "CONFERIDO", actor_id="u-analista")
    assert agendar_alertas(
        conn, now=datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc),
        resolver_destinatarios=lambda context: ["u-gestor-beta"],
        destinatario_autorizado=lambda user_id, context: True,
    ) == 0
    history = conn.execute("SELECT new_status FROM obligation_history WHERE obligation_id=? ORDER BY id",
                           (obligation_id,)).fetchall()
    assert [row["new_status"] for row in history] == ["NAO_RECEBIDO", "CONFERIDO"]
