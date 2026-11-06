# D4-09 — Testes de segurança e cenários adversos

| Campo | Valor |
|---|---|
| Prioridade | P1 |
| Branch | `test/d4-09-adversarial-scenarios` (parte de `main` em `e8e5e0f`) |
| Arquivos | `api/tests/test_d4_09_adversarial.py` (33 casos), `api/docrisk_core/routes/__init__.py` (correção), este documento |

## Defeito encontrado e corrigido — travamento da API com uploads simultâneos

| | |
|---|---|
| Componente / dono | `routes/__init__.py` `upload_batch` e `resubmit_issue` — F1/Dev2 |
| Causa | Rotas `async def` executavam SQLite e renderização **bloqueantes dentro do event loop**. Uma requisição esperando o lock de escrita (busy timeout 30 s) bloqueava o loop, e o *teardown* da dependência `get_conn` da requisição que detinha o lock (que confirma a transação) não podia ser agendado → esperas de 30 s em cadeia. |
| Reprodução real (uvicorn, `SYNC=0`, 16 uploads simultâneos, `textlayer`) | **Antes:** 5×202, 2×500 (`database is locked`), 9× timeout de 120 s; `GET /api/batches` seguinte também em timeout (API indisponível). **Depois:** 16×202 em 1,1 s; `GET` em 0,3 s; 16 lotes. Com `SYNC=1`: antes 2×202 + 14 timeouts; depois 16×202 em 2,5 s. |
| Correção | Parte síncrona das duas rotas (após `await file.read`) executada com `run_in_threadpool`; nenhuma regra alterada. **Requer revisão de Dev2.** |
| Regressão | `test_CC02_uploads_simultaneos_geram_lotes_distintos`: falha sem a correção (verificado com `git stash`), passa com ela. |

## Matriz

Pré-condição comum: banco isolado por teste (`banco`), seed demo sintético, leitor `textlayer`.
Resultado observado = execução local de 06/11/2026 (Windows, Python 3.13.14). Evidência = nome do teste.

| ID | Cenário | Ação | Esperado | Observado | Status |
|---|---|---|---|---|---|
| MT01 ×7 | Empresa Gama acessa recurso da Beta por ID | lote, documentos do lote, original, reprocessar, documento, anonimizado, imagem de página | 403/404 sem dados | 403/404, sem vazamento | ✅ |
| MT02 | IDs vizinhos, extremos e injeção | 0, -1, id+1, 2³¹, 2⁶³-1, `1;DROP…`, `../1`, `1e3` | 403/404/422, tabela intacta | conforme | ✅ |
| MT03 | Listagens e busca | `/api/batches`, `/api/documents`, `/api/search` com contrato alheio | só contrato próprio; busca alheia negada | conforme | ✅ |
| MT04 | Upload em contrato alheio | Gama envia para CT-001 | 404, nenhum lote | conforme | ✅ |
| UP01–08 | Vazio, corrompido, executável, zip/HTML/SVG disfarçados, PNG truncado, TIFF lixo | upload | 422, sem lote/arquivo, sem traceback/caminho | conforme | ✅ |
| UP09 ×8 | Nomes maliciosos (`../`, `..\`, absoluto, `C:\`, NUL, 500 chars, `<script>`, `CON`) | upload | arquivo em `UPLOAD_DIR` com nome gerado; exibição sem separadores, ≤200 | conforme | ✅ |
| UP10 | PDF com páginas em branco | processar | não derruba o worker; estado terminal | conforme | ✅ |
| CC01 | 4 threads processando o mesmo lote ao mesmo tempo | `processar_lote` ×4 com barreira | sem erro; 8 páginas distintas; 6 documentos; 4 pendências únicas; 3 análises vigentes (= sequencial) | conforme — **hipótese de duplicação refutada** | ✅ |
| CC02 | 8 uploads simultâneos | threads × `POST /api/supplier/batches` | 8×202, ids/arquivos distintos | **falhava** (500 `database is locked`); passa após correção | ✅ (corrigido) |
| CC03 | Enfileirar o mesmo lote 5× | `enfileirar` | 1 item na fila | conforme | ✅ |
| PV01 | Logs do fluxo de upload | captura de log DEBUG | sem token válido/inválido e sem texto do documento | conforme | ✅ |
| PV02 | Respostas de 3 papéis × 6 rotas | GET | sem token do próprio usuário, sem `DATA_DIR`/`uploads` | conforme | ✅ |
| PV03 | `/api/demo/users` fora do modo demo | GET | 403/404 | conforme | ✅ |

Cobertos em outras suítes (não repetidos): sessões/token inválido/desativado/reativação (D4-01),
arquivo acima do limite e TIFF real (`test_f1_security.py`), demo sem transporte (D4-02),
reinício durante processamento e banco/armazenamento indisponível na inicialização (D4-04).

## Não coberto / pendente

- Token expirado e logout no servidor: inexistentes no contrato (Dev2, D2-01).
- Disputa entre **workers em processos distintos**: impedida por design (instância única, D4-04); fila distribuída = D4-10.
- Gemini indisponível/timeout/resposta inválida com o cliente real: testes de Dev1 (`test_f2_gemini.py`) usam dublês; sem chamada real.
- Queda intermitente de rede entre front e API: tratada no frontend (Dev3, PR #26).
- Defesa em profundidade sugerida a Dev1: `Image.open(..., formats=[...])` (ver D4-05).

## Execução

```bash
cd api
AI_PROVIDER=textlayer .venv/Scripts/python.exe -m pytest -q tests/test_d4_09_adversarial.py   # 33 passed
AI_PROVIDER=textlayer .venv/Scripts/python.exe -m pytest -q                                   # 270 passed, 1 skipped
```

## Status: PARCIAL

Suíte automatizada cobrindo multiempresa, uploads, concorrência e privacidade; um defeito grave
encontrado, corrigido e coberto por regressão. Pendentes: itens acima e CI remoto.
