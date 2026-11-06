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
- Contratante, administrador, conciliações, fila de revisão e pareceres ficam para as próximas etapas.
- Os três módulos futuros continuam apenas como visão de expansão na landing.

Rotas de backend planejadas estão em `api/docrisk_core/routes/__init__.py`. Autenticação e rotas operacionais ainda precisam ser implementadas antes de integrar dados reais. O formulário de contato continua sem canal comercial fictício e sem envio.

## Verificações desta etapa

Build e TypeScript aprovados. Conferência de desktop no navegador: escolha de ambas as perspectivas, navegação, busca documental, expansão de detalhes, mudança de contrato e orientação de pendência. A seleção de arquivos foi revisada no código; não houve transmissão ou processamento. CSS adaptado para telas estreitas; visualização móvel não verificada neste ambiente.

## Lotes — etapa atual

`lib/batches.ts` contém sete lotes sintéticos com os quatro estados oficiais: RECEBIDO, PROCESSANDO, CONCLUIDO e FALHA_PROCESSAMENTO. Os exemplos incluem PDF, imagem e AEJ. AEJ não tem páginas nem OCR; os estados são retratos fixos, sem atualização em tempo real.

Documentos dos lotes reutilizam `lib/demo.ts`. As pendências exibidas no detalhe são somente aquelas cujo documento de referência pertence ao lote; solicitações sem documento associado continuam no acompanhamento geral. Os links de conferência abrem a biblioteca filtrada por `?lote=...`, com detalhe em `?documento=...`; orientações abrem por `?pendencia=...`. Contrato e competência continuam limitando os resultados.

Na perspectiva da fornecedora, apenas o Contrato Alfa está disponível. Um lote de outro contexto exige selecionar o contexto correspondente antes de exibir os detalhes. Esses comportamentos organizam a demonstração e não substituem autorização no backend. O reprocessamento é apenas explicado; não há botão que finja executar a operação.

Validação desta etapa: build estático e TypeScript; verificação de integridade de vínculos lote/documento/pendência e limites de páginas; conferência desktop da busca, detalhes, navegação documento/pendência, falha técnica e cenário AEJ. Nenhum arquivo real foi enviado. Visualização móvel segue não verificada.
