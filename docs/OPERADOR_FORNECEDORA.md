# Operador da Fornecedora — fechamento do fluxo

Reaproveitados envio de PDF/imagem/AEJ, acompanhamento de lotes, consulta documental, busca, histórico de versões e correções. O acesso é organizacional pelos contratos autorizados, sem limitar a consulta ao remetente do lote.

Ajustes desta etapa:

- Filtro de documentos usa “Em análise” para a fornecedora e traduz esse estado no backend. O histórico de versões usa o mesmo rótulo externo, sem revelar status de revisão interna.
- GET /api/documents e GET /api/search aceitam contract_id opcional, validado pelo backend antes da consulta e dos limites. A tela aplica o contrato à lista e à busca; troca de contrato reinicia a busca.
- Documento pendente oferece acesso às correções do contrato correspondente.
- Reenvio admite AEJ/TXT além de PDF e imagens; aplica a validação de arquivo já utilizada no envio e bloqueia submissão duplicada enquanto aguarda resposta.
- A demonstração offline acompanha os filtros e estados externos.

Validação enxuta: três testes focados (documentos compartilhados/filtros/permissões, busca por contrato, envio e reenvio real de PDF sintético por outro usuário com preservação de versões). Compilação e TypeScript aprovados. Não foi executada suíte completa nem teste de navegador nesta etapa; integração final permanece pendente.

A gestão de operadores pertence ao Gestor da Fornecedora (PR #19), não ao Operador. Publicação de parecer e revisão analítica continuam exclusivas da Bernhoeft. A branch parte da main que contém o PR #15 e preserva as branches dos PRs #18 e #19. Sem merge ou deploy; autenticação produtiva e refinamento visual seguem pendentes.
