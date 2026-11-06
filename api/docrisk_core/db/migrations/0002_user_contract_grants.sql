-- Sem backfill operacional: cada concessão é explícita. Histórico preservado.
CREATE TABLE IF NOT EXISTS user_contract_grants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL REFERENCES users(id),
  contract_id TEXT NOT NULL REFERENCES contracts(id),
  granted_by TEXT NOT NULL REFERENCES users(id),
  granted_at TEXT NOT NULL,
  expires_at TEXT,
  revoked_at TEXT,
  revoked_by TEXT REFERENCES users(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_user_contract_grants_open
  ON user_contract_grants(user_id, contract_id) WHERE revoked_at IS NULL;
