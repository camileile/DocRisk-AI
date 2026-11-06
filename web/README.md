# DocRisk AI — Web

Interface em Next.js (App Router) + TypeScript, com identidade oficial DocRisk AI v1, Sora e DM Sans, ligada à API FastAPI de `api/`.

```bash
npm ci
npm run dev          # http://127.0.0.1:3000
```

O botão **Acesso** da landing page aponta para `/entrar` quando Clerk está habilitado e para `/operacao` no modo local de testes. O ambiente fictício permanece acessível somente pela URL `/demo`, sem botões públicos que o divulguem.

A URL da API vem de `NEXT_PUBLIC_API_URL` (ou `NEXT_PUBLIC_DOCRISK_API_URL`, ver `.env.local.example`) (padrão `http://127.0.0.1:8000`). A API precisa liberar a origem do front em `CORS_ORIGINS` (padrão: `http://localhost:3000,http://127.0.0.1:3000`).

Validação: `npm run typecheck`, `npm run build` (exportação estática em `out/`, com `trailingSlash`) e os smokes `node scripts/smoke.cjs` (fluxo completo com o lote sintético) e `node scripts/live-api-smoke.cjs` (login por token e upload de PDF/PNG), ambos contra a API real (ver README da raiz e `docs/INTEGRACAO_F1_FRONTEND.md`).

## Acesso e dois modos separados

- **Demonstração offline** (`/demo`): seleção local dos seis papéis, sem API, sem credencial e sem necessidade de FastAPI. Os dados de `web/lib/offline-demo.ts` são exemplos fictícios; ficam na sessão desta aba. Uploads, reenvios, revisão e publicação são **desativados**, jamais enviados ao servidor. É adequado para navegar pela interface pública hospedada na Vercel.
- **Integração com API de testes**: em ambiente local, inicie FastAPI e conecte um token de teste pelo formulário independente. Neste modo, `GET /api/me` determina papel, `GET /api/contracts` limita contratos, e a API autoriza todas as operações. Tokens demonstrativos devem permanecer no ambiente local e nunca ser expostos em uma implantação pública.

Para verificar a navegação pública sem iniciar a API, gere `npm run build`, sirva `out/` via HTTP e execute `node scripts/offline-smoke.cjs` com Playwright instalado. A CI verifica esta navegação antes de iniciar o backend e também executa o teste de integração real com arquivos sintéticos.

## Site institucional multipágina

A landing em `/` apresenta uma visão curta do produto. O menu superior, o rodapé e os cartões da home levam a páginas próprias, não a seções da mesma landing:

- `/solucao`: proposta da plataforma, base documental modular, evidências, responsabilidades e revisão humana.
- `/como-funciona`: etapas do processamento, triagem de arquivos ilegíveis, divergências a conferir, revisão e indicadores.
- `/modulos`: núcleo compartilhado, módulo Trabalhista em desenvolvimento/validação e **três módulos futuros claramente rotulados**.
- `/contato`: mantém o contato institucional existente.

O botão **Acesso** continua no fluxo operacional da PR #52: `/entrar` com Clerk ou `/operacao` no teste local; a demo offline só em `/demo`. As páginas institucionais permanecem públicas nos dois builds. Os painéis internos e permissões não são alterados. As páginas reutilizam a identidade visual e estilos em `app/marketing-pages.css`. A navegação é verificada com Playwright, inclusive no viewport de celular.

## Páginas

| Rota | Perfis | API |
| --- | --- | --- |
| `/`, `/solucao`, `/como-funciona`, `/modulos`, `/contato` | público | nenhuma (site institucional) |
| `/demo` | seis perfis fictícios | nenhuma API, somente leitura |
| `/entrar` | perfis operacionais (Clerk) | login e vínculos reais, se configurados |
| `/operacao` | perfis operacionais (modo token local) | `/api/me` e `/api/contracts` através de token de teste |
| `/acesso` | acesso legado | login operacional (não abre a demo) |
| `/painel` | analista, fornecedora | `/api/bernhoeft/metrics` ou `/api/batches` + `/api/supplier/issues` |
| `/painel/envio` | fornecedora | `POST /api/supplier/batches` com confirmação de arquivo fictício e acompanhamento (componente `api-upload` da integração F1) |
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

## Login Clerk

O modo produtivo, os convites, a recuperação e o bootstrap institucional estão documentados em [`docs/D3_07_CLERK.md`](../docs/D3_07_CLERK.md). O modo padrão mantém a exportação offline; `NEXT_PUBLIC_AUTH_MODE=clerk` usa runtime Next.js e exige a configuração da instância.
