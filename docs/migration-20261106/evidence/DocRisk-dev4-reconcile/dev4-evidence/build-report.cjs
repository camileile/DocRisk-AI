const fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
const root=process.cwd(),e=path.join(root,'dev4-evidence');
const rows=[
['01','test/d4-01-pr22-integration','22f294c','auth','Não','CONCLUÍDA LOCALMENTE'],
['02','test/d4-02-demo-isolation','185b4ae','demo','Não','CONCLUÍDA LOCALMENTE'],
['03','chore/d4-03-release-readiness','96bb15c','release','Não; adaptação do ensaio','PARCIAL'],
['04','fix/d4-04-local-runtime','98166a2','runtime','api.py e config.py','CONCLUÍDA LOCALMENTE'],
['05','chore/d4-05-dependency-security','dcb749f','security','Não; lock atualizado','PARCIAL'],
['06','feat/d4-06-private-pilot','e043d75','pilot','Não; diagnóstico atualizado','BLOQUEADA'],
['07','feat/d4-07-observability','b3d186d','ops','api.py','PARCIAL'],
['08','feat/d4-08-backup-recovery','8583c00','backup','Não','PARCIAL'],
['09','codex/d4-09-validated-snapshot','1cab173','adversarial','routes/__init__.py','FALHOU'],
['10','feat/d4-10-distributed-processing','5d09bc9','reconcile','Não','NÃO INICIADA'],
];
function git(args,cwd=root){const r=spawnSync('git',args,{cwd,encoding:'utf8'});if(r.status!==0)throw Error(r.stderr||r.stdout);return r.stdout.trim();}
const checks=[];let table='| Tarefa | SHA original | Novo SHA | Conflitos/adaptações | Testes finais | Status |\n|---|---|---|---|---|---|\n';
for(const [id,branch,original,name,conflict,status] of rows){const cwd=path.resolve('../DocRisk-dev4-'+name);const sha=git(['rev-parse','--short',branch]);const log=fs.readFileSync(path.join(e,`d4-${id}-${id==='05'?'final':'baseline'}-pytest.txt`),'utf8');const result=log.trim().split(/\r?\n/).at(-1);const backup=git(['rev-parse','--short',`backup/d4-${id}-20261106`]);if(backup!==original)throw Error('Backup mismatch '+id);git(['merge-base','--is-ancestor','f085df4',branch]);git(['diff','--check','f085df4'],cwd);const py=path.join(root,id==='05'?'.venv-dev4/Scripts/python.exe':'.venv-main/Scripts/python.exe');const c=spawnSync(py,['-m','compileall','-q',path.join(cwd,'api/docrisk_core'),path.join(cwd,'api/scripts')],{encoding:'utf8'});if(c.status!==0)throw Error(c.stderr);checks.push({id,branch,sha,original,backup,cwd,result,status,trackedStatus:git(['status','--porcelain','--untracked-files=no'],cwd)});table+=`| D4-${id} | ${original} | ${sha}${id==='09'?' (cópia); original d591967':''} | ${conflict} | ${result} | ${status} |\n`;}
fs.writeFileSync(path.join(e,'final-snapshot.json'),JSON.stringify(checks,null,2));
const report=`# DocRisk AI — reconciliação Dev4 — 06/11/2026

## Resultado e limites

Nove branches originais reconciliadas independentemente com f085df4 (PR #47). A branch original D4-09 permanece em d591967, baseada em a1f6109, por estar associada à pasta usada simultaneamente por outro trabalho. A pedido explícito do usuário essa pasta ficou intocada após a detecção. A versão final D4-09 está preservada em codex/d4-09-validated-snapshot e é descendente de f085df4. Não mover essa referência para a branch original enquanto a árvore estiver em uso.

Durante a sessão origin/main avançou de 1cbd57f para a1f6109 e depois f085df4. A última rodada usa f085df4 fixo. Nenhum push, PR, merge em main ou deploy foi realizado. A main local não foi atualizada.

${table}

Cada suíte tem 1 ignorado. Os totais de diferentes branches se sobrepõem e não devem ser somados. D4-09 tem uma falha real; não foi ocultada. CI remoto/Linux não executado.

## Auditoria e preservação

Árvore inicial limpa; sem stashes. Dez branches e commits informados encontrados, derivados da base e8e5e0f. Nenhuma das dez estava em worktree no início. As evidências históricas foram lidas de suas referências individuais. Backups exatos: backup/d4-01-20261106 até backup/d4-10-20261106. Todos conferidos contra os SHAs originais no relatório; nenhum sobrescrito. Também preservados os commits auxiliares 758bea0 e 69e2c46 por ancestralidade das branches originais.

Worktrees pré-existentes de revisão não foram modificados. Foram criados worktrees próprios DocRisk-dev4-* para isolamento. A pasta original apresentou alteração concorrente em web/next-env.d.ts e fetch externo, confirmados pelo usuário; a alteração foi preservada. D4-09 foi copiada em worktree próprio para completar investigação sem tocar na referência em uso.

Arquitetura confirmada no código: FastAPI, SQLite WAL, fila queue.Queue e worker em thread por processo, frontend Next com export estático, leitor TextLayer offline e integração Gemini, seis papéis e autorização interna. A base atual incorpora autenticação Clerk, vínculos/convites e controle de seed, além de proveniência/cache de IA no PR #47. Isso substitui partes do diagnóstico antigo; não foi reimplementado o projeto.

## A. Modificações já absorvidas pela main

- PR #22 e PR #26 já integrados (merge de #26: 88960eb). Preservado teste de isolamento, sem reaplicar código antigo da demo.
- CORS atual do Dev2, métodos PUT e cabeçalhos de identidade mantidos.
- Seed condicionado ao modo demo/token e bloqueio de tokens demo fora do modo adequado já presentes. D4-01 adaptou expectativa 403 para 401 na base OIDC; não mudou autenticação.
- Clerk, vínculos, convites e revogação foram incorporados pelo PR #46; D4-06 atualizou diagnóstico/configuração preliminar.
- Proteção condicional de reenvio do Dev2, incluindo 409 e limpeza de lote concorrente, preservada.
- Coerção de booleanos na administração e trabalho bloqueante nas rotas assíncronas ainda exigiam as correções Dev4. Foram mantidas. Não houve descarte automático de commits por suposta equivalência.

## B. Conflitos e adaptações

- D4-04, api/docrisk_core/api.py: mantida validação CORS do Dev2; adicionados validação de runtime e bloqueio de instância. Preservados validate_configuration, roteador de identidade, cabeçalhos Clerk e seed condicionado.
- D4-04, api/docrisk_core/config.py: combinados _num do Dev4 com funções de tarifas e limites Gemini do Dev1; nenhum limite novo removido.
- D4-09, api/docrisk_core/routes/__init__.py: corpo síncrono do reenvio executado em run_in_threadpool, preservando a comparação de estado/histórico do Dev2, erro 409 e limpeza correspondente.
- D4-07, api.py: combinados logs/correlação com inicialização Clerk, métodos HTTP e cabeçalhos de sessão atuais.
- D4-03: preparo do lote integracao-f1-sintetico.pdf via API antes do navegador, como no CI. A falha inicial era ausência dessa pré-condição. O ensaio seguinte na base antiga falhou ao trocar sessão; não se reproduziu nas bases Clerk e final.
- D4-05: lock com hashes regenerado para PyJWT[crypto]; SBOMs regenerados. Pillow 13 preservado.

## C. Testes e ambiente

Windows; Python 3.13.14; Node 22.23.2. Ambiente isolado .venv-main com Pillow 12.3.0 para branches compatíveis com a faixa da main; .venv-dev4 com Pillow 13.0.0 para D4-05. Ambos passaram em pip check. Testes com TextLayer, bancos temporários e dados sintéticos; sem APIs pagas. Clerk foi testado com assinaturas locais/provedor simulado, sem comprovar configuração externa real.

Comandos reproduzíveis, executados no worktree de cada branch:

- Python do ambiente correspondente: -m pytest api/tests -q. Resultados completos na tabela e nos arquivos d4-XX-baseline-pytest.txt (D4-05: d4-05-final-pytest.txt).
- D4-02: npm ci, npm run build e node web/scripts/demo-isolation.cjs com servidor estático local. Resultado 26/26 após Clerk. PR #47 não altera frontend; branch atualizada e suíte backend repetida em f085df4.
- D4-04: python api/scripts/runtime_check.py --json, 11/11 verificações, incluindo CORS, instâncias duplicadas, queda e reinício. Relatório d4-04-final-runtime.json.
- D4-03: node web/scripts/release-rehearsal.cjs --json, 7/7 etapas em 70,8s na base final. Relatório d4-03-final-rehearsal.json.
- D4-09: pytest api/tests/test_d4_09_adversarial.py -k CC02 -q --durations=2: 16 uploads aceitos, 1 teste aprovado, chamada em 3,23s. São requisições concorrentes via TestClient; não substitui carga em infraestrutura privada. A suíte inteira inclui reenvio/isolamento/consistência e falha em CC01.
- D4-08: 11 testes de backup/integridade/restauração incluídos na suíte, usando schema atualizado (inclusive tabelas de identidade/proveniência).
- Frontend do ensaio final: npm run typecheck, test:p0 e test:transport aprovados, inclusive renovação Clerk. Build aprovado. Não existe comando de lint backend/frontend configurado nos scripts/workflows inspecionados; executados diff --check e compileall em todos os worktrees finais.
- D4-05: piptools compile --generate-hashes --extra test --strip-extras --allow-unsafe; pip install --require-hashes; pip-audit --require-hashes --disable-pip; npm ci e npm audit. Lock atualizado sem vulnerabilidades conhecidas; npm audit zero. SBOMs nos respectivos commits.

Scan separado do ambiente da main: 41 registros em 2 pacotes (Pillow 12.3.0 e pip 26.1.2). Há registros duplicados por aliases de advisories; não interpretar como 41 CVEs distintas. O lock D4-05 com Pillow13 foi auditado separadamente sem achados. O apontamento de pip é ferramenta do ambiente, não dependência do lock da aplicação. Detalhes em main-audit.txt e d4-05-final-audit.txt.

Rodadas intermediárias e suas falhas permanecem registradas. A rodada redundante em Pillow13 para branches sem esse requisito foi interrompida; os resultados finais da tabela usam Pillow12.3, exceto D4-05. Tempos ocorreram com várias suítes locais simultâneas e não são benchmarks de produção.

## D. Regressões e bloqueios reais

D4-09/CC01: quatro chamadas concorrentes a processar_lote para o mesmo lote resultam em IntegrityError: UNIQUE constraint failed: doc_pages.page_id. Observado na suíte final (419 aprovados, 1 falha, 1 ignorado) e confirmado na execução isolada (27 aprovados antes da falha). Na base a1f6109 o teste havia passado; isso localiza a observação, mas não prova a causa exata. A checagem de documentos existentes em consolidar_lote e a inserção em doc_pages precisam de investigação Dev1/Dev2. Não foi alterado processamento nem enfraquecido o teste. Logs: d4-09-baseline-pytest.txt e d4-09-investigation.txt.

parar_worker ainda marca parada antes de inserir None na fila. Permanece risco de sentinela remanescente; investigado por leitura, sem afirmar reprodução determinística nem alterar código Dev1.

A D4-09 original está numa árvore ativa: reconciliar sua referência final depende de liberação dessa árvore. A cópia validada preserva todas as alterações e a regressão encontrada.

## E. Pendências por frente

- Dev1/Dev2: investigar CC01, assegurar consolidação idempotente e repetir testes; avaliar ciclo do worker/sentinela. Nenhum contrato de estados foi alterado.
- Dev1/Dev4: integrar telemetria do PR #47 ao endpoint ops; chamadas/retries/custo ainda aparecem null nesse endpoint.
- Dev2/Dev4: bootstrap/provisionamento real, configuração Clerk externa e validação do piloto. Seed sintético fora da demo já resolvido; não manter esse bloqueio antigo como vigente.
- Dev3/Dev4: manter validação de export Windows/RSC em ambiente equivalente ao de publicação; workaround de normalização de RSC permanece no orquestrador do ensaio.
- Responsáveis pelo projeto: decisão de licença do projeto e avaliação PyMuPDF; nenhum LICENSE encontrado na base. Não há conclusão jurídica neste relatório.
- Dev4: ensaio no host privado, backup/restauração no ambiente final, vídeo de contingência e escolha do SHA de release após correção concorrente.
- D4-10: lease/heartbeat/limites distribuídos/escala10x não implementados. A presença do diagnóstico ou da telemetria não conclui a tarefa.

## F. Publicação

Nenhuma publicação realizada. D4-01, D4-02 e D4-04 prontas para revisão local e, mediante autorização, push/PR, sem garantir CI remoto. D4-05 tem validação técnica local aprovada e deve ser revisada com prioridade pelos achados de Pillow; licenças e CI pendentes. D4-03, D4-06, D4-07, D4-08 e D4-10 só podem ser apresentadas como entregas parciais/diagnóstico conforme a tabela, não tarefas concluídas. D4-09 não está pronta: regressão CC01 e referência original ocupada. Nenhuma aprovação de release decorre dos testes isolados das demais branches.

## G. Apresentação

Demo isolada 26/26. Ensaio final conectado 7/7 em 70,8s, incluindo queda/reinício e navegador após reinício. São dados sintéticos e leitor offline, não evidência de Gemini em produção. Sem vídeo e sem SHA congelado. A regressão de consolidação concorrente impede classificar a release como pronta. Cada branch é irmã de f085df4; nenhuma suíte foi executada numa branch que combine todas as dez entregas, pois isso exigiria uma integração separada.

## Evidências e referências

As evidências individuais foram atualizadas e commitadas em docs/dev4 de cada branch, preservando os relatos históricos e acrescentando as revalidações. final-snapshot.json registra os SHAs finais, diretórios e estado dos arquivos rastreados. Os logs e este relatório estão em ${e.replaceAll('\\','/')}. Worktrees e ambientes foram mantidos para revisão; nada foi removido. Aguardar autorização antes de publicar branches ou abrir PRs.
`;
fs.writeFileSync(path.join(e,'RELATORIO_RECONCILIACAO_DEV4.md'),report);
console.log(table);console.log('Tracked changes: '+checks.filter(c=>c.trackedStatus).map(c=>c.id+': '+c.trackedStatus).join('; '));
