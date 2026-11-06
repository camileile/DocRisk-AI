# DocRisk AI — Documento Técnico e Arquitetural

**Versão:** 0.1 — minuta para revisão da equipe técnica  
**Data-base:** 06/11/2026  
**Fonte:** `main` no commit `0008ab2d97f759002aa6e60b485d1e2b6965a36b`  
**Alcance:** arquitetura implementada no MVP; não é laudo de segurança ou arquitetura de SaaS produtivo.

## 1. Visão de componentes

```text
Navegador (Next.js 16 / React 19 / TypeScript)
    │  sessão Clerk e vínculo ativo (modo operacional)
    ▼
API FastAPI/Python ── autorização por papel, organização e contrato
    ├─ Convites, identidades, cadastros e trilha de auditoria
    ├─ Upload, lotes, documentos, páginas e busca
    ├─ Worker de processamento por fila interna
    │   ├─ Renderização PDF/imagens
    │   ├─ Leitura documental Gemini ou TextLayer (teste)
    │   ├─ Segmentação/classificação; associação de metadados
    │   └─ AEJ: parser estruturado e vínculos a trabalhador
    ├─ Regras Trabalhistas
    │   ├─ Pendências e reenvios versionados
    │   ├─ Revisão humana e correção auditável
    │   └─ Conciliação de horas extras
    └─ Indicadores, rascunho, prévia, publicação e PDF
         │
         ▼
SQLite + uploads privados + páginas renderizadas (persistência necessária)
```

A diagramação acima representa módulos lógicos, não serviços independentes. O worker usa fila/processamento na aplicação; **não há infraestrutura externa de filas** validada para o MVP.

## 2. Stack e execução

| Camada | Tecnologia observada | Ponto de atenção |
|---|---|---|
| Frontend | Next.js 16.4.5, React 19.2.3, TypeScript | Build operacional Clerk requer runtime de servidor; demo offline é separada. |
| Componentes/UI | CSS próprio, Lucide, Sora e DM Sans | Revisão de contraste, textos muito pequenos e projeção pendente. |
| Backend | FastAPI, Python 3.11+ | Validar CORS e dependências no ambiente real. |
| Banco | SQLite | Armazenamento persistente e um contexto operacional controlado; não afirmar escalabilidade horizontal. |
| Documentos | PyMuPDF, Pillow; Tesseract opcional | Inspeção e renderização têm limites de arquivo/páginas. |
| IA | SDK `google-genai`, Gemini configurável; TextLayer em testes | Gemini real ainda carece de avaliação visual comprovada no corpus. |
| Identidade | Clerk, JWT/JWKS, vínculos locais | Chaves/domínios, verificação de e-mail e sessões reais precisam de validação. |
| PDF de parecer | Geração backend a partir do snapshot publicado | Não reconstruir conteúdo público a partir de OCR privado após publicar. |

## 3. Domínio de dados

| Entidade/tabela | Significado |
|---|---|
| `organizations`, `organization_profiles`, `organization_auditors` | Identidades e relações entre auditoras, contratantes e fornecedoras. |
| `platform_accounts`, `users` | Contas institucionais separadas dos usuários operacionais. |
| `identity_links`, `identity_invitations` | Identidade Clerk ↔ vínculo autorizado, convites e revogação. |
| `contracts`, `contract_metadata` | Relação contratante-fornecedora-auditora; situação e datas contratuais. |
| `workers` | Trabalhadores vinculados ao contrato; sintéticos no hackathon. |
| `batches`, `pages`, `documents`, `doc_pages` | Origem e processamento dos arquivos, páginas, documento lógico/versões. |
| `document_field_reviews` | Histórico auditável de mudanças em campos extraídos. |
| `aej_worker_mappings`, `aej_imports`, `aej_records`, `aej_documents` | Evidências AEJ e associações a trabalhadores. |
| `issues`, `analyses` | Pendências e conciliações por contrato, trabalhador e competência. |
| `reports`, `report_editorial`, `report_previews` | Rascunho, texto público, prévias conferidas, publicação imutável. |
| `audit`, `ai_cache`, `ai_telemetry` | Ações, cache e telemetria de leitura. |

A migração aditiva de **obrigações e outbox** (`docs/D2-13_OBRIGACOES_OUTBOX.md`) fornece funções internas, mas **não há entrega externa de notificações nem rotas administrativas desse fluxo**. Não confundir com o tratamento de `issues` atualmente exibido no MVP.

## 4. Contratos e estados públicos

**Documento:** `APTO`, `PENDENTE_CORRECAO`, `REVISAO_HUMANA`, `SUBSTITUIDO`.  
**Conciliação:** `AGUARDANDO_DOCUMENTOS`, `BLOQUEADA_PENDENCIA`, `REVISAO_HUMANA`, `ANALISADA`.  
**Resultado da conciliação:** `NAO_AVALIADO`, `DADOS_INSUFICIENTES`, `DIVERGENCIA_A_VERIFICAR`, `SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS`.  
**Pendência:** `ABERTA`, `NOTIFICADA`, `REENVIADA`, `RESOLVIDA`, `REABERTA`.  
**Parecer:** `RASCUNHO`, `EM_REVISAO`, `APROVADO_PUBLICADO`, `SUBSTITUIDO_POR_VERSAO`.

A distinção entre documento, análise e parecer é obrigatória para evitar que o frontend conte um documento processado como análise validada.

## 5. APIs principais (inventário resumido)

| Contexto | Endpoints de referência | Autorização esperada |
|---|---|---|
| Sessão e contratos | `GET /api/me`, `GET /api/contracts` | Vínculo ativo. |
| Login e convites | `/api/auth/links`, `/api/auth/invitations`, `/api/auth/managed-links` | Regras de emissor e destinatário. |
| Administração da auditora | `/api/admin/registry`, `/api/admin/companies`, `/api/admin/contracts`, `/api/admin/overview` | Administrador Bernhoeft; criação de token só na demo. |
| Envio | `POST /api/supplier/batches` | Perfil de fornecedora no contrato permitido. |
| Lotes/documentos | `/api/batches`, `/api/batches/{id}/documents`, `/api/documents/{id}`, `/api/pages/{id}/image` | Apenas perfis documentais autorizados. |
| Pendências | `/api/supplier/issues`, `POST /api/issues/{id}/resubmit` | Fornecedora autorizada. |
| Revisão | `/api/review-queue`, `PATCH /api/documents/{id}/review` | Analista autorizado, com evidência e registro. |
| Conciliação | `GET /api/analyses`, `GET /api/analyst/overview` | Analista, escopo permitido. |
| Parecer | `POST /api/reports`, `/preview`, `/publish`, `/pdf` | Analista para criação/publicação; consulta pública externa só onde permitido. |
| Contratante | `GET /api/client/overview`, `GET /api/client/reports` | Gestor da contratante, snapshots publicados. |
| Administração institucional | `/api/platform/registry`, `/api/platform/auditors` | Administrador da Plataforma. |

A especificação executável de rotas/modelos deve ser obtida do **OpenAPI da instância da API**, gerado a partir da versão testada; esta tabela não substitui contrato OpenAPI e não define todos os campos ou códigos de retorno.

## 6. Segurança e segregação

- **Autenticação real:** frontend obtém sessão do Clerk; backend valida JWT/JWKS, emissor, origem autorizada e estado da sessão; o vínculo local é validado em cada contexto.
- **Autorização:** checagem do papel e dos IDs organizacionais/contratuais no backend; não confiar em filtros client-side.
- **Convites:** um uso, prazo limitado; confirmação de e-mail principal e vínculo autorizado. Não liberar papéis por cadastro livre.
- **Revogação:** usuário e vínculo devem perder acesso na requisição seguinte, sem reviver tela por cache/polling.
- **Arquivos:** imagens/documentos privados; não embutir documentos nem OCR em telas administrativas ou portal da contratante.
- **Pareceres:** rascunhos privados; publicação gera snapshot; contratante não acessa originais ou valores extraídos restritos.
- **Segredos:** configurados no ambiente, nunca em commits, arquivos públicos ou documentação de apresentação.
- **Proteção de dados:** somente dados sintéticos nesta etapa. Não atestar certificação, pentest ou adequação LGPD com base nesses testes.

## 7. Pipeline documental e AEJ

**PDF/imagem:** recepção, registro de lote, renderização de páginas, leitura, classificação/segmentação, documentos lógicos, pendências e revisão. O mecanismo pode usar Gemini; o caminho determinístico TextLayer é apropriado como fallback de teste, mas **não representa inferência de IA visual**.

**AEJ:** parser estruturado, normalização de vínculo/jornada, identificação de trabalhador/competência, revisão de associações quando aplicável. A interpretação atual dos excedentes diários não substitui cálculo completo de banco de horas, semanal ou verificação criptográfica de assinaturas.

**Conciliação:** confronta horas extras do espelho de ponto e do holerite. Sem quantidade de horas extraível em uma das fontes, retorna dados insuficientes — não infere regularidade nem converte valor monetário em horas.

## 8. Rastreabilidade e publicação

A correção de campo deve registrar autor, antes/depois, justificativa, página de origem e versão. Para publicar, o analista confere a prévia; a API compara o hash dos dados conferidos e bloqueia publicação se o conteúdo mudou. O PDF deriva da cópia publicada, incluindo origem, responsável, resumo, recomendações e limitações. Reenvios não eliminam versões anteriores.

## 9. Observabilidade e desempenho

A base oferece tempos por página, status dos lotes, cache e telemetria de IA. Esses dados apoiam o diagnóstico, mas não podem ser confundidos com **precisão**. O documento `docs/BENCHMARK.md` mede 300 páginas / 100 trabalhadores **com TextLayer local**, não com Gemini. `docs/AVALIACAO_VISUAL_GEMINI.md` registra avaliação **bloqueada sem credencial**, portanto não há medição real reproduzível ali.

## 10. Riscos e limitações técnicas

1. SQLite/armazenamento em filesystem: não implantar em plataforma efêmera; preservar volumes e backup consistente.
2. Worker interno/fila: testar concorrência e recuperação após falha para o volume da demonstração; sem promessa de escalonamento horizontal.
3. Upload assíncrono: validar lote simultâneo, limpeza de órfãos e estados finais.
4. Reenvio/duplicidade: validar associação inequívoca ao mesmo trabalhador, competência, contrato e tipo, com versões consistentes.
5. Clerk: testes simulados aprovados não provam configurações reais de domínio, e-mail, sessão, recuperação e revogação.
6. Gemini: provar modelo/cota/credencial e acertos/erros em corpus fixo antes de citar taxas.
7. UX: revisar visualmente projeção, telas pequenas e semântica de estados.

## 11. Referências

- `api/docrisk_core/db/schema.sql`, `api/docrisk_core/routes/`, `api/docrisk_core/contracts.py`.
- `api/docrisk_core/rules/`, `api/docrisk_core/pipeline/`, `api/docrisk_core/aej.py`.
- `docs/D3_07_CLERK.md`, `docs/H03_PROVISIONAMENTO_CLERK_MVP.md`.
- `docs/D3_08_PARECER_CORPORATIVO.md`, `docs/D2-13_OBRIGACOES_OUTBOX.md`.
- `docs/BENCHMARK.md`, `docs/AVALIACAO_VISUAL_GEMINI.md`.
