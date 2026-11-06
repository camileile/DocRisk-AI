/* Estado React do login produtivo, com SDK e API simulados, sem rede externa. */
const assert = require('node:assert/strict');
const React = require('react');
const { create, act } = require('react-test-renderer');
const { environment } = require('./regression-env.cjs');
global.IS_REACT_ACT_ENVIRONMENT = true;
(async () => {
  let path = '/entrar';
  let signedIn = true;
  let signOuts = 0;
  let linksQueries = 0;
  let analystContracts = ['CT-A'];
  const token = async () => signedIn ? 'jwt-test' : null;
  const signOut = async () => { signOuts++; signedIn = false; };
  const env = environment(true, { process: { env: { ...process.env, NEXT_PUBLIC_AUTH_MODE: 'clerk' } } }, {
    '@docrisk/clerk': { useAuth: () => ({ isLoaded:true,isSignedIn:signedIn,sessionId:signedIn?'session-one':null,getToken:token }),useClerk:()=>({signOut}) },
    'next/navigation': { usePathname: () => path },
  });
  const api = env.load('./lib/api.ts');
  const session = env.load('./lib/api-session.ts');
  const provider = env.load('./components/demo-provider.tsx');
  const { ClerkSessionBridge } = env.load('./components/clerk-session.tsx');
  api.api = async resource => {
    if (resource === '/api/auth/links') { linksQueries++; return [
      {id:'link-analyst',nome:'Analista',org_nome:'Auditora',papel:'ANALISTA_BH'},
      {id:'link-supplier',nome:'Operador',org_nome:'Fornecedora',papel:'OPERADOR_FORN'},
    ]; }
    if (resource === '/api/me') return session.captureSession().link === 'link-analyst'
      ? {id:'analyst',nome:'Analista',org_id:'BH',org_tipo:'BERNHOEFT',papel:'ANALISTA_BH'}
      : {id:'supplier',nome:'Operador',org_id:'FORN',org_tipo:'FORNECEDORA',papel:'OPERADOR_FORN'};
    if (resource === '/api/contracts') return session.captureSession().link==='link-analyst'
      ? analystContracts.map(id => ({id})) : [{id:'CT-B'}];
    throw Error('unexpected resource '+resource);
  };
  let value;
  function Probe() { value=provider.useSession();return null; }
  function Root() { return React.createElement(provider.DemoProvider, { identityBridge:React.createElement(ClerkSessionBridge) },React.createElement(Probe)); }
  let renderer;
  await act(async()=>{renderer=create(React.createElement(Root));});
  assert.equal(linksQueries,1,'the identity bridge must survive child/session remounts');
  assert.equal(value.me,null);assert.equal(value.links.length,2);
  await act(async()=>{await value.chooseLink('link-analyst');});
  assert.equal(value.me.id,'analyst');assert.equal(value.contract,'CT-A');
  const previousScope = session.captureSession();
  analystContracts = ['CT-C'];
  await act(async()=>{session.notifyContractsChanged();});
  assert.equal(value.contract,'CT-C');
  assert.equal(value.contracts.length,1);
  assert.equal(value.me.id,'analyst','contract revocation must not log out another authorized contract');
  assert(previousScope.signal.aborted,'responses belonging to the revoked scope must be cancelled');
  const stableVersion = session.getSessionVersion();
  await act(async()=>{session.notifyContractsChanged();});
  assert.equal(session.getSessionVersion(),stableVersion,'a repeated 404 must not create a remount loop');
  analystContracts = [];
  await act(async()=>{session.notifyContractsChanged();});
  assert.equal(value.contract,'');assert.equal(value.contracts.length,0);
  await assert.rejects(value.chooseLink('forged-link'));
  await act(async()=>{await value.chooseLink('link-supplier');});
  assert.equal(value.me.id,'supplier');assert.equal(value.contract,'CT-B');
  assert.equal(linksQueries,1);
  await act(async()=>{value.setContract('CT-FORGED');});
  assert.equal(value.contract,'CT-B');
  path='/painel';
  await act(async()=>{value.enterDemo('ANALISTA_BH');renderer.update(React.createElement(Root));});
  assert.equal(value.isDemo,true);assert.equal(session.captureSession().clerkProvider,null);
  const before=linksQueries;
  await act(async()=>{renderer.update(React.createElement(Root));});
  assert.equal(linksQueries,before,'entering demo must not reconnect operational identity');
  path='/entrar';
  await act(async()=>{renderer.update(React.createElement(Root));});
  assert.equal(value.isDemo,false);assert.equal(value.links.length,2);
  await act(async()=>{await value.chooseLink('link-analyst');});
  await act(async()=>{session.invalidateSession();});
  assert.equal(value.me,null);assert.equal(value.links.length,0);assert.equal(value.contract,'');
  assert.equal(signOuts,1);assert(value.error.includes('sessão'));
  await act(async()=>renderer.unmount());
  console.log('PASS: SDK bridge stable, authorized bindings, demo isolation and revoked session clears context');
})().catch(error=>{console.error(error);process.exitCode=1;});
