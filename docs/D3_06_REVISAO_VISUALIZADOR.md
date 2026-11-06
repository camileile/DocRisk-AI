# D3-06 — revisão assistida e visualizador por página

Depende do transporte D3-05 (PR #34). Nenhum novo OCR foi implementado: o visualizador e as evidências usam as imagens e análises já preservadas.

## Comportamento

- Detalhes e revisão de documentos têm seletor de página, anterior/próxima, zoom de 50% a 300%, rotação em passos de 90° e restauração. Uma única imagem fica montada por vez; mudanças de página cancelam a leitura anterior e liberam o blob.
- As telas pedem `GET /api/documents/{id}?include_page_text=false`, que devolve referências de páginas sem carregar o texto OCR de todas elas. O texto é consultado em `GET /api/documents/{id}/pages/{page_id}` e a imagem continua na rota existente. A página deve pertencer ao documento e o contrato precisa estar autorizado. O parâmetro mantém o padrão anterior para consumidores existentes.
- Campos mostram valor atual, valores extraídos nas páginas, origem real (`TEXTO_PDF`, `TESSERACT`, etc.) e confiança da **classificação**. Não existe confiança individual por campo na extração atual; a interface declara essa limitação e não inventa percentuais.
- O Analista pode corrigir os cinco campos extraídos de documentos não AEJ em revisão/pendência. Cada alteração exige justificativa, página de origem válida e o estado lido (`esperado_em`). Horas e valores continuam distintos, finitos e não negativos; campo vazio vira nulo, nunca zero. Datas são validadas no backend.
- A ação `editar_campos` mantém a revisão pendente e recalcula a conciliação do par afetado. Aprovar continua sendo uma decisão separada. AEJ preserva o fluxo de cálculo e revisão estruturada existente.
- O histórico interno guarda autor, data, justificativa, fonte e antes/depois na nova tabela `document_field_reviews`, criada de forma aditiva por `db.init_db`. O OCR e as análises originais permanecem intactos. União de documento com histórico de correção é recusada, preservando a rastreabilidade.
- Fornecedoras não recebem evidências ou histórico interno de campos. A nova leitura por página mantém mascaramento do texto para a fornecedora. Admin Bernhoeft, Admin Geral e Contratante não ganham acesso documental.
- A demo offline suporta o visualizador com os dados fictícios existentes; correções continuam bloqueadas.

## Validação direcionada

- 20 casos de `api/tests/test_d3_06_review_viewer.py`: carga sob demanda, fontes, histórico, conciliação, valores inválidos/ausentes, estado obsoleto, atomicidade e permissões de escrita/leitura afetadas.
- 17 casos existentes de `api/tests/test_f1_revision.py` passaram sem mudanças, cobrindo aprovação, agrupamento e reprocessamento. Não foi repetida a suíte inteira por perfil.
- `npm run test:transport` e `npm run test:p0` aprovados após a integração, incluindo seis perfis offline sem rede e concorrência.
- TypeScript, build e exportação estática aprovados.
- `DOCRISK_VIEWER_DOC_ID=<id sintético> node web/scripts/review-viewer-smoke.cjs`: navegador Chromium contra FastAPI/SQLite, documento sintético de 80 páginas. Verifica uma imagem/texto por seleção, reaproveitamento no zoom/rotação, edição com página/justificativa, persistência do histórico, viewport de 390 px e visualizador offline sem fetch operacional. Aceita `DOCRISK_CHROMIUM_PATH` para Chromium local.

A inspeção responsiva automatizada não substitui auditoria manual de acessibilidade (D3-09), dispositivo físico ou projeção. Evidências indicam páginas de origem; não há coordenadas/bounding boxes por campo nos dados atuais. Histórico na tela é limitado às 50 correções mais recentes. Sem merge ou deploy.
