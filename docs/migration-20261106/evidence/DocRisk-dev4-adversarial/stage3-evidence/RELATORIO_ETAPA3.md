# DocRisk AI / Dev4 — Etapa 3 — revisão e validação combinada

## Resultado executivo

A revisão e a preparação local foram executadas. Não recomendo integrar D4-09 nem preparar a release candidate neste estado. A combinação tem 2 failed, 485 passed, 1 skipped, 2 warnings in 135.57s (0:02:15). Os dois testes que falham revelam defeitos preexistentes também reproduzidos na main: AEJ concorrente duplicado e falha tardia rebaixando sucesso. Nenhum teste foi ignorado/xfail para fabricar aprovação. O teste ignorado da suíte já existia.

A correção original d370717 foi preservada byte a byte em worker.py. Novos testes estão em uma cópia de revisão separada. Não houve alteração estrutural de banco, autenticação, contratos ou fila. Nenhum push, PR aberto, merge em main ou deploy. Os cherry-picks foram somente aplicação local no worktree temporário expressamente autorizado.

## 1. Main e estado das fontes

Fetch efetuado nesta etapa: origin/main permanece 1148e76d4d550846604ab3ddb2f1602beb901982; não avançou desde a validação 1148e76 do PR #49. Nenhuma adaptação de código dessas fontes foi necessária.

| Entrega | Fonte preparada | SHA | Estado |
|---|---|---|---|
| D4-01 | codex/d4-01-review-1148 | 47c3ff9 | Preparada para revisão; sem publicação |
| D4-02 | codex/d4-02-review-1148 | b81b4a0 | Preparada para revisão; sem publicação |
| D4-04 | codex/d4-04-review-1148 | 33d17d7 | Preparada para revisão; sem publicação |
| D4-09 | codex/d4-09-stage3-review | 5a568d6 | BLOQUEADA: duas falhas novas de revisão |


A fonte original D4-09 codex/d4-09-concurrency-investigation continua em d37071743e45b9bf5a341a2bd2119f1c43af03fc. A fonte preparada para revisão ampliada é codex/d4-09-stage3-review, que acrescenta os testes ed5f1a4 e 5a568d6. As três fontes de revisão anteriores (47c3ff9, b81b4a0, 33d17d7) e todas as branches originais/backups foram preservadas. Checagem: All protected references unchanged.

Validações individuais anteriores continuam associadas aos mesmos SHAs e à mesma base: D4-01 420 aprovados/1 ignorado; D4-02 399/1 e demo26/26; D4-04 424/1 e runtime11/11. Não foram repetidas sem mudança de código/base: a rodada nova exigida é a combinação dessas fontes. D4-09 ampliada nesta etapa: 2 failed, 439 passed, 1 skipped, 2 warnings in 129.20s (0:02:09).

## 2. Revisão D4-09 e parecer Dev1/Dev2

[Nota específica de revisão](C:/Users/Pichau/Documents/GitHub/DocRisk-dev4-adversarial/stage3-evidence/NOTA_REVISAO_DEV1_DEV2.md).

- Escopo/duração: reserva inicial termina antes de render/provedor. Reserva de consolidação começa antes da leitura de idempotência e dura até commit do chamador, incluindo segmentação, gravação e F3. Continua sendo o escritor global SQLite; não foi medido throughput de produção/carga10x.
- Contenção/timeout: SQLITE_BUSY é explícito. Testes com 100ms cobrem contenção inicial e na consolidação, ausência de documentos parciais e retentativa. O padrão real é 30s por conexão; o tratamento de erro pode disputar escrita novamente e ampliar o tempo total. Não há retry silencioso.
- Deadlock: os cenários testados terminam por sucesso ou timeout, sem espera infinita. Isso não prova ausência universal de deadlocks impostos por futuros chamadores que aguardem outra thread enquanto seguram escrita.
- Transação existente: conexão já escritora mantém propriedade e rollback integral. Snapshot DEFERRED antigo causa SQLITE_BUSY_SNAPSHOT, exigindo rollback e retry do dono, sem commit/reabertura automática de transação alheia.
- Idempotência PDF: testes antigos e reprodução coordenada continuam passando; IDs e vínculos preservados, sem INSERT OR IGNORE em doc_pages nem captura de IntegrityError para sucesso.
- Interrupção: processo real foi morto após INSERT não confirmado; rollback, integridade, páginas preservadas e retomada passaram.
- Reenvio/AEJ: testes existentes de reenvio, UPDATE condicional, versões e AEJ sequencial permanecem aprovados. A revisão paralela do mesmo AEJ revelou lacuna específica abaixo.
- Estados finais: uma falha atrasada pode sobrescrever CONCLUIDO; não foi alterada a política de estados sem decisão de Dev2.

### Bloqueio A — AEJ concorrente

Quatro chamadas passam pela checagem de _processar_lote_aej antes de persistir. Produzem 4 documents e 4 aej_documents para um AEJ de um vínculo/competência, em vez de 1. A proteção em consolidar_lote não se aplica a esse caminho. Teste: test_same_aej_concurrently_does_not_duplicate_derived_documents. Reproduzido na main sem o candidato e na combinação; não atribuído à proposta. Dev1 precisa revisar a fronteira de idempotência AEJ com Dev2, preservando regras e schema.

### Bloqueio B — falha tardia rebaixa sucesso

Uma execução é suspensa antes de render/registro; outra conclui o mesmo lote; a primeira recebe OSError controlado. _marcar_falha sobrescreve o status já concluído e deixa finished_at preenchido. Seis documentos válidos permanecem, porém o lote fica em FALHA_PROCESSAMENTO. Teste: test_late_failure_cannot_downgrade_a_successful_concurrent_batch. Reproduzido também na main sem o candidato. Dev2 deve decidir política monotônica/condicional ou identificação de tentativa em conjunto com Dev1. Não foram adicionados estados, leases ou alterações de contrato nesta etapa.

Logs de controle: main-risk-controls.txt (ambos falham na main), aej-main-control.txt (AEJ isolado). A suíte não trata essas falhas como sucesso. D4-09 exige revisão de Dev1/Dev2 antes de integrar, além da decisão sobre correções/escopo dos bloqueios.

## 3. Integração temporária e commits

Worktree: C:/Users/Pichau/Documents/GitHub/DocRisk-dev4-stage3-integration; branch codex/dev4-stage3-integration. Base 1148e76d4d550846604ab3ddb2f1602beb901982; SHA testado cf9b09cefb0f9cf5d120012dd7a7f330c99569c8. Aplicação na ordem D4-01, D4-02, D4-04, D4-09. Foram incluídos 23 commits de fonte por cherry-pick local, sem conflitos de conteúdo ou decisões semânticas de resolução.

[integration-manifest.json](C:/Users/Pichau/Documents/GitHub/DocRisk-dev4-adversarial/stage3-evidence/integration-manifest.json) contém SHA completo das quatro fontes, cada commit original, seu commit aplicado e patch-id estável. Todos os 23 pares foram conferidos. integration-included-commits.txt lista os commits na ordem real. A tentativa local de reaplicar o próprio HEAD gerou operação vazia, encerrada após confirmar igualdade; nenhum commit de fonte foi descartado e o manifesto final confere a aplicação completa.

Entre 4c6a767 (início dos testes frontend/runtime) e o SHA final cf9b09c foram acrescentados apenas dois testes. A igualdade de api/docrisk_core, api/scripts, web, workflows e .env.example foi verificada; os artefatos de aplicação testados são iguais aos do SHA final. A suíte completa foi executada novamente no SHA final, incluindo esses testes.

## 4. Resultados da combinação

| Verificação | Resultado | Evidência |
|---|---|---|
| Suíte completa | 2 failed, 485 passed, 1 skipped, 2 warnings in 135.57s (0:02:15) | combined-final-pytest.txt |
| Novos testes transacionais | 5 passam, 2 falham (bloqueios acima) | transaction-review-final.txt e suíte final |
| Cinco repetições CC01 + CC02 + reprodução PDF | 15 aprovações, zero falhas; CC02 usa16 uploads | combined-concurrency-repeated.txt |
| Demo atual/export | 26/26 sem transporte operacional | combined-isolation.json/txt |
| Runtime com processos reais | 11/11 | combined-runtime.json/txt |
| TypeScript/build estático | aprovados | typecheck.txt / build.txt |
| P0 e transporte/Clerk | aprovados | combined-p0.txt / combined-transport.txt |
| diff --check / compileall | aprovados | verificação local dos worktrees |

Ambiente: Windows, Python3.13.14, Node22.23.2, Pillow12.3 (faixa da main); TextLayer, dados temporários inteiramente sintéticos. Sem API paga. A nova classe de teste usa barreiras/falhas sintéticas somente na instrumentação; o teste de interrupção mata apenas o subprocesso criado para o ensaio. O TestClient concorrente não substitui teste de carga de produção. CI remoto/Linux ainda pendente.

Contratos: suíte inclui papéis/reativação administrativa, status HTTP e rejeição de coerção, isolamento multiempresa, seed/demo, Clerk/OIDC, reenvio condicional, revisão/versões, AEJ e parecer corporativo do PR49. CORS/métodos/cabeçalhos atuais foram preservados. Nenhuma suíte combinada verde foi declarada.

## 5. Quatro textos de PR preparados

- [D4-01](C:/Users/Pichau/Documents/GitHub/DocRisk-dev4-adversarial/stage3-evidence/PR_D4-01.md): Dev2; validação administrativa e papéis.
- [D4-02](C:/Users/Pichau/Documents/GitHub/DocRisk-dev4-adversarial/stage3-evidence/PR_D4-02.md): Dev3/Dev4; isolamento e workflow.
- [D4-04](C:/Users/Pichau/Documents/GitHub/DocRisk-dev4-adversarial/stage3-evidence/PR_D4-04.md): Dev1/Dev2; runtime/configuração/lifecycle.
- [D4-09 — bloqueado](C:/Users/Pichau/Documents/GitHub/DocRisk-dev4-adversarial/stage3-evidence/PR_D4-09.md): Dev1/Dev2 obrigatórios; SQL concorrente, testes adversos e dois riscos comprovados.

Cada arquivo inclui título, descrição/problema, lista exata de arquivos, SHA, evidências, testes, dependências, riscos e revisores. São arquivos locais; nenhum PR remoto ou rascunho remoto foi criado.

## 6. Ordem recomendada e bloqueios

Ordem de revisão/publicação autorizada futura: D4-01, D4-02, D4-04; D4-09 somente após parecer obrigatório e resolução/decisão explícita dos bloqueios, mantendo evidências visíveis. As três primeiras são independentes e podem ser revisadas antes, mas não liberam a release. CI remoto e revalidação da combinação final integrada continuam necessários.

Não recomendo integrar o conjunto completo enquanto os dois testes novos falharem. A proposta PDF de seis linhas continua tecnicamente comprovada em seu escopo, mas não equivale a garantia de exclusão de processamento integral, idempotência AEJ ou monotonicidade de estado sob falhas concorrentes.

## 7. Release e demais tarefas

Ensaio anterior D4-03 7/7 em70,8s preservado, base f085df4/branch fd97fd3; o JSON não foi regravado. Hash registrado na etapa anterior: 87A03E1EFA4A65EAA6B60DE4269F28C106D2CDBB0BAF9D2AAA783B80060198E5. O worktree de combinação é validação temporária, NÃO release candidate. Não houve congelamento/tag do SHA da apresentação. Release candidate só após integração autorizada, correções/revisões e testes do código integrado. Vídeo de contingência permanece pendente.

D4-05, D4-07 e D4-08 continuam PARCIAIS; D4-06 BLOQUEADA; D4-10 NÃO INICIADA para implementação. Nenhuma dessas branches foi alterada. A pasta original e worktrees de outros desenvolvedores não foram modificados. As fontes originais e backups foram conferidos, e os worktrees de código rastreado estão limpos; somente evidências locais novas permanecem fora dos commits no worktree da investigação.
