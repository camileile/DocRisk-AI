# Administrador Geral da Plataforma

Novo papel ADMIN_PLATAFORMA, independente de ADMIN_BH. A área `/plataforma` contém visão geral institucional, catálogo informativo dos quatro módulos e auditoria das ações da administração geral. `/plataforma/auditoras` cadastra uma organização auditora com administrador inicial e permite ativar/desativar esses administradores. `/plataforma/configuracoes` edita os dados do cadastro institucional (nome e contato de suporte).

O cadastro institucional não altera o branding do site, domínios, autenticação ou regras de análise. Os três módulos futuros continuam PLANEJADOS, sem ativação funcional fictícia.

A identidade geral fica na tabela platform_accounts e é autenticada por token próprio. Ela não pertence à Bernhoeft nem recebe contratos operacionais. A tabela é aditiva: não recria organizations nem modifica vínculos ou tokens existentes. A conta demonstrativa é criada apenas quando DOCRISK_DEMO_MODE=1; a inicialização é idempotente. Não há fluxo de criação de administradores gerais por usuários empresariais.

GET /api/platform/registry retorna apenas estrutura de auditoras, administradores, catálogo, dados institucionais e os últimos 30 eventos da administração geral. Não retorna tokens, documentos, análises ou pareceres. POST /api/platform/auditors cria a auditora e um ADMIN_BH associado; o token inicial de teste aparece somente nessa resposta. PATCH /api/platform/administrators/{uid}/status aceita apenas administradores de auditoras. PATCH /api/platform/settings salva dados institucionais. Todas as mutações exigem modo demo e papel/identidade institucional conferidos pelo backend.

O administrador de uma auditora nova começa com escopo empresarial vazio e não acessa dados da Bernhoeft. Desativação bloqueia seu token na próxima requisição. As alterações são auditadas sem gravar tokens. O Admin Geral não entra nas áreas operacionais nem publica pareceres.

A demonstração offline inclui o sexto perfil, sem contratos e somente consulta. O acesso com token continua demonstrativo; autenticação corporativa, convites, recuperação de acesso e provisionamento produtivo do administrador geral permanecem pendentes.

Validação enxuta: três cenários focados de API (identidade/permissões/idempotência, cadastro e revogação de administrador de auditora, configurações e bloqueio de mutações fora do demo) e build com TypeScript. Suíte completa e navegador ficam para a integração final dos seis perfis. Sem merge ou deploy; refinamento visual adiado.
