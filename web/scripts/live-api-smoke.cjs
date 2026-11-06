/* Fluxo real: navegador Next estático + API FastAPI local + SQLite efêmero.
 * O servidor do CI deve usar DOCRISK_DEMO_MODE=1, AI_PROVIDER=textlayer e
 * ser acessível SOMENTE em 127.0.0.1:8000. Nunca imprime tokens demo.
 */
const assert = require("node:assert/strict");
const { chromium } = require("playwright");

const site = "http://localhost:3000";
const api = "http://127.0.0.1:8000";

async function run() {
  const result = await fetch(api + "/api/demo/users");
  assert.equal(result.status, 200, "API demo de CI indisponível");
  const users = await result.json();
  const analyst = users.find((u) => u.id === "u-analista");
  const supplier = users.find((u) => u.id === "u-oper-beta");
  assert(analyst?.token && supplier?.token, "Tokens efêmeros demo ausentes no banco do CI");

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 850 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));

  async function enter(token) {
    await page.goto(site + "/acesso/", { waitUntil: "domcontentloaded" });
    await page.getByLabel("Token Bearer de teste").fill(token);
    await page.getByRole("button", { name: "Conectar API de testes" }).click();
    await page.waitForURL((url) => url.pathname.startsWith("/painel"), { timeout: 30000 });
  }

  try {
    console.log("[live 1/3] Identidade e contratos do SQLite via FastAPI");
    await enter(analyst.token);
    await page.getByText("Acesso confirmado como Analista Bernhoeft (demo)").waitFor();
    const select = page.getByRole("combobox", { name: "Contrato" });
    assert.equal(await select.locator("option").count(), 2);
    await page.getByText("integracao-f1-sintetico.pdf").waitFor();

    console.log("[live 2/3] Consulta lote/documentos processados pela F2");
    await page.getByRole("link", { name: "Lotes enviados", exact: true }).click();
    await page.getByText("integracao-f1-sintetico.pdf").waitFor();
    await page.getByRole("button", { name: "Ver documentos" }).first().click();
    await page.getByText(/Documento #\d+/).first().waitFor();
    assert.equal(await page.getByText("LOTE-009").count(), 0);

    console.log("[live 3/3] Fornecedora vê apenas seu contrato real na API");
    await enter(supplier.token);
    await page.getByText("Acesso confirmado como Operador Beta (demo)").waitFor();
    assert.equal(await page.getByRole("combobox", { name: "Contrato" }).locator("option").count(), 1);
    await page.getByRole("link", { name: "Lotes enviados", exact: true }).click();
    await page.getByText("integracao-f1-sintetico.pdf").waitFor();
    assert.equal(await page.getByRole("link", { name: "Pareceres", exact: true }).count(), 0);
    assert.equal(errors.length, 0, "Falhas JS no navegador: " + errors.join(" | "));
    console.log("Smoke F1 real: PASSOU (FastAPI + SQLite + TextLayer + frontend)");
  } finally {
    await browser.close();
  }
}
run().catch((error) => {
  console.error("Smoke F1 real: FALHOU", error);
  process.exitCode = 1;
});
