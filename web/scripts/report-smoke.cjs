/* D3-08: somente backend demonstrativo com dados sintéticos, Analista + Contratante. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require('playwright');
const site=process.env.DOCRISK_WEB_URL||'http://127.0.0.1:4173';
const api=process.env.DOCRISK_API_URL||'http://127.0.0.1:8000';
const webApi=process.env.DOCRISK_WEB_API_URL||'http://127.0.0.1:8000';
(async()=>{
 const users=await(await fetch(api+'/api/demo/users')).json();
 const analyst=users.find(user=>user.id==='u-analista');
 const client=users.find(user=>user.id==='u-gestor-alfa');
 const headers={Authorization:'Bearer '+analyst.token,'Content-Type':'application/json'};
 const browser=await chromium.launch({headless:true,executablePath:process.env.DOCRISK_CHROMIUM_PATH||undefined,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1365,height:1000},acceptDownloads:true});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 if(api!==webApi) await page.route(webApi+'/**',route=>route.continue({url:api+route.request().url().slice(webApi.length)}));
 async function login(token,prefix){
  await page.goto(site+'/operacao/');
  await page.getByLabel('Token Bearer de teste').fill(token);
  await page.getByRole('button',{name:'Conectar API de testes'}).click();
  await page.waitForURL(url=>url.pathname.startsWith(prefix));
 }
 function nextPreview(){return page.waitForResponse(response=>/\/api\/reports\/\d+\/preview$/.test(response.url())&&response.status()===200).then(response=>response.json());}
 async function download(label){
  const promise=page.waitForEvent('download');await page.getByRole('button',{name:label,exact:true}).click();
  const file=await promise;const bytes=fs.readFileSync(await file.path());assert.equal(bytes.subarray(0,4).toString(),'%PDF');return file.suggestedFilename();
 }
 try {
  await login(analyst.token,'/painel');
  await page.goto(site+'/painel/pareceres/');
  await page.getByLabel('Observações internas',{exact:true}).fill('NOTA_INTERNA_SINTETICA');
  await page.getByLabel('Recomendações ao cliente',{exact:true}).fill('Conferir os registros sintéticos com a fornecedora.');
  const first=nextPreview();await page.getByRole('button',{name:'Criar rascunho'}).click();const original=await first;
  const article=page.locator('.report-document');
  await article.getByText('Responsável pela conferência',{exact:true}).waitFor();
  assert(!(await article.textContent()).includes('NOTA_INTERNA_SINTETICA'));
  const publish=page.getByRole('button',{name:'Publicar',exact:true});assert(await publish.isDisabled());
  assert((await download('PDF da prévia')).includes('-previa.pdf'));
  await page.getByLabel('Recomendações ao cliente (visíveis no parecer)').fill('Conferir e completar a documentação sintética.');
  assert(await publish.isDisabled());
  const edited=nextPreview();await page.getByRole('button',{name:'Atualizar recomendações'}).click();const updated=await edited;
  assert.notEqual(updated.conteudo_sha256,original.conteudo_sha256);
  // Outra alteração torna a prévia da tela obsoleta: a publicação deve ser recusada.
  const change=await fetch(`${api}/api/reports/${updated.id}`,{method:'PATCH',headers,body:JSON.stringify({conteudo_sha256:updated.conteudo_sha256,recomendacoes:'Orientação pública após conferência concorrente.'})});assert.equal(change.status,200);
  await page.getByRole('checkbox',{name:/Conferi autoria/}).check();await publish.click();
  await page.getByText('Conteúdo alterado desde a prévia; atualize e confira antes de publicar',{exact:false}).waitFor();
  assert(await publish.isDisabled());
  const refreshed=nextPreview();await page.getByRole('button',{name:'Atualizar prévia',exact:true}).click();const checked=await refreshed;
  await article.getByText('Orientação pública após conferência concorrente.',{exact:true}).waitFor();
  await page.getByRole('checkbox',{name:/Conferi autoria/}).check();
  const publishedResponse=page.waitForResponse(response=>response.url().endsWith(`/api/reports/${checked.id}/publish`)&&response.status()===200);
  await publish.click();const published=await(await publishedResponse).json();
  assert.deepEqual(published.conteudo_json,checked.conteudo_json);
  await page.getByText('Parecer publicado. A contratante já pode consultá-lo.',{exact:true}).waitFor();
  assert(!(await download('Baixar PDF')).includes('-previa'));
  await login(client.token,'/contratante');await page.goto(site+'/contratante/pareceres/');
  await article.getByText('Orientação pública após conferência concorrente.',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Publicar',exact:true}).count(),0);
  assert.equal(await page.getByLabel('Observações internas',{exact:true}).count(),0);
  await download('Baixar PDF');
  await page.setViewportSize({width:390,height:844});
  assert(await article.isVisible());
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),'corporate report must fit mobile viewport');
  assert.deepEqual(errors,[]);
  console.log('PASS: preview PDF, public recommendations, stale publish blocked, exact publication and contractor PDF; mobile viewport');
 } catch(error) {
  if(process.env.DOCRISK_REPORT_DEBUG_DIR) {
   fs.writeFileSync(process.env.DOCRISK_REPORT_DEBUG_DIR+'/report-debug.txt',await page.locator('body').innerText());
   await page.screenshot({path:process.env.DOCRISK_REPORT_DEBUG_DIR+'/report-debug.png'});
  }
  throw error;
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
