# Administrador Geral da Plataforma

Novo papel ADMIN_PLATAFORMA, independente de ADMIN_BH. A área `/plataforma` contém visão geral institucional, catálogo informativo dos quatro módulos e auditoria das ações da administração geral. `/plataforma/auditoras` cadastra uma organização auditora com administrador inicial e permite ativar/desativar esses administradores. `/plataforma/configuracoes` edita os dados do cadastro institucional (nome e contato de suporte).

O cadastro institucional não altera o branding do site, domínios, autenticação ou regras de análise. Os três módulos futuros continuam PLANEJADOS, sem ativação funcional fictícia.

A identidade geral fica na tabela platform_accounts e é autenticada por token próprio. Ela não pertence à Bernhoeft nem recebe contratos operacionais. A tabela é aditiva: não recria organizations nem modifica vínculos ou tokens existentes. A conta demonstrativa é criada apenas quando DOCRISK_DEMO_MODE=1; a inicialização é idempotente. Não há fluxo de criação de administradores gerais por usuários empresariais.

GET /api/platform/registry retorna apenas estrutura de auditoras, administradores, catálogo, dados institucionais e os últimos 30 eventos da administração geral. Não retorna tokens, documentos, análises ou pareceres. POST /api/platform/auditors cria a auditora e um ADMIN_BH associado; o token inicial de teste aparece somente nessa resposta. PATCH /api/platform/administrators/{uid}/status aceita apenas administradores de auditoras. PATCH /api/platform/settings salva dados institucionais. Todas as mutações exigem modo demo e papel/identidade institucional conferidos pelo backend.

O administrador de uma auditora nova começa com escopo empresarial vazio e não acessa dados da Bernhoeft. Desativação bloqueia seu token na próxima requisição. As alterações são auditadas sem gravar tokens. O Admin Geral não entra nas áreas operacionais nem publica pareceres.

A demonstração offline inclui o sexto perfil, sem contratos e somente consulta. O acesso com token continua demonstrativo; autenticação corporativa, convites, recuperação de acesso e provisionamento produtivo do administrador geral permanecem pendentes.

Validação enxuta: três cenários focados de API (identidade/permissões/idempotência, cadastro e revogação de administrador de auditora, configurações e bloqueio de mutações fora do demo) e build com TypeScript. Suíte completa e navegador ficam para a integração final dos seis perfis. Sem merge ou deploy; refinamento visual adiado.

## Cadastro da auditora e administrador inicial (Clerk)

No modo demonstrativo (DOCRISK_AUTH_MODE=token e DOCRISK_DEMO_MODE=1), o cadastro continua criando a organização e o usuário ADMIN_BH imediatamente, devolvendo um token **apenas de teste**. A demonstração offline permanece somente leitura.

No modo operacional (DOCRISK_AUTH_MODE=clerk e DOCRISK_DEMO_MODE=0), a mesma ação exige **nome da organização, nome e e-mail do administrador inicial**. A API:

1. Confirma a identidade institucional ADMIN_PLATAFORMA e o vínculo Clerk ativo de quem está cadastrando.
2. Rejeita nomes de auditoras duplicados, inclusive diferenças de caixa e espaços nas extremidades.
3. Cria a organização e emite um convite para ADMIN_BH pelo fluxo já existente de Clerk, com validade de 72 horas.
4. Só considera a criação concluída quando o convite é registrado como PENDING. Falha no envio desfaz o cadastro da organização e remove o convite local.
5. **Não cria usuário operacional nem retorna token demonstrativo** nessa etapa. O administrador é criado em users e recebe vínculo autorizado somente após confirmar o e-mail e aceitar o convite.
6. Exibe convite pendente e administrador ativado na listagem de auditoras. A revogação de vínculo real acontece na tela Vínculos; botões de status por token de testes permanecem indisponíveis em modo Clerk.

O Admin Geral pode emitir novo convite para ADMIN_BH em uma auditora já cadastrada, pela gestão de vínculos, caso o convite anterior expire ou seja revogado. Recuperação de senha é responsabilidade do Clerk. A auditora começa sem contratos ou empresas.

Este ajuste não implementa autorização individual por contrato nem libera outras mutações de plataforma para produção. O ensaio real depende de uma instância Clerk configurada, e-mail controlado, domínio autorizado e armazenamento persistente.

Evidências: api/tests/test_d3_07_clerk.py e web/components/platform-portal.tsx.
