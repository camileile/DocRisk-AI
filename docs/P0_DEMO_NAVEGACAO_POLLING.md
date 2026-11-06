# D3-01 a D3-04 — demonstração, navegação e concorrência

Branch dependente de `fix/revisao-admin-bernhoeft` (PR #25), atualizada com a main. O Administrador Bernhoeft mantém somente gestão; não recebeu acesso documental. Nenhum módulo futuro foi implementado.

| Item | Implementação | Evidência / limite |
| --- | --- | --- |
| D3-01 | `/acesso` contém apenas a seleção dos seis perfis offline. `/operacao` contém o token da API de testes, sem sugerir login produtivo. Site público tem entradas distintas. Barra global mantém DEMO, perfil, limitações, troca, reinício e saída. | Exportação estática e navegação conferidas. O mesmo build continua suportando demo e API local; não há novo build produtivo ou credencial embutida. |
| D3-02 | Perfil e token têm estado em memória quando sessionStorage é bloqueado. Demo intercepta leituras, recusa mutações/originais e impede o transporte legado. Sem sessão, não há fallback para fetch operacional. Trocar, reiniciar e sair desmontam o estado anterior. Respostas tardias da identificação não reabrem sessão encerrada. | Teste dos seis perfis com/sem storage, mutações, originais e saída: zero fetches. Com storage bloqueado, recarregar perde a sessão e exige escolher novamente, sem chamar a API. |
| D3-03 | Analista tem atalhos diretos a Documentos e Conciliações, preservando Fila de Exceções. Contexto da demo permanece visível fora da sidebar; textos de tabelas/evidências ficam maiores. | Caminho no navegador desktop conferido. Regras responsivas mantêm perfil e barra; inspeção em dispositivo móvel e ensaio físico em projeção ainda pendentes. Não equivale à auditoria de acessibilidade D3-09. |
| D3-04 | useApi associa dados ao caminho e à sessão, cancela requisições anteriores e ignora resultados obsoletos, inclusive em reloads concorrentes. Caminho nulo limpa dados/erro. Polling retoma após erro transitório e para ao concluir. Acompanhamento do upload também retenta rede/5xx, com limite existente de 60 consultas. Reprocessar impede clique simultâneo e recarrega o lote. | Testes direcionados de resposta fora de ordem, caminho nulo, falha transitória e estado terminal. Backend de reprocessamento e suas permissões não foram alterados. |

## Validação enxuta

- `cd web && npm run test:p0`: regressões de transporte e hook React, sem backend ou navegador.
- `cd web && npm run build`: compilação, TypeScript e exportação estática.
- Navegador sobre a exportação estática: demo do Analista → Documentos → troca para Admin BH somente gestão → reinício → recarga → saída → rota exclusiva da API.
- Scripts existentes de smoke foram ajustados à nova rota conectada e aos atalhos; não foi repetida a suíte completa de browser/API.
- Não houve merge na main, publicação ou deploy.

A unificação completa de transportes (D3-05), revisão assistida (D3-06), login real (D3-07), parecer corporativo (D3-08), acessibilidade (D3-09) e refinamento comercial/visual (D3-10) continuam fora deste pacote.
