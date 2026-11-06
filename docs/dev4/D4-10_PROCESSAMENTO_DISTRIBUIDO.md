# D4-10 — Processamento distribuído e escala (F11)

| Campo | Valor |
|---|---|
| Prioridade | P2 |
| Branch | `feat/d4-10-distributed-processing` (parte de `main` em `e8e5e0f`) |
| Dependências | D2-14 (contrato de estados/fila — Dev2) e D1-10 (telemetria de IA — Dev1): **não disponíveis** |
| Entrega | **Somente diagnóstico e proposta.** Nenhuma alteração no worker. |

## Diagnóstico obrigatório (código em `main`)

| # | Pergunta | Situação real |
|---|---|---|
| 1 | Fila atual | `queue.Queue` em memória + `set` `_na_fila` (dedupe) em `pipeline/worker.py`; **uma thread por processo** |
| 2 | Reserva de jobs | Não há reserva: o lote vai para a fila do processo que o recebeu; status `PROCESSANDO` sem dono nem prazo |
| 3 | Transição de estados | `RECEBIDO → PROCESSANDO → CONCLUIDO \| FALHA_PROCESSAMENTO`; páginas `PENDENTE → OK \| ERRO` |
| 4 | Retries | Gemini: até 4 tentativas com backoff/`Retry-After` (`ai/gemini.py`); lote: reprocessamento manual (`/reprocess`), lendo só páginas não `OK` |
| 5 | Idempotência | Página `OK` não volta à IA; `ai_cache` por hash; `consolidar_lote` não regrava se já há documentos. D4-09 CC01: 4 threads no mesmo lote → resultado idêntico ao sequencial |
| 6 | Transações/locking | SQLite WAL, transações curtas por página; sem `BEGIN IMMEDIATE`; lock de escrita global do arquivo |
| 7 | Falha de worker | Retomada só no próximo `iniciar_worker()` (reinício do processo). Thread morta não é reiniciada; detectável via `/health/ready` (D4-07). Defeito do sentinela em `parar_worker()` (D4-07) |
| 8 | Limites globais | `LimitadorRPM` é **por processo** (thread-safe, não entre processos); não há orçamento de IA; concorrência = 1 lote por processo |

Hoje vários processos são **impedidos** pela trava de instância única (D4-04) justamente porque
não há reserva: dois processos retomariam os mesmos lotes.

## Proposta (alinhar com Dev2/D2-14 antes de implementar)

Sem segunda fila: o próprio banco é a fila (adequado ao MVP; em PostgreSQL, `FOR UPDATE SKIP LOCKED`).

- **Lease**: `lease_owner`, `lease_until`, `attempts` em `batches` (ou tabela `job_leases`); reserva
  atômica em `BEGIN IMMEDIATE` de um lote elegível (`RECEBIDO`/`PROCESSANDO` com lease nulo ou vencido), conferindo `changes()`.
- **Heartbeat**: renovar `lease_until` a cada página; quem perde o lease para antes de consolidar.
- **Recuperação**: lease vencido volta a ser elegível; reaproveita páginas `OK` e cache.
- **Dead-letter**: `attempts >= N` ⇒ `FALHA_PROCESSAMENTO` "esgotou tentativas" + auditoria; reprocessamento manual zera.
- **Limites globais**: tabela de tokens por janela (RPM/orçamento) consultada em `BEGIN IMMEDIATE`, compartilhada entre processos.
- **Idempotência de efeitos**: consolidação condicionada ao `lease_owner` atual na mesma transação.
  Entrega *ao menos uma vez* com efeitos idempotentes — não "exatamente uma vez".

## Testes previstos (não executados)

Dois workers no mesmo lote; kill abrupto; lease vencido; heartbeat interrompido; retry; lote
inválido → dead-letter; operação repetida; reinício; limite global atingido; carga-base
(ex.: 10 lotes × 16 páginas, `textlayer`) e 10× (100 lotes), medindo vazão, latência, erros,
backlog, CPU/memória, recuperação e duplicidade. Sem API paga.

## Status: NÃO INICIADA (implementação)

Diagnóstico concluído; implementação aguarda D2-14 (o lease muda o contrato de estados de Dev2)
e a estabilização da release P0.

## Reconciliação Codex — 2026-11-06
Base a1f6109; backup backup/d4-10-20261106 (5d09bc9); rebase sem conflitos.
Diagnóstico relido no código atual: fila local/thread e ausência de lease
persistente permanecem. A trava mencionada acima pertence à D4-04, que é branch
irmã e não está integrada nesta branch. Nenhuma implementação distribuída foi feita.
Sem testes de carga 10x; alterações de schema/estados exigem alinhamento Dev1/Dev2.
Status: NÃO INICIADA para implementação; apenas diagnóstico reconciliado.
Suíte na base a1f6109: 370 aprovados, 1 ignorado (98,49s). D1-10 foi integrado depois no PR #47; telemetria agora existe, porém não implementa distribuição.
