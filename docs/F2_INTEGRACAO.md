# F2 — Motor documental e IA: como integrar

Branch: `feat/f2-motor-ia`. Nada de `contracts.py` ou `schema.sql` foi alterado.

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

Ainda não implementado na F2 (pedido pela rota de revisão): `dividir` e `unir_proximo` de documentos.
Proposta: `pipeline.revisao.dividir(conn, doc_id, posicao)` e `unir_proximo(conn, doc_id)`, reaproveitando `segmentar` sobre as páginas do documento.

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
