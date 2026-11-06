/* Regressões P0 sem backend: transporte, isolamento de sessão e concorrência. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const { create, act } = require('react-test-renderer');
global.IS_REACT_ACT_ENVIRONMENT = true;
const root = path.resolve(__dirname, '..');
function environment(blocked = false) {
  const storage = new Map();
  let fetches = 0;
  const context = vm.createContext({
    console, process, Error, URL, URLSearchParams, Headers, FormData, Blob, AbortController,
    sessionStorage: {
      getItem(key) { if (blocked) throw Error('blocked'); return storage.get(key) ?? null; },
      setItem(key, value) { if (blocked) throw Error('blocked'); storage.set(key, value); },
      removeItem(key) { if (blocked) throw Error('blocked'); storage.delete(key); },
    },
    fetch: async () => { fetches++; throw Error('unexpected operational fetch'); },
    setTimeout, clearTimeout, window: { setTimeout, clearTimeout },
  });
  const cache = new Map();
  function load(file) {
    if (!file.startsWith('.')) return require(file);
    const resolved = path.resolve(root, file);
    if (cache.has(resolved)) return cache.get(resolved).exports;
    const mod = { exports: {} }; cache.set(resolved, mod);
    const source = ts.transpileModule(fs.readFileSync(resolved, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
    const localRequire = (id) => id.startsWith('.') ? load('./' + path.relative(root, path.resolve(path.dirname(resolved), id + (path.extname(id) ? '' : '.ts')))) : require(id);
    vm.runInContext('(function(require,module,exports){' + source + '\n})', context, { filename: resolved })(localRequire, mod, mod.exports);
    return mod.exports;
  }
  return { load, context, storage, fetches: () => fetches };
}
async function transport() {
  for (const blocked of [false, true]) {
    const env = environment(blocked);
    const demo = env.load('./lib/offline-demo.ts');
    const api = env.load('./lib/api.ts');
    const legacy = env.load('./lib/api-client.ts');
    api.setToken('old-operational-token');
    for (const role of demo.DEMO_ROLES) {
      api.setToken(null); demo.setDemoRole(role);
      assert.equal((await api.api('/api/me')).papel, role);
      await assert.rejects(api.api('/api/supplier/batches', { method: 'POST' }));
      await assert.rejects(api.downloadBatchSource(101));
      await assert.rejects(legacy.fetchApiBatch('old-operational-token', 101));
      if (role === 'ADMIN_BH') await assert.rejects(api.api('/api/documents'));
    }
    demo.setDemoRole(null); api.setToken(null);
    await assert.rejects(api.api('/api/me'));
    await assert.rejects(api.apiBlob('/api/pages/1/image'));
    assert.equal(env.fetches(), 0, 'demo/logout must never use operational transport');
    if (!blocked) assert.equal(env.storage.size, 0);
  }
  console.log('PASS: six offline profiles, blocked storage, forbidden writes/files and logout: zero network calls');
}
async function hooks() {
  const env = environment();
  const api = env.load('./lib/api.ts');
  const pending = [];
  api.api = (resource, init) => new Promise((resolve, reject) => pending.push({ resource, init, resolve, reject }));
  const { useApi } = env.load('./lib/use-api.ts');
  let result;
  function Probe({ resource, poll = false }) {
    result = useApi(resource, poll ? { pollMs: 5, shouldPoll: (data) => data.status === 'PROCESSANDO' } : {});
    return null;
  }
  let renderer;
  await act(async () => { renderer = create(React.createElement(Probe, { resource: '/old' })); });
  const old = pending.shift();
  await act(async () => { renderer.update(React.createElement(Probe, { resource: '/new' })); });
  assert(old.init.signal.aborted);
  const latest = pending.shift();
  await act(async () => latest.resolve({ name: 'new' }));
  await act(async () => old.resolve({ name: 'old' }));
  assert.equal(result.data.name, 'new');
  await act(async () => { renderer.update(React.createElement(Probe, { resource: null })); });
  assert.equal(result.data, null); assert.equal(result.error, null); assert.equal(result.loading, false);
  await act(async () => { renderer.update(React.createElement(Probe, { resource: '/batch', poll: true })); });
  await act(async () => pending.shift().resolve({ status: 'PROCESSANDO' }));
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 15)); });
  await act(async () => pending.shift().reject(Error('temporary outage')));
  assert.equal(result.error, 'temporary outage');
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 15)); });
  assert.equal(pending.length, 1, 'poll must resume after transient failure');
  await act(async () => pending.shift().resolve({ status: 'CONCLUIDO' }));
  assert.equal(result.data.status, 'CONCLUIDO'); assert.equal(result.error, null);
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 15)); });
  assert.equal(pending.length, 0, 'terminal status must stop polling');
  await act(async () => { renderer.unmount(); });
  console.log('PASS: stale responses discarded, empty paths cleared, transient polling recovered, terminal status stopped');
}
(async () => { await transport(); await hooks(); })().catch(error => { console.error(error); process.exitCode = 1; });
