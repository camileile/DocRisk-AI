# Gestor da Contratante — portal funcional

## Navegação e fluxo

- `/contratante`: indicadores dos pareceres publicados e resultados por contrato/fornecedora.
- `/contratante/pareceres`: consulta da publicação, versão, competência, escopo, resumo, evidências referenciadas e limitações.
- Filtros por fornecedora, contrato e competência ficam na URL. O link “Consultar parecer” preserva o filtro e identifica a publicação.
- Ao mudar fornecedora, o contrato e a competência são limpos; ao mudar contrato, a competência é limpa. A seleção inicial usa a competência mais recente com publicação no escopo.
- Sem publicação, a tela informa a ausência. Sem comparação válida, taxa e cobertura ficam indisponíveis (—).
- Navegação móvel usa o mesmo menu recolhível das demais áreas.

## API e acesso

`GET /api/client/overview` e `GET /api/client/reports` aceitam `fornecedora_id`, `contract_id` e `competencia` (MM/AAAA).

Ambos exigem token de `GESTOR_CONTR` e restringem o escopo por `contracts.contratante_id` da organização autenticada. O frontend não define a organização autorizada. Fornecedora compartilhada não concede acesso aos contratos de outra contratante. Filtros fora do escopo retornam resultado vazio; a organização também precisa ser do tipo CONTRATANTE.

Pareceres visíveis têm status `APROVADO_PUBLICADO`; rascunhos, em revisão e versões substituídas não entram nas consultas. Caso existam duplicatas de publicação para contrato/competência, a versão mais alta é usada uma vez. O endpoint de pareceres mantém sua resposta anterior e acrescenta filtros opcionais. Sem competência, a API de pareceres retorna todas as competências; a tela aplica a competência selecionada no portal.

O dashboard lê somente os snapshots publicados. Não lê análises, trabalhadores, documentos ou pendências atuais. Assim, mudanças internas não publicadas não alteram indicadores externos. A consulta detalhada reaproveita o parecer publicado existente, sem acesso às imagens, texto de OCR, valores de pagamento ou observações internas da Bernhoeft.

## Indicadores

- Contratos com parecer / contratos no escopo, para a competência exibida.
- Comparações válidas: `com_divergencia + sem_divergencia` no resumo publicado. `dados_insuficientes` não entra nesse denominador, mesmo que a análise interna tenha status ANALISADA.
- Taxa: divergências / comparações válidas. Sem comparações válidas: indisponível.
- Cobertura nos pareceres: comparações válidas / trabalhadores nos snapshots publicados. Sem trabalhadores publicados: indisponível.
- Trabalhadores contam por vínculo contratual; o painel não promete pessoas únicas entre contratos.
- Sem comparação válida: dados insuficientes + bloqueados + em revisão + aguardando documentos, conforme a publicação.
- Contratos sem publicação aparecem separadamente e não são considerados regulares. Sua população não entra na cobertura dos pareceres publicados.

## Demonstração e validação

A demonstração offline inclui duas fornecedoras, uma sem publicação, e duas competências. Os dados são fictícios e somente para consulta. Setembro demonstra taxas indisponíveis; outubro demonstra divergência e cobertura parcial.

Validações:

```bash
# Na raiz, com dependências de api instaladas
python -m pytest api/tests -q
# Em web
npm ci
npm run typecheck
npm run build
# Com Playwright/Chromium e exportação servida em 127.0.0.1:4173
node scripts/offline-smoke.cjs
node scripts/contractor-smoke.cjs
# Com FastAPI local em modo demo, leitor textlayer e SQLite de testes
node scripts/smoke.cjs
DOCRISK_CONNECTED=1 node scripts/contractor-smoke.cjs
```

O smoke conectado publica um parecer pelo Analista antes de consultar o portal da Contratante. O teste específico cobre filtros, links diretos, recarga, ausência de publicação, erro com recuperação, bloqueio de navegação fora do perfil e menu/tabelas no celular. As mesmas validações foram adicionadas ao CI.

## Integração e continuidade

Branch independente de `main`, que já contém os PRs #14 (Analista) e #16 (AEJ). O PR #15 (Admin Bernhoeft) permanece separado: este trabalho não altera sua branch nem faz merge ou deploy. A compatibilidade precisa ser conferida na integração final, especialmente nos pontos comuns de rotas, demonstração e CI.

Continuam pendentes os próximos perfis na ordem aprovada: Gestor da Fornecedora, Operador da Fornecedora e Administrador Geral da Plataforma. A autenticação ainda é demonstrativa por token; convites, cadastro produtivo e autenticação corporativa não são entregues por esta etapa. Refinamento visual continua adiado.
