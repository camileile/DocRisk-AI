# D4-06 — Ambiente de piloto privado (F45)

| Campo | Valor |
|---|---|
| Prioridade | P1 |
| Branch | `feat/d4-06-private-pilot` (parte de `main` em `e8e5e0f`) |
| Dependências | D2-01 (autenticação de produção) e D2-09 (provisionamento) — **não existem** |
| Arquivos | `docs/dev4/pilot.env.example`, este documento. **Nenhum deploy realizado.** |

## Bloqueios verificados (não declarados como concluídos)

| # | Bloqueio | Evidência | Dono |
|---|---|---|---|
| B1 | Autenticação é token fixo de demonstração; não há SSO/OIDC, expiração, logout nem convite | `auth.py`, D4-01 | Dev2 (D2-01) |
| B2 | **Seed fictício roda fora do modo demo**: com `DOCRISK_DEMO_MODE=0`, `init_db()` cria 4 organizações, 6 usuários com token e 6 trabalhadores fictícios | execução local em 06/11/2026: `orgs 4 users 6 workers 6 platform 0` | Dev2 (`db/__init__.py`) |
| B3 | Cadastro de empresas/usuários/operadores só funciona em modo demo (403 fora dele); não há provisionamento | `admin_management._write_allowed`, D4-01 | Dev2 (D2-09) |
| B4 | PyMuPDF é AGPL-3.0: oferecer o serviço pela rede exige publicar o código aos usuários ou licença comercial | D4-05 | Decisão humana |
| B5 | Processo único + SQLite: sem alta disponibilidade | README, D4-04 | Aceito para piloto pequeno; D4-10 |

Sem B1–B3 resolvidos, **um piloto com dados reais não deve ser aberto**: qualquer pessoa com um
token do seed teria acesso, e não há como criar usuários reais.

## Arquitetura recomendada (sem migrar tecnologia)

Mesma stack: um host privado (VM) com:

```
[usuários da organização] --HTTPS--> proxy reverso (TLS, allowlist de IP/VPN)
                                         |-- /        -> export estático do web (NEXT_PUBLIC_API_URL=https://<host-piloto>)
                                         |-- /api,/health -> uvicorn 127.0.0.1:8000 (1 processo, DOCRISK_SYNC=0)
DATA_DIR em volume persistente (disco dedicado, criptografia em repouso)
backup diário (scripts/backup.py, D4-08) para armazenamento fora do host
```

Justificativa: a aplicação já é um processo único com SQLite; containers ou serviços gerenciados
não resolvem B1–B3 e adicionam custo. TLS e restrição de acesso ficam no proxy; a API continua
ouvindo só em loopback (regra do README).

## Diferenças entre ambientes

| Variável | Demo (Vercel) | Local conectado | Piloto |
|---|---|---|---|
| `DOCRISK_DEMO_MODE` | n/a (sem API) | `1` | **`0`** |
| `AI_PROVIDER` | n/a | `textlayer`/`gemini` | `gemini` (chave em cofre) |
| `CORS_ORIGINS` | n/a | `http://127.0.0.1:3000` | `https://<host-piloto>` |
| `DOCRISK_DATA_DIR` | n/a | `./data` | volume persistente dedicado |
| `DOCRISK_SYNC` | n/a | `0` | `0` |
| `DOCRISK_LOG_JSON` | n/a | `0` | `1` (D4-07) |
| Seed fictício | — | sim | **não** (bloqueio B2) |

Com D4-04 mergeado, a API recusa `DOCRISK_DEMO_MODE=1` com origem não local, `*` e HTTP fora de
loopback em `CORS_ORIGINS`.

## Checklist de abertura do piloto (todos obrigatórios)

- [ ] B1–B3 resolvidos por Dev2 e testados (D4-01/D4-09 reexecutados)
- [ ] Decisão de licença (B4) registrada
- [ ] TLS válido no proxy; API só em 127.0.0.1
- [ ] Segredos (`GEMINI_API_KEY`) fora do repositório e do host de build
- [ ] `/health/ready` (D4-07) monitorado; backup diário + `verify` (D4-08) ensaiado no host
- [ ] Restauração ensaiada no host com tempo medido
- [ ] Acesso restrito (VPN/allowlist) testado de fora da rede
- [ ] Nenhum token demo válido no banco do piloto

## Validação realizada

Somente local: confirmação dos bloqueios B2/B3 e preparo de `docs/dev4/pilot.env.example`. **Sem
infraestrutura nem credenciais disponíveis; nenhuma validação externa feita.**

## Status: BLOQUEADA

Depende de D2-01/D2-09, da correção do seed (B2) e de decisão de licença (B4).

## Atualização Codex — 2026-11-06 (substitui o diagnóstico antigo acima)
Base a1f6109; backup backup/d4-06-20261106 (e043d75); rebase sem conflitos.
B2 resolvido na main: seed_demo retorna fora do modo demo; lifespan condiciona
seed ao modo token + demo. B1/B3 evoluíram: PR #46 implementa Clerk, vínculos,
convites, revogação e autorização interna. Não são mais inexistentes.
Modelo pilot.env.example atualizado para DOCRISK_AUTH_MODE=clerk, sem chaves.
Testes Clerk usam assinaturas locais e provedor simulado, sem chamadas externas.
Não houve provisionamento real, teste de TLS/VPN, integração externa Clerk,
backup no host nem deploy. Licença do projeto/PyMuPDF exige decisão responsável.
DOCRISK_SINGLE_INSTANCE/LOG_JSON dependem das branches D4-04/D4-07, não empilhadas.
Status: BLOQUEADA para abertura do piloto; preparação documental PARCIAL.
Validação local: pytest api/tests -q, 370 aprovados, 1 ignorado (97,20s), Windows/Python 3.13.14; diff --check aprovado.

Base final f085df4: 387 aprovados, 1 ignorado (160,16s), Pillow12.3; diff --check aprovado. Status BLOQUEADA para piloto real pelos requisitos externos documentados; nenhuma infraestrutura alterada.
