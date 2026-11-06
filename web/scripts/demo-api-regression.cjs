const assert = require('node:assert/strict');
const { environment } = require('./regression-env.cjs');

(async () => {
  function setup(settings = {}, users = [{ role: 'OPERADOR_FORN', token: 'local-test-token' }]) {
    const calls = [];
    const env = environment(false, {
      process: { env: { NEXT_PUBLIC_DEMO_API_ENABLED: '1', NEXT_PUBLIC_API_URL: 'http://127.0.0.1:8000', ...settings } },
      fetch: async (url, options) => { calls.push({url, options}); return Response.json(users); },
    });
    return { ...env.load('./lib/demo-api.ts'), calls };
  }
  const enabled = setup();
  assert.equal(await enabled.demoApiToken('OPERADOR_FORN'), 'local-test-token');
  assert.equal(enabled.calls[0].url, 'http://127.0.0.1:8000/api/demo/users');
  assert.equal(enabled.calls[0].options.credentials, 'omit');
  assert.equal(enabled.calls[0].options.redirect, 'error');
  await assert.rejects(enabled.demoApiToken('ANALISTA_BH'), /perfil escolhido/);
  for (const settings of [
    { NEXT_PUBLIC_DEMO_API_ENABLED: '' },
    { NEXT_PUBLIC_AUTH_MODE: 'clerk' },
    { NEXT_PUBLIC_API_URL: 'https://api.example.com' },
    { NEXT_PUBLIC_API_URL: 'http://127.0.0.1:8000/path' },
    { NEXT_PUBLIC_API_URL: 'http://secret@localhost:8000' },
  ]) {
    const blocked = setup(settings);
    await assert.rejects(blocked.demoApiToken('OPERADOR_FORN'));
    assert.equal(blocked.calls.length, 0);
  }
  await assert.rejects(setup({}, {}).demoApiToken('OPERADOR_FORN'), /perfis/);
  console.log('PASS: local demo bootstrap, selected role, Clerk isolation and remote API blocked');
})().catch(err => { console.error(err); process.exitCode = 1; });
