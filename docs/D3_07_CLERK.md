# D3-07 — login produtivo com Clerk

Provedor escolhido pelo usuário: **Clerk**. Implementação em branch própria, sem merge/deploy, criação de instância ou envio de e-mails reais nesta entrega.

## O que está implementado

- `/entrar`: identificação e recuperação nativas do Clerk; depois da identificação, exibe os vínculos ativos e os convites do e-mail principal verificado. A pessoa escolhe o vínculo, sem atribuir papel no navegador.
- `/cadastro`: ativação da identificação do destinatário. Criar conta no Clerk, isoladamente, não concede acesso a organizações ou documentos.
- `/vinculos`: troca entre vínculos autorizados; emissão/revogação de convites e ativação/revogação de acessos conforme o papel do emissor. O atalho aparece na barra de sessão produtiva.
- `/acesso`: mantém os seis perfis fictícios offline. `/operacao` continua com token apenas no build de testes; no build Clerk, encaminha para o login produtivo.
- No modo Clerk, a API recusa tokens demonstrativos, não expõe `/api/demo/users` e não cria organizações/contas do seed na inicialização.
- O SDK fornece um Bearer atualizado a cada requisição. O DocRisk não grava esse JWT em sessionStorage. O cabeçalho `X-DocRisk-Link` identifica o vínculo escolhido; a API confirma que pertence ao subject autenticado.
- JWT validado com PyJWT/criptografia, algoritmo RS256, emissor, assinatura JWKS, expiração, emissão, subject/session e `azp` permitido. Audience é validada quando configurada no token. JWKS usa cache temporário com atualização para nova chave.
- A sessão é consultada online no Clerk em cada requisição autenticada; verificar assinatura, sozinho, não detecta revogação. Falha do provedor bloqueia a operação, sem fallback demo.
- Revogação do vínculo é efetiva na próxima requisição. Resposta de sessão/contexto inválido encerra o contexto local, desmonta as telas e cancela requisições anteriores. Erros 403 comuns não trocam o perfil automaticamente.
- A identidade institucional continua em `platform_accounts`, exclusiva de vínculos operacionais. Uma restrição no banco e o bootstrap impedem combinar os dois tipos de identidade. Admin Geral e Admin Bernhoeft continuam sem acesso documental.

## Convites e recuperação

| Emissor | Acesso que pode conceder |
| --- | --- |
| Admin Geral | Admin Bernhoeft de organização auditora cadastrada |
| Admin Bernhoeft | Admin/Analista da própria auditora; gestores de empresas ligadas por seus contratos |
| Gestor da Fornecedora | Operadores da própria fornecedora |
| Demais perfis | Não emitem convites |

Convites têm uso único e validade de **72 horas**. O registro interno mantém emissor, vínculo emissor, destinatário, organização e papel. A criação no Clerk admite destinatário já existente, para permitir novos vínculos da mesma identidade; duplicidade do mesmo convite pendente é bloqueada localmente, inclusive por índice único.

A aceitação confere e-mail principal verificado no Clerk, validade/estado local e estado do convite no provedor; revalida o vínculo e a autorização do emissor e ativa a conta/vínculo na mesma transação. Convite expirado, revogado, já utilizado ou de outro e-mail não ativa acesso. A revogação local é persistida mesmo se a revogação do e-mail no Clerk falhar; a resposta informa `provider_pending`.

Recuperação de senha é feita pelo formulário oficial do Clerk. O DocRisk não recebe/guarda senhas e não emite reset próprio. Recuperar a identidade não reativa um vínculo revogado. Habilitar verificação de e-mail e recuperação no painel Clerk faz parte da configuração da instância.

## Configuração para ativação

Não commitar chaves nem transmiti-las por chat. Configurar os segredos no ambiente de execução do frontend e da FastAPI. Os exemplos estão em `.env.example` e `web/.env.local.example`.

**Instância Clerk:** criar/selecionar a aplicação, configurar identificação por e-mail/senha, verificação de e-mail, recuperação e restrição de cadastro por convite quando aplicável. Cadastrar os domínios e retornos autorizados. Usar a mesma instância no frontend e backend; não misturar chaves de teste e produção.

**Frontend Next.js:**

```dotenv
NEXT_PUBLIC_AUTH_MODE=clerk
NEXT_PUBLIC_API_URL=https://api.seu-dominio.com
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=<chave-publica-da-instancia>
CLERK_SECRET_KEY=<segredo-da-instancia-somente-no-servidor>
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/entrar
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/cadastro
```

Esse modo usa runtime Next.js e o SDK/middleware oficial. O modo padrão permanece a exportação estática; adaptadores de build excluem os recursos de servidor do Clerk da demo. Alterar variáveis `NEXT_PUBLIC_*` exige novo build. O build operacional não pode ser servido como diretório `out/`.

**FastAPI:**

```dotenv
DOCRISK_AUTH_MODE=clerk
DOCRISK_DEMO_MODE=0
CLERK_ISSUER=https://sua-instancia.clerk.accounts.dev
CLERK_SECRET_KEY=<segredo-da-mesma-instancia>
CLERK_AUTHORIZED_PARTIES=https://app.seu-dominio.com
CLERK_INVITE_REDIRECT_URL=https://app.seu-dominio.com/cadastro
CORS_ORIGINS=https://app.seu-dominio.com
DOCRISK_DATA_DIR=/volume-persistente/docrisk
```

`CLERK_ISSUER` deve ser o emissor exato informado pelo Clerk; não usar `api.clerk.com` como emissor. `CLERK_AUTHORIZED_PARTIES` aceita uma lista explícita de origens separadas por vírgula, sem caminhos. Configurar `CLERK_AUDIENCE` somente quando a audience também estiver definida no token emitido.

O armazenamento precisa ser durável. A entrega mantém a implementação SQLite atual; não provisiona banco/host produtivo nem altera todo o cadastro administrativo, cujas mutações gerais continuam limitadas ao modo demonstrativo. Login produtivo não equivale a plataforma inteira pronta para produção.

## Bootstrap institucional

Em banco produtivo, o seed não cria o primeiro administrador. Após criar a identidade no Clerk e confirmar seu subject `user_...`, um operador autorizado executa no ambiente da API:

```bash
python api/scripts/link_clerk_identity.py --subject user_EXEMPLO --account-id platform-institucional --platform --name 'Admin Geral institucional'
```

A API deve estar instalada/importável, com `DOCRISK_AUTH_MODE=clerk` e emissor configurados. O script cria a conta institucional se necessário, sem credencial demonstrativa utilizável no modo Clerk. Para vincular uma conta empresarial já cadastrada, usar seu ID em `--account-id` e omitir `--platform`. Não vincular identidades por domínio de e-mail ou por papel recebido do navegador.

Empresas/contratos produtivos precisam estar previamente provisionados/importados no cadastro autorizado; isso não é feito por um cadastro público. Operações de convite acrescentam o acesso do usuário à organização existente, sem duplicar a identidade da fornecedora.

## Evidências e limites

- 28 casos direcionados em `api/tests/test_d3_07_clerk.py`: JWT com assinatura RSA real e provedor simulado; emissor/origem/expiração/algoritmo, sessão encerrada, vínculo adulterado/revogado, permissões, convites verificados/expirados/revogados/reutilizados, revogação no provedor, ausência de fallback e de seed produtivo.
- 6 testes existentes de CORS/AEJ passaram após acrescentar o cabeçalho de vínculo e a exposição do sinal de contexto inválido.
- `npm run test:transport`: JWT renovado a cada requisição, vínculo capturado, descarte após saída, ausência de JWT no storage e contexto revogado; regressões anteriores preservadas.
- `npm run test:clerk`: provider/bridge React com SDK simulado, troca autorizada, limpeza dos contratos antigos, estabilidade do conector ao remontar telas, entrada na demo e sessão invalidada.
- `npm run test:p0`: seis perfis offline, sem storage, sem rede operacional, polling e respostas tardias.
- Build/exportação da demo e build do modo Clerk aprovados. O build Clerk usou chaves de formato de teste **fictícias**, sem autenticar em uma instância real.
- Navegador na exportação: orientação de login → demo Analista → Documentos → saída, sem chamadas operacionais ou Clerk e sem erros de JavaScript.

**Validação ainda necessária na instância configurada:** receber convite em e-mail controlado → ativar/verificar identificação → aceitar vínculo → acessar operação permitida → recuperar senha → encerrar/revogar sessão. Esta etapa não foi executada porque o ambiente não recebeu chaves/domínio Clerk reais. Nenhum e-mail real foi enviado. Não foi repetida a suíte completa por perfil nem realizado deploy.

## Complemento — convite do administrador inicial ao cadastrar auditora

A rota POST /api/platform/auditors aceita no modo Clerk os campos nome, administrador e email. Apenas a identidade institucional ADMIN_PLATAFORMA pode criar organizações auditoras. A operação cria a organização e emite convite ADMIN_BH pelo mecanismo de /api/auth/invitations, retornando convite_status=PENDING, sem administrador_id nem token_teste. Em caso de falha no envio, a compensação remove apenas o convite identificado pela tentativa inicial. A organização só é removida, sob transação de escrita, se não houver outros convites, usuários ou contratos; operações concorrentes bem-sucedidas são preservadas e auditadas.

O usuário interno somente é criado após o destinatário aceitar o convite em /api/auth/invitations/{id}/accept, com e-mail verificado, provedor ativo e revalidação do emissor. A listagem institucional mostra convites iniciais e administradores já ativados. O cadastro por token continua restrito ao ambiente demonstrativo.

O envio exige que a conta Admin Geral já tenha sido provisionada e autenticada pelo Clerk. Não substitui a validação manual de convite e login em instância real.
