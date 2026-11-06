# D4-07 — Observabilidade e readiness (F34)

| Campo | Valor |
|---|---|
| Prioridade | P1 |
| Branch | `feat/d4-07-observability` (parte de `main` em `e8e5e0f`) |
| Dependência | D1-10 (telemetria da IA) — **não disponível**: chamadas, retries e custo da IA não são registrados hoje |
| Arquivos | `api/docrisk_core/observability.py` (novo), `api/docrisk_core/api.py` (middleware/rotas/CORS expose), `api/tests/test_d4_07_observability.py` |

## Entregue

| Item | Implementação |
|---|---|
| Liveness | `GET /health/live` → `{"status":"ok"}` (só o processo) |
| Readiness | `GET /health/ready` → 200/503 com `checks.banco` (abre somente leitura, `SELECT 1`), `checks.armazenamento` (`uploads/` e `pages/` graváveis), `checks.worker` (thread viva quando `DOCRISK_SYNC=0`). Barato: nenhuma leitura de documento nem chamada externa |
| `/health` | **inalterado** (contrato do front e do CI) |
| Correlação | `X-Request-ID` aceito se `[A-Za-z0-9._-]{1,64}`, senão gerado (16 hex); devolvido na resposta e exposto via CORS; presente em todo log `docrisk.*` |
| Logs | `DOCRISK_LOG_JSON=1` → uma linha JSON por evento (`ts, level, logger, msg, request_id, pid, thread, method, path, status, ms`). Log de acesso registra só método, caminho **sem query** e status. `Bearer <token>` em mensagens é mascarado (`[REDACTED]`). Eventos do worker (lote criado, página lida/falhou, consolidado, concluído, retomados) já existiam com `id` do lote e agora saem pelo mesmo handler |
| Métricas | `GET /api/ops/metrics` (somente `ADMIN_PLATAFORMA`): lotes por status, backlog (`RECEBIDO`), em processamento, concluídos, com falha, taxa de falha, duração p50/p95, páginas por status, leitura p50/p95/máx, fila em memória, worker vivo, entradas de cache de IA. **Calculadas do banco; nada estimado** — `ia.chamadas`, `ia.retries`, `ia.custo_estimado_usd` = `null` até D1-10 |

## Evidências

- pytest `tests/test_d4_07_observability.py`: 8 passed (health original, live, ready síncrono,
  **worker parado com processo vivo → 503 e live 200**, banco/armazenamento indisponíveis → 503,
  matriz de acesso das métricas, métricas = estado do banco sem nomes/IDs de trabalhador,
  request-id propagado/sanitizado, log JSON correlacionado sem token).
- Suíte completa: **245 passed, 1 skipped**.
- Processo real (uvicorn, `SYNC=0`, `DOCRISK_LOG_JSON=1`): `/health/ready` = ready com os 3 checks;
  `GET /api/me` com `X-Request-ID: demo-1` gerou
  `{"logger": "docrisk.http", "msg": "http GET /api/me 401", "request_id": "demo-1", "status": 401, "ms": 1, ...}`.

## Defeito encontrado (F2/Dev1, não corrigido aqui)

`worker.parar_worker()` sempre coloca o sentinela `None` na fila. Se chamado com a thread já
parada (ex.: thread morreu e o lifespan encerra), o `None` permanece e **encerra imediatamente o
próximo worker iniciado no mesmo processo**. Proposta: enfileirar o sentinela só se a thread estiver
viva, ou drenar a fila em `iniciar_worker()`. Reproduzido ao escrever o teste de readiness.

## Limitações

- Sem exportação Prometheus/OpenTelemetry (não há coletor no projeto); JSON é consumível por qualquer agregador.
- Correlação requisição → lote é pelo `batch_id` nos logs; o `request_id` não atravessa para a thread do worker.
- Latência por etapa limitada ao que o banco registra (ms de leitura por página, duração do lote).

## Status: PARCIAL

Jobs rastreáveis, logs estruturados, métricas reais, worker indisponível detectável e readiness
correta. Pendente: métricas de IA (D1-10), CI remoto.

## Reconciliação Codex — 2026-11-06
Base a1f6109; backup backup/d4-07-20261106 (b3d186d).
Conflitos api.py: preservados validate_configuration, seed condicionado ao modo
de autenticação/demo, métodos PUT e cabeçalhos X-DocRisk-Link/Invalid; adicionados
logs, middleware e X-Request-ID sem substituir a autenticação atual.
pytest api/tests -q: 378 aprovados, 1 ignorado em 80,15s; testes de readiness,
worker indisponível, métricas e correlação incluídos. compileall/diff --check OK.
Windows/Python 3.13.14, TextLayer offline. Métricas de IA sem dados continuam null.
Sentinela: parar_worker ainda insere None após marcar parada; risco de sentinela
remanescente no reinício permanece para Dev1. Não alterado nesta branch.
Status: PARCIAL (limitações de IA e ciclo do worker permanecem).
