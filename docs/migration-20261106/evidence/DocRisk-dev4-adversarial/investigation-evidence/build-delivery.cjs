const fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
function git(args,cwd=process.cwd()){const r=spawnSync('git',args,{cwd,encoding:'utf8'});if(r.status!==0)throw Error(r.stderr||r.stdout);return r.stdout.trim();}
const root=process.cwd(),ev=path.join(root,'investigation-evidence');
const data=[['01','test/d4-01-pr22-integration','codex/d4-01-review-1148','420','Dev2: StatusInput e validação de payload'],['02','test/d4-02-demo-isolation','codex/d4-02-review-1148','399 + isolamento 26/26','Dev3: cobertura da demo; Dev4: workflow'],['04','fix/d4-04-local-runtime','codex/d4-04-review-1148','424 + runtime 11/11','Dev1: configuração/worker; Dev2: lifespan/CORS/identidade']];
let table='| D4 | Original preservada | Cópia de revisão | SHA final da cópia | Validação | Revisão necessária |\n|---|---|---|---|---|---|\n';const snapshot=[];
for(const [id,orig,branch,result,owner] of data){const cwd=path.resolve('../DocRisk-dev4-review'+id);const sha=git(['rev-parse',branch]),old=git(['rev-parse',orig]);git(['merge-base','--is-ancestor','1148e76',branch]);git(['diff','--check','1148e76'],cwd);const sourceDiff=git(['diff','HEAD^','HEAD','--','api','web','.github','.env.example'],cwd);if(sourceDiff)throw Error('Documentation commit changed code');const files=git(['diff','--name-only','1148e76',branch]);snapshot.push({id,original:orig,originalSha:old,branch,sha,sourceTestedSha:git(['rev-parse','HEAD^'],cwd),files,result,trackedStatus:git(['status','--porcelain','--untracked-files=no'],cwd)});table+=`| ${id} | ${orig} (${old.slice(0,7)}) | ${branch} | ${sha.slice(0,7)} | ${result}; 1 ignorado | ${owner} |\n`;}
fs.writeFileSync(path.join(ev,'review-snapshot.json'),JSON.stringify(snapshot,null,2));
const report=`# DocRisk AI — etapa após reconciliação Dev4 — 06/11/2026

## D4-09: entrega principal

Causa raiz e proposta em [D4-09_DIAGNOSTICO_CONCORRENCIA.md](${root.replaceAll('\\','/')}/docs/dev4/D4-09_DIAGNOSTICO_CONCORRENCIA.md).

Branch isolada codex/d4-09-concurrency-investigation, commit d37071743e45b9bf5a341a2bd2119f1c43af03fc, base main 1148e76. O teste foi repetido no commit final: 434 aprovados, 1 ignorado em 119,26s. Dez repetições dos dois cenários concorrentes: 20 aprovações. A reprodução na main sem proposta falha de maneira controlada, com quatro checagens sem transação, três violações de UNIQUE e FALHA_PROCESSAMENTO coexistindo com finished_at.

Não é colisão de pages.id: os IDs são gerados pelo SQLite e as páginas preservam UNIQUE(batch_id,ordem). Duas ou mais consolidações usam a mesma decisão obsoleta de que o lote ainda não tem documentos. A transação implícita só começa no INSERT, tarde demais para proteger a leitura. A proposta reserva a escrita antes das checagens, preserva os IDs e restrições e não captura IntegrityError para simular sucesso. Inclui rollback/retentativa com falha sintética de persistência.

A correção equivalente não está na main consultada. O padrão inseguro existe desde a base antiga e não pode ser atribuído causalmente ao PR #47. É necessária revisão Dev1/Dev2 das fronteiras transacionais e contenção SQLite antes de integração. A proposta não impede todo trabalho redundante de IA/renderização e não implementa processamento distribuído. D4-09 permanece PARCIAL: candidato validado localmente, sem alinhamento/integração nem CI remoto.

Logs: before.txt; current-main-proof.txt; after-proof-final.txt; full-suite-final-sha.txt; repeated-race.txt; tested-sha.txt. Os arquivos estão neste diretório. A prova na main usa uma cópia destacada de 1148e76 e o novo teste; não modifica a referência main.

## D4-01, D4-02 e D4-04: preparação para revisão

${table}

Todos os números acima são aprovações de pytest, com um ignorado por suíte. Cada branch de revisão é cópia independente da original e foi reconciliada com 1148e76 sem conflitos. A main mudou desde a rodada anterior; por isso os testes foram executados novamente. Os SHAs finais incluem um último commit apenas documental: o diff de api/web/workflows/configuração entre esse commit e seu pai é vazio, verificado pelo gerador deste relatório. review-snapshot.json registra o SHA do código testado, SHA final e arquivos do diff.

D4-01: admin_management.py, teste de papéis e documentação. A main ainda aceita coerção nesse StatusInput; a alteração não duplica uma correção já absorvida. Dev2 deve revisar também a rejeição de campos extras. D4-02: somente script de teste, workflow e documentação; nenhuma versão antiga da demo foi reintroduzida. D4-04: runtime/configuração/API/testes/workflow/documentação; preservados Clerk, seed condicionado, métodos e cabeçalhos CORS atuais. Existe sobreposição intencional entre a validação CORS no import e a política operacional do runtime. Isso foi registrado para revisão, sem afirmar ausência absoluta de lógica semelhante nem promover refatoração estrutural.

Nenhuma nova regressão foi observada nessas suítes. Isso não é garantia universal nem validação da combinação das branches; a falha de consolidação permanece na main sem o candidato D4-09. Rascunhos locais de PR: PR_D4-01_RASCUNHO.md, PR_D4-02_RASCUNHO.md e PR_D4-04_RASCUNHO.md. Nenhum foi publicado.

## D4-03: evidência e procedimento

[Pré-congelamento e vídeo](${ev.replaceAll('\\','/')}/D4-03_PRE_CONGELAMENTO_E_VIDEO.md).

Preservado o ensaio histórico 7/7 em 70,8s, base f085df4 / branch fd97fd3. SHA-256 do JSON: 87A03E1EFA4A65EAA6B60DE4269F28C106D2CDBB0BAF9D2AAA783B80060198E5. Ele não valida automaticamente a main 1148e76 nem uma integração das dez branches. Ainda faltam revisão/inclusão autorizada da correção concorrente, CI e ensaio no commit candidato integrado, decisão de SHA final e vídeo efetivamente gravado/reproduzido. O documento contém os pré-requisitos e roteiro de captura, conferência e manifesto. D4-03 continua PARCIAL; nenhum SHA foi congelado e nenhum vídeo foi fabricado/declarado existente.

## Demais tarefas e preservação

D4-05, D4-07 e D4-08 permanecem PARCIAIS; D4-06 BLOQUEADA; D4-10 NÃO INICIADA para implementação. Nenhuma dessas branches foi modificada nesta etapa. Nenhuma alteração estrutural para resolver documentação, nenhum processamento distribuído, nenhuma alteração de contrato público/schema/estados.

A pasta original e as referências originais de Dev4 ficaram preservadas. Foram usadas cópias isoladas e novos commits locais. Não houve push, abertura de PR, merge, deploy, alteração de credenciais ou uso de API paga. Ambiente dos testes: Windows, Python 3.13.14, Pillow12.3, TextLayer offline e dados sintéticos; Clerk com provedor simulado nos testes. Aguardar autorização para qualquer publicação.
`;
fs.writeFileSync(path.join(ev,'ENTREGA_DEV4_ETAPA2.md'),report);console.log(table);
