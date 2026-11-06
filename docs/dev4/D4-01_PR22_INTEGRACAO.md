# D4-01 — Validação integrada do PR #22

| Campo | Valor |
|---|---|
| Prioridade | P0 |
| Branch | `test/d4-01-pr22-integration` (parte de `main` em `e8e5e0f`) |
| PR de origem | #22 `test/integracao-seis-perfis` → `main`, **já mergeado** em 06/11/2026 05:35 UTC (merge `0eba5da`) |
| SHA do head do PR #22 | `9ee2c99d33a7716102cf2bbbaa4418c097d881f1` |

## Estado real do PR #22 (consultado na API pública do GitHub)

- Estado: `closed`, `merged=true`. Não há PR a duplicar nem branch a alterar.
- Checks no head `9ee2c99`: `Testes da API, motor documental e regras` = success;
  `TypeScript, build e navegação` = success; `Vercel Preview Comments` = success.
- Checks na `main` atual `e8e5e0f` (após #23, #24, #25): os dois workflows = success.
- Reconciliação com a base: desnecessária (já integrado).

## Papéis reais (`api/docrisk_core/contracts.py::Papel`)

`ADMIN_PLATAFORMA`, `ADMIN_BH`, `ANALISTA_BH`, `GESTOR_FORN`, `OPERADOR_FORN`, `GESTOR_CONTR`.

## O que foi acrescentado

`api/tests/test_d4_01_roles_reactivation.py` (22 casos):

| Caso | Cobertura |
|---|---|
| Seed × enum | Os seis papéis do seed demo são exatamente os do contrato `Papel`; `/api/me` não devolve token |
| Matriz | Para cada papel: 1 operação permitida (200) e 1 proibida (403) em rotas reais |
| Sem autenticação / token inválido | 8 formas (ausente, vazio, `Bearer` sem valor, `Basic`, sem esquema, inexistente, 4 KB) × 6 rotas → 401 + `WWW-Authenticate: Bearer` |
| Usuário desativado | Token rejeitado em `/api/me` e na rota que antes era permitida, inclusive para tentar se reativar |
| Reativação autorizada | Três caminhos reais: Admin Geral → Admin da auditora; Admin BH → Analista; Gestor da fornecedora → Operador |
| Reativação sem privilégio | Os demais papéis recebem 403; gestor de outra fornecedora recebe 404 (não revela existência) |
| Payload adverso | `{"ativo": "1"}` não reativa (422) |
| Persistência | Desativação e reativação sobrevivem a novo ciclo de vida da aplicação (`init_db` idempotente); papel, organização e contratos voltam idênticos, sem escalada |
| Fora do modo demo | Mutações de status → 403 |
| Auditoria | Desativação e reativação registradas com o ator |

## Defeito encontrado e corrigido (rota de Dev2)

`PATCH /api/admin/users/{uid}/status` aceitava `{"ativo": "1"}` (coerção do Pydantic) e
**reativava** o usuário, divergindo das rotas de plataforma e fornecedora, que já usam
`ConfigDict(extra="forbid")` + `Field(strict=True)`. A correção (commit separado
`fix(admin): ...`) aplica o mesmo contrato. O frontend já envia booleano JSON
(`web/app/administracao/usuarios/page.tsx`), portanto não há quebra de UI.
**Requer revisão de Dev2** (autor da rota).

## Execução

```bash
cd api
AI_PROVIDER=textlayer .venv/Scripts/python.exe -m pytest -q tests/test_d4_01_roles_reactivation.py   # 22 passed
AI_PROVIDER=textlayer .venv/Scripts/python.exe -m pytest -q                                          # 258 passed, 1 skipped
```

Local: Windows 11, Python 3.13.14 (CI usa 3.12). O skip é o teste de OCR Tesseract (não instalado).
**CI remoto desta branch: não executado** (branch não publicada no momento do registro).

## Limitações

- **Sessão expirada não existe no contrato atual**: tokens são fixos de demonstração, sem
  expiração nem logout no servidor. O caso "sessão expirada" do plano não é testável sem
  implementação de Dev2 (SSO/OIDC, D2-01). Registrado como pendência, não como aprovado.
- O fluxo de reativação pela interface já é exercitado no smoke conectado (`web/scripts/smoke.cjs`, PR #22).

## Status: PARCIAL

Critérios atendidos: seis papéis testados, reativação comprovada (3 caminhos), defeito
identificado com correção mínima. Pendentes: CI remoto no SHA desta branch (exige publicação) e
caso de sessão expirada (depende de Dev2).

## Reconciliação Codex — 2026-11-06

Base: origin/main 1cbd57f. Backup: backup/d4-01-20261106 (22f294c).
Rebase independente sem conflitos. A correção 758bea0 ainda é necessária:
StatusInput da administração na main aceitava coerção de booleanos.
A suíte inicial teve 360 aprovados, 1 ignorado e 1 falha de expectativa antiga.
Contrato OIDC atual recusa tokens demo com 401 fora da demonstração; teste
adaptado de 403 para 401 sem alterar autenticação/autorização.
Ambiente: Windows, Python 3.13.14, leitor textlayer, dados sintéticos temporários.
Comando: api/.venv/Scripts/python.exe -m pytest api/tests -q.
Verificações: git diff --check origin/main e compileall aprovados.
Não houve publicação nem chamadas pagas.
`nResultado final: 361 aprovados, 1 ignorado (76,99 s). CONCLUÍDA LOCALMENTE.
