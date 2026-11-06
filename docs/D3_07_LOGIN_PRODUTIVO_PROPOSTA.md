# D3-07 — proposta para login produtivo

Estado: proposta para definição do provedor, convites e recuperação. O usuário escolheu ampliar D3-07 para login produtivo. Este documento não troca o login existente, não cria contas, não envia mensagens e não provisiona serviços.

## Provedor recomendado

Recomendo **Clerk**, com SDK oficial para Next.js e verificação de identidade na FastAPI. Entrega identificação, verificação de e-mail, sessão e recuperação sem implementar armazenamento de senhas na aplicação. A decisão final depende de saber se a Bernhoeft exige um provedor corporativo específico, como Microsoft Entra ID/SSO. Não há informação confirmada sobre essa exigência, plano contratado ou região de dados.

A seleção do provedor não transfere a autorização do DocRisk para claims editáveis no navegador. O backend continua determinando papel, organização, contratos e operações permitidas a partir dos cadastros internos. Não usar os papéis genéricos de uma organização Clerk como substitutos dos seis perfis aprovados.

Alternativa caso exista identidade corporativa obrigatória: integrar o provedor OIDC da organização e preservar o mesmo contrato de autorização descrito abaixo. Verificar suporte e plano antes de assumir que federação/SSO está disponível.

## Entradas e execução

- `/acesso`: demo offline, com os seis perfis fictícios e nenhuma credencial operacional.
- `/entrar`: identificação produtiva pelo provedor escolhido, sem seletor de papel.
- `/operacao`: token demonstrativo disponível apenas na configuração de testes. Backend produtivo recusa os tokens do seed e não expõe `/api/demo/users`.
- O build operacional precisa de runtime Next.js para sessão e proteção das rotas; `output: export` fica no build explícito da demo. O site público pode continuar com a mesma identidade e conteúdo. Configurar essa separação faz parte da implementação de D3-07.
- Manter FastAPI como autoridade de autorização. Ambiente produtivo requer armazenamento durável dos cadastros, vínculos, convites e bloqueios; SQLite da demonstração não deve virar um banco efêmero de produção. Infraestrutura/banco, domínio e remetente verificado precisam ser definidos na preparação do ambiente produtivo.

## Identidade e vínculos

Criar um vínculo persistido entre `(issuer, subject)` validado pelo provedor e a conta interna autorizada. Nunca associar uma conta apenas pelo domínio do e-mail nem aceitar `org_id`, papel ou contratante fornecidos pela tela como prova de permissão.

Usuários empresariais continuam pertencendo à organização correspondente. A identidade da fornecedora permanece única, mesmo com contratos de várias contratantes. A seleção mostra exclusivamente os vínculos ativos do usuário, retornados pela API; mudar vínculo não duplica empresa ou contrato e refaz o contexto da interface. IDs adulterados retornam acesso negado antes de consultar documentos.

Admin Geral mantém a identidade institucional independente em `platform_accounts`; não converter essa identidade em usuário operacional nem dar acesso documental por troca de contexto. Admin Bernhoeft mantém somente gestão e auditoria segregada. Uma identidade autenticada sem vínculo ativo recebe a tela de acesso pendente, sem dados operacionais.

## Convites

Convites são emitidos pelo backend após conferir papel do emissor, organização e contrato. Cadastro público não concede acesso ao produto. Proposta de prazo: **72 horas**, com uso único e possibilidade de revogação/reemissão pelo responsável autorizado.

| Emissor | Pode convidar | Limite preservado |
| --- | --- | --- |
| Admin Geral | Administradores Bernhoeft | Cadastro institucional da organização auditora; sem documentos operacionais |
| Admin Bernhoeft | Analistas/administrativos e gestores empresariais já previstos no cadastro | Somente sua auditora e empresas/contratos autorizados; não concede privilégios de plataforma |
| Gestor da Fornecedora | Operadores da própria fornecedora | Mesma identidade empresarial e escopo de contratos autorizado |
| Demais perfis | Nenhum convite administrativo | Mantém as funções atuais |

O registro interno guarda emissor, e-mail destinatário normalizado, organização/conta pretendida, papel, contratos, expiração e estado. O provedor envia a identificação/aceitação; a ativação do vínculo acontece apenas quando a identidade verificada corresponde ao destinatário e o convite permanece válido. Revogar ou expirar um convite impede a ativação mesmo se o usuário tiver criado uma conta no provedor.

Aceitar convite não permite editar o papel ou os contratos. Links usam destinos permitidos, sem redirecionamento arbitrário. O primeiro Admin Geral é provisionado institucionalmente, fora de um cadastro público. Nenhum convite real deve ser enviado durante os testes.

## Recuperação de acesso

Usar recuperação nativa do provedor, com e-mail verificado e retorno para domínio permitido. O DocRisk não guarda senhas nem cria um reset por token próprio. A resposta pública não revela se o e-mail possui conta/vínculo.

Recuperar a identificação não reativa vínculo desativado, convite revogado ou empresa sem autorização. Um administrador autorizado pode revogar sessões/vínculos; o titular pode encerrar as próprias sessões. Mudança de credencial e revogação devem invalidar sessões conforme os recursos do provedor selecionado, com tratamento explícito na aplicação.

## Sessão inválida e revogação

Na API, validar assinatura por JWKS confiável, algoritmo permitido, emissor, destinatário/audience e validade temporal do token, usando SDK/biblioteca mantida. Resolver o usuário e seus vínculos ativos no backend a cada requisição. Token válido sem vínculo autorizado não libera documentos.

O vínculo revogado localmente deve ser negado imediatamente nas requisições seguintes. Para sessão encerrada no provedor, definir integração de revogação (eventos autenticados/idempotentes e checagem do estado da sessão nas operações protegidas). Não presumir que verificar apenas a assinatura JWT detecta revogação: um JWT emitido pode continuar válido até expirar. O tempo de propagação de eventos e a estratégia de consulta ao provedor devem ficar explícitos na implementação e nos testes.

O frontend encerra o contexto em 401, cancela requisições e remove dados do perfil anterior. Um 403 não muda automaticamente o usuário para outro perfil. Troca de vínculo só usa opções autorizadas. Falha do provedor não ativa fallback para seed/token demonstrativo.

## Entrega proposta após definir o provedor

1. Integrar identidade e verificação na FastAPI, com configuração produtiva separada da demo e do seed.
2. Implementar `/entrar`, contexto autorizado e sessão inválida, apoiando-se no transporte D3-05.
3. Implementar convites e recuperação conforme os limites acima, usando destinos e remetente verificados.
4. Testar login → vínculo → operação autorizada → saída, convite válido/expirado/revogado, recuperação, sessão encerrada e tentativa de acesso entre organizações. Reaproveitar os testes de permissão existentes.

Não há credenciais, criação de conta no provedor, provisionamento de banco, envio de e-mail, merge ou deploy neste documento. A escolha a resolver antes de implementar é se podemos adotar Clerk ou se existe um provedor corporativo obrigatório.
