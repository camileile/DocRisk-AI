/* Smoke de integração da interface com contratos F1 usando uma API simulada.
 * Não exige token real, não cria lotes nem aciona o pipeline.
 * NEXT_PUBLIC_DOCRISK_API_URL deve ser http://127.0.0.1:8000 no build.
 */
const assert = require("node:assert/strict");
const { chromium } = require("playwright");

const base = process.env.DOCRISK_WEB_URL || "http://127.0.0.1:4173";
const mockUrl = "http://127.0.0.1:8000/api/**";
const cors = {
  "access-control-allow-origin": base,
  "access-control-allow-methods": "GET, OPTIONS",
  "access-control-allow-headers": "Authorization, Content-Type, Accept",
  "content-type": "application/json",
};

const analyst = { id: "u-analista", nome: "Analista F1 Teste", org_id: "ORG-BH", org_tipo: "BERNHOEFT", papel: "ANALISTA_BH" };
const supplier = { id: "u-oper-beta", nome: "Operadora Beta Teste", org_id: "ORG-BETA", org_tipo: "FORNECEDORA", papel: "OPERADOR_FORN" };
const contracts = [
  { id: "CT-001", nome: "Contrato F1 Alfa", contratante_id: "ORG-ALFA", fornecedora_id: "ORG-BETA", bernhoeft_id: "ORG-BH", prazo_correcao_dias: 3 },
  { id: "CT-002", nome: "Contrato F1 Gama", contratante_id: "ORG-ALFA", fornecedora_id: "ORG-GAMA", bernhoeft_id: "ORG-BH", prazo_correcao_dias: 3 },
];
const batches = [
  { id: 21, contract_id: "CT-001", uploaded_by: "u-oper-beta", filename: "lote-real-teste.pdf", tipo_arquivo: "PDF", status: "CONCLUIDO", total_pages: 2, issue_id: null, erro: null, created_at: "2026-11-05T20:00:00", finished_at: "2026-11-05T20:00:07" },
  { id: 20, contract_id: "CT-002", uploaded_by: "u-oper-gama", filename: "outro-contrato.png", tipo_arquivo: "PNG", status: "PROCESSANDO", total_pages: 1, issue_id: null, erro: null, created_at: "2026-11-05T18:00:00", finished_at: null },
];
const docs = [
  { id: 88, batch_id: 21, contract_id: "CT-001", tipo: "HOLERITE", worker_id: "T001", competencia: "10/2026", status: "REVISAO_HUMANA", versao: 1, motivos_pendencia: [], motivos_revisao: ["revisar vínculo"] },
];

function mockResponse(route, status, body) {
  return route.fulfill({ status, headers: cors, body: JSON.stringify(body) });
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 850 } });
  const runtimeErrors = [];
  const seen = [];
  page.on("pageerror", (error) => runtimeErrors.push(error.message));
  await page.route(mockUrl, (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    if (req.method() === "OPTIONS") return route.fulfill({ status: 204, headers: cors });
    const token = req.headers().authorization;
    seen.push({ path, token: token ? "presente" : "ausente" });
    if (token !== "Bearer test-analyst-token" && token !== "Bearer test-supplier-token") {
      return mockResponse(route, 401, { detail: "Token inválido" });
    }
    const isSupplier = token === "Bearer test-supplier-token";
    if (path === "/api/me") return mockResponse(route, 200, isSupplier ? supplier : analyst);
    if (path === "/api/contracts") return mockResponse(route, 200, isSupplier ? [contracts[0]] : contracts);
    if (path === "/api/batches") return mockResponse(route, 200, isSupplier ? [batches[0]] : batches);
    if (path === "/api/batches/21") return mockResponse(route, 200, batches[0]);
    if (path === "/api/batches/21/documents") {
      return mockResponse(route, 200, isSupplier
        ? [{ ...docs[0], status: "EM_ANALISE", motivos_revisao: undefined }]
        : docs);
    }
    return mockResponse(route, 404, { detail: "Não encontrado" });
  });
  try {
    await page.goto(base + "/acesso/", { waitUntil: "domcontentloaded" });

    console.log("[F1 1/5] Token inválido mantém o usuário fora da área API");
    await page.getByLabel("Token Bearer de teste").fill("token-incorreto");
    await page.getByRole("button", { name: "Conectar API de testes" }).click();
    await page.getByRole("alert").getByText(/Token inválido/).waitFor();
    assert(page.url().includes("/acesso"));

    console.log("[F1 2/5] Identidade e contratos autorizados do analista");
    await page.getByLabel("Token Bearer de teste").fill("test-analyst-token");
    await page.getByRole("button", { name: "Conectar API de testes" }).click();
    await page.waitForURL((url) => url.pathname.startsWith("/painel"));
    await page.getByText("Acesso confirmado como Analista F1 Teste").waitFor();
    await page.getByRole("combobox", { name: "Contrato" }).selectOption("CT-002");
    await page.getByText("outro-contrato.png").waitFor();
    assert.equal(await page.getByText("lote-real-teste.pdf").count(), 0);
    await page.getByRole("combobox", { name: "Contrato" }).selectOption("CT-001");

    console.log("[F1 3/5] Lotes e documentos obtidos da API, sem dados sintéticos");
    await page.getByRole("link", { name: "Lotes enviados", exact: true }).click();
    await page.getByText("lote-real-teste.pdf").waitFor();
    assert.equal(await page.getByText("LOTE-009").count(), 0);
    await page.getByRole("button", { name: "Ver documentos" }).click();
    await page.getByText("Documento #88").waitFor();
    await page.getByText(/revisar vínculo/).waitFor();
    assert.equal(await page.getByRole("link", { name: "Pareceres", exact: true }).count(), 0);

    console.log("[F1 4/5] Saída limpa a sessão e demonstração continua disponível");
    await page.getByRole("link", { name: "Trocar perspectiva" }).click();
    await page.waitForURL((url) => url.pathname.startsWith("/acesso"));
    const html = await page.content();
    assert(!html.includes("test-analyst-token"), "Token apareceu no HTML");
    await page.getByRole("radio", { name: "Analista Bernhoeft" }).check();
    await page.getByRole("button", { name: "Explorar demonstração" }).click();
    await page.waitForURL((url) => url.pathname.startsWith("/painel"));
    await page.getByRole("link", { name: "Lotes enviados", exact: true }).click();
    await page.getByText("LOTE-009").waitFor();

    console.log("[F1 5/5] Fornecedora vê somente dados autorizados, sem revisão interna");
    await page.goto(base + "/acesso/");
    await page.getByLabel("Token Bearer de teste").fill("test-supplier-token");
    await page.getByRole("button", { name: "Conectar API de testes" }).click();
    await page.waitForURL((url) => url.pathname.startsWith("/painel"));
    await page.getByRole("link", { name: "Lotes enviados", exact: true }).click();
    assert.equal(await page.getByText("outro-contrato.png").count(), 0);
    assert.equal(await page.getByRole("link", { name: "Pareceres", exact: true }).count(), 0);
    await page.getByRole("button", { name: "Ver documentos" }).click();
    await page.getByText("Em análise").waitFor();
    assert.equal(await page.getByText("revisar vínculo").count(), 0);

    assert(seen.every((request) => request.token === "presente"));
    assert.equal(runtimeErrors.length, 0, "Erros JS: " + runtimeErrors.join("; "));
    console.log("Smoke F1: PASSOU");
  } finally {
    await browser.close();
  }
}

run().catch((error) => {
  console.error("Smoke F1: FALHOU", error);
  process.exitCode = 1;
});
