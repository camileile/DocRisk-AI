const {spawn,spawnSync}=require('node:child_process');
const fs=require('node:fs');const path=require('node:path');
const root=process.cwd();const evidence=path.resolve('../DocRisk-dev4-adversarial/investigation-evidence');
const python=path.resolve('../DocRisk-dev4-reconcile/.venv-dev4/Scripts/python.exe');
const log=fs.openSync(path.join(evidence,'review02-server.txt'),'w');
const server=spawn(python,['-m','http.server','4189','--bind','127.0.0.1','--directory',path.join(root,'web/out')],{stdio:['ignore',log,log],windowsHide:true});
(async()=>{try{for(let i=0;i<50;i++){try{if((await fetch('http://127.0.0.1:4189/')).ok)break;}catch{} await new Promise(r=>setTimeout(r,100));}
const out=fs.openSync(path.join(evidence,'review02-isolation.txt'),'w');
const r=spawnSync(process.execPath,['web/scripts/demo-isolation.cjs'],{env:{...process.env,DOCRISK_WEB_URL:'http://127.0.0.1:4189',DOCRISK_ISOLATION_REPORT:path.join(evidence,'review02-isolation.json')},stdio:['ignore',out,out],timeout:900000,windowsHide:true});process.exitCode=r.status??1;
}finally{server.kill();}})();
