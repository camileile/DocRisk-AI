# H03 — Provisionamento operacional do MVP autenticado

Esta etapa prepara **organizações, contratos, vínculos e trabalhadores exclusivamente sintéticos** sem habilitar `DOCRISK_DEMO_MODE` e sem introduzir credenciais por token no Clerk.

## Ambiente obrigatório

- Backend: `DOCRISK_AUTH_MODE=clerk`, `DOCRISK_DEMO_MODE=0`, `DOCRISK_SYNC=0`; mesma instância Clerk e origens autorizadas do frontend, HTTPS e armazenamento persistente.
- Frontend: build com runtime Next.js para Clerk, não exportação estática offline.
- Nenhum seed de organizações/usuários é executado no modo Clerk; bootstrap institucional documentado em `D3_07_CLERK.md`.
- Os arquivos e dados para apresentação são **sintéticos**; a estrutura de contrato não depende de uma conta fictícia compartilhada.

## Cadastros disponíveis pela interface autenticada

1. **ADMIN_PLATAFORMA**: após bootstrap de sua identidade, cadastra auditora e envia o convite inicial ADMIN_BH.
2. **ADMIN_BH**: em **Empresas e Contratos**, cadastra contratante e fornecedora (contrato inicial), cria contratos adicionais entre organizações já vinculadas e consulta o registro da sua auditora. A API valida papel, organização, escopo e persistência antes de responder sucesso.
3. **ADMIN_BH**: em **Gestão de Usuários**, envia convites Clerk aos administradores/analistas da própria auditora e gestores das empresas vinculadas. O usuário só passa a existir no ambiente operacional após aceitar convite válido e verificar o e-mail.
4. **GESTOR_FORN**: em **Operadores**, envia convites a operadores de sua organização. A lista mostra membros já vinculados. Revoga/reativa vínculos pela API de identidades, não por alteração de token.

**No Clerk, `POST /api/admin/users`, `PATCH /api/admin/users/{id}/status`, `POST /api/supplier/operators` e seus controles de token de testes continuam proibidos.** A API `/api/auth/invitations` e `/api/auth/links/{link_id}` gerencia convites e revogações de vínculos, com verificação de autorização.

## Trabalhadores sintéticos — preparação controlada

Os registros de trabalhadores pertencem a contratos, **não são contas com login**. Para o MVP, o responsável pela API prepara um CSV estritamente fictício, sem dados reais, com as colunas:

```csv
id,nome
T001,Trabalhador Sintético Um
T002,Trabalhadora Sintética Dois
```

No ambiente do backend, usando as variáveis do ambiente Clerk corretamente configuradas:

```sh
python api/scripts/provision_mvp_workers.py --contract-id CT-ID-REAL-DO-AMBIENTE --csv api/scripts/trabalhadores_sinteticos.csv
python api/scripts/provision_mvp_workers.py --contract-id CT-ID-REAL-DO-AMBIENTE --csv api/scripts/trabalhadores_sinteticos.csv --apply --confirm-synthetic
```

O primeiro comando **não grava**. O segundo exige confirmação explícita, verifica se o contrato existe, impede troca silenciosa de nomes ou colisões de IDs entre contratos, grava atomicamente e registra evento de auditoria. **T001/T002 são exemplos:** os identificadores devem coincidir com os documentos fictícios que serão processados. Não anexar planilha real ao repositório e não usar scripts demonstrativos para popular a instância autenticada.

## Ordem de preparação

1. Dev4 configura Clerk, HTTPS, domínio, persistência, caminhos de upload e variáveis.
2. Dev2 faz bootstrap institucional e confirma o vínculo do ADMIN_PLATAFORMA real.
3. ADMIN_PLATAFORMA cadastra auditora, envia convite; o ADMIN_BH aceita.
4. ADMIN_BH cria contratante e fornecedora, contrato(s) e convida analista e gestores.
5. Dev2 provisiona somente trabalhadores sintéticos no(s) contrato(s) necessário(s).
6. GESTOR_FORN aceita vínculo e convida operador; operador aceita seu próprio vínculo.
7. ADMIN_BH atribui contratos aos analistas em **Gestão de Usuários**; GESTOR_FORN atribui contratos aos operadores em **Operadores**. Sem concessão individual, esses usuários não acessam contratos. Consulte `ACESSO_INDIVIDUAL_CONTRATOS.md`.
8. Cada participante acessa seu próprio painel com Clerk; ninguém recebe token demonstrativo.

## Checklist obrigatório de aceite

- [ ] `DOCRISK_DEMO_MODE=0` e `DOCRISK_AUTH_MODE=clerk` conferidos na instância.
- [ ] Criação e consulta de empresas/contratos pelo ADMIN_BH autenticado funcionam após nova requisição.
- [ ] ADMIN_PLATAFORMA/fornecedora/contratante não podem usar os endpoints administrativos da auditora.
- [ ] Conta sem vínculo não tem dados; convites reais são entregues, aceitos e revogados com a instância escolhida.
- [ ] Usuários por token não podem ser criados/reativados no Clerk.
- [ ] Trabalhadores sintéticos do contrato estão presentes após reinício e são vistos pelo analista autorizado.
- [ ] O lote sintético, a revisão, a conciliação, a publicação e o PDF da contratante funcionam no mesmo release.
- [ ] As evidências da execução real (domínio e SHA) foram anexadas ao checklist da equipe.

**Observação:** os testes automatizados do repositório simulam o provedor Clerk. Eles não substituem o teste manual H12 em instância real, com entrega efetiva de e-mail.
