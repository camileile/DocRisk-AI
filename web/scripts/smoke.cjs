/* Smoke tests against the statically exported DocRisk AI frontend.
 * Run after npm run build and serve web/out at http://127.0.0.1:4173.
 * Install Playwright + Chromium when using outside of CI.
 */
const assert = require("node:assert/strict");
const { chromium } = require("playwright");

const base = process.env.DOCRISK_WEB_URL || "http://127.0.0.1:4173";

async function navigate(page, path) {
  await page.goto(base + path, { waitUntil: "domcontentloaded" });
  await page.locator("body").waitFor({ state: "visible" });
}

async function selectProfile(page, name, expectedPath) {
  await navigate(page, "/acesso/");
  const radio = page.getByRole("radio", { name });
  await radio.waitFor();
  await radio.check();
  await page.getByRole("button", { name: /Explorar demonstração/ }).click();
  await page.waitForURL((url) => url.pathname.startsWith(expectedPath), { timeout: 20000 });
  assert(page.url().includes(expectedPath), "Rota inesperada após selecionar " + name);
}

async function clickNavigation(page, label, expected) {
  await page.getByRole("link", { name: label, exact: true }).click();
  await page.waitForURL((url) => url.pathname.startsWith(expected), { timeout: 20000 });
  assert(page.url().includes(expected), "Falhou ao navegar para " + expected);
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1365, height: 900 } });
  const runtimeErrors = [];
  page.on("pageerror", (error) => runtimeErrors.push(error.message));
  try {
    console.log("[1/6] Institucional e contato");
    await navigate(page, "/");
    await page.locator("body").getByText("DocRisk", { exact: false }).first().waitFor();
    await navigate(page, "/contato/");
    await page.locator("body").waitFor();

    console.log("[2/6] Perfil analista e módulos operacionais");
    await selectProfile(page, "Analista Bernhoeft", "/painel");
    for (const [label, path] of [
      ["Lotes enviados", "/painel/lotes/"],
      ["Documentos", "/painel/documentos/"],
      ["Fila de revisão", "/painel/revisao/"],
      ["Conciliações", "/painel/conciliacoes/"],
      ["Pareceres", "/painel/pareceres/"],
      ["Pendências", "/painel/pendencias/"],
    ]) {
      await clickNavigation(page, label, path);
    }

    console.log("[3/6] Perfil fornecedora e limites da navegação");
    await selectProfile(page, "Operador da fornecedora", "/painel");
    await clickNavigation(page, "Prévia de envio", "/painel/envio/");
    assert.equal(await page.getByRole("link", { name: "Fila de revisão", exact: true }).count(), 0);
    assert.equal(await page.getByRole("link", { name: "Conciliações", exact: true }).count(), 0);

    console.log("[4/6] Portal da contratante e conteúdo publicado");
    await selectProfile(page, "Gestor da contratante", "/contratante");
    await page.getByRole("heading", { name: /Pareceres prontos para consulta/ }).waitFor();
    await page.getByRole("link", { name: /Consultar/ }).first().click();
    await page.waitForURL((url) => url.pathname.startsWith("/contratante/") && url.pathname !== "/contratante/");
    await page.getByText("Parecer de acompanhamento documental").waitFor();

    console.log("[5/6] Administrador, filtros e detalhe do evento");
    await selectProfile(page, "Administrador Bernhoeft", "/administracao");
    await page.getByRole("heading", { name: "Auditoria de ações." }).waitFor();
    await page.getByRole("combobox", { name: "Resultado" }).selectOption("NEGADO");
    await page.getByText("2 de 12 eventos").waitFor();
    const details = page.getByRole("button", { name: "Detalhes", exact: true });
    assert.equal(await details.count(), 2);
    await details.first().click();
    await page.locator("#admin-event-title").waitFor();
    await page.getByRole("button", { name: "Fechar detalhes" }).click();
    await page.getByRole("button", { name: "Limpar filtros" }).click();
    await page.getByText("12 de 12 eventos").waitFor();
    await page.getByRole("textbox", { name: "Pesquisar eventos de auditoria" }).fill("DOC-010");
    await page.getByText("1 de 12 eventos").waitFor();

    console.log("[6/6] Navegação administrativa no celular");
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
