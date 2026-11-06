/* Navegador → FastAPI → SQLite: atribuição, compartilhamento e revogação seletiva.
 * Somente API local de demonstração com dados sintéticos e frontend estático. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const base = process.env.DOCRISK_WEB_URL || 'http://127.0.0.1:4173';
const api = process.env.DOCRISK_API_URL || 'http://127.0.0.1:8000';

async function run() {
  assert(['127.0.0.1', 'localhost'].includes(new URL(api).hostname), 'Use somente API local de testes');
  const usersResponse = await fetch(api + '/api/demo/users');
  assert.equal(usersResponse.status, 200);
  const users = await usersResponse.json();
  const manager = users.find(u => u.id === 'u-gestor-beta');
  const admin = users.find(u => u.id === 'u-admin');
  async function request(resource, token, init = {}) {
    const response = await fetch(api + resource, { ...init,
      headers: { Authorization: 'Bearer ' + token, ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }) } });
    assert(response.ok, `${resource}: HTTP ${response.status}`);
    return response.json();
  }
  const suffix = Date.now();
  const second = await request('/api/admin/contracts', admin.token, { method: 'POST', body: JSON.stringify({
    nome: 'Contrato sintético acesso ' + suffix, contratante_id: 'ORG-ALFA', fornecedora_id: 'ORG-BETA',
  }) });
  const op = await request('/api/supplier/operators', manager.token, { method: 'POST', body: JSON.stringify({ nome: 'Operador Acesso ' + suffix }) });
  const analyst = await request('/api/admin/users', admin.token, { method: 'POST', body: JSON.stringify({
    nome: 'Analista Acesso ' + suffix, org_id: 'ORG-BH', papel: 'ANALISTA_BH',
  }) });
  assert.deepEqual(await request('/api/contracts', op.token_teste), []);
  const form = new FormData();
  form.set('contract_id', 'CT-001');
  form.set('file', new Blob([fs.readFileSync(path.resolve(__dirname, '../../api/scripts/lote_demo/lote_demo.pdf'))], { type: 'application/pdf' }), 'lote-sintetico-acesso.pdf');
  const upload = await request('/api/supplier/batches', manager.token, { method: 'POST', body: form });
  const docs = await request(`/api/batches/${upload.batch_id}/documents`, manager.token);
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  const contexts = [];
  const errors = [];
  async function login(token) {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } }); contexts.push(context);
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + '/operacao/');
    await page.getByLabel('Token Bearer de teste').fill(token);
    await page.getByRole('button', { name: 'Conectar API de testes' }).click();
    await page.waitForURL(url => url.pathname.startsWith('/painel') || url.pathname.startsWith('/administracao'));
    return page;
  }
  try {
    const managerPage = await login(manager.token);
    await managerPage.goto(base + '/painel/operadores/');
    await managerPage.getByRole('button', { name: 'Gerenciar contratos de ' + op.nome, exact: true }).click();
    const panel = managerPage.getByRole('region', { name: 'Atribuição de contratos' });
    for (const cid of ['CT-001', second.id]) {
      const row = panel.getByRole('row').filter({ hasText: cid });
      await row.getByRole('button', { name: 'Atribuir contrato', exact: true }).click();
      await row.getByRole('cell', { name: 'Atribuído', exact: true }).waitFor();
    }
    const adminPage = await login(admin.token);
    await adminPage.goto(base + '/administracao/usuarios/');
    await adminPage.getByRole('button', { name: 'Gerenciar contratos de ' + analyst.nome, exact: true }).click();
    const analystPanel = adminPage.getByRole('region', { name: 'Atribuição de contratos' });
    const analystRow = analystPanel.getByRole('row').filter({ hasText: 'CT-001' });
    await analystRow.getByRole('button', { name: 'Atribuir contrato', exact: true }).click();
    await analystRow.getByRole('cell', { name: 'Atribuído', exact: true }).waitFor();
    assert.deepEqual((await request('/api/contracts', analyst.token_teste)).map(c => c.id), ['CT-001']);
    const operatorPage = await login(op.token_teste);
    await operatorPage.goto(base + `/painel/documentos/detalhe/?id=${docs[0].id}`);
    await operatorPage.getByRole('heading', { name: 'Leitura do documento', exact: true }).waitFor();
    const row = panel.getByRole('row').filter({ hasText: 'CT-001' });
    await row.getByRole('button', { name: 'Revogar contrato', exact: true }).click();
    await row.getByRole('cell', { name: 'Sem acesso', exact: true }).waitFor();
    // Foco atualiza concessões, desmonta conteúdo antigo e mantém outro contrato.
    await operatorPage.evaluate(() => window.dispatchEvent(new Event('focus')));
    await operatorPage.getByRole('alert').filter({ hasText: 'Contrato não encontrado' }).waitFor();
    assert.equal(await operatorPage.getByRole('heading', { name: 'Leitura do documento', exact: true }).count(), 0);
    assert.deepEqual(await operatorPage.getByRole('combobox', { name: 'Contrato', exact: true }).locator('option').evaluateAll(options => options.map(o => o.value)), [second.id]);
    assert.deepEqual((await request('/api/contracts', op.token_teste)).map(c => c.id), [second.id]);
    assert.equal((await fetch(api + `/api/batches/${upload.batch_id}/source`, { headers: { Authorization: 'Bearer ' + op.token_teste } })).status, 404);
    assert((await request(`/api/batches/${upload.batch_id}`, manager.token)).id === upload.batch_id, 'histórico preservado');
    await managerPage.setViewportSize({ width: 390, height: 844 });
    await panel.getByRole('heading', { name: 'Contratos de ' + op.nome }).waitFor();
    assert.deepEqual(errors, []);
    console.log('PASS: gestor atribui/revoga, admin atribui analista, colega lê lote autorizado, revogação limpa tela e preserva outro contrato/histórico; desktop/mobile sem erros JS');
  } finally {
    for (const context of contexts) await context.close();
    await browser.close();
  }
}
run().catch(error => { console.error(error); process.exitCode = 1; });
