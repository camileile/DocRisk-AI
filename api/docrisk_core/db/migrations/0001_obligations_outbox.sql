CREATE TABLE IF NOT EXISTS obligations (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  contract_id       TEXT NOT NULL REFERENCES contracts(id),
  competencia       TEXT NOT NULL CHECK (
    competencia GLOB '[0-1][0-9]/[0-9][0-9][0-9][0-9]' AND
    substr(competencia, 1, 2) BETWEEN '01' AND '12'
  ),
  tipo_documento    TEXT NOT NULL,
  due_date          TEXT NOT NULL CHECK (date(due_date) IS NOT NULL),
  timezone          TEXT NOT NULL,
  status            TEXT NOT NULL CHECK (status IN (
    'NAO_RECEBIDO', 'RECEBIDO', 'EM_REVISAO', 'CONFERIDO', 'INSUFICIENTE',
    'REJEITADO', 'NAO_APLICAVEL'
  )),
  responsavel_id    TEXT REFERENCES users(id),
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL,
  UNIQUE (contract_id, competencia, tipo_documento)
);
CREATE INDEX IF NOT EXISTS ix_obligations_contract_due
  ON obligations (contract_id, due_date, status);

CREATE TABLE IF NOT EXISTS obligation_history (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  obligation_id   INTEGER NOT NULL REFERENCES obligations(id),
  actor_id        TEXT REFERENCES users(id),
  event           TEXT NOT NULL,
  old_status      TEXT,
  new_status      TEXT,
  details_json    TEXT NOT NULL DEFAULT '{}',
  created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_obligation_history_obligation
  ON obligation_history (obligation_id, id);

CREATE TABLE IF NOT EXISTS notification_schedules (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  contract_id     TEXT NOT NULL REFERENCES contracts(id),
  tipo_documento  TEXT NOT NULL DEFAULT '*',
  event            TEXT NOT NULL CHECK (event IN ('ANTES_PRAZO', 'NO_PRAZO', 'APOS_PRAZO')),
  offset_days      INTEGER NOT NULL CHECK (offset_days >= 0),
  local_time       TEXT NOT NULL CHECK (local_time GLOB '[0-2][0-9]:[0-5][0-9]'),
  timezone         TEXT NOT NULL,
  channel          TEXT NOT NULL DEFAULT 'SIMULADO',
  ativo            INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
  created_at       TEXT NOT NULL,
  UNIQUE (contract_id, tipo_documento, event, offset_days)
);
CREATE INDEX IF NOT EXISTS ix_notification_schedules_active
  ON notification_schedules (contract_id, ativo);

CREATE TABLE IF NOT EXISTS notification_outbox (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  obligation_id     INTEGER NOT NULL REFERENCES obligations(id),
  recipient_id      TEXT NOT NULL REFERENCES users(id),
  channel           TEXT NOT NULL,
  event             TEXT NOT NULL,
  idempotency_key   TEXT NOT NULL UNIQUE,
  payload_json      TEXT NOT NULL,
  status            TEXT NOT NULL CHECK (status IN ('PENDENTE', 'SIMULADO', 'FALHA')),
  attempts          INTEGER NOT NULL DEFAULT 0,
  last_result       TEXT,
  created_at        TEXT NOT NULL,
  attempted_at      TEXT
);
CREATE INDEX IF NOT EXISTS ix_notification_outbox_pending
  ON notification_outbox (status, id);

CREATE TABLE IF NOT EXISTS notification_attempts (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  outbox_id       INTEGER NOT NULL REFERENCES notification_outbox(id),
  result          TEXT NOT NULL CHECK (result IN ('SIMULADO', 'FALHA')),
  detail          TEXT NOT NULL,
  attempted_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_notification_attempts_outbox
  ON notification_attempts (outbox_id, id);
