# F2 — Motor documental e IA: como integrar

Integração F2 do motor documental e IA. A extensão D1-10 adiciona telemetria em `schema.sql`; o contrato funcional da página permanece inalterado.

## Para a F1 (API)

```python
from docrisk_core.pipeline.worker import criar_lote, enfileirar, iniciar_worker, parar_worker
from docrisk_core.pipeline.render import ArquivoInvalido
from docrisk_core.ai import ErroConfiguracaoIA
```

| Onde | Chamada | Observação |
|---|---|---|
| lifespan (início) | `db.init_db(); iniciar_worker()` | Com `DOCRISK_SYNC=1` não sobe thread (processa no `enfileirar`). |
| lifespan (fim) | `parar_worker()` | Encerramento ordenado. |
| `POST /api/supplier/batches` | `bid = criar_lote(usuario, contract_id, arquivo.filename, await arquivo.read())` e depois `enfileirar(bid)` | `ArquivoInvalido` → **422** com `str(exc)` (mensagem objetiva, sem caminho). A autorização (contrato/papel) é da rota. |
| `POST /api/issues/{id}/resubmit` | `criar_lote(..., issue_id=id)` + `enfileirar` | A versão anterior vira `SUBSTITUIDO` na consolidação. |
| `POST /api/batches/{id}/reprocess` | `enfileirar(id)` | Relê só as páginas com `ERRO`. |

O que a F1 lê do banco depois do processamento:
- `batches.status` (`RECEBIDO` → `PROCESSANDO` → `CONCLUIDO` | `FALHA_PROCESSAMENTO`) e `batches.erro` (mensagem para exibir).
- `pages`: `ordem`, `image_path` (servir só por rota autenticada), `texto`, `analise_json`, `ms`, `status`, `erro`.
- `documents` + `doc_pages`: `tipo`, `worker_id`, `competencia`, `status`, `confianca`,
  `motivos_pendencia` (pode ir à fornecedora), `motivos_revisao` (**só Bernhoeft**), `campos_json`, `versao`, `substitui_id`.
- `page_fts`: busca com `MATCH` **sempre** filtrada por `contract_id` do usuário.

### Dividir e unir na revisão (`pipeline/revisao.py`)

A rota `PATCH /api/documents/{id}/review` (ações `dividir` e `unir_proximo`) deve só autorizar e chamar:

```python
from docrisk_core.pipeline.revisao import RevisaoInvalida, dividir, unir_proximo

try:
    if acao == "dividir":
        r = dividir(conn, document_id, payload["apos_pagina"], usuario_id=user.id)  # 1..n-1
    else:
        r = unir_proximo(conn, document_id, usuario_id=user.id)
except RevisaoInvalida as exc:
    raise HTTPException(409 if exc.conflito else 422, str(exc)) from exc
# r.documentos -> ids resultantes; r.removidos -> absorvidos na união; r.pares_afetados -> já reconciliados
```

- Campos, tipo, trabalhador e competência são recalculados a partir das páginas (nada é copiado entre as partes).
- Os documentos ajustados voltam para `REVISAO_HUMANA`; a decisão final continua sendo `aprovar`.
- Uma página fica em um único documento; na união, as pendências do documento absorvido passam para o que ficou.
- `substitui_id`/`versao` não são usados aqui (são do reenvio). Documento com histórico de versões não é unido (409).
- A conciliação dos pares afetados já é chamada dentro da função; a rota não precisa repetir.
- Tudo roda na transação da requisição: qualquer erro desfaz o ajuste inteiro.

## Para a F3 (regras)

O worker chama, dentro da mesma transação da consolidação (via `pipeline/integracao_f3.py`):

| Quando | Chamada |
|---|---|
| Documento de foco `PENDENTE_CORRECAO` | `rules.pendencias.criar_pendencia(conn, contract_id=, document_id=, worker_id=, competencia=, tipo_documento=, categoria=ILEGIVEL\|PAGINA_FALTANTE, motivo=, evidencia="Lote N, página(s) X", acao=)` |
| Reenvio substitui versão anterior | `rules.pendencias.atualizar_por_nova_versao(conn, documento_antigo_id, novo_status)` |
| Para cada par trabalhador+competência afetado pelo lote | `rules.conciliacao.conciliar(conn, contract_id, worker_id, competencia)` |

Enquanto essas funções levantam `NotImplementedError`, a etapa **não é executada** (nada é simulado) e o log avisa "Integração F3 pendente". Qualquer outro erro da F3 sobe, o lote fica `FALHA_PROCESSAMENTO` e a consolidação é desfeita (rollback).

`campos_json` do documento traz `horas_extras_h` (horas) e `horas_extras_valor` (R$) separados; valores divergentes entre páginas viram `null` + alerta (nunca escolha).

Para o teste integrado com o lote da F3, use `AI_PROVIDER=textlayer` e `DOCRISK_SYNC=1`. O TextLayerProvider espera:
- título do documento no topo (primeiros 300 caracteres);
- `Página X de Y` em qualquer lugar (rodapé ok);
- `Matrícula: T001`, `Competência: 10/2026`;
- ponto: `TOTAL DE HORAS EXTRAS: 12,00 h`; holerite: `Horas extras 50% | Ref.: 8,00 h | R$ 160,00`;
- holerite legível precisa de `Proventos`/`Salário base`/`Líquido` no corpo; o ilegível do T002 deve ter só título, matrícula e competência na camada de texto.

## Gemini

- `api/.env`: `AI_PROVIDER=gemini`, `GEMINI_API_KEY=...`, `GEMINI_MODEL=...`, `GEMINI_RPM=...`.
- Conferir modelos da conta: `python -m docrisk_core.ai.poc_gemini --modelos` (dentro de `api/`).
- Prova de uma página fictícia: `python -m docrisk_core.ai.poc_gemini`.

### Controle e proveniência (D1-10)

- A resposta usa saída estruturada pelo schema `AnalisePagina`. Ao alterar o prompt ou o schema, incremente `VERSAO_PROMPT` ou `VERSAO_SCHEMA`; ambas fazem parte da chave do cache.
- `GEMINI_TIMEOUT_MS` limita o tempo HTTP por chamada (padrão `60000`) e `GEMINI_MAX_OUTPUT_TOKENS` limita a saída (padrão `2048`). Ambos precisam ser inteiros positivos.
- Para estimar custo por página, configure `GEMINI_INPUT_USD_PER_MILLION` e `GEMINI_OUTPUT_USD_PER_MILLION` com as tarifas atuais do modelo escolhido. Sem as duas tarifas e os tokens retornados pelo SDK, `estimated_cost_usd` fica `NULL`; não é tratado como custo zero.
- `ai_telemetry` registra uma linha por página, incluindo provedor, modelo, versões do prompt/schema, tokens, tarifas, custo estimado, timeout, limite de saída, duração, cache e status. Falhas registram somente o tipo da exceção, sem conteúdo do documento nem chave.
- Para uma página servida do cache, `cache_hit=1`; o uso e o custo desta execução ficam em zero para Gemini. Leitores locais registram custo de API zero e contagem de tokens nula.
- `AI_PROVIDER` não troca de provedor automaticamente: configuração inválida ou indisponibilidade falha explicitamente, sem fallback oculto.
