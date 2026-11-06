/* Regressões D3-05: rede única, sessão, erros e leitura de corpos. */
const assert = require('node:assert/strict');
const { environment } = require('./regression-env.cjs');

function connected(overrides = {}, blocked = false) {
  const env = environment(blocked, overrides);
  const api = env.load('./lib/api.ts');
  const uploads = env.load('./lib/api-upload.ts');
  const session = env.load('./lib/api-session.ts');
  api.setToken('test-token');
  return { ...env, ...api, uploads, session };
}
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
function clock() {
  const timers = new Map();
  return {
    timers,
    setTimeout(fn, ms) { const id = {}; timers.set(id, { fn, ms }); return id; },
    clearTimeout(id) { timers.delete(id); },
    fire() { for (const { fn } of [...timers.values()]) fn(); },
  };
}
function error(env, status, kind) {
  return e => e instanceof env.ApiError && e.status === status && e.kind === kind;
}

async function httpAndBodies() {
  const calls = [];
  const env = connected({ fetch: async (url, init) => {
    calls.push({ url, init });
    return new Response('{"ok":true}', { status: 200 });
  } });
  assert.deepEqual(JSON.parse(JSON.stringify(await env.api('/api/me'))), { ok: true });
  await env.api('/api/review', { method: 'POST', body: '{"campo":1}', headers: { Authorization: 'wrong' } });
  assert.equal(calls[1].init.headers.get('Authorization'), 'Bearer test-token');
  assert.equal(calls[1].init.headers.get('Content-Type'), 'application/json');
  assert.equal(calls[0].init.cache, 'no-store');
  assert.equal(calls[0].init.redirect, 'error');
  assert.equal(calls[0].url, 'http://127.0.0.1:8000/api/me');
  for (const invalid of ['https://example.com/api/me', '//example.com/api/me', '/api/../me', '/api/./me', '/api/x#fragment', '/api/x\\secret'])
    await assert.rejects(env.api(invalid), error(env, 0, 'validation'));
  assert.equal(calls.length, 2, 'invalid paths must not reach fetch');
  const raw = new Blob(['image']);
  env.context.fetch = async () => new Response(raw);
  assert.equal(await (await env.apiBlob('/api/pages/1/image')).text(), 'image');
  for (const status of [401, 403, 404, 409, 413, 422, 500, 503]) {
    env.context.fetch = async () => new Response('<html>internal-secret</html>', { status });
    for (const action of [() => env.api('/api/me'), () => env.apiBlob('/api/pages/1/image'), () => env.downloadBatchSource(1)])
      await assert.rejects(action(), e => error(env, status, 'http')(e) && !e.message.includes('internal-secret') && e.retryable === (status >= 500));
  }
  // Mensagem `detail` do backend: exibida quando é texto simples; o resto cai na mensagem controlada.
  const json = (body, status) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  env.context.fetch = async () => json({ detail: 'Somente rascunhos podem ser publicados' }, 409);
  await assert.rejects(env.api('/api/reports/1/publish', { method: 'POST' }),
    e => error(env, 409, 'http')(e) && e.message === 'Somente rascunhos podem ser publicados');
  env.context.fetch = async () => json({ detail: 'Falha simulada do portal' }, 503);
  await assert.rejects(env.api('/api/client/overview'), e => e.message === 'Falha simulada do portal' && e.retryable);
  for (const unsafe of ['<b>internal-secret</b>', 'Traceback (most recent call last): internal-secret',
    'linha 1\ninternal-secret', 'x'.repeat(301), [{ loc: ['body'], msg: 'internal-secret' }]]) {
    env.context.fetch = async () => json({ detail: unsafe }, 422);
    await assert.rejects(env.api('/api/me'), e => error(env, 422, 'http')(e) &&
      !e.message.includes('internal-secret') && !e.message.includes('xxxx'));
  }
  env.context.fetch = async () => new Response('not json');
  await assert.rejects(env.api('/api/me'), error(env, 200, 'invalid_response'));
  env.context.fetch = async () => { throw new TypeError('network down'); };
  for (const action of [() => env.api('/api/me'), () => env.apiBlob('/api/pages/1/image'), () => env.downloadBatchSource(1)])
    await assert.rejects(action(), e => error(env, 0, 'network')(e) && e.retryable);
  console.log('PASS: JSON/blob/originals share HTTP/network errors, headers and path validation');
}

async function uploadsAndTimeouts() {
  const time = clock();
  let calls = 0;
  let init;
  const env = connected({ ...time, fetch: async (_url, options) => {
    calls++; init = options;
    return new Response('{"batch_id":9,"status":"RECEBIDO"}');
  } });
  const file = new File(['synthetic'], 'synthetic.pdf');
  assert.equal((await env.uploads.uploadApiBatch('test-token', 'CT-001', file)).batch_id, 9);
  assert(init.body instanceof FormData);
  assert.equal(init.body.get('contract_id'), 'CT-001');
  assert.equal(init.headers.get('Content-Type'), null);
  assert.equal(time.timers.size, 0, 'successful request clears timers');
  await assert.rejects(env.uploads.uploadApiBatch('old-token', 'CT-001', file), error(env, 401, 'session'));
  await assert.rejects(env.uploads.uploadApiBatch('test-token', 'CT-001', new File(['x'], 'bad.exe')), error(env, 0, 'validation'));
  assert.equal(calls, 1);
  env.context.fetch = async () => { calls++; return new Response('{"batch_id":0}'); };
  await assert.rejects(env.uploads.uploadApiBatch('test-token', 'CT-001', file), e => error(env, 0, 'invalid_response')(e) && /lotes/.test(e.message));
  env.context.fetch = (_url, options) => {
    calls++;
    return new Promise((_yes, no) => options.signal.addEventListener('abort', () => no(new Error('aborted')), { once: true }));
  };
  const before = calls;
  const pending = env.uploads.uploadApiBatch('test-token', 'CT-001', file);
  const rejection = assert.rejects(pending, e => error(env, 0, 'timeout')(e) && /antes de reenviar/.test(e.message));
  assert.equal([...time.timers.values()][0].ms, 120000);
  time.fire(); await rejection;
  assert.equal(calls, before + 1, 'mutations must not retry automatically');
  assert.equal(time.timers.size, 0);
  const read = env.api('/api/me');
  const readRejected = assert.rejects(read, e => error(env, 0, 'timeout')(e) && e.retryable);
  assert.equal([...time.timers.values()][0].ms, 15000);
  time.fire(); await readRejected;
  // O timeout cobre o corpo, inclusive quando o fetch já entregou os cabeçalhos.
  const body = deferred();
  env.context.fetch = async () => ({ ok: true, status: 200, json: () => body.promise });
  const reading = env.api('/api/me');
  const readingRejected = assert.rejects(reading, error(env, 0, 'timeout'));
  await Promise.resolve(); time.fire(); body.resolve({ late: true }); await readingRejected;
  assert.equal(time.timers.size, 0);
  console.log('PASS: multipart, upload receipt, 120s/15s timeouts, late bodies and no automatic resend');
}

async function cancellationAndSession() {
  for (const blocked of [false, true]) {
    let init;
    const next = deferred();
    const env = connected({ fetch: (_url, options) => { init = options; return next.promise; } }, blocked);
    const pending = env.api('/api/me');
    const rejected = assert.rejects(pending, error(env, 0, 'session'));
    env.setToken(null); env.setToken('test-token');
    assert(init.signal.aborted, 'logout/login with same token aborts previous request');
    next.resolve(new Response('{"old":true}')); await rejected;
    const aborter = new AbortController();
    aborter.abort();
    await assert.rejects(env.api('/api/me', { signal: aborter.signal }), error(env, 0, 'cancelled'));
    const body = deferred();
    env.context.fetch = async (_url, options) => {
      init = options; return { ok: true, status: 200, blob: () => body.promise };
    };
    const controller = new AbortController();
    const cancelled = env.apiBlob('/api/pages/1/image', { signal: controller.signal });
    const cancelledRejected = assert.rejects(cancelled, error(env, 0, 'cancelled'));
    await Promise.resolve(); controller.abort(); body.resolve(new Blob(['late'])); await cancelledRejected;
    const late = deferred();
    env.context.fetch = async (_url, options) => { init = options; return late.promise; };
    const download = env.downloadBatchSource(9);
    const downloadRejected = assert.rejects(download, error(env, 0, 'session'));
    env.session.setDemoRole('ANALISTA_BH');
    assert(init.signal.aborted);
    late.resolve(new Response('file')); await downloadRejected;
  }
  console.log('PASS: caller abort, session replacement and stale files discarded with/without storage');
}
async function clerkSessions() {
  let bearer = 'jwt-first';
  const calls = [];
  const env = connected({ fetch: async (_url, init) => { calls.push(init); return new Response('{"ok":true}'); } });
  env.session.configureClerkSession(async () => bearer, 'session-id');
  env.session.selectClerkLink('link-authorized');
  assert.equal(env.storage.has('docrisk.token'), false, 'Clerk credentials must not persist in sessionStorage');
  await env.api('/api/me');
  bearer = 'jwt-refreshed';
  await env.api('/api/me');
  assert.equal(calls[0].headers.get('Authorization'), 'Bearer jwt-first');
  assert.equal(calls[1].headers.get('Authorization'), 'Bearer jwt-refreshed');
  assert.equal(calls[1].headers.get('X-DocRisk-Link'), 'link-authorized');
  const obsolete = env.getToken();
  env.session.selectClerkLink('link-other');
  await assert.rejects(env.api('/api/me', { expectedToken: obsolete }), error(env, 401, 'session'));
  let invalidated = false;
  const unsubscribe = env.session.onSessionInvalidated(() => { invalidated = true; });
  env.context.fetch = async () => new Response('{}', { status: 403, headers: { 'X-DocRisk-Link-Invalid': '1' } });
  await assert.rejects(env.api('/api/me'), e => e.status === 403);
  assert(invalidated); assert.equal(env.getToken(), null); unsubscribe();
  const late = deferred();
  env.session.configureClerkSession(() => late.promise, 'another-session');
  const request = env.api('/api/me');
  const rejected = assert.rejects(request, error(env, 0, 'session'));
  env.session.clearClerkSession();
  late.resolve('jwt-obsolete'); await rejected;
  assert.equal(calls.length, 2, 'old token provider must not trigger a request after logout');
  console.log('PASS: Clerk renewal, binding headers, revoked context, no stored JWT and late identity discarded');
}
(async () => { await httpAndBodies(); await uploadsAndTimeouts(); await cancellationAndSession(); await clerkSessions(); })()
  .catch(e => { console.error(e); process.exitCode = 1; });
