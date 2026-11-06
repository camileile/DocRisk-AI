# D4-09 — Diagnóstico causal e proposta validada — 06/11/2026

## Escopo e referências

Investigação em codex/d4-09-concurrency-investigation, cópia isolada da D4-09, atualizada para origin/main@1148e76 (PR #49). As branches originais e seus backups não foram movidos. A reprodução adicional usa worktree destacado da main exata, DocRisk-dev4-race-baseline. Nenhum push, PR, merge ou deploy.

## Causa raiz comprovada

Não é colisão do gerador de IDs. pages.id é INTEGER PRIMARY KEY AUTOINCREMENT (schema.sql); _registrar_paginas faz INSERT OR IGNORE e UNIQUE(batch_id, ordem) mantém uma página por posição. consolidar_lote lê esses mesmos IDs e os associa aos segmentos por ordem. doc_pages.page_id é UNIQUE intencionalmente: cada página deve pertencer a um documento.

A corrida está entre a checagem SELECT 1 FROM documents WHERE batch_id = ? LIMIT 1 e os INSERTs de documents/doc_pages. db.tx() só gerencia commit/rollback: no modo legado usado pelo sqlite3 desta aplicação, SELECT não inicia a transação implícita. Quatro conexões podem ler simultaneamente a ausência de documentos. O primeiro INSERT reserva a escrita; os outros aguardam e depois continuam com a decisão antiga, sem repetir a checagem. Criam outros IDs de documento e tentam vincular os mesmos IDs de página, violando UNIQUE(doc_pages.page_id).

O rollback desfaz a consolidação perdedora, mas o handler externo chama _marcar_falha e pode sobrescrever CONCLUIDO do vencedor com FALHA_PROCESSAMENTO. A reprodução na main mostrou páginas existentes e finished_at preenchido junto com FALHA_PROCESSAMENTO e mensagem de erro de consolidação: estado operacional inconsistente.

### Prova controlada

O teste test_d4_09_consolidation_race.py prepara oito páginas OK sem documentos e intercepta apenas a conexão de teste. Quando a checagem de idempotência ocorre fora de uma transação, uma barreira força quatro consultas vazias antes de permitir escrita. Não substitui a consolidação nem o mecanismo de persistência.

- Main exata 1148e76, sem proposta: guard_in_transaction=[False, False, False, False], três IntegrityError de doc_pages.page_id e lote FALHA_PROCESSAMENTO com finished_at já preenchido. Evidência: current-main-proof.txt, executado com --showlocals.
- Cópia antes da proposta: mesma falha (before.txt).
- Com proposta: todas as checagens dentro de transação, quatro chamadas terminam sem exceção, mesmos oito IDs de pages, um vínculo por página, seis documentos, lote CONCLUIDO/erro NULL/finished_at preenchido, foreign_key_check vazio e integrity_check=ok. Nova chamada preserva IDs dos documentos e finished_at.
- Falha sintética de persistência: exceção continua propagada; nenhum documento/vínculo parcial permanece. Retentativa preserva IDs de páginas e conclui corretamente.

A main atual não contém correção equivalente. O mesmo padrão de checagem sem reserva aparece em e8e5e0f; é corrida latente anterior ao PR #47, não defeito comprovadamente introduzido por ele.

## Proteção atual e limites

_na_fila protege apenas deduplicação de itens na fila em memória; o item é retirado desse conjunto antes do processamento. Não é reserva transacional do lote. DOCRISK_SYNC chama processar_lote diretamente. Uma thread de worker por processo limita o caminho normal, mas não torna a função idempotente para chamadas simultâneas nem protege múltiplos processos.

## Proposta mínima (seis linhas em worker.py)

1. Em processar_lote, BEGIN IMMEDIATE antes de consultar o status inicial: leitura e transição para PROCESSANDO passam a compartilhar a reserva de escrita. Evita aplicar decisão de status já obsoleta.
2. Em consolidar_lote, se a conexão ainda não está em transação, BEGIN IMMEDIATE antes da checagem de documentos existentes. O chamador mantém commit/rollback. Quem aguarda a escrita lê o estado já confirmado pelo vencedor e retorna os pares existentes, sem reinserir documentos/vínculos.

Preservados UNIQUE, geração de IDs, relações, estados, respostas HTTP, autorização e regras de segmentação/análise. Não há INSERT OR IGNORE em doc_pages, captura de IntegrityError para retornar sucesso, exclusão corretiva de dados nem lease/fila distribuída. A exceção real de persistência continua falhando e causando rollback.

## Resultados

Windows; Python 3.13.14; Pillow 12.3.0 (faixa da main); dados temporários sintéticos; TextLayer; sem APIs pagas.

- Suíte completa: 434 aprovados, 1 ignorado, 127,59s (full-suite.txt), incluindo reenvio, isolamento multiempresa e 16 uploads concorrentes.
- Antes do teste adicional de rollback: 34 direcionados aprovados; após o teste e a expansão apenas diagnóstica da mensagem: 2 novos testes aprovados em 2,12s (after-proof-final.txt).
- Dez repetições dos dois cenários concorrentes (CC01 + reprodução controlada): 20 aprovações, zero falhas (repeated-race.txt).
- diff --check e compileall aprovados.

## Arquivos e dependências de revisão

- api/docrisk_core/pipeline/worker.py: candidato de seis linhas. Dev1 deve revisar o escopo das transações, duração da consolidação e integração com AEJ/reprocessamento. Não foram alteradas as regras de análise nem o caminho AEJ.
- api/docrisk_core/db/__init__.py: diagnóstico do comportamento de tx/connect; sem mudança. Dev2 deve confirmar a fronteira transacional e o comportamento com conexões fornecidas já em transação. Os chamadores atuais foram inspecionados e cobertos pela suíte; uma transação explícita DEFERRED com snapshot anterior exige avaliação própria.
- api/docrisk_core/db/schema.sql: restrições inspecionadas, sem mudança. UNIQUE(page_id) permanece.
- api/tests/test_d4_09_consolidation_race.py: reprodução controlada e rollback/retentativa.
- api/tests/test_d4_09_adversarial.py: CC01 original e 16 uploads preservados, sem enfraquecer expectativas.

A reserva IMMEDIATE é do escritor SQLite, não apenas do lote: deve ser revisada quanto à contenção. Não fica mantida durante renderização ou chamadas ao provedor; somente nas duas seções transacionais descritas. A proposta impede dupla consolidação no cenário comprovado, mas não é um lease de processamento integral: leituras de IA/renderização podem ser redundantes e cenários de provedores divergentes/falhas concorrentes continuam exigindo desenho específico. Não há teste de carga 10x nem implementação distribuída.

Status D4-09: proposta validada localmente, PARCIAL enquanto aguarda revisão/alinhamento Dev1/Dev2 e integração autorizada. A main sem a proposta continua reproduzindo a falha. Não substituir esse diagnóstico por declaração de tarefa integrada/concluída.
