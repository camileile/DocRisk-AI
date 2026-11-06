/* D3-06: usar somente com FastAPI demo e documento sintético de muitas páginas. */
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const site = process.env.DOCRISK_WEB_URL || 'http://127.0.0.1:4173';
const api = process.env.DOCRISK_API_URL || 'http://127.0.0.1:8000';
const docId = Number(process.env.DOCRISK_VIEWER_DOC_ID);
if (!Number.isSafeInteger(docId) || docId <= 0) throw Error('Informe DOCRISK_VIEWER_DOC_ID de um documento inteiramente sintético em revisão.');

(async () => {
  const users = await (await fetch(api + '/api/demo/users')).json();
  const analyst = users.find(user => user.id === 'u-analista');
  const headers = { Authorization: 'Bearer ' + analyst.token };
  const doc = await (await fetch(`${api}/api/documents/${docId}?include_page_text=false`, { headers })).json();
  assert(doc.paginas.length >= 50 && doc.status === 'REVISAO_HUMANA');
  assert(doc.paginas_detalhe.every(page => !('texto' in page)));
  const browser = await chromium.launch({ headless: true, executablePath: process.env.DOCRISK_CHROMIUM_PATH || undefined, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [], images = [], texts = [], operational = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (request.url().startsWith(api + '/')) operational.push(request.url());
    if (/\/api\/pages\/\d+\/image$/.test(request.url())) images.push(request.url());
    if (/\/api\/documents\/\d+\/pages\/\d+$/.test(request.url())) texts.push(request.url());
  });
  try {
    await page.goto(site + '/operacao/');
    await page.getByLabel('Token Bearer de teste').fill(analyst.token);
    await page.getByRole('button', { name: 'Conectar API de testes' }).click();
    await page.waitForURL(url => url.pathname.startsWith('/painel'));
    await page.goto(`${site}/painel/revisao/detalhe/?id=${docId}`);
    const viewer = page.getByRole('region', { name: 'Imagem ampliada; use as setas para rolar' });
    await viewer.getByRole('img').waitFor();
    assert.equal(images.length, 1, 'only the selected page image may load');
    assert.equal(texts.length, 1, 'only the selected page text may load');
    await page.getByRole('button', { name: 'Aumentar zoom' }).click();
    assert.equal(await page.getByLabel('Zoom atual').textContent(), '125%');
    await page.getByRole('button', { name: 'Girar página 90 graus' }).click();
    assert.match(await viewer.getByRole('img').getAttribute('style'), /rotate\(90deg\)/);
    await page.getByRole('button', { name: 'Restaurar visualização' }).click();
    assert.equal(images.length, 1, 'zoom/rotation must reuse the image');
    await page.getByRole('combobox', { name: 'Página do documento', exact: true }).selectOption(String(doc.paginas.at(-1).page_id));
    await page.getByRole('status').filter({ hasText: `Página ${doc.paginas.length} de ${doc.paginas.length}` }).waitFor();
    await viewer.getByRole('img').waitFor();
    assert.equal(images.length, 2);
    assert.equal(texts.length, 2);
    const hourInput = page.getByRole('spinbutton', { name: 'Horas extras (h)', exact: true });
    await hourInput.fill('12');
    const save = page.getByRole('button', { name: 'Salvar campos conferidos' });
    assert(await save.isDisabled(), 'page and reason are required');
    await page.getByRole('combobox', { name: 'Página conferida para Horas extras (h)', exact: true }).selectOption(String(doc.paginas[49].page_id));
    await page.getByRole('textbox', { name: 'Justificativa da edição' }).fill('Conferência sintética da página 50.');
    await save.click();
    await page.getByText('Campos corrigidos com justificativa. Confira a classificação antes de aprovar.', { exact: true }).waitFor();
    const saved = await (await fetch(`${api}/api/documents/${docId}?include_page_text=false`, { headers })).json();
    assert.equal(saved.campos.horas_extras_h, 12);
    assert.equal(saved.status, 'REVISAO_HUMANA');
    assert.equal(saved.revisoes_campos[0].justificativa, 'Conferência sintética da página 50.');
    // A fonte abre a página exata sem carregar as demais.
    await page.getByRole('button', { name: 'Lote p. 50', exact: true }).click();
    await page.getByRole('status').filter({ hasText: 'Página 50 de' }).waitFor();
    await viewer.getByRole('img').waitFor();
    // Verificação responsiva do visualizador, sem repetir os seis perfis.
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(100);
    assert(await page.getByRole('combobox', { name: 'Página do documento', exact: true }).isVisible());
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2), 'page must fit the mobile viewport');
    await page.goto(site + '/acesso/');
    await page.getByRole('radio', { name: /Analista Bernhoeft/i }).check();
    await page.getByRole('button', { name: 'Explorar demonstração' }).click();
    await page.waitForURL(url => url.pathname === '/painel/');
    const beforeDemo = operational.length;
    await page.goto(site + '/painel/revisao/detalhe/?id=204');
    await page.getByRole('region', { name: 'Imagem ampliada; use as setas para rolar' }).getByRole('img').waitFor();
    assert(await page.getByRole('button', { name: 'Salvar campos conferidos' }).isDisabled());
    assert.equal(operational.length, beforeDemo, 'offline viewer must not use operational network');
    assert.deepEqual(errors, []);
    console.log(`PASS: ${doc.paginas.length} pages on demand, zoom/rotation, justified edit, history, mobile viewport and offline viewer`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
