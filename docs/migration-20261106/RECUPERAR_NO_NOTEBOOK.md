# Continuar DocRisk AI no notebook

Backup remoto verificado em 06/11/2026. Repositório: https://github.com/camileile/DocRisk-AI. Isto preserva desenvolvimento, não aprova integração/release. A main consultada está em 753c9945e1ef7d7b160f3034982cd78864b222a4 (PR50); as quatro frentes em revisão e a combinação histórica usam 1148e76. Nenhum rebase/merge foi feito nesta migração.

## 1. Clonar e atualizar referências

No PowerShell, em uma pasta de sua escolha:

```powershell
git clone https://github.com/camileile/DocRisk-AI.git
cd DocRisk-AI
git fetch origin
git branch -r
```

Os caminhos do notebook podem ser diferentes. Worktrees, ambientes virtuais, arquivos ignorados e dados privados não são recriados automaticamente pelo clone.

## 2. Continuar a D4-09 na cópia de revisão

```powershell
git switch --create codex/notebook-d4-09 --track origin/codex/d4-09-stage3-review
git rev-parse HEAD
```

Esperado: 5a568d6052924a387ce6f5bfba763106f9c3ae24. Essa versão contém os dois testes vermelhos e a proposta PDF. A original d370717 está preservada separadamente; não substitua uma pela outra e não trate o backup como aprovação.

| Referência recuperável | SHA preservado |
|---|---|
| codex/d4-01-review-1148 | 47c3ff998e5d92cbc624662478247a4c09e0eb34 |
| codex/d4-02-review-1148 | b81b4a0652445ac8ea35ca9a9a429b1fc40b615d |
| codex/d4-04-review-1148 | 33d17d71742bcc5ab2b03682303b91f047afff6c |
| codex/d4-09-stage3-review | 5a568d6052924a387ce6f5bfba763106f9c3ae24 |
| codex/d4-09-concurrency-investigation | d37071743e45b9bf5a341a2bd2119f1c43af03fc |
| codex/dev4-stage3-integration | cf9b09cefb0f9cf5d120012dd7a7f330c99569c8 |

## 3. Recriar worktrees independentes

Execute a partir do clone. Os novos nomes locais são distintos dos backups:

```powershell
git worktree add -b codex/notebook-d4-01 ../DocRisk-d4-01 origin/codex/d4-01-review-1148
git worktree add -b codex/notebook-d4-02 ../DocRisk-d4-02 origin/codex/d4-02-review-1148
git worktree add -b codex/notebook-d4-04 ../DocRisk-d4-04 origin/codex/d4-04-review-1148
git worktree add -b codex/notebook-integracao ../DocRisk-integracao origin/codex/dev4-stage3-integration
git worktree add --detach ../DocRisk-proposta-original origin/codex/d4-09-concurrency-investigation
git worktree list
```

A integração deve apontar para cf9b09cefb0f9cf5d120012dd7a7f330c99569c8. As branches são irmãs; não as empilhe nem faça merge nesta recuperação. A main avançou depois da validação histórica: analisar esse avanço é trabalho futuro, não foi embutido no backup.

## 4. Recuperar os relatórios e manifestos

```powershell
git worktree add --detach ../DocRisk-relatorios origin/backup/migration-20261106/dev4-evidence
git worktree add --detach ../DocRisk-logs origin/backup/migration-20261106/dev4-raw-logs
```

No primeiro worktree, abrir:

- docs/migration-20261106/evidence/DocRisk-dev4-adversarial/stage3-evidence/RELATORIO_ETAPA3.md
- docs/migration-20261106/evidence/DocRisk-dev4-adversarial/stage3-evidence/NOTA_REVISAO_DEV1_DEV2.md
- docs/migration-20261106/evidence/DocRisk-dev4-adversarial/stage3-evidence/PR_D4-01.md (e 02/04/09)
- docs/migration-20261106/evidence/DocRisk-dev4-adversarial/stage3-evidence/integration-manifest.json
- docs/migration-20261106/evidence/DocRisk-dev4-adversarial/stage3-evidence/integration-included-commits.txt
- docs/migration-20261106/evidence/DocRisk-dev4-reconcile/dev4-evidence/RELATORIO_RECONCILIACAO_DEV4.md

Os arquivos foram preservados sem editar conteúdo. Links absolutos antigos apontam para a máquina anterior; use os caminhos relativos acima ou o índice remoto INDEX_EVIDENCIAS.md. Scripts auxiliares antigos também podem conter caminhos absolutos históricos: não executá-los cegamente.

## 5. Dependências no notebook

Instalar Git, Python (3.13.14 foi usado localmente; projeto declara >=3.11), Node22 (22.23.2 foi usado) e npm. Os snapshots JSON environment-main/security/original-api registram versões, sem segredos. São evidência histórica, não instrução para misturar ambientes.

Na integração recuperada:

```powershell
cd ../DocRisk-integracao/api
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest tests -q
```

Resultado histórico: 485 aprovados, 2 falhas, 1 ignorado. Dependências novas podem alterar o resultado; registrar versões e investigar diferenças. Os dois testes vermelhos não devem ser removidos/ignorados para obter verde. D4-05 possui lock separado com Pillow13; não misture esse lock com branches que declaram Pillow<13. A migração não atualizou dependências nem corrigiu os avisos existentes.

Frontend:

```powershell
cd ../web
npm ci
npm install --no-save --package-lock=false playwright@1.58.2
npx playwright install chromium
npm run typecheck
npm run build
```

Para verificações futuras de PDF/OCR, conferir também as dependências externas citadas no README (por exemplo, Tesseract apenas se usar esse provedor). Os testes investigados usaram TextLayer, não Gemini.

## 6. Configuração local e segredos

Criar api/.env a partir de .env.example somente se ainda não existir; não sobrescrever configuração pessoal. Para trabalho sintético offline, configurar explicitamente AI_PROVIDER=textlayer, DOCRISK_DEMO_MODE=1, DOCRISK_AUTH_MODE=token, DOCRISK_SYNC conforme o ensaio e CORS_ORIGINS apenas com as origens locais usadas. Escolher DOCRISK_DATA_DIR novo no notebook. NEXT_PUBLIC_API_URL aponta para a API local quando necessário.

Os nomes presentes no .env privado da máquina antiga eram: DOCRISK_DEMO_MODE, DOCRISK_DATA_DIR, AI_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL, GEMINI_RPM, LIMIAR_CONFIANCA, LIMIAR_LEGIBILIDADE, MAX_UPLOAD_MB, MAX_PAGINAS, NEXT_PUBLIC_API_URL. Nenhum valor desse arquivo foi enviado.

Para autenticação operacional, configurar privadamente DOCRISK_AUTH_MODE=clerk, CLERK_ISSUER, CLERK_SECRET_KEY, CLERK_AUTHORIZED_PARTIES, CLERK_INVITE_REDIRECT_URL e CLERK_AUDIENCE quando aplicável, além de NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY no frontend. Conferir modelos e .env.example da branch escolhida. Chaves reais devem vir de gerenciador de segredos ou transferência criptografada, nunca de commit, relatório público ou mensagem aberta. APIs pagas não são necessárias para retomar os testes locais.

## 7. O que precisa de transferência privada

Ainda não está no GitHub:

- C:/Users/Pichau/Documents/GitHub/DocRisk-AI/api/.env
- C:/Users/Pichau/Documents/GitHub/DocRisk-AI/api/data/ (SQLite, uploads, páginas)
- C:/Users/Pichau/Documents/GitHub/DocRisk-reconcile38-data/
- C:/Users/Pichau/Documents/GitHub/DocRisk-review42-data/
- C:/Users/Pichau/Documents/GitHub/DocRisk-review42-seed/
- C:/Users/Pichau/Documents/GitHub/DocRisk-review44-browser-data/
- C:/Users/Pichau/Documents/GitHub/DocRisk-review44-data/
- C:/Users/Pichau/Documents/GitHub/DocRisk-review45-browser-data/

Esses bancos podem conter tokens e arquivos cuja proveniência não foi autorizada para publicação. Se precisar manter esses estados, transferir por mídia/canal criptografado, separadamente do Git. Não copiar somente o arquivo SQLite de uma API ativa: usar backup SQLite consistente e incluir uploads/páginas referenciados, ou encerrar controladamente a instância própria antes de copiar o diretório completo incluindo WAL/SHM, conforme o procedimento do projeto. Não encerrar processos de outras pessoas.

A branch feat/d4-08-backup-recovery preserva api/scripts/backup.py com backup/verify/restore e remapeamento de caminhos; consultar e revisar essa ferramenta antes de restaurar em um diretório NOVO do notebook. O schema e os caminhos absolutos existentes exigem validação. Nenhuma restauração ou modificação de banco foi feita nesta migração.

C:/Users/Pichau/AppData/Local/Temp/docrisk-* e pastas pytest contêm estados temporários de testes. Logs relevantes foram preservados; bancos e arquivos temporários não foram publicados. Normalmente são recriados pelos testes; transferir privadamente apenas se precisar exatamente desses estados. .venv*, node_modules, .next, out, caches e navegadores Playwright devem ser reinstalados/regerados, não são trabalho de código perdido. Não retire a máquina antiga de uso antes de decidir e concluir a transferência privada necessária.

## 8. Verificar igualdade e retomar os bloqueios

```powershell
git cat-file -t d37071743e45b9bf5a341a2bd2119f1c43af03fc
git cat-file -t cf9b09cefb0f9cf5d120012dd7a7f330c99569c8
git ls-remote origin refs/heads/codex/d4-09-stage3-review refs/heads/codex/dev4-stage3-integration
git status --short
```

Os tipos devem ser commit, e os SHAs precisam coincidir com a tabela. branch-verification.json e fresh-remote-verification.json registram o que foi conferido num repositório vazio baixado do GitHub; evidence-file-manifest.json permite comparar SHA-256 dos arquivos recuperados.

No worktree D4-09 ou integração:

```powershell
cd api
.\.venv\Scripts\python.exe -m pytest tests/test_d4_09_transaction_review.py -k "same_aej or late_failure" -q
.\.venv\Scripts\python.exe -m pytest tests/test_d4_09_adversarial.py tests/test_d4_09_consolidation_race.py -q
```

No primeiro comando, resultado esperado: duas falhas reais (AEJ cria quatro derivados; falha tardia rebaixa CONCLUIDO). Ler a nota Dev1/Dev2 e os logs antes de modificar código. A proposta PDF BEGIN IMMEDIATE está em d370717 e permanece preservada; não substituí-la sem necessidade demonstrada. Nenhum contrato de AEJ/estados deve ser alterado sem alinhamento. No segundo comando os cenários anteriores de concorrência/rollback e 16 uploads estavam aprovados.

## 9. Outras referências e pendências

As dez branches backup/d4-XX-20261106 foram enviadas, assim como todas as branches locais não-main. backup/migration-20261106/history/* preserva 67 commits anteriormente sem referência, incluindo snapshots de stash antigos. Não havia stash ativo. Não aplicar esses snapshots automaticamente; inspecionar git show/git diff em cópia isolada.

Nenhuma revisão de D4-01/02/04 foi aprovada remotamente por este backup. D4-09 continua bloqueada pelos dois testes; Dev1/Dev2, CI remoto e decisão de integração permanecem pendentes. D4-03 preserva o ensaio7/7, mas vídeo, release candidate e congelamento continuam pendentes. D4-10 não foi implementada. Push de backup não equivale a merge ou deploy.
