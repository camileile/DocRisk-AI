# D3-06 — revisão assistida e visualizador por página

Depende do transporte D3-05 (PR #34). Nenhum novo OCR foi implementado: o visualizador e as evidências usam as imagens e análises já preservadas.

## Comportamento

- Detalhes e revisão de documentos têm seletor de página, anterior/próxima, zoom de 50% a 300%, rotação em passos de 90° e restauração. Uma única imagem fica montada por vez; mudanças de página cancelam a leitura anterior e liberam o blob.
- As telas pedem `GET /api/documents/{id}?include_page_text=false`, que devolve referências de páginas sem carregar o texto OCR de todas elas. O texto é consultado em `GET /api/documents/{id}/pages/{page_id}` e a imagem continua na rota existente. A página deve pertencer ao documento e o contrato precisa estar autorizado. O parâmetro mantém o padrão anterior para consumidores existentes.
- Campos mostram valor atual, valores extraídos nas páginas, origem real (`TEXTO_PDF`, `TESSERACT`, etc.) e confiança da **classificação**. Não existe confiança individual por campo na extração atual; a interface declara essa limitação e não inventa percentuais.
- O Analista pode corrigir os cinco campos extraídos de documentos não AEJ em revisão/pendência. Cada alteração exige justificativa, página de origem válida e o estado lido (`esperado_em`). Horas e valores continuam distintos, finitos e não negativos; campo vazio vira nulo, nunca zero. Datas são validadas no backend.
- A ação `corrigir_campos` mantém a revisão pendente e recalcula a conciliação do par afetado. Aprovar continua sendo uma decisão separada. AEJ preserva o fluxo de cálculo e revisão estruturada existente.
- O histórico interno guarda autor, data, justificativa, fonte e antes/depois na tabela canônica existente `document_field_reviews`, criada de forma aditiva por `db.init_db`. O OCR e as análises originais permanecem intactos. União de documento com histórico de correção é recusada, preservando a rastreabilidade.
- Fornecedoras não recebem evidências ou histórico interno de campos. A nova leitura por página mantém mascaramento do texto para a fornecedora. Admin Bernhoeft, Admin Geral e Contratante não ganham acesso documental.
- A demo offline suporta o visualizador com os dados fictícios existentes; correções continuam bloqueadas.

## Validação direcionada

- 20 casos de `api/tests/test_d3_06_review_viewer.py`: carga sob demanda, fontes, histórico, conciliação, valores inválidos/ausentes, estado obsoleto, atomicidade e permissões de escrita/leitura afetadas.
- 17 casos existentes de `api/tests/test_f1_revision.py` passaram sem mudanças, cobrindo aprovação, agrupamento e reprocessamento. Não foi repetida a suíte inteira por perfil.
- `npm run test:transport` e `npm run test:p0` aprovados após a integração, incluindo seis perfis offline sem rede e concorrência.
- TypeScript, build e exportação estática aprovados.
- `DOCRISK_VIEWER_DOC_ID=<id sintético> node web/scripts/review-viewer-smoke.cjs`: navegador Chromium contra FastAPI/SQLite, documento sintético de 80 páginas. Verifica uma imagem/texto por seleção, reaproveitamento no zoom/rotação, edição com página/justificativa, persistência do histórico, viewport de 390 px e visualizador offline sem fetch operacional. Aceita `DOCRISK_CHROMIUM_PATH` para Chromium local.

A inspeção responsiva automatizada não substitui auditoria manual de acessibilidade (D3-09), dispositivo físico ou projeção. Evidências indicam páginas de origem; não há coordenadas/bounding boxes por campo nos dados atuais. Histórico na tela é limitado às 50 correções mais recentes. Sem merge ou deploy.

## Reconciliação com D1-06 (#41)

A revisão usa a ação `corrigir_campos` e o histórico por campo já existente em `document_field_reviews`, sem segunda tabela ou formulário duplicado. O visualizador envia `motivo`, `esperado_em` e `fontes` por campo; a fonte validada é registrada no histórico canônico. A revisão com página conferida aceita ausência explícita (`null`) e mantém o documento em revisão até aprovação. O contrato anterior com `motivo` e `fonte` textual continua compatível.

## Complemento — revisão manual iniciada pelo Analista

A revisão não deve ficar limitada à fila automática. Na área **Documentos**, somente o perfil ANALISTA_BH visualiza um atalho **Revisar** para documentos em REVISAO_HUMANA ou PENDENTE_CORRECAO, além de **Abrir** para consultar o detalhe. O documento pendente pode ser conferido na tela de revisão, sem revogar automaticamente a pendência junto à fornecedora.

Em documento **APTO**, o detalhe exibe **Iniciar revisão manual**. O Analista informa motivo de 10 a 500 caracteres, e a API valida papel, escopo do contrato, status e o instante da leitura para impedir alterações sobre estado obsoleto. A operação muda o documento para REVISAO_HUMANA, conserva o motivo no histórico de motivos, registra evento de auditoria, recalcula a conciliação pertinente e redireciona ao formulário de revisão existente. O documento passa a aparecer na fila de exceções. Esse fluxo também vale para um AEJ apto: após iniciar, usa a tela de conferência estruturada do AEJ.

Não é permitido reabrir uma versão **SUBSTITUIDO** nem transformar uma pendência de correção em revisão por esse comando. A ação não concede permissão à fornecedora, contratante ou administradores. A demonstração offline continua sem mutações. O histórico de campo corrigido é preservado; a abertura guarda autor, motivo e data na trilha administrativa.

Validação: api/tests/test_d3_06_review_viewer.py, ações de revisão voluntária e controles de permissão/estado; web/scripts/smoke.cjs, navegação real pelo novo botão de abertura e aprovação subsequente.
