const {spawn}=require('node:child_process');const fs=require('node:fs');const path=require('node:path');
const root=process.cwd();const py=path.join(root,'.venv-main/Scripts/python.exe');
const jobs=[['01','auth'],['02','demo'],['04','runtime'],['03','release'],['09','adversarial'],['07','ops'],['08','backup'],['06','pilot'],['10','reconcile']];
async function one([id,name]){const cwd=path.resolve('../DocRisk-dev4-'+name);const out=fs.openSync(path.join(root,'dev4-evidence/d4-'+id+'-baseline-pytest.txt'),'w');
return await new Promise(resolve=>{const p=spawn(py,['-m','pytest','api/tests','-q'],{cwd,env:{...process.env,PYTHONPATH:path.join(cwd,'api'),AI_PROVIDER:'textlayer'},windowsHide:true,stdio:['ignore',out,out]});p.on('close',code=>{fs.closeSync(out);fs.writeFileSync(path.join(root,'dev4-evidence/d4-'+id+'-baseline-exit.txt'),String(code));console.log(id+': '+code);resolve();});});}
let i=0;async function worker(){while(i<jobs.length){await one(jobs[i++]);}}
Promise.all([worker(),worker(),worker()]).then(()=>console.log('Done'));
