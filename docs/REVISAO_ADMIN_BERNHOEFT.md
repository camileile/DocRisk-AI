# Revisão do Administrador Bernhoeft

Decisão confirmada nesta revisão: **somente gestão**. O Admin Bernhoeft administra empresas, contratos, usuários administrativos/gestores, indicadores agregados e auditoria. A execução e consulta detalhada do trabalho documental ficam com o Analista.

## Correções

| Achado | Correção |
| --- | --- |
| A interface era administrativa, mas a API permitia leitura documental e analítica pelo Admin | Rotas de documentos, lotes, páginas, fonte original, busca, pendências detalhadas, análises, pareceres/prévia, trabalhadores e mapeamento/revisão AEJ exigem Analista ou fornecedora conforme o fluxo. Admin também não reprocessa lotes. |
| Auditoria retornava os últimos 500 eventos da plataforma inteira | Retorna ações da própria auditora e eventos de documentos/lotes/pendências/acessos negados vinculados aos seus contratos. A restrição vem antes do limite. Compartilhar uma fornecedora não compartilha o histórico de outra auditora. |
| Empresas já cadastradas, mas ainda sem contrato, ficavam fora dos contadores | Visão geral considera as empresas registradas/vinculadas à auditora. Filtrar uma contratante sem contrato mostra uma contratante e zero fornecedoras/contratos. |
| Nomes com espaços passavam pela validação da API | Empresa, usuário e contrato têm o nome aparado antes de validar o comprimento mínimo. |

Foram acrescentados rótulos legíveis para eventos administrativos na auditoria e guardas nos formulários para impedir nova submissão enquanto uma requisição estiver em andamento.

## Permissões finais

- Mantém: visão geral, empresas/contratos, criação de ADMIN_BH/ANALISTA_BH e gestores de empresas autorizadas, ativação/desativação permitida, indicadores agregados e auditoria segregada.
- Não recebe: documentos, páginas/OCR/fontes, lotes, busca documental, análises ou pareceres detalhados; revisão, reprocessamento ou publicação de parecer.
- Operadores continuam geridos pelo Gestor da Fornecedora. Admin Geral permanece um papel independente.
- Acesso à própria conta não pode ser desativado pelo Admin Bernhoeft, como já ocorria.

## Validação

Na validação inicial, 18 verificações direcionadas e o build com TypeScript foram aprovados. Após integrar a main com os PRs #23 e #24, a suíte backend completa passou com 237 testes aprovados e 1 ignorado, com um aviso de compatibilidade Starlette/HTTPX. A validação de navegador não foi repetida localmente.

O teste do PDF anonimizado foi alinhado à decisão de gestão apenas: Admin recebe 403, os demais perfis operacionais autorizados continuam recebendo PDF e a tentativa negada não gera evento de download concluído. Essa rota também integra a matriz de bloqueios do Admin.

Cadastros e alterações permanecem restritos ao modo de testes. Autenticação produtiva e refinamento visual seguem pendentes. Alterações entregues em branch/PR próprio, sem merge ou deploy automático.
