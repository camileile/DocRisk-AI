/* Portal contratante: mesma navegação offline e com FastAPI/SQLite reais.
 * Conectado: executar depois de smoke.cjs (publica CT-001/10/2026).
 * DOCRISK_CONNECTED=1 habilita o modo conectado. */
const assert = require("node:assert/strict");
const { chromium } = require("playwright");
const base = process.env.DOCRISK_WEB_URL || "http://127.0.0.1:4173";
const api = process.env.DOCRISK_API_URL || "http://127.0.0.1:8000";
const connected = process.env.DOCRISK_CONNECTED === "1";

async function run() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1365, height: 900 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  try {
    await page.goto(base + "/acesso/");
    await page.getByRole("radio").first().waitFor();
    if (connected) {
      const users = await (await fetch(api + "/api/demo/users")).json();
      const user = users.find((u) => u.role === "GESTOR_CONTR");
      assert(user?.token);
      await page.getByLabel("Token Bearer de teste").fill(user.token);
      await page.getByRole("button", { name: "Conectar API de testes" }).click();
    } else {
      await page.getByRole("radio", { name: /Gestor da contratante/i }).check();
      await page.getByRole("button", { name: "Explorar demonstração" }).click();
    }
    await page.waitForURL((url) => url.pathname === "/contratante/");
    await page.getByText("Cobertura nos pareceres", { exact: true }).waitFor();
    assert.deepEqual((await page.getByLabel("Navegação da contratante").getByRole("link").allTextContents()).map((s) => s.trim()), ["Visão geral", "Pareceres publicados"]);
    await page.getByText("Sem parecer publicado nesta competência", { exact: true }).waitFor();
    const supplier = connected ? "ORG-BETA" : "demo-forn";
    const gamma = connected ? "ORG-GAMA" : "demo-gama";
    const contract = connected ? "CT-001" : "demo-001";
    await page.getByRole("combobox", { name: "Fornecedora", exact: true }).selectOption(supplier);
    await page.getByText("Cobertura nos pareceres", { exact: true }).waitFor();
    await page.getByRole("combobox", { name: "Contrato", exact: true }).selectOption(contract);
    await page.getByText("Cobertura nos pareceres", { exact: true }).waitFor();
    await page.getByRole("combobox", { name: "Competência", exact: true }).selectOption("10/2026");
    await page.getByRole("link", { name: "Consultar parecer", exact: true }).click();
    await page.getByRole("heading", { name: "Por trabalhador", exact: true }).waitFor();
    assert.equal(await page.locator(".report-draft-flag").count(), 0);
    assert.equal(await page.getByRole("img", { name: /página/i }).count(), 0);
    assert.equal(await page.getByRole("button", { name: "Publicar", exact: true }).count(), 0);
    assert.equal(await page.getByRole("combobox", { name: "Parecer", exact: true }).locator("option").count(), 1);
    assert(page.url().includes("contract_id=" + contract) && page.url().includes("parecer_id="));
    // A URL conserva filtros e publicação após recarga / acesso direto.
    await page.reload();
    await page.getByRole("heading", { name: "Por trabalhador", exact: true }).waitFor();
    await page.getByRole("button", { name: "Limpar filtros", exact: true }).click();
    await page.getByRole("heading", { name: "Por trabalhador", exact: true }).waitFor();
    await page.getByRole("combobox", { name: "Fornecedora", exact: true }).selectOption(gamma);
    await page.getByText("Nenhum parecer publicado ainda.", { exact: true }).waitFor();
    assert.equal(await page.locator(".report-document").count(), 0, "Filtro vazio não pode manter parecer anterior");
    await page.getByRole("link", { name: "Visão geral", exact: true }).click();
    await page.getByText("Cobertura nos pareceres", { exact: true }).waitFor();
    if (!connected) {
      await page.getByRole("combobox", { name: "Competência", exact: true }).selectOption("09/2026");
      await page.getByText("Competência exibida: 09/2026", { exact: true }).waitFor();
      const card = page.locator(".stat-card", { hasText: "Taxa de divergências" });
      assert.equal(await card.locator("strong").textContent(), "—");
      await page.getByRole("button", { name: "Limpar filtros", exact: true }).click();
    } else {
      // Erro de rede e recuperação não deixam indicadores antigos na tela.
      await page.route("**/api/client/overview*", (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Falha simulada do portal" }) }));
      await page.reload();
      await page.getByText("Falha simulada do portal", { exact: true }).waitFor();
      assert.equal(await page.getByText("Cobertura nos pareceres", { exact: true }).count(), 0);
      await page.unroute("**/api/client/overview*");
      await page.getByRole("button", { name: /Tentar novamente/ }).click();
      await page.getByText("Cobertura nos pareceres", { exact: true }).waitFor();
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole("button", { name: "Abrir navegação" }).click();
    await page.getByLabel("Navegação da contratante").getByRole("link", { name: "Pareceres publicados", exact: true }).click();
    await page.getByRole("heading", { name: "Por trabalhador", exact: true }).waitFor();
    assert.equal(await page.locator("aside.workspace-sidebar.visible").count(), 0);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    assert.equal(overflow, false, "Tabelas devem rolar no próprio contêiner no celular");
    await page.screenshot({ path: "/tmp/docrisk-contratante-mobile.png", fullPage: true });
    await page.goto(base + "/painel/");
    await page.waitForURL((url) => url.pathname.startsWith("/contratante"));
    await page.getByText("Cobertura nos pareceres", { exact: true }).waitFor();
    assert.deepEqual(errors, []);
    console.log(`Portal contratante: PASSOU (${connected ? "FastAPI + SQLite" : "offline"}, filtros, pareceres, erros, celular)`);
  } finally { await browser.close(); }
}
run().catch((err) => { console.error(err); process.exitCode = 1; });
