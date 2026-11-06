/* Navegação de demonstração offline: NÃO inicia FastAPI e NÃO acessa 127.0.0.1:8000.
 * Rodar com a exportação estática servida em 127.0.0.1:4173. */
const assert = require("node:assert/strict");
const { chromium } = require("playwright");

const base = process.env.DOCRISK_WEB_URL || "http://127.0.0.1:4173";
const profiles = [
  ["Administrador Bernhoeft", "/administracao/"],
  ["Analista Bernhoeft", "/painel/"],
  ["Gestor da fornecedora", "/painel/"],
  ["Operador da fornecedora", "/painel/"],
  ["Gestor da contratante", "/contratante/"],
];

async function run() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const runtimeErrors = [];
  const calls = [];
  page.on("pageerror", (err) => runtimeErrors.push(err.message));
  page.on("request", (req) => {
    if (req.url().includes(":8000/")) calls.push(req.url());
  });
  try {
    await page.goto(base + "/acesso/", { waitUntil: "domcontentloaded" });
    assert.equal(await page.getByRole("radio").count(), 5);
    assert.equal(await page.getByText("Não foi possível conectar à API").count(), 0);
    for (const [role, route] of profiles) {
      await page.goto(base + "/acesso/", { waitUntil: "domcontentloaded" });
      await page.getByRole("radio", { name: new RegExp(role, "i") }).check();
      await page.getByRole("button", { name: "Explorar demonstração" }).click();
      await page.waitForURL((url) => url.pathname === route, { timeout: 15000 });
      await page.getByText("Demonstração offline:", { exact: false }).first().waitFor();
      if (role === "Operador da fornecedora" || role === "Gestor da fornecedora") {
        await page.goto(base + "/painel/envio/", { waitUntil: "domcontentloaded" });
        await page.getByText("Envio desativado nesta demonstração").waitFor();
      }
      if (role === "Analista Bernhoeft") {
        await page.goto(base + "/painel/revisao/", { waitUntil: "domcontentloaded" });
        await page.getByRole("heading", { name: "Fila de Exceções" }).waitFor();
        const nav = await page.locator('nav[aria-label="Navegação do painel"] a').allTextContents();
        assert.deepEqual(nav.map((label) => label.trim()), [
          "Visão geral", "Fila de Exceções", "Pareceres",
        ]);
        await page.getByRole("link", { name: /Conferir/ }).first().waitFor();
        await page.getByText("Diferença fictícia de 4 h", { exact: false }).waitFor();
        await page.getByText("Página ilegível no arquivo de demonstração.", { exact: false }).waitFor();
        await page.goto(base + "/painel/pareceres/", { waitUntil: "domcontentloaded" });
        await page.getByText("Exemplo fictício:", { exact: false }).first().waitFor();
        assert.equal(await page.getByRole("button", { name: "Criar rascunho" }).isDisabled(), true);
      }
      if (role === "Gestor da contratante") {
        await page.getByRole("heading", { name: /O que foi conferido/ }).waitFor();
        await page.goto(base + "/painel/", { waitUntil: "domcontentloaded" });
        await page.waitForURL((url) => url.pathname.startsWith("/contratante/"), { timeout: 15000 });
      }
      await page.goto(base + "/acesso/", { waitUntil: "domcontentloaded" });
      assert.equal(await page.getByRole("radio").count(), 5);
    }
    assert.deepEqual(calls, [], "Modo demo nao deve acessar o backend");
    assert.deepEqual(runtimeErrors, [], "Nao deve haver erros JS");
    console.log("Offline demo smoke: PASSOU (5 perfis, 0 chamadas API)");
  } finally {
    await browser.close();
  }
}
run().catch((err) => { console.error("Offline demo smoke: FALHOU", err); process.exitCode = 1; });
