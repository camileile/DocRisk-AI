# D4-08 — Backup, reconciliação e restauração (F17/F18)

| Campo | Valor |
|---|---|
| Prioridade | P1 |
| Branch | `feat/d4-08-backup-recovery` (parte de `main` em `e8e5e0f`) |
| Dependência | D2-06 (persistência/retensão — Dev2): **nenhuma política de retenção existe hoje** |
| Arquivos | `api/scripts/backup.py`, `api/tests/test_d4_08_backup.py`, este documento |

## Análise inicial

| Item | Situação real |
|---|---|
| Banco | SQLite WAL em `DATA_DIR/docrisk.sqlite` |
| Originais | `DATA_DIR/uploads/lote-NNNNNN.ext`, hash em `batches.sha256` |
| Derivados | `DATA_DIR/pages/lote-NNNNNN/pNNNN.png`, hash em `pages.sha256`; texto/análises/FTS/cache no banco |
| Relação banco ↔ storage | **caminhos absolutos** em `batches.arquivo` e `pages.image_path`; rotas exigem que estejam dentro do `DATA_DIR` atual |
| Backup/retenção existentes | nenhum |

Copiar a pasta com a API ativa **não** é consistente (WAL + arquivos gravados durante a cópia).

## Procedimento (`api/scripts/backup.py`)

1. `backup` — snapshot online pela API de backup do SQLite; copia só os arquivos que o snapshot
   referencia, com SHA-256 e conferência contra os hashes do banco; `manifest.json` com contagens,
   problemas e duração. Arquivos posteriores ao snapshot ficam de fora (seriam órfãos).
2. `verify` — hash do banco, `PRAGMA integrity_check`, hash de cada arquivo.
3. `restore` — só de backup verificado; recusa `DATA_DIR` com API ativa (trava D4-04, quando presente)
   e banco existente sem `--force` (o atual é **renomeado**, nunca apagado); **remapeia os caminhos**.
4. `reconcile [--repair]` — originais ausentes/corrompidos, páginas ausentes/corrompidas, lotes
   `CONCLUIDO` com páginas não `OK`, órfãos. `--repair` re-renderiza páginas do original e só grava
   se o hash for idêntico ao registrado; original perdido é **relatado como irrecuperável**, não inventado.

```bash
cd api
python scripts/backup.py backup --data-dir data --out ../backups
python scripts/backup.py verify ../backups/docrisk-AAAAMMDD-HHMMSS
python scripts/backup.py restore ../backups/docrisk-AAAAMMDD-HHMMSS --data-dir data-restaurado
python scripts/backup.py reconcile --data-dir data --repair
```

Retenção proposta (sem implementação automática): 7 diários + 4 semanais, fora da máquina da API,
com `verify` após cada cópia. Backups contêm documentos — mesmo nível de proteção do `DATA_DIR`.

## Cenários (pytest, diretórios temporários) — 11 passed

| # | Cenário obrigatório | Teste | Estado antes → falha → depois |
|---|---|---|---|
| 1 | Perda de arquivo derivado | B01 | 3 páginas apagadas → detectadas → re-renderizadas com **hash idêntico** |
| 1b | Perda do original | B01b | original + página apagados → relatados irrecuperáveis |
| 2/3 | Interrupção/crash durante processamento | B03 | falha na 4ª página → `FALHA_PROCESSAMENTO` → reprocessar 2× → `CONCLUIDO`, 8 páginas distintas, 6 documentos |
| 4 | Banco reiniciado | B04 | dois ciclos de lifespan → estado idêntico |
| 5 | Storage indisponível | B05 | página ausente no backup → registrada em `problemas` (não silenciosa) |
| 6 | Estado inconsistente | B06 | lote `CONCLUIDO` com página `PENDENTE` → detectado |
| 7 | Restauração | B07, B07b–d | estado (lotes, documentos, pendências, análises) idêntico; imagem e original servidos pela API no novo dir; backup com escrita concorrente consistente; backup corrompido recusado; sem `--force` não sobrescreve |
| 8 | Recuperação sem duplicidade | B08 | restaurar e reprocessar não cria documentos |

Tempos medidos: backup do lote sintético (8 páginas) **0,07 s**, restauração **0,025 s**.
CLI sobre o banco do ensaio D4-03 (2 lotes, 17 páginas): backup 0,15 s, verify ok, restore 0,05 s,
reconcile sem pendências. Perdas observadas: nenhuma além dos cenários de original apagado (por desenho).

Suíte completa: 248 passed, 1 skipped.

## Limitações

- Sem backup incremental nem agendamento; volume medido só em escala sintética pequena.
- A checagem de API ativa depende do `runtime.py` do D4-04; sem ele, recusa apenas pelo banco existente.
- `ai_cache`, FTS e auditoria vão no snapshot; não há criptografia do backup (decisão para o piloto, D4-06).

## Status: PARCIAL

Backup/restauração reproduzíveis, consistência e recuperação ensaiadas com tempos. Pendentes:
política de retenção aprovada (D2-06), agendamento e teste em volume de piloto.

## Reconciliação Codex — 2026-11-06
Base a1f6109; backup backup/d4-08-20261106 (8583c00); rebase sem conflitos.
pytest api/tests -q: 381 aprovados, 1 ignorado em 125,39s, incluindo 11 testes
 de backup, hashes, integridade, restauração e remapeamento usando schema atual.
Windows/Python 3.13.14, banco temporário sintético, TextLayer offline.
compileall e diff --check aprovados. Schema atual inclui tabelas Clerk, copiadas
pelo snapshot SQLite integral, sem alterar contratos de autenticação.
Status: PARCIAL. Validação local aprovada; ensaio de recuperação em infraestrutura
privada e proteção operacional integrada com D4-04 continuam pendentes.

Base final f085df4 (novo schema de proveniência/cache): 398 aprovados, 1 ignorado, 176,04s, Pillow12.3. Inclui os 11 testes de backup/integridade/restauração. Status PARCIAL; ensaio privado e integração operacional de proteção continuam pendentes.
