# D4-04 — Estabilidade do ambiente conectado local

| Campo | Valor |
|---|---|
| Prioridade | P0 |
| Branch | `fix/d4-04-local-runtime` (parte de `main` em `e8e5e0f`) |
| Dependências | D2-03 (backend) e D1-02 (Gemini): **não alteradas**; Gemini real não exercitado |
| Arquivos | `api/docrisk_core/runtime.py` (novo), `api/docrisk_core/api.py` (gancho no lifespan), `api/docrisk_core/config.py` (mensagens de número inválido), `api/tests/test_d4_04_runtime.py`, `api/scripts/runtime_check.py`, `.env.example`, `.github/workflows/backend-tests.yml` |

## Diagnóstico (antes, em `main`)

| Situação | Comportamento observado |
|---|---|
| `AI_PROVIDER=xyz` | API **sobe**; cada lote falha depois |
| `AI_PROVIDER=gemini` sem `GEMINI_API_KEY` | API **sobe**; cada lote falha depois |
| `GEMINI_RPM=abc` | `ValueError: invalid literal for int()` (traceback cru no import) |
| `DOCRISK_DATA_DIR` aponta para arquivo | `FileExistsError` no lifespan |
| Duas instâncias no mesmo `DATA_DIR` | **Ambas sobem**; cada uma tem fila em memória e retoma os mesmos lotes → processamento duplicado |
| `CORS_ORIGINS=*` | Aceito com `allow_credentials=True` |

Arquitetura mantida: FastAPI + SQLite (WAL) + worker em thread no mesmo processo. **Docker não
foi introduzido**: o projeto não o usa, o alvo é Windows local e a reprodutibilidade aqui depende
de variáveis, diretório de dados e processo único — resolvidos sem nova camada.

## Solução

`runtime.preparar_inicio()` roda no início do lifespan, antes do banco:

1. **Validação reunida** (todas as falhas numa mensagem, sem valores secretos): provedor de IA,
   chave obrigatória para `gemini`, números positivos, limiares em [0,1], `CORS_ORIGINS`
   (origem explícita; `*`/`null`, caminho, credenciais e HTTP fora de loopback recusados;
   com `DOCRISK_DEMO_MODE=1` só origens locais), `DATA_DIR` criável e gravável, banco existente legível
   (aberto em modo somente leitura; nunca alterado).
2. **Instância única por `DATA_DIR`**: trava do SO em `DATA_DIR/api.lock` (`msvcrt`/`fcntl`),
   liberada automaticamente se o processo morrer — sem arquivo pid órfão. Reentrante no
   mesmo processo (testes). `DOCRISK_SINGLE_INSTANCE=0` desliga só para diagnóstico.
3. Resumo de inicialização sem segredos (provedor, modelo, chave presente/ausente, sync, demo, CORS).
4. `config.py`: número inválido → `Variável GEMINI_RPM deve ser inteiro; recebido 'abc'. Ver .env.example.`
5. Encerramento: `parar_worker()` + liberação da trava no `finally` do lifespan.

## Evidências

### pytest — `tests/test_d4_04_runtime.py` (25 casos)

Configuração padrão válida; 5 valores inválidos com mensagem; problemas reunidos; 10 casos de
CORS; demo + origem pública; `DATA_DIR` arquivo; banco corrompido recusado e preservado; startup
recusado + trava não presa; número inválido em subprocesso; CORS permitido/negado (preflight e
requisição simples); trava reentrante; segundo processo recusado e liberado após encerramento.

Suíte completa na branch: **262 passed, 1 skipped** (skip = Tesseract não instalado).

### Processos reais — `python scripts/runtime_check.py` (Windows 11, Python 3.13.14, textlayer)

| ID | Verificação | Resultado observado |
|---|---|---|
| C01 | `AI_PROVIDER=xyz` | recusado, saída 3, 0,91 s, mensagem clara |
| C02 | `DATA_DIR` é arquivo | recusado, saída 3, 0,93 s |
| C03 | banco corrompido | recusado, saída 3, 0,89 s; arquivo preservado |
| C04 | inicialização limpa | `/health` em 1,06 s |
| C05 | 2ª instância mesmo `DATA_DIR` | recusada, saída 3 |
| C06 | CORS | origem autorizada 200 com `allow-origin`; não autorizada 400 sem cabeçalho |
| C07 | job sintético (`lote_demo.pdf`, 16 p.) | `CONCLUIDO`, 14 documentos, 1,58 s |
| C08 | kill durante `PROCESSANDO` (0 páginas lidas) → reinício | `CONCLUIDO` em 2,1 s; 14 documentos; 16 páginas, 16 distintas (sem duplicidade) |
| C09 | encerramento por sinal (`CTRL_BREAK`) | `Application shutdown complete`, trava liberada |
| C10 | reinício no mesmo `DATA_DIR` | `/health` em 0,81 s; 2 lotes concluídos preservados |

**11/11 OK.** No CI (Linux) o mesmo script roda no workflow de backend, com relatório como artefato.

## Runbook — ambiente conectado local

Pré-requisitos: Python ≥ 3.11 (CI 3.12), Node 22, `api/.env` a partir do `.env.example`.
Variáveis necessárias (sem valores secretos): `AI_PROVIDER`, `GEMINI_API_KEY` (só com `gemini`),
`GEMINI_MODEL`, `GEMINI_RPM`, `DOCRISK_DATA_DIR`, `CORS_ORIGINS`, `DOCRISK_DEMO_MODE`.

```powershell
cd api; .venv\Scripts\activate
$env:AI_PROVIDER="textlayer"   # ou gemini com chave no api\.env
uvicorn docrisk_core.api:app --host 127.0.0.1 --port 8000
```

1. Ordem: API primeiro; aguardar `GET /health` = 200; depois `npm run dev` (web).
2. Teste sintético: `python scripts/runtime_check.py` (usa portas livres e diretório temporário;
   não toca no `DATA_DIR` real).
3. Encerramento: `Ctrl+C` no terminal da API (lifespan para o worker e libera a trava).
4. Recuperação: reiniciar o mesmo comando; lotes `RECEBIDO`/`PROCESSANDO` são retomados.
5. "Já existe uma instância": há outro processo da API no mesmo `DATA_DIR` — encerre-o ou use outro diretório.

## Limitações e pendências

- **Gemini real não exercitado** (sem autorização para consumir a chave/cota). A infraestrutura
  foi validada com o leitor `textlayer`, que **não é IA**. Teste conectado com Gemini = pendente (D1-02).
- Timeout/retry do Gemini são de Dev1 (`ai/gemini.py`); não alterados.
- "Worker indisponível" com processo vivo (thread morta) é detectado pela readiness em D4-07.
- A trava cobre processos na mesma máquina/sistema de arquivos local; não substitui fila
  distribuída (D4-10).
- `api.py` e `config.py` são de F1/Dev2: mudanças mínimas, **requerem revisão de Dev2**.

## Status: PARCIAL

Ambiente local inicia, recusa configurações inseguras, impede duplicidade e recupera-se de queda
com evidência medida. Pendente: validação com Gemini real e CI remoto desta branch.

## Reconciliação Codex — 2026-11-06

Base independente origin/main 1cbd57f; backup backup/d4-04-20261106 (98166a2).
Conflito em api.py: mantidos _configured_cors_origins e métodos GET/POST/PUT/PATCH
atuais do Dev2; mantidos validação no lifespan e bloqueio de instância do Dev4.
Ensaio: runtime_check.py --json, 11/11 verificações aprovadas, incluindo CORS,
processos duplicados, queda abrupta, retomada e reinício com persistência.
Windows/Python 3.13.14; TextLayer offline; banco sintético temporário.
O sentinela em parar_worker permanece no código de Dev1; não alterado aqui.
Suíte completa: 365 aprovados, 1 ignorado em 74,83 s. compileall e diff --check aprovados. Status: CONCLUÍDA LOCALMENTE para runtime local.
