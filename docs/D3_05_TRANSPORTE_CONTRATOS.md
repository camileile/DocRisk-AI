# D3-05 — transporte e contratos compartilhados

O frontend passa a usar um único ponto de rede (`web/lib/api-transport.ts`) para JSON, imagens, originais e multipart. `api.ts` mantém os nomes públicos usados pelas telas e intercepta a demo antes de qualquer rede. Os tipos estão em `api-contracts.ts`; `api-upload.ts` mantém validação de arquivo e recibo, sem transporte próprio. Todos os consumidores foram migrados antes de remover `api-client.ts`, inclusive o teste P0.

## Contrato do cliente

- `ApiError` contém `status` (zero quando não há resposta HTTP), `kind` e `retryable`. Rede, timeout e HTTP 5xx permitem nova consulta; permissão, sessão, cancelamento e resposta inválida interrompem o polling automático. Mutações nunca são reenviadas automaticamente.
- Leituras e operações comuns têm timeout de 15 s. Upload, reenvio e reprocessamento síncrono recebem 120 s. O limite e o vínculo de sessão cobrem a leitura do corpo, não apenas os cabeçalhos.
- `AbortSignal` do consumidor é propagado; trocar/reiniciar/sair invalida e cancela a geração anterior, inclusive ao reutilizar o mesmo token. Respostas tardias são descartadas mesmo se o transporte não respeitar o cancelamento.
- O token é obtido da sessão atual e não entra em URL. Operações F1 vinculadas a um token anterior são recusadas. URLs de API aceitam HTTPS ou HTTP local; somente caminhos `/api/` válidos são enviados. Redirecionamentos são recusados.
- Cabeçalhos de erro usam mensagens controladas; corpos HTML, detalhes de validação internos e stack traces não são exibidos. FormData deixa o navegador definir o boundary.
- Cancelar ou perder a confirmação de uma mutação não desfaz o processamento no backend. A mensagem orienta consultar o resultado antes de repetir.
- A sessão permanece demonstrativa, com fallback em memória quando sessionStorage é bloqueado. Não foi implementado login produtivo, revogação global ou novo vínculo empresarial (D3-07).

## Evidências e limites

- `cd web && npm run test:transport`: status HTTP, rede, JSON inválido, multipart/recibo, limites 15 s/120 s, corpo tardio, cancelamento, troca de sessão e originais tardios; com/sem storage nos casos de sessão.
- `cd web && npm run test:p0`: seis perfis offline sem rede, bloqueio de mutações/originais, caminho nulo, respostas obsoletas, recuperação e término de polling; acrescentada parada por 403 e isolamento da sessão no mesmo recurso.
- TypeScript e build com exportação estática aprovados. A primeira tentativa de build foi interrompida por bloqueio de subprocesso no sandbox; a execução com a configuração de ambiente adequada passou.
- Nenhuma rota/permissão backend foi alterada. Não foram repetidas as suítes completas de browser/API por perfil nem a inspeção móvel/projeção já pendente.

Administrador Bernhoeft continua somente gestão. Identidade e módulos futuros não foram alterados.
