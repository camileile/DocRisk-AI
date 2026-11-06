# D4-02 — Isolamento universal da demonstração (F43)

| Campo | Valor |
|---|---|
| Prioridade | P0 |
| Branch | `test/d4-02-demo-isolation` (parte de `main` em `e8e5e0f`) |
| Dependências | D3-01/D3-02 = PR #26 `fix/p0-demo-navegacao-polling` (Dev3), **aberto** |
| Arquivos | `web/scripts/demo-isolation.cjs`, `.github/workflows/frontend-validation.yml`, este documento |

## Problema

A demonstração pública (exportação estática, também publicada na Vercel) não pode transportar
dados para os serviços operacionais. O controle de isolamento do frontend é do Dev3 (PR #26);
faltava um teste de regressão **universal** que falhe para qualquer transporte, não só `fetch`
para `:8000`, como no `offline-smoke.cjs` existente.

## Solução (escopo Dev4: teste + CI; nenhuma alteração no código da aplicação)

`web/scripts/demo-isolation.cjs` (Playwright, já usado pelo projeto):

- **Camada de rede** (`context.route("**/*")`): toda requisição para a origem da API, para
  `/api/` na própria origem ou para origem externa não inventariada é **abortada antes de sair
  do navegador** e registrada. Cobre documentos/navegação, redirecionamentos, fetch, XHR,
  EventSource, beacon (`ping`), form posts e requisições de workers. Service workers bloqueados.
- **Instrumentação da página** (`addInitScript`): `fetch`, `XMLHttpRequest.open`, `WebSocket`,
  `EventSource`, `navigator.sendBeacon`, `form.submit` e submissões nativas não interceptadas,
  `Worker`, `SharedWorker`, `serviceWorker.register`, `window.open` — com a linha da pilha
  (chunk) que originou a chamada.
- **Autoteste do detector**: antes dos cenários, dispara deliberadamente cada transporte e
  exige que todos sejam capturados; se o detector "cegar", o teste falha.
- Registro por tentativa: cenário, transporte, origem (page/network/navigation), destino
  **sem query nem credenciais**, rota, resultado (`BLOQUEADO`) e componente (chunk). Relatório
  JSON opcional (`DOCRISK_ISOLATION_REPORT`), publicado como artefato no CI.
- Sem backend, sem credenciais, sem dados reais.

## Cenários (26 + autoteste)

| ID | Cenário | Requisito do plano |
|---|---|---|
| S01 | `/`, `/contato/`, `/acesso/` | 1 página inicial |
| S02 ×6 | Cada perfil: entra pela demo, clica em todos os links do menu, refresh em cada rota | 2, 3, 4 |
| S03 | 21 links diretos com storage vazio, sem sessão | 5, 6, 8 |
| S04 ×6 | 21 links diretos com sessão demo de cada perfil | 5 |
| S05 | Valor de perfil demo inválido no storage | 9 |
| S06 ×6 | `sessionStorage`/`localStorage` lançando `SecurityError`; navegação e reload | 7 |
| S07 | Tentativa de upload em *Enviar lote* e *Pendências* (operador) | 10 |
| S08 | Conciliações, detalhe de lote/documento/revisão, pareceres; botões de ação | 11 |
| S09 | Navegação direta à URL da API: comprova bloqueio | 12 |
| S10 | Rede offline após a carga; navegação no app | 13 |
| S11 | Sair e reentrar com outro perfil | — |

## Resultados observados (local, Windows 11, Node 22.23.2, Chromium do Playwright)

| Alvo | SHA | Resultado |
|---|---|---|
| `main` | `e8e5e0f` | **FALHA — 20/26**. Os 6 cenários S06 (storage indisponível) fazem `fetch` para `http://127.0.0.1:8000/api/...` em todos os perfis (ex.: `/api/platform/registry`, `/api/admin/registry`, `/api/analyst/overview`, `/api/batches`, `/api/client/overview`). Causa: `getDemoRole()` retorna `null` sem storage e `api()` cai no transporte operacional. |
| PR #26 | `56f765e` | **PASSA — 26/26**, zero transporte operacional. |

Autoteste nos dois alvos: capturou `fetch`, `xhr`, `WebSocket`, `EventSource`, `beacon`,
`form.submit` e as requisições de rede correspondentes (`document`, `fetch`, `xhr`, `eventsource`, `ping`).

Observação S07: na demo **nenhum campo de arquivo é oferecido** em *Enviar lote* ou *Pendências*
(0 inputs nos dois alvos). O upload não é "tentado" porque a interface não o expõe; o
cenário confirma que nada é transmitido, não que um upload foi bloqueado em voo.

## Inventário de recursos externos

| Recurso | Origem | Tipo | Tratamento offline |
|---|---|---|---|
| Google Fonts (DM Sans, Sora) | `fonts.googleapis.com`, `fonts.gstatic.com` via `web/app/globals.css` | Estático, não operacional | Bloqueado no teste; páginas renderizam com fontes do sistema sem erro. Para sala sem internet, sugerido a Dev3 hospedar as fontes localmente (`next/font/local`). |
| Links para GitHub | `app/contato`, `components/footer` | Navegação por clique do usuário | Não carregado automaticamente. |

## Execução

```bash
cd web
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run build
python -m http.server 4173 --bind 127.0.0.1 --directory out   # outro terminal
node scripts/demo-isolation.cjs                               # sem API em execução
```

## CI

Passo `Isolamento universal da demonstracao (D4-02)` no job de frontend, depois do smoke offline
e **antes** de subir a FastAPI; relatório publicado como artefato `demo-isolation-report`.
Timeout do job: 20 → 35 min (o teste leva ~5 min localmente).

**Consequência esperada:** sobre a `main` atual o passo falha (defeito F43 real). A ordem de
merge correta é **PR #26 → este PR**. Não foi usado `skip`/`continue-on-error` para obter verde.

## Limitações

- Cobre a demo exportada servida localmente; a URL pública da Vercel não foi testada (não acessar
  ambiente público sem autorização).
- O modo conectado (`/operacao` no PR #26, token no storage) é transporte legítimo e não faz parte do
  escopo; com um token deixado no storage a aplicação entra em modo conectado — comportamento
  documentado, não violação.
- Requisições de `Worker` são cobertas pela camada de rede; a aplicação atual não cria workers.

## Status: PARCIAL

Teste universal, CI e evidências prontos; zero transporte comprovado no PR #26. Depende do merge
do PR #26 para que a `main` passe. CI remoto desta branch não executado (não publicada).
