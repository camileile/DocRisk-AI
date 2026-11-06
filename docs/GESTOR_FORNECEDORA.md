# Gestor da Fornecedora

As telas existentes de envio, lotes, documentos e pendências foram reaproveitadas. A visão geral agora respeita o contrato selecionado, como as outras consultas. O gestor pode reprocessar lotes com falha enviados por outros usuários de sua fornecedora; a API verifica o contrato antes da ação.

Nova tela: `/painel/operadores`, exclusiva de GESTOR_FORN. Lista a equipe da organização inteira, independentemente do filtro de contrato, cadastra operadores e ativa/desativa seus acessos sem apagar histórico.

API: GET/POST `/api/supplier/operators`, PATCH `/api/supplier/operators/{id}/status`. A organização e o papel OPERADOR_FORN são determinados pelo backend. Não é possível escolher outra empresa, promover usuários nem alterar gestores. A listagem nunca retorna tokens. Desativação invalida o acesso já emitido na próxima requisição.

Cadastros e alterações de acesso exigem DOCRISK_DEMO_MODE=1. O cadastro retorna um token de teste uma única vez, conforme o padrão do Admin Bernhoeft. Não há convite ou autenticação produtiva nesta etapa. Na demonstração offline, a lista é fictícia e somente para consulta.

Validação enxuta: três testes focados em cadastro/acesso compartilhado/revogação, isolamento e restrição ao demo, reprocessamento autorizado; compilação frontend. A suíte completa e a validação integrada de todos os perfis ficam para a etapa final. PR independente, sem merge ou deploy; refinamento visual adiado.
