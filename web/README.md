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
| `/painel/pareceres` | Versões e situação dos pareceres na visão Bernhoeft |
| `/painel/pareceres/[id]` | Conteúdo, revisão e preparação local de encaminhamento |
| `/contratante` | Pareceres publicados do contrato da contratante |
| `/contratante/[id]` | Consulta da versão publicada com conteúdo específico |
| `/administracao` | Auditoria demonstrativa do perfil ADMIN_BH (eventos sintéticos) |
| `/painel/pendencias` | Busca, filtros e orientações de correção |
| `/painel/envio` | Prévia local de seleção de arquivos sintéticos |

## Explorar

1. Abra `/acesso` ou use “Acessar demonstração” na landing.
2. Selecione Analista Bernhoeft, Operador da fornecedora, Gestor da contratante ou Administrador Bernhoeft.
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
- Administração e auditoria, pareceres e portal da contratante estão disponíveis como demonstração. A fila e a conferência documental estão disponíveis como demonstração.
- Os três módulos futuros continuam apenas como visão de expansão na landing.

O backend expõe rotas de autenticação e operações em `api/docrisk_core/routes/__init__.py`, mas a interface ainda não está integrada à API e parte dos serviços de processamento/regras depende das frentes F2/F3. O formulário de contato continua sem canal comercial fictício e sem envio.

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

## Pareceres e contratante — etapa atual

O perfil GESTOR_CONTR foi incluído em `/acesso` e direciona para `/contratante`. O portal demonstra somente o Contrato Alfa e as versões aprovadas/publicadas da competência selecionada. Uma navegação interna em `/painel` com essa perspectiva apresenta um redirecionamento orientado ao portal, sem montar suas telas internas. Isso é organização de demonstração, não autenticação ou autorização de produção.

`lib/reports.ts` contém seis versões internas com os quatro estados oficiais. A série PAR-001 possui versão 1 substituída, versão 2 publicada e versão 3 em rascunho. O rascunho não substitui a versão publicada. A versão antiga não é reconstruída com dados atuais: o detalhe preserva a referência histórica e aponta para a versão publicada.

`lib/published-reports.ts` contém somente dois retratos sintéticos de consulta da contratante, com campos explícitos e sem dependência dos módulos internos. O portal e seus componentes de conteúdo não importam análises financeiras, documentos internos ou dados dos rascunhos. Apenas os identificadores publicados têm páginas estáticas no portal. Não há links para documentos internos, valores financeiros, texto de OCR ou notas internas no conteúdo de consulta. Referências de documento/lote/página/versão aparecem como texto.

Os pareceres incluem contratante, fornecedora, contrato, competência, regra, versão, aprovação demonstrativa, escopo, limitações, resumo e itens por trabalhador. Totais incluem bloqueados, revisões e aguardando documentos. Dados insuficientes fazem parte dos avaliados, mas não são tratados como sem divergência.

A preparação do encaminhamento exige três conferências e observação interna. Uma prévia de publicação só pode ser preparada no exemplo EM_REVISAO. Nenhuma ação altera o status, publica, cria versão ou registra auditoria. A publicação real deve ser implementada na API com autorização do analista, snapshot imutável e nova versão para correções posteriores.

Verificação: build e TypeScript; integridade das versões, referências documentais e denominadores; exclusão de rascunhos, campos financeiros e texto de OCR do retrato de consulta; conferência desktop da listagem interna, rascunho, preparação de encaminhamento, troca de perspectiva e consulta da versão 2 após preparar a versão 3. Visualização móvel ainda não verificada.


## Administração e auditoria — etapa demonstrativa

O perfil `ADMIN_BH` foi incluído em `/acesso` e encaminha para `/administracao`, com layout independente do painel trabalhista e do portal da contratante. A perspectiva administrativa não monta as telas operacionais. A navegação por perfil é apenas uma experiência de demonstração: não autentica, não autoriza e não protege dados reais.

`lib/audit.ts` fornece eventos **inteiramente sintéticos** com os campos compatíveis com a estrutura de `GET /api/audit`: `id`, `user_id`, `org_id`, `acao`, `alvo`, `resultado` e `instante`. O painel oferece indicadores derivados desses registros, pesquisa por ação, alvo, organização ou usuário, filtros por ação/resultado/organização e detalhes somente de leitura. Não existem atualização em tempo real, registro de eventos, exportação oficial, gestão de usuários, permissões editáveis, conteúdo de documentos, OCR ou valores financeiros nesta tela.

A API da frente F1 disponibiliza `GET /api/audit` para `ADMIN_BH`, mas **o frontend não chama a API**; substituir os eventos sintéticos pela resposta autenticada é uma etapa futura de integração. Os dados demonstrativos não comprovam auditoria real, integridade ou retenção dos logs. Recomenda-se verificar o comportamento móvel e a integração ponta a ponta antes de considerar a tela pronta para produção.
