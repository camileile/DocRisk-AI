# D3-08 — parecer corporativo e publicação conferida

Complementa as proteções D2-05/D2-08 existentes, sem alterar os denominadores ou regras trabalhistas.

## Comportamento

- A prévia e o parecer passam a mostrar número/versão, organização responsável, autor do rascunho, responsável pela conferência e recomendações, além de escopo, resultados, evidências e limitações existentes.
- Autor é identificado pelo backend a partir da conta que criou o rascunho. Responsável pela conferência é o Analista autenticado que solicita a prévia/publica. Os nomes e IDs entram no snapshot; mudanças posteriores no cadastro não reescrevem a identificação histórica.
- Recomendações ao cliente são texto público, separado das observações internas. Podem ser preenchidas na criação ou editadas enquanto o parecer é rascunho. Se vazias, a prévia propõe orientações conservadoras a partir das situações do resumo, sem inventar impacto financeiro nem tratar dados insuficientes como regularidade.
- Editar recomendações exige o hash da prévia atual e é recusado para versões publicadas. A tela bloqueia PDF/publicação enquanto há texto não atualizado e exige marcar a conferência de autoria, responsável, recomendações, resultados e limitações.
- A publicação mantém o bloqueio transacional e a regra de versões do D2-08. Mudança de dados, recomendações ou identificação após a conferência retorna 409 e exige nova prévia. Submissões duplicadas também têm guarda na interface.

## Correspondência exata da prévia

O hash continua ignorando `gerado_em`, preservando a correção D2-08 para quem publica minutos depois. A diferença é que cada combinação de parecer/Analista/hash guarda sua prévia em `report_previews`; pedidos repetidos do mesmo conteúdo recebem a mesma cópia. Publicar confere o hash contra os dados atuais e grava **essa cópia**, inclusive seu horário e metadados, em `reports.conteudo_json`.

Assim, a passagem do tempo não invalida a conferência nem regenera o conteúdo publicado. Duas abas com o mesmo conteúdo recebem o mesmo horário. Alteração do conteúdo gera outro hash. Outro Analista precisa conferir sua própria prévia, que registra sua identidade como responsável. A prévia não publica o rascunho e não é exposta à Contratante.

`report_editorial` guarda o texto público editável do rascunho; `report_previews` guarda as cópias conferíveis. As tabelas são aditivas, criadas por `db.init_db`, sem remover registros ou exigir coluna nova nos pareceres existentes. Observações internas não são incorporadas ao snapshot público.

## PDF e identidade

`GET /api/reports/{id}/pdf` gera PDF a partir do snapshot. Para rascunho, exige `conteudo_sha256` de prévia existente do próprio Analista e recusa exportação quando os dados já mudaram. O arquivo é marcado como **PRÉVIA DO RASCUNHO — não publicada**. Publicados usam exclusivamente o conteúdo congelado; não consultam documentos/OCR para reconstruí-lo.

O PDF inclui autoria/conferência, versão/competência, resumo, recomendações, itens/evidências e limitações, com paginação e rodapé. Usa o logo oficial, cores índigo/violeta e faces derivadas Sora/DM Sans, com fontes/licenças empacotadas na API. Não depende de fontes remotas durante a geração. O PNG do logo deriva do SVG oficial e preserva seus gradientes; o SVG original também é mantido.

Parecer histórico sem autoria/recomendações no snapshot indica “não registrado nesta versão”; não inventa dados históricos a partir do cadastro atual. PDF não contém observações internas nem valores monetários extraídos dos documentos.

| Perfil | Acesso preservado |
| --- | --- |
| Analista Bernhoeft | Criar/editar rascunho, conferir, publicar e exportar versões de contratos autorizados |
| Gestor da Contratante | Consultar/baixar somente parecer atual publicado dos próprios contratos |
| Admin Bernhoeft / Admin Geral | Sem parecer, prévia, publicação ou PDF documental |
| Gestor/Operador da Fornecedora | Sem acesso a parecer/PDF |

A demonstração offline usa identificação/recomendações fictícias, com edição/publicação/PDF bloqueados. Continua sem fetch operacional.

## Evidências

- 12 casos novos de `api/tests/test_d3_08_report_document.py`: cópia exata apesar do tempo, autoria/conferência, notas privadas, edição/estado obsoleto, papéis/contratos, versões, histórico e PDF de 120 trabalhadores com o último item preservado.
- 4 regressões existentes de publicação foram aprovadas (versões, prévia obsoleta, concorrência e passagem do tempo). As asserções foram adaptadas ao acréscimo de metadados; o caso de tempo agora exige igualdade integral entre prévia e publicado.
- 4 testes existentes do portal da Contratante e 2 de contratos/OpenAPI de pareceres aprovados. Total: 22 verificações direcionadas de backend, sem repetir a suíte inteira por perfil.
- `npm run test:p0` e `npm run test:transport` aprovados. TypeScript/build/exportação estática aprovados.
- `web/scripts/report-smoke.cjs`, Chromium contra FastAPI/SQLite reais, com dados inteiramente sintéticos: PDF da prévia; edição pública; alteração concorrente seguida de publicação recusada; atualização/conferência; igualdade integral do conteúdo publicado; PDF do Analista e da Contratante; ausência de edição/notas internas no portal; viewport 390 px; sem erros de JavaScript.
- Logo/primeira página de PDF inspecionados visualmente. A composição preserva grupos de título/conteúdo ao mudar de página.

Execução do smoke: servir a exportação, iniciar FastAPI em modo demonstrativo com dados sintéticos e rodar `node web/scripts/report-smoke.cjs` com Playwright disponível. Aceita `DOCRISK_WEB_URL`, `DOCRISK_API_URL`, `DOCRISK_WEB_API_URL` e `DOCRISK_CHROMIUM_PATH`. Se a porta da API diferir da gravada no bundle, o teste encaminha a requisição para a API local real, mantendo método/payload/cabeçalhos; não fabrica respostas. A suíte completa de navegador não foi repetida.

Sem merge ou deploy. Inspeção física em dispositivo/projeção e auditoria manual de acessibilidade continuam pendentes; esta entrega não equivale à etapa D3-09.
