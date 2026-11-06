/* Fluxo real: navegador Next estático + API FastAPI local + SQLite efêmero.
 * O servidor do CI deve usar DOCRISK_DEMO_MODE=1, AI_PROVIDER=textlayer e
 * ser acessível SOMENTE em 127.0.0.1:8000. Nunca imprime tokens demo.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { chromium } = require("playwright");

const site = process.env.DOCRISK_LIVE_WEB_URL || "http://localhost:3000";
const api = process.env.DOCRISK_LIVE_API_URL || "http://127.0.0.1:8000";
const uploads = process.env.DOCRISK_UPLOAD_DIR || "/tmp";

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
    await page.goto(site + "/operacao/", { waitUntil: "domcontentloaded" });
    // Aguarda o formulário exclusivo do ambiente conectado.
    await page.getByLabel("Token Bearer de teste").waitFor({ timeout: 20000 });
    await page.getByLabel("Token Bearer de teste").fill(token);
    await page.getByRole("button", { name: "Conectar API de testes" }).click();
    await page.waitForURL((url) => url.pathname.startsWith("/painel"), { timeout: 30000 });
  }

  try {
    console.log("[live 1/5] Identidade e contratos do SQLite via FastAPI");
    await enter(analyst.token);
    await page.locator(".workspace-person").getByText("Analista Bernhoeft (demo)").waitFor();
    // O Analista agora seleciona contratante/fornecedora/competência e só
    // aprofunda por contrato quando necessário.
    await page.getByRole("heading", { name: "Visão geral das divergências." }).waitFor();
    await page.getByText("Cobertura da análise").waitFor();
    const clientFilter = page.getByRole("combobox", { name: "Contratante" });
    assert.equal(await clientFilter.locator("option").count(), 2);
    const contractFilter = page.getByRole("combobox", { name: "Contrato (opcional)" });
    assert.equal(await contractFilter.locator("option").count(), 3);
    await clientFilter.selectOption("ORG-ALFA");
    await page.getByRole("combobox", { name: "Fornecedora" }).selectOption("ORG-BETA");
    await page.getByRole("combobox", { name: "Contrato (opcional)" }).selectOption("CT-001");
    assert.equal(await page.getByRole("link", { name: "Lotes enviados", exact: true }).count(), 0);

    console.log("[live 2/5] Consulta lote/documentos processados pela F2");
    // Rota de consulta preservada, embora sem atalho no menu do Analista.
    await page.goto(site + "/painel/lotes/", { waitUntil: "domcontentloaded" });
    await page.getByText("integracao-f1-sintetico.pdf").waitFor();
    await page.getByRole("row", { name: /integracao-f1-sintetico\.pdf/ }).getByRole("link", { name: /Abrir/ }).click();
    await page.getByText(/documento\(s\) separados/).waitFor();
    assert.equal(await page.getByText("LOTE-009").count(), 0);

    console.log("[live 3/5] Fornecedora vê apenas seu contrato real na API");
    await enter(supplier.token);
    await page.locator(".workspace-person").getByText("Operador Beta (demo)").waitFor();
    assert.equal(await page.getByRole("combobox", { name: "Contrato" }).locator("option").count(), 1);
    await page.getByRole("link", { name: "Lotes enviados", exact: true }).click();
    await page.getByText("integracao-f1-sintetico.pdf").waitFor();
    assert.equal(await page.getByRole("link", { name: "Pareceres", exact: true }).count(), 0);

    console.log("[live 4/5] Upload real do navegador, processamento F2 e histórico");
    await page.getByLabel("Navegação do painel").getByRole("link", { name: "Enviar lote", exact: true }).click();
    await page.getByRole("heading", { name: "Envio de documentos." }).waitFor();
    await page.getByLabel("Selecionar arquivo para envio real").setInputFiles({
      name: "teste-browser-f2.pdf",
      mimeType: "application/pdf",
      buffer: fs.readFileSync(uploads + "/docrisk-browser-upload.pdf"),
    });
    await page.getByRole("checkbox", { name: /Confirmo que o arquivo é/ }).check();
    await page.getByRole("button", { name: "Enviar arquivo ao backend" }).click();
    await page.getByText(/Recebimento confirmado — lote #/).waitFor({ timeout: 30000 });
    await page.getByText(/Processamento documental concluído/).waitFor({ timeout: 60000 });

    console.log("[live 5/5] Upload de PNG sintético, sem camada de texto");
    await page.getByRole("button", { name: "Preparar outro arquivo" }).click();
    await page.getByLabel("Selecionar arquivo para envio real").setInputFiles({
      name: "teste-browser-f2.png",
      mimeType: "image/png",
      buffer: fs.readFileSync(uploads + "/docrisk-browser-upload.png"),
    });
    await page.getByRole("checkbox", { name: /Confirmo que o arquivo é/ }).check();
    await page.getByRole("button", { name: "Enviar arquivo ao backend" }).click();
    await page.getByText(/Recebimento confirmado — lote #/).waitFor({ timeout: 30000 });
    await page.getByText(/Processamento documental concluído/).waitFor({ timeout: 60000 });
    await page.getByRole("link", { name: "Consultar histórico de lotes" }).click();
    await page.getByText("teste-browser-f2.pdf").waitFor({ timeout: 15000 });
    await page.getByText("teste-browser-f2.png").waitFor({ timeout: 15000 });

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
