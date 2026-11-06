/* Smoke ponta a ponta: front estático (web/out) + API real (FastAPI, leitor offline).
 * Pré-requisitos: API em DOCRISK_API_URL (padrão http://127.0.0.1:8000) com
 * DOCRISK_DEMO_MODE=1 e AI_PROVIDER=textlayer; front servido em DOCRISK_WEB_URL;
 * lote sintético em api/scripts/lote_demo. Instale Playwright + Chromium fora do CI.
 */
const assert = require("node:assert/strict");
const path = require("node:path");
const { chromium } = require("playwright");

const base = process.env.DOCRISK_WEB_URL || "http://127.0.0.1:4173";
const lote = path.resolve(__dirname, "../../api/scripts/lote_demo");

async function go(page, route) {
  await page.goto(base + route, { waitUntil: "domcontentloaded" });
}

async function login(page, roleLabel, expectedPath) {
  await page.evaluate(() => sessionStorage.clear()).catch(() => {});
  await go(page, "/acesso/");
  const radio = page.getByRole("radio", { name: new RegExp(roleLabel) }).first();
  await radio.waitFor({ timeout: 20000 });
  await radio.check();
  await page.getByRole("button", { name: /^Entrar/ }).click();
  await page.waitForURL((url) => url.pathname.startsWith(expectedPath), { timeout: 20000 });
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1365, height: 900 } });
  const runtimeErrors = [];
  page.on("pageerror", (error) => runtimeErrors.push(error.message));
  try {
    console.log("[1/7] Institucional e bloqueio sem sessão");
    await go(page, "/");
    await page.getByRole("heading", { name: /Documentos complexos/ }).waitFor();
    await go(page, "/painel/");
    await page.getByText("Entre com um perfil para continuar.").waitFor();

    console.log("[2/7] Fornecedora envia o lote sintético e acompanha o processamento");
    await login(page, "Operador da fornecedora", "/painel");
    assert.equal(await page.getByRole("link", { name: "Fila de revisão", exact: true }).count(), 0);
    assert.equal(await page.getByRole("link", { name: "Pareceres", exact: true }).count(), 0);
    await page.getByRole("link", { name: "Enviar lote", exact: true }).first().click();
    await page.getByLabel("Selecionar arquivo para envio real").setInputFiles(path.join(lote, "lote_demo.pdf"));
    await page.getByRole("checkbox", { name: /Confirmo que o arquivo é/ }).check();
    await page.getByRole("button", { name: "Enviar arquivo ao backend" }).click();
    await page.getByText(/Processamento documental concluído/).waitFor({ timeout: 60000 });
    await page.getByRole("link", { name: "Consultar histórico de lotes" }).click();
    await page.getByRole("link", { name: /Abrir/ }).first().click();
    await page.getByText("14 documento(s) separados").waitFor({ timeout: 60000 });

    console.log("[3/7] Pendência ilegível do T002 e reenvio corrigido");
    await go(page, "/painel/pendencias/");
    const card = page.locator(".issue-card", { hasText: "Página ilegível" });
    await card.waitFor();
    await card.locator('input[type="file"]').setInputFiles(path.join(lote, "reenvio_holerite_T002.pdf"));
    await card.getByRole("button", { name: /Reenviar/ }).click();
    await page.getByText(/Reenvio da pendência #\d+ recebido/).waitFor();

    console.log("[4/7] Analista: conciliação, revisão humana e busca");
    await login(page, "Analista Bernhoeft", "/painel");
    await go(page, "/painel/conciliacoes/");
    await page.getByText(/diferença de 4 h a conferir/).waitFor({ timeout: 30000 });
    await page.locator(".analysis-card", { hasText: "Trabalhador T002" }).locator(".status-badge", { hasText: "Sem divergência" }).waitFor({ timeout: 30000 });
    await go(page, "/painel/revisao/");
    await page.getByRole("link", { name: /Conferir/ }).first().click();
    await page.getByRole("combobox", { name: /^Tipo/ }).selectOption("OUTRO");
    await page.getByRole("button", { name: /Aprovar classificação/ }).click();
    await page.getByText("Fila vazia.").waitFor();
    await go(page, "/painel/documentos/");
    await page.getByRole("searchbox").fill("T001");
    await page.getByRole("button", { name: "Buscar" }).click();
    await page.locator(".search-results mark").first().waitFor();

    console.log("[5/7] Analista publica o parecer");
    await go(page, "/painel/pareceres/");
    await page.getByRole("button", { name: /Criar rascunho/ }).click();
    await page.getByText("PRÉVIA DO RASCUNHO").waitFor();
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Publicar" }).click();
    await page.getByText(/Parecer publicado/).waitFor();

    console.log("[6/7] Contratante vê somente o publicado");
    await login(page, "Gestor da contratante", "/contratante");
    await page.getByText("Com divergência a verificar").waitFor();
    assert.equal(await page.getByText("PRÉVIA DO RASCUNHO").count(), 0);
    await go(page, "/painel/");
    await page.waitForURL((url) => url.pathname.startsWith("/contratante"), { timeout: 20000 });

    console.log("[7/7] Administrador consulta a auditoria; navegação no celular");
    await login(page, "Administrador Bernhoeft", "/administracao");
    await page.getByText("Parecer publicado").first().waitFor();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole("button", { name: "Abrir navegação" }).click();
    await page.locator("aside.workspace-sidebar.visible").waitFor({ state: "visible" });
    await page.getByRole("button", { name: "Fechar navegação" }).first().click();
    assert.equal(await page.locator("aside.workspace-sidebar.visible").count(), 0);

    assert.equal(runtimeErrors.length, 0, "Erros JavaScript na navegação: " + runtimeErrors.join(" | "));
    console.log("Frontend smoke: PASSOU");
  } finally {
    await browser.close();
  }
}

run().catch((error) => {
  console.error("Frontend smoke: FALHOU\n", error);
  process.exitCode = 1;
});
