# H03 — Provisionamento operacional do MVP (Clerk real)

> **Objetivo:** preparar organizações, contratos, vínculos e trabalhadores **sintéticos** em ambiente autenticado, sem habilitar o seed nem distribuir tokens demonstrativos. Esta etapa configura os dados de negócio; a validação da instância e dos convites reais permanece em H01/H02.

## Pré-condições

- Frontend Next.js em runtime, `NEXT_PUBLIC_AUTH_MODE=clerk`; API FastAPI com `DOCRISK_AUTH_MODE=clerk`, `DOCRISK_DEMO_MODE=0` e a mesma instância Clerk.
- `DOCRISK_DATA_DIR` em armazenamento persistente, com backup do SQLite **e** dos arquivos em `uploads/` e `pages/`. Não usar filesystem efêmero para o release.
- HTTPS, CORS, emissor e origens autorizadas corretamente configurados em H01.
- ADMIN_PLATAFORMA provisionado uma única vez pelo procedimento em `docs/D3_07_CLERK.md`; auditoria cadastrada por `/plataforma` com convite ADMIN_BH aceito. Não colocar chaves no Git ou no chat.
- Toda a base de apresentação é **sintética**: empresas fictícias, pessoas fictícias e contratos fictícios. Não importar informação real.

## Sequência de preparação

1. ADMIN_PLATAFORMA entra com Clerk e cadastra a organização auditora; o primeiro ADMIN_BH recebe e aceita o convite por e-mail (H02).
2. ADMIN_BH entra por `/entrar`, seleciona seu vínculo e usa `/administracao/empresas` para criar **contratante**, **fornecedora** e o **contrato inicial**. Pode cadastrar contratos adicionais entre empresas já associadas à sua auditora.
3. ADMIN_BH abre `/administracao/usuarios` → **Gerenciar convites e acessos**, que direciona a `/vinculos`. Convida ANALISTA_BH (própria auditora), GESTOR_FORN e GESTOR_CONTR (organizações vinculadas pelo contrato). O backend atribui o vínculo; nenhuma conta recebe `token_teste`.
4. Cada destinatário confirma o e-mail, aceita o convite e seleciona o vínculo. O Gestor da Fornecedora utiliza `/painel/operadores` → **Convidar e gerenciar operadores** para convidar OPERADOR_FORN, também via Clerk.
5. Para o contrato criado, preparar os trabalhadores fictícios por ferramenta controlada no servidor da API, **com o ADMIN_BH já ativado**:

   - Criar um CSV UTF-8, por exemplo `trabalhadores_sinteticos.csv`, com colunas `id,nome`:
     ```csv
     id,nome
     T001,Trabalhador Fictício 001
     T002,Trabalhador Fictício 002
     T003,Trabalhador Fictício 003
     ```
   - No diretório `api/` do ambiente que monta o **mesmo volume persistente** da API e com as variáveis Clerk configuradas:
     ```bash
     python scripts/provision_synthetic_workers.py --contract-id CT-EXEMPLO --admin-id u-EXEMPLO --csv trabalhadores_sinteticos.csv --confirm-synthetic
     ```
   - Substituir os IDs de exemplo pelos valores do cadastro. O `--admin-id` é o identificador interno de um ADMIN_BH ativo, vinculado via Clerk à auditora do contrato. O script não recebe JWT, senha, e-mail nem chaves de API.
   - É **idempotente** para o mesmo par `id,nome` dentro do contrato. Aborta e desfaz toda a importação quando um ID já pertence a outro contrato ou possui outro nome. Por enquanto, IDs de trabalhador são globais no banco: usar identificadores exclusivos entre contratos.
   - A operação registra a quantidade de entradas criadas/ignoradas e um evento auditável, sem escrever nomes de pessoas no log de sucesso.
6. Conferir, com a identidade autenticada de cada perfil, `GET /api/contracts` e `GET /api/contracts/{id}/workers`, além da página de documentos. A fornecedora deve enxergar seu contrato; o Analista os documentos permitidos; a Contratante apenas pareceres publicados.

## O que não pode ser feito

- Não ajustar `DOCRISK_DEMO_MODE=1` para desbloquear empresa/contrato em Clerk.
- Não criar gestores, analistas ou operadores por `/api/admin/users` ou `/api/supplier/operators`: essas rotas continuam exclusivas do ambiente de testes com token. Em Clerk, utilizar `/api/auth/invitations` e `/api/auth/links`.
- Não ativar seed automático, copiar banco sintético legado para a instalação operacional nem reutilizar tokens de teste.
- Não executar o script em um computador com outra cópia do SQLite, pois os trabalhadores não apareceriam no servidor implantado.

## Critérios de aceite H03

- [ ] Clerk com `DEMO_MODE=0`, banco persistente e administrador inicial ativado.
- [ ] Empresa e contrato cadastrados por ADMIN_BH real; outros perfis e auditoras não autorizadas recebem 403 ou 422/404.
- [ ] Convites em `/vinculos` emitidos/aceitos por destinatário real, sem criar token de demonstração.
- [ ] Trabalhadores sintéticos provisionados no contrato correto, auditados e consultáveis pela API.
- [ ] Operador autenticado visualiza seu contrato e pode enviar um lote sintético; Analista visualiza os documentos autorizados; Contratante consulta somente publicações autorizadas.
- [ ] Nenhum seed demonstrativo foi criado no ambiente operacional.

**Provas necessárias:** resultado dos testes automatizados com provedor Clerk simulado, seguido da execução H12 com contas e e-mails reais, SHA do release, domínio/ambiente e evidências do navegador. Um teste com provedor simulado **não comprova** H01/H02/H12.
