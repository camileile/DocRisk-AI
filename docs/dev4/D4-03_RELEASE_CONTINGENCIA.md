# D4-03 — Release candidate, roteiro e contingência da apresentação

| Campo | Valor |
|---|---|
| Prioridade | P0 |
| Branch | `chore/d4-03-release-readiness` (parte de `main` em `e8e5e0f`) |
| Arquivos | `web/scripts/release-rehearsal.cjs`, este documento |

## 1. Release candidate — NÃO CONGELADO

| Item | Valor |
|---|---|
| Candidato avaliado | `main` @ `e8e5e0f0045a23a9d8e4e5bb108e634171999ae3` (merge do PR #25) |
| CI remoto nesse SHA | backend `success`, frontend `success` (GitHub Actions, Linux) |
| Testes locais nesse SHA | pytest 237 passed, 1 skipped (Windows, Python 3.13.14) |
| Data da validação | 06/11/2026 |

**Por que não está congelado:** ainda estão abertos itens que mudam o código da apresentação:
PR #26 (isolamento da demo — o teste D4-02 **falha** na `main` atual com storage bloqueado),
PR #27 (texto do benchmark, Dev1) e as branches D4-01/D4-02/D4-04 deste trabalho. Congelar
agora seria apresentar como estável um código que ainda vai mudar. Proposta de congelamento:
**após merge de #26 → D4-02 → D4-04 → D4-01**, reexecutar CI e este ensaio no SHA resultante.

Dependências relevantes (instaladas localmente): fastapi 0.162.0, starlette 1.10.0,
uvicorn 0.54.0, pydantic 2.14.3, PyMuPDF 1.28.2, Pillow 12.3.0 (ver D4-05: vulnerável),
google-genai 1.75.0; next 16.4.5, react 19.2.0, typescript 5.9.3; Playwright 1.58.2 (só testes).

## 2. Dados sintéticos

Reutilizados, versionados e já validados pelo CI: `api/scripts/lote_demo/lote_demo.pdf`
(16 páginas, 14 documentos), `reenvio_holerite_T002.pdf`, `arquivo_corrompido.pdf`, `gabarito.json`.
Seed demo: organizações/usuários/trabalhadores fictícios (`db/__init__.py`). Nenhum dado real.

## 3. Roteiro de apresentação (somente funcionalidades existentes)

1. **Preparação** — terminal da API e navegador abertos; `api/.env` revisado; aba anônima.
2. **Inicialização** — API (`uvicorn ... --host 127.0.0.1 --port 8000`), aguardar `/health`; front.
3. **Acesso** — `/acesso`: demonstração offline (6 perfis) ou token de teste (conectado).
4. **Demonstração principal** — Operador da fornecedora envia `lote_demo.pdf` e acompanha o processamento.
5. **Análises** — Pendências: reenviar `reenvio_holerite_T002.pdf`; Analista: Conciliações
   (T001: 4 h a conferir; T003 bloqueado; T004 dados insuficientes), Fila de Exceções, busca "T001".
6. **Resultados** — Analista publica o parecer; Gestor da contratante vê só o publicado; Admin vê auditoria.
7. **Limitações** — tokens de demonstração, SQLite/processo único, leitor offline ≠ IA,
   AEJ sem validação de assinatura (`p7s_validated=false`), divergência = indício a conferir.
8. **Encerramento** — `Ctrl+C` na API (encerramento ordenado), fechar navegador.

### Benchmark (alinhado com Dev1, PR #27)

Números do `docs/BENCHMARK.md` são do leitor **TextLayer** em lote sintético de 300 páginas: medem
vazão local e conferência com gabarito, **não precisão visual do Gemini**. O custo Gemini é
**estimativa**, não medição. Ao citar qualquer número: dizer origem (TextLayer/estimativa),
amostra (sintética, semente 2026) e limite (não generaliza para documentos reais).

## 4. Plano offline

- Ativar: abrir `/acesso` e escolher um perfil ("Explorar demonstração"). Não exige API nem token.
- Recursos: exportação estática (Vercel ou `web/out`). Google Fonts é o único recurso externo; sem
  internet, cai para fontes do sistema sem erro (D4-02).
- Verificar isolamento: `node scripts/demo-isolation.cjs` (D4-02) — 26/26 só passa com PR #26.
- Restaurar estado inicial: botão Sair / fechar a aba (estado em `sessionStorage`).
- Limitações: mutações desativadas; dados ilustrativos; sem upload.

## 5. Plano conectado

Ver runbook em `docs/dev4/D4-04_AMBIENTE_CONECTADO.md` (branch D4-04): variáveis sem valores,
ordem API → `/health` → front, teste sintético (`scripts/runtime_check.py`), encerramento.

## 6. Contingência

| Falha | Ação | Evidência |
|---|---|---|
| Queda de internet | Ir para a demo offline (`/acesso`); fontes do sistema | D4-02 S10; E2 abaixo |
| Falha/queda da API | Reiniciar o mesmo comando; dados preservados; lotes retomados | E6 (reinício 0,88 s até `/health`); D4-04 C08/C10 |
| Gemini indisponível/sem cota | Reiniciar a API com `AI_PROVIDER=textlayer` e **declarar que não é IA** | Ensaio inteiro roda assim |
| Worker interrompido | Reiniciar a API (retoma `RECEBIDO`/`PROCESSANDO`) | D4-04 C08 |
| Falha do navegador | Reabrir; a sessão é por aba: entrar de novo com o perfil/token | — |
| Reinicialização necessária | Mesmo `DATA_DIR`: estado preservado; para zerar, apontar `DOCRISK_DATA_DIR` para pasta nova | D4-04 C10 |

**Vídeo de contingência: NÃO produzido** (sem recurso de gravação nesta execução). Roteiro de
captura: seções 3.3–3.6 com o lote sintético, ~3 min, gravado a partir de um ambiente que passe o
ensaio E4–E7. Pendência.

## 7. Ensaio cronometrado (automatizado)

`cd web && node scripts/release-rehearsal.cjs --json ensaio.json` — portas livres, banco novo,
`textlayer`, sem Gemini. Executado 3× localmente (Windows 11, Node 22.23.2, Python 3.13.14) em `e8e5e0f`:

| Etapa | Resultado | Duração (última execução) |
|---|---|---|
| E1 build + exportação | OK | 7,3 s |
| E2 demo offline, 6 perfis (offline-smoke + contractor-smoke) | OK | 6,2 s |
| E3 API real até `/health` | OK | 0,9 s |
| E4 roteiro conectado por perfil (`smoke.cjs`) | **FALHOU** (3/3), passo 4/7: após "Conferir" na Fila de Exceções o seletor *Tipo* não aparece em 30 s | 36,3 s |
| E5 portal da contratante conectado | **FALHOU** (3/3) — provável cascata de E4 (parecer não publicado ⇒ duas linhas "Sem parecer publicado") | 2,1 s |
| E6 contingência: kill da API, indisponibilidade confirmada, reinício | OK | 1,4 s (reinício 0,88 s) |
| E7 navegador × FastAPI/SQLite após reinício (`live-api-smoke`) | **FALHOU** (3/3): nome do PDF enviado não aparece na lista | 33,8 s |

**Total medido: 88 s; 4/7 etapas OK.** Os mesmos scripts E4/E5/E7 **passam no CI Linux** neste SHA.

### Incidentes e diagnóstico

1. **Export estático gerado no Windows (Next 16.4.5) grava payloads RSC com caminho aninhado**
   (`painel/revisao/__next.painel/revisao/__PAGE__.txt`) enquanto o cliente pede o nome achatado
   (`__next.painel.revisao.__PAGE__.txt`) → 404 na navegação cliente. **Confirmado.** Builds Linux não
   têm o problema. O ensaio copia os arquivos para o nome esperado no Windows (24 arquivos, registrado
   no JSON), mas **E4/E7 continuaram falhando** — portanto há outra causa ainda **não identificada**.
2. Isoladamente (mesmo banco do ensaio), a tela de detalhe da revisão carrega com o seletor *Tipo*;
   a falha só ocorre dentro do roteiro completo. Causa raiz pendente (Dev3, frontend).
3. Não foi possível validar o fluxo com `next dev`: já há um servidor de desenvolvimento deste projeto
   em execução na máquina (porta 3000, outro processo), e o Next recusa o segundo. Não foi encerrado.
4. No Windows, o Python da Microsoft Store virtualiza `AppData` e esconde os navegadores do Playwright
   de processos filhos — por isso o orquestrador é em Node.

### Consequência para a apresentação

- **Demo offline:** pronta no export gerado no Linux (Vercel/CI); validar com PR #26 mergeado.
- **Conectado em Windows com export estático: NÃO recomendado** até resolver E4/E7. Usar o
  front gerado em Linux ou ensaiar com `npm run dev` numa máquina sem outro dev server.
- **Ensaio humano com projeção, cronometragem por apresentador: pendente.**

## Status: FALHOU (ensaio) / PARCIAL (artefatos)

Roteiro, planos offline/conectado, contingência e ensaio automatizado estão prontos; o ensaio
conectado local falhou em 3 etapas com diagnóstico parcial. SHA não congelado (justificado acima).

## Reconciliação Codex — 2026-11-06
Base 1cbd57f, backup backup/d4-03-20261106 (96bb15c), rebase sem conflitos.
Ensaio reexecutado em Windows/Node 22.23.2/Python 3.13.14, TextLayer offline.
Ajustado orquestrador para criar o lote integracao-f1-sintetico.pdf via API antes
 do live-api-smoke (mesmo preparo do CI). A primeira falha era lote ausente.
Após o ajuste: 6/7 etapas aprovadas; E7 falha ao trocar do analista para operador:
botão Conectar API de testes permanece desabilitado (live-api-smoke.cjs:31).
Build, modo offline, conectado por perfil, portal contratante e contingência
passaram; reinício até health cerca de 0,9s. Sem vídeo ou release congelada.
Suíte backend: 340 aprovados, 1 ignorado; TypeScript, P0 e transporte aprovados.
Status: FALHOU no ensaio completo. Necessita investigação da troca de sessão
com Dev3, revalidação com Clerk recém-integrado e novo ensaio antes de release.

### Revalidação após Clerk (a1f6109)
O ensaio completo passou em 7/7 etapas, total 46,1s, TextLayer offline e banco
novo sintético. Inclui build, demo sem API, fluxo conectado por perfil, portal
contratante, queda/reinício e navegador real após reinício. A falha anterior de
troca de sessão não se reproduziu nesta base. Não houve alteração do frontend.
Relatório: dev4-evidence/d4-03-latest-rehearsal.json no worktree de reconciliação.
Status atual: PARCIAL para release (ensaio aprovado; sem vídeo e sem SHA congelado).
Suíte a1f6109: 370 aprovados, 1 ignorado (99,23s).

Base final f085df4: suíte com Pillow12.3, 387 aprovados, 1 ignorado (183,51s). Ensaio 7/7 em 70,8s. TypeScript/P0/transporte aprovados (incluindo renovação Clerk). Não congelar release enquanto regressão concorrente D4-09/CC01 estiver aberta; vídeo continua pendente. Status PARCIAL.
