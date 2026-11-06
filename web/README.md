# DocRisk AI — Web

Interface em Next.js (App Router) + TypeScript, com identidade oficial DocRisk AI v1, Sora e DM Sans. CSS responsivo e componentes comuns de navegação.

```bash
npm install
npm run dev
```

Validação: `npm run build` e `npm run typecheck`. A exportação estática fica em `out/`, com `trailingSlash` para acesso direto às rotas em servidores estáticos.

## Páginas

| Rota | Conteúdo |
| --- | --- |
| `/` | Landing institucional e módulos |
| `/contato` | Preparação de mensagem para copiar, sem envio |
| `/acesso` | Seleção de perfil demonstrativo |
| `/painel` | Indicadores documentais e pendências do contexto |
| `/painel/lotes` | Histórico, busca e filtros dos lotes enviados |
| `/painel/lotes/[id]` | Arquivo, etapas, leitura, documentos e pendências vinculadas |
| `/painel/documentos` | Busca, situação e detalhes de referência documental |
| `/painel/revisao` | Fila de revisão documental do analista |
| `/painel/revisao/[id]` | Conferência das páginas e preparação da decisão |
| `/painel/conciliacoes` | Situação e resultado por trabalhador e competência |
| `/painel/conciliacoes/[id]` | Comparação de horas, insumos e limitações da análise |
| `/painel/pendencias` | Busca, filtros e orientações de correção |
| `/painel/envio` | Prévia local de seleção de arquivos sintéticos |

## Explorar

1. Abra `/acesso` ou use “Acessar demonstração” na landing.
2. Selecione Analista Bernhoeft ou Operador da fornecedora.
3. No painel, altere contrato/competência e navegue entre documentos e pendências.
4. Busque `DOC-002` nos documentos e abra os detalhes para ver a referência de evidência.
5. Consulte a orientação de `PEN-001` nas pendências.
6. Troque de perspectiva para explorar a prévia de envio da fornecedora.

O estado existe apenas na memória do navegador. Recarregar uma rota interna volta à seleção de perspectiva. Isso é navegação de demonstração, não autenticação nem controle de acesso de produção. O operador visualiza o Contrato Alfa e o rótulo “Em análise”, sem motivos internos da revisão no conteúdo apresentado. A autorização real deve ser feita pela API.

## Dados e integração

Os exemplos sintéticos estão em `lib/demo.ts`; os estados seguem os nomes de `api/docrisk_core/contracts.py`. Indicadores e listas usam a mesma fonte e o mesmo filtro de contrato/competência.

- O envio permite selecionar até 10 arquivos não vazios de até 20 MB, nas extensões PDF, PNG, JPG, JPEG e AEJ. Essas são restrições desta prévia, não um contrato definitivo da API.
- A seleção usa apenas nome e tamanho. Não lê conteúdo, transmite arquivos, cria lote, executa OCR ou resolve pendências.
- Detalhes de evidência usam referências sintéticas; não exibem um PDF original inexistente.
- Busca e filtros funcionam localmente. Revisão, aprovação, notificações e publicação não são simuladas como ações concluídas.
- Perfil, arquivos selecionados e filtros não são persistidos.
- Contratante, administrador e pareceres ficam para as próximas etapas. A fila e a conferência documental estão disponíveis como demonstração.
- Os três módulos futuros continuam apenas como visão de expansão na landing.

Rotas de backend planejadas estão em `api/docrisk_core/routes/__init__.py`. Autenticação e rotas operacionais ainda precisam ser implementadas antes de integrar dados reais. O formulário de contato continua sem canal comercial fictício e sem envio.

## Verificações desta etapa

Build e TypeScript aprovados. Conferência de desktop no navegador: escolha de ambas as perspectivas, navegação, busca documental, expansão de detalhes, mudança de contrato e orientação de pendência. A seleção de arquivos foi revisada no código; não houve transmissão ou processamento. CSS adaptado para telas estreitas; visualização móvel não verificada neste ambiente.

## Lotes — etapa atual

`lib/batches.ts` contém nove lotes sintéticos com os quatro estados oficiais: RECEBIDO, PROCESSANDO, CONCLUIDO e FALHA_PROCESSAMENTO. Os exemplos incluem PDF, imagem e AEJ. AEJ não tem páginas nem OCR; os estados são retratos fixos, sem atualização em tempo real.

Documentos dos lotes reutilizam `lib/demo.ts`. As pendências exibidas no detalhe são somente aquelas cujo documento de referência pertence ao lote; solicitações sem documento associado continuam no acompanhamento geral. Os links de conferência abrem a biblioteca filtrada por `?lote=...`, com detalhe em `?documento=...`; orientações abrem por `?pendencia=...`. Contrato e competência continuam limitando os resultados.

Na perspectiva da fornecedora, apenas o Contrato Alfa está disponível. Um lote de outro contexto exige selecionar o contexto correspondente antes de exibir os detalhes. Esses comportamentos organizam a demonstração e não substituem autorização no backend. O reprocessamento é apenas explicado; não há botão que finja executar a operação.

Validação desta etapa: build estático e TypeScript; verificação de integridade de vínculos lote/documento/pendência e limites de páginas; conferência desktop da busca, detalhes, navegação documento/pendência, falha técnica e cenário AEJ. Nenhum arquivo real foi enviado. Visualização móvel segue não verificada.

## Revisão humana — etapa atual

A fila `/painel/revisao` aparece somente na perspectiva ANALISTA_BH. Ela usa o mesmo contrato, competência e estados da biblioteca documental. Os exemplos `DOC-002`, `DOC-006` e `DOC-008` possuem referências de página em `lib/review.ts`; este último inclui o agrupamento de páginas 1–3 do novo `LOTE-008` e um candidato contíguo (`DOC-009`, página 4) para demonstrar união. Os indicadores existentes são derivados da mesma base e incorporam esses exemplos.

A tela de conferência oferece navegação entre páginas sintéticas, zoom textual, ajuste de classificação/vínculo/competência e preparação de quatro ações: aprovar, solicitar correção, dividir e unir ao próximo. Divisão exige múltiplas páginas; união exige candidato contíguo com lote, contrato, trabalhador, competência e tipo compatíveis. Os campos não modificam as fontes de dados.

Uma justificativa e a confirmação de conferência são obrigatórias para preparar a prévia. Editar os campos elimina a prévia anterior. Restaurar campos repõe os valores originais. A prévia não executa a ação, não cria pendência e não altera a fila. Nenhum parecer é publicado. O fluxo final depende da implementação e autorização da API, inclusive auditoria. Divisão e união reais continuam pendentes no backend, conforme `docs/F2_INTEGRACAO.md`.

As páginas exibidas são reconstruções HTML explicitamente sintéticas, não arquivos originais, OCR ou resultados do Gemini. Horas e reais aparecem separados. Na integração, usar a imagem privada por rota autenticada e respeitar os motivos internos exclusivos da Bernhoeft. A ocultação na interface não é uma barreira de segurança.

Verificação: build estático e TypeScript; integridade das páginas e dos vínculos com documentos/lotes; conferência desktop da fila, paginação, zoom, prévias de divisão/união e permanência do documento na fila. A visualização móvel ainda não foi verificada.

## Conciliações — etapa atual

`/painel/conciliacoes` e `/painel/conciliacoes/[id]` pertencem à perspectiva ANALISTA_BH. Busca, filtros de situação/resultado e contexto usam dez retratos sintéticos fixos em `lib/analyses.ts`, com os nomes de estados e resultados do contrato Python. Não há implementação do motor de conciliação no frontend nem chamada operacional à API.

Exemplos principais:

- `ANA-001`: documento em revisão, horas disponíveis como campos sintéticos, sem comparação liberada.
- `ANA-002`: página de ponto ausente, bloqueio seletivo, vínculo com `PEN-001`.
- `ANA-007`: 12 h no ponto e 8 h na folha, indício de diferença de 4 h a conferir.
- `ANA-008`: 10 h em ambos os documentos e diferença de 0 h, sem atestar regularidade integral.
- `ANA-009`: ponto com 6 h e folha somente com valor em reais; referência em horas ausente, diferença não comparada.
- `ANA-010`: acompanhamento inicial antes de receber os documentos, sem execução de comparação.

`LOTE-009` e os documentos `DOC-010` a `DOC-017` fornecem os exemplos documentais dos três resultados analisados. `lib/document-fields.ts` disponibiliza campos sintéticos nos detalhes do documento, sem representar OCR ou extração. A integridade entre valores da análise e esses campos foi conferida. Os valores em reais aparecem em seção própria, separados da comparação de horas. Ausências ficam como não informadas; diferença zero continua visível. Ausência de comprovante não é apresentada como prova de atraso e presença não atesta quitação integral.

Os detalhes incluem fonte por documento/lote/página/versão, registro demonstrativo em Recife, regra de referência HE-CMP-v1, solicitações do par e próximos passos de conferência. Uma pendência resolvida ou reenviada não libera automaticamente uma análise. Uma ausência documental pode estar demonstrada sem uma solicitação já cadastrada; a criação de pendências depende do backend. Nenhuma análise é aprovada, recalculada ou publicada pela interface.

Verificação desta etapa: build e TypeScript; integridade dos pares e dos insumos, diferenças em horas, zero versus ausência e valores em reais; conferência desktop da listagem, filtro de divergências, detalhe do indício, documento de origem e cenário de dados insuficientes. Visualização móvel ainda não verificada.
