# Nota de revisão obrigatória — Dev1 / Dev2 — D4-09, etapa 3

Base consultada: origin/main 1148e76. Proposta original d370717 permanece intacta. O diff de worker.py entre d370717 e a cópia de revisão da etapa 3 é vazio. Novos commits acrescentam somente testes objetivos; não há migração, fila nova nem alteração de autenticação/contratos.

## Parecer

A reserva de escrita antes das checagens fecha a corrida comprovada de dupla consolidação PDF, mantendo UNIQUE e rollback. NÃO recomendo integrar D4-09 ainda: a revisão ampliada encontrou duas falhas de concorrência/estado, ambas reproduzidas também na main sem a proposta. A validação combinada deve permanecer vermelha até correção revisada ou decisão explícita de escopo/aceite pelos responsáveis; não ocultar testes por xfail, ignore, INSERT OR IGNORE ou captura silenciosa.

## Decisões para Dev1

1. Confirmar a fronteira de consolidação: BEGIN IMMEDIATE antes da checagem de documentos; o bloqueio permanece por segmentar/rotear, gravação e consolidação F3 até commit do chamador. Não cobre o tempo de renderização/provedor no caminho processar_lote. O custo dessas operações locais pode aumentar a contenção; ainda não há benchmark de produção ou carga 10x.
2. Resolver/decidir o tratamento do mesmo AEJ concorrente. O caminho _processar_lote_aej faz sua checagem fora da transação de persistência e não chama consolidar_lote. Com quatro chamadas coordenadas surgem quatro documents e quatro aej_documents para um AEJ de um único vínculo/competência. Os INSERT OR IGNORE existentes em imports/records não tornam os documentos derivados idempotentes. Nenhuma regra/extração AEJ foi alterada nesta etapa.
3. Definir política para trabalho redundante: a proposta não é exclusão do processamento integral do lote. _na_fila deduplica apenas a fila, e o caminho síncrono permite chamadas simultâneas. Não inferir garantia de única chamada Gemini ou único render.
4. Confirmar a recuperação após interrupção: teste com processo real morto depois do primeiro INSERT de documento não confirmado passou. Há rollback, lote PROCESSANDO recuperável, páginas OK preservadas e nova execução conclui. O teste mata somente seu próprio subprocesso, não a API de outros worktrees.

## Decisões para Dev2

1. Confirmar o contrato de propriedade da transação: consolidar_lote não faz commit/rollback do chamador. Conexão já escritora passa, mantém in_transaction e permite rollback integral pelo dono. Não executar BEGIN aninhado.
2. Conexão explicitamente DEFERRED com snapshot antigo reproduz SQLITE_BUSY_SNAPSHOT ao promover leitura para escrita. Teste confirma erro visível e recuperação após rollback e nova tentativa pelo dono. Chamadores futuros precisam reservar a escrita antes de ler ou adotar política de retry na fronteira correta; não confirmar/reabrir silenciosamente transação alheia.
3. Definir a transição monotônica de estado em falha atrasada: uma chamada suspensa na etapa de leitura pode sofrer OSError depois que outra já confirmou CONCLUIDO. _marcar_falha então sobrescreve o status e mantém finished_at preenchido. O teste demonstra seis documentos persistidos, mas lote em FALHA_PROCESSAMENTO. Deve-se decidir entre exclusão por lote, atualização condicional/versão de execução ou outra política acordada, sem introduzir estados unilateralmente.
4. Confirmar a política de timeout/backpressure. db.connect usa timeout de 30 segundos e WAL não permite dois escritores. Testes com busy_timeout=100ms mostram que contenção falha explicitamente, sem espera infinita. No início o lote permanece RECEBIDO e retentativa funciona. Na consolidação, a tentativa de registrar falha pode também disputar o escritor: o lote pode permanecer PROCESSANDO, sem documentos parciais, até recuperação. O teste cobre essa retomada. Não há retry automático da proposta; tempos de várias operações podem acumular. A prova não exclui deadlocks impostos por futuros chamadores que aguardem threads enquanto seguram uma transação.

## Evidências objetivas

api/tests/test_d4_09_transaction_review.py contém sete cenários:

- Conexão já escritora e rollback pelo proprietário: passa.
- Snapshot DEFERRED antigo, erro explícito e rollback/retry: passa.
- Timeout de escritor no início e retentativa: passa.
- Processo morto com INSERT não confirmado e retomada: passa.
- Mesmo AEJ concorrente sem duplicação: FALHA (4 documentos/derivados em vez de 1).
- Falha tardia sem rebaixar sucesso: FALHA (CONCLUIDO é sobrescrito por FALHA_PROCESSAMENTO).
- Timeout durante consolidação e recuperação: passa.

Os dois cenários que falham foram executados também em worktree destacado de main@1148e76 e falharam da mesma forma. São problemas preexistentes, não regressões comprovadas introduzidas pelos seis linhas da proposta. Isso não os torna aceitáveis para uma recomendação ampla de idempotência e consistência do lote.

Os cenários PDF anteriores, 16 uploads, rollback/retentativa e testes de reenvio permanecem na suíte. A validação combinada inclui também papéis administrativos, isolamento multiempresa, Clerk, AEJ sequencial e ambiente runtime. Consultar os resultados finais no relatório da etapa; nenhum verde foi fabricado excluindo os dois casos novos.

## Encaminhamento

Dev1 e Dev2 devem validar a solução PDF e deliberar sobre os dois bloqueios antes de integrar D4-09. Revisão de Dev2 também é necessária para as alterações já existentes de run_in_threadpool nas rotas de upload/reenvio e preservação do UPDATE condicional de reenvio. Não houve envio desta nota por mensagem, abertura de PR nem publicação. D4-10 continua fora do escopo.

Leitura dos caminhos atuais: a trava _trava da fila é liberada antes de processar_lote; render/provedor ficam fora das duas reservas adicionadas, e a consolidação usa a conexão do chamador para F3. Não foi identificado ciclo de locks nesses caminhos inspecionados. Essa análise e os testes de timeout não garantem segurança de futuras chamadas com espera entre threads sob transação aberta.
