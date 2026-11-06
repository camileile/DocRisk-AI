# DocRisk AI — Plano de Homologação e Qualidade

**Versão:** 0.1 — checklist executável para o MVP  
**Data-base:** 06/11/2026  
**Código de referência:** `main` / `0008ab2d97f759002aa6e60b485d1e2b6965a36b`  
**Estado:** critérios definidos; validação real não executada nesta rodada documental.

## 1. Objetivo

Demonstrar, num **único ambiente configurado**, o percurso:

**Login Clerk real → vínculo autorizado → lote sintético → processamento → exceção/correção → revisão humana → conciliação → parecer conferido e publicado → contratante autenticada consulta/baixa PDF**.

O documento separa **implementação**, **teste simulado** e **evidência real**. Nenhuma etapa recebe o rótulo de homologada apenas por compilar ou por existir na interface.

## 2. Níveis de evidência

| Nível | Evidência admissível | O que prova |
|---|---|---|
| E0 — Implementado | Arquivo/rota/regra presente no commit | Existe código, não comprova execução correta. |
| E1 — Teste automatizado | Teste/API/smoke verde no SHA, com relatório | Comportamento sob fixture e configurações de teste. |
| E2 — Integração real | Cliente HTTP ou navegador com API, banco e armazenamento persistentes, dados fictícios | Fluxo da aplicação integrada. |
| E3 — Identidade/provedor real | Clerk e e-mail reais, autorização entre perfis; Gemini real se reivindicado | Integrações externas efetivamente operacionais. |
| E4 — Ensaio de apresentação | Navegação presencial com evidências pré-carregadas, latência e plano B | Viabilidade da demonstração no evento. |

**Critério de aceite do MVP demonstrado:** E3 para identidade e E2/E4 para toda a jornada. E3 também para o Gemini caso seja apresentado como IA efetivamente executada no evento, sem confundir com TextLayer.

## 3. Matriz de homologação

| ID | Cenário | Aceite objetivo | Evidência mínima | Situação a comprovar |
|---|---|---|---|---|
| H01 | Clerk real e recuperação | Login por e-mail verificado, origem/issuer corretos, logout/recuperação, sem fallback demo | Capturas da sessão + requisições autorizadas e negadas | **Pendente de ambiente real** |
| H02 | Convite e vínculo | Admin autoriza perfil, destinatário aceita, revogação bloqueia requisição seguinte | Convite real + novo login + 403 após revogação | **Pendente de ambiente real** |
| H03 | Empresas/contratos/trabalhadores | Admin BH cadastra empresas/contrato sem demo e base sintética aparece no mesmo banco | Registros antes/depois + perfil correto | Implementado; **execução real pendente** |
| H04 | Isolamento entre contas | Fornecedora A não consulta B; analista só contratos permitidos; contratante não acessa originais | Testes negativos por perfil e contrato | Implementado; validar no navegador real |
| H05 | Prévia e parecer | Rascunho, prévia, hash, autoria, publicação versionada e PDF acessível à contratante | PDF publicado + snapshot + ausência de rascunho no portal | Testes codificados; **E2/E3 pendente** |
| H06 | Upload concorrente | Lotes paralelos não se misturam, entram em estado terminal e não deixam órfãos | Dois uploads sintéticos + verificação de DB/arquivos | **Pendente de regressão direcionada** |
| H07 | Correção com rastreabilidade | Não aceita payload antigo; exige página, motivo, autor e concorrência | Histórico antes/depois e erro 409/422 apropriado | Código integrado; homologação E2 pendente |
| H08 | Reenvio | Nova versão vinculada à pendência certa; não encerra incorretamente uma revisão | Reenvio de holerite sintético e histórico | **Pendente de regressão E2** |
| H09 | Duplicatas | Duplicidade não gera análise atual conflitante nem substitui documento errado | Lote com arquivo repetido / versões | **Pendente de regressão E2** |
| H10 | Navegação e clareza | Operador e analista entendem próxima ação e o estado do lote | Ensaio em navegador desktop e mobile | **Inspeção visual presencial pendente** |
| H11 | Qualidade/proveniência da IA | Mesmo corpus, provedor, modelo, origem, falhas e custos documentados; TextLayer não apresentado como Gemini | Relatório reproduzível Gemini + gabarito | **Gemini real não comprovado** |
| H12 | E2E com login real | Todos os passos do objetivo no mesmo ambiente/SHA, com perfis distintos | Vídeo/capturas anonimizadas e log de execução | **Pendente** |
| H13 | CI e release | Backend e frontend verdes no SHA publicado | URL, SHA, jobs, ambiente, rollback | CI da referência aprovado; release real a verificar |
| H14 | Ensaio, freeze e fallback | Jornada completa sem espera de processamento durante pitch; backup offline identificado como offline | Check de ensaio e fallback testado | **Pendente** |

A matriz organiza os critérios, não atribui proprietários nem declara entregas que dependem de evidência ausente.

## 4. Testes automatizados de referência

**API** (a partir da pasta `api/`):

```bash
python -m pytest -q
python -m pytest -q tests/test_d3_07_clerk.py tests/test_d3_08_report_document.py
python -m pytest -q tests/test_d3_06_review_viewer.py tests/test_profiles_integration.py
python -m pytest -q tests/test_aej.py tests/test_d2_13_obligations_outbox.py
```

**Frontend** (a partir da pasta `web/`):

```bash
npm ci
npm run typecheck
npm run test:p0
npm run test:transport
npm run test:clerk
npm run build
```

Os smokes de browser/API do repositório estão em `web/scripts/` (`smoke.cjs`, `live-api-smoke.cjs`, `report-smoke.cjs`, `review-viewer-smoke.cjs`, `contractor-smoke.cjs`, `offline-smoke.cjs`). Sua execução demanda servidor/configuração corretos. **Não execute testes que alterem dados do ambiente de apresentação sem base dedicada e backup.**

A CI consultada para o SHA de referência reportou **sucesso** em “Testes da API, motor documental e regras” e “TypeScript, build e navegação”. Isso é evidência E1, não E3.

## 5. Dados de prova

**Obrigatório:** só pessoas, organizações e documentos fictícios, com IDs consistentes e competências válidas. Preparar dois grupos distintos:

- **Lote A — demonstração principal pré-processada:** ao menos um documento apto, um ilegível/pendente, um para revisão humana, um par com divergência de horas e um par sem comparação válida; AEJ estruturado se estiver ativo.
- **Lote B — regressão/reserva:** documento duplicado, reenvio, páginas de continuação, arquivo inválido e referências cruzadas de contrato. Usar somente na prova técnica; não consumir tempo de palco.

Para cada caso: ID de contrato, trabalhador, competência, arquivo-fonte, status esperado, evidência de origem, resultado esperado e link para lote/documento. Manter o gabarito **fora das conclusões calculadas pelo sistema**.

## 6. Registro de execução e provas

Cada execução E2–E4 deve registrar:

| Campo | Preencher na homologação |
|---|---|
| Data/hora e fuso | `[a preencher]` |
| Domínio/URL | `[a preencher]` |
| SHA do frontend publicado | `[a preencher]` |
| SHA/backend de referência | `[a preencher]` |
| Modo de autenticação e demo | `clerk` / `0` (verificar no ambiente, não registrar segredos) |
| Banco e persistência | `[tipo, volume, retenção e backup a preencher]` |
| Provedor/modelo IA | `[com evidência ou rotulado como modo de testes]` |
| Resultado por etapa | `[aprovado / reprovado / bloqueado + link de evidência]` |
| Defeitos e responsável | `[identificador/descrição, dono, decisão]` |

Não publicar tokens, CPF, nomes/e-mails reais de testers ou conteúdo privado em evidências.

## 7. Critérios de bloqueio do pitch

**Bloqueia a narrativa de login real:** instância Clerk indisponível, convite/e-mail não validado, erro de sessão, vínculos indevidos.  
**Bloqueia a narrativa de IA real:** só há TextLayer ou modelo Gemini ainda não medido/acionado.  
**Bloqueia conclusão da jornada:** não criar/abrir prévia, não publicar, contratante não consultar/baixar o PDF.  
**Bloqueia alegação de segurança:** A consegue acessar contrato de B, contratante consulta documento original ou token demo funciona no modo Clerk.  
**Bloqueia publicação:** dado incompleto sem ressalva, snapshot inconsistente, autoria sem rastreabilidade ou versão incorreta.

Defeitos apenas estéticos não devem se sobrepor aos bloqueios de acesso, processamento e publicação. Mesmo assim, textos muito pequenos ou botões não visíveis podem inviabilizar a demonstração projetada.

## 8. Checklist do dia da apresentação

- [ ] URL, ambiente e SHA registrados.
- [ ] Três sessões isoladas preparadas: Operador, Analista, Contratante; outros perfis sob demanda.
- [ ] Lote principal **previamente processado** e verificado.
- [ ] Um item de correção e um de revisão preparados e identificáveis.
- [ ] Conciliações e indicadores coerentes com a competência.
- [ ] Parecer revisado e PDF publicados, legíveis, correspondentes aos dados sintéticos.
- [ ] Navegador e projetor testados (resolução, escala/zoom, internet).
- [ ] Plano B offline pronto, **apresentado como offline**, não equivalente à integração real.
- [ ] Anotações de defeitos e de pontos não validados disponíveis para a equipe.

## 9. Referências

`docs/D3_07_CLERK.md`; `docs/H03_PROVISIONAMENTO_CLERK_MVP.md`; `docs/D3_08_PARECER_CORPORATIVO.md`; `docs/BENCHMARK.md`; `docs/AVALIACAO_VISUAL_GEMINI.md`; `api/tests/`; `.github/workflows/backend-tests.yml`; `.github/workflows/frontend-validation.yml`.
