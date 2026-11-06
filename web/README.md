# DocRisk AI — Web

Interface em Next.js (App Router) + TypeScript, com identidade oficial DocRisk AI v1, Sora e DM Sans, ligada à API FastAPI de `api/`.

```bash
npm ci
npm run dev          # http://127.0.0.1:3000
```

A URL da API vem de `NEXT_PUBLIC_API_URL` (padrão `http://127.0.0.1:8000`). A API precisa liberar a origem do front em `CORS_ORIGINS` (padrão: `http://localhost:3000,http://127.0.0.1:3000`).

Validação: `npm run typecheck`, `npm run build` (exportação estática em `out/`, com `trailingSlash`) e o smoke ponta a ponta `node scripts/smoke.cjs` (ver README da raiz).

## Sessão e permissões

`/acesso` lista os perfis de demonstração de `GET /api/demo/users` (só existe com `DOCRISK_DEMO_MODE=1`). Ao entrar, o token fica em `sessionStorage` e o perfil é lido de `GET /api/me`. Cada área (`/painel`, `/contratante`, `/administracao`) só monta para os papéis correspondentes e redireciona os demais. **A autorização real é da API**: a interface apenas esconde o que a API já recusa (401/403/404).

## Páginas

| Rota | Perfis | API |
| --- | --- | --- |
| `/acesso` | todos | `/api/demo/users`, `/api/me`, `/api/contracts` |
| `/painel` | analista, fornecedora | `/api/bernhoeft/metrics` ou `/api/batches` + `/api/supplier/issues` |
| `/painel/envio` | fornecedora | `POST /api/supplier/batches` |
| `/painel/lotes`, `/painel/lotes/detalhe?id=` | analista, fornecedora | `/api/batches`, `/api/batches/{id}`, `/documents`, `POST /reprocess`; atualiza sozinho durante o processamento |
| `/painel/documentos`, `/painel/documentos/detalhe?id=` | analista, fornecedora | `/api/documents`, `/api/documents/{id}`, `/api/search`, `/api/pages/{id}/image` (blob com token) |
| `/painel/revisao`, `/painel/revisao/detalhe?id=` | analista | `/api/review-queue`, `PATCH /api/documents/{id}/review` (aprovar, dividir, unir, solicitar correção) |
| `/painel/pendencias` | analista, fornecedora | `/api/issues` ou `/api/supplier/issues`, `POST /api/issues/{id}/resubmit` |
| `/painel/conciliacoes` | analista | `/api/analyses` |
| `/painel/pareceres` | analista | `/api/reports`, `/preview`, `/publish` |
| `/contratante` | gestor da contratante | `/api/client/reports` (só publicados) |
| `/administracao` | administrador | `/api/audit`, `/api/bernhoeft/metrics` |

Rotas de detalhe usam `?id=` porque a exportação estática não gera páginas para IDs que só existem em tempo de execução.

## Cuidados

- O trecho da busca chega escapado e marcado com `[[ ]]`; é renderizado como texto com `<mark>`, nunca como HTML.
- A fornecedora recebe `EM_ANALISE` no lugar de `REVISAO_HUMANA`, sem motivos internos nem campos extraídos.
- A contratante não acessa imagens, documentos, busca nem rascunhos; o parecer não traz valores em reais nem texto de OCR.
- O formulário de contato continua sem envio.
