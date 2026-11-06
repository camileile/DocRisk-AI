/* Navegação de demonstração offline: NÃO inicia FastAPI e NÃO acessa 127.0.0.1:8000.
 * Rodar com a exportação estática servida em 127.0.0.1:4173. */
const assert = require("node:assert/strict");
const { chromium } = require("playwright");

const base = process.env.DOCRISK_WEB_URL || "http://127.0.0.1:4173";
const profiles = [
  ["Administrador geral da plataforma", "/plataforma/"],
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
    await page.goto(base + "/", { waitUntil: "domcontentloaded" });
    assert.equal(await page.locator('a[href="/demo"]').count(), 0, "A landing não deve divulgar a demo fictícia.");
    await page.getByRole("navigation", { name: "Navegação principal" }).getByRole("link", { name: "Acesso", exact: true }).click();
    await page.waitForURL((url) => url.pathname === "/operacao/");
    assert.equal(await page.getByRole("radio").count(), 0, "Acesso institucional não deve abrir os perfis fictícios.");
    await page.goto(base + "/acesso/", { waitUntil: "domcontentloaded" });
    await page.waitForURL((url) => url.pathname === "/operacao/", { timeout: 15000 });
    assert.equal(await page.getByRole("radio").count(), 0, "Rota antiga de acesso não deve abrir a demo.");
    await page.goto(base + "/demo/", { waitUntil: "domcontentloaded" });
    assert.equal(await page.getByRole("radio").count(), 6);
    assert.equal(await page.getByText("Não foi possível conectar à API").count(), 0);
    for (const [role, route] of profiles) {
      await page.goto(base + "/demo/", { waitUntil: "domcontentloaded" });
      await page.getByRole("radio", { name: new RegExp(role, "i") }).check();
      await page.getByRole("button", { name: "Explorar demonstração" }).click();
      await page.waitForURL((url) => url.pathname === route, { timeout: 15000 });
      await page.getByText("Demonstração offline:", { exact: false }).first().waitFor();
      if (role === "Administrador geral da plataforma") {
        await page.getByRole("heading", { name: "Estrutura do DocRisk AI." }).waitFor();
        await page.getByRole("link", { name: "Organizações Auditoras", exact: true }).click();
        await page.getByRole("heading", { name: "Organizações auditoras.", exact: true }).waitFor();
        assert.equal(await page.getByRole("button", { name: "Cadastrar organização auditora", exact: true }).isDisabled(), true);
        await page.getByRole("link", { name: "Dados da Plataforma", exact: true }).click();
        await page.getByRole("heading", { name: "Dados institucionais da plataforma.", exact: true }).waitFor();
        await page.goto(base + "/administracao/");
        await page.waitForURL((url) => url.pathname === "/plataforma/");
      }
      if (role === "Administrador Bernhoeft") {
        const labels = await page.locator('nav[aria-label="Navegação administrativa"] a').allTextContents();
        assert.deepEqual(labels.map((text) => text.trim()), [
          "Visão Geral", "Empresas e Contratos", "Gestão de Usuários", "Auditoria",
        ]);
        await page.getByRole("heading", { name: "Visão geral da organização." }).waitFor();
        await page.goto(base + "/administracao/empresas/", { waitUntil: "domcontentloaded" });
        await page.getByRole("heading", { name: "Empresas e Contratos." }).waitFor();
        assert.equal(await page.getByRole("button", { name: "Cadastrar empresa" }).isDisabled(), true);
        await page.goto(base + "/administracao/usuarios/", { waitUntil: "domcontentloaded" });
        await page.getByRole("heading", { name: "Gestão de Usuários." }).waitFor();
        assert.equal(await page.getByRole("button", { name: "Criar acesso de teste" }).isDisabled(), true);
        await page.goto(base + "/administracao/auditoria/", { waitUntil: "domcontentloaded" });
        await page.getByRole("heading", { name: "Quem fez o quê, e quando." }).waitFor();
      }
      if (role === "Operador da fornecedora" || role === "Gestor da fornecedora") {
        await page.goto(base + "/painel/envio/", { waitUntil: "domcontentloaded" });
        await page.getByText("Envio desativado nesta demonstração").waitFor();
      }
      if (role === "Gestor da fornecedora") {
        await page.goto(base + "/painel/operadores/");
        await page.getByRole("heading", { name: "Operadores da sua empresa." }).waitFor();
        assert.equal(await page.getByRole("button", { name: "Cadastrar operador", exact: true }).isDisabled(), true);
      }
      if (role === "Operador da fornecedora") {
        assert.equal(await page.getByRole("link", { name: "Operadores", exact: true }).count(), 0);
        await page.goto(base + "/painel/documentos/");
        await page.getByRole("combobox", { name: "Situação", exact: true }).selectOption("EM_ANALISE");
        await page.getByRole("row", { name: /T003/ }).waitFor();
      }
      if (role === "Analista Bernhoeft") {
        await page.getByRole("heading", { name: "Visão geral das divergências." }).waitFor();
        await page.getByRole("combobox", { name: "Contratante" }).selectOption("demo-contr");
        await page.getByRole("combobox", { name: "Fornecedora" }).selectOption("demo-forn");
        await page.getByRole("combobox", { name: "Competência" }).selectOption("10/2026");
        await page.getByText("Cobertura da análise").waitFor();
        await page.getByText("Evolução mensal das divergências").waitFor();
        await page.goto(base + "/painel/revisao/", { waitUntil: "domcontentloaded" });
        await page.getByRole("heading", { name: "Fila de Exceções" }).waitFor();
        const nav = await page.locator('nav[aria-label="Navegação do painel"] a').allTextContents();
        assert.deepEqual(nav.map((label) => label.trim()), [
          "Visão geral", "Documentos", "Fila de Exceções", "Conciliações", "Pareceres",
        ]);
        await page.getByRole("link", { name: /Conferir/ }).first().waitFor();
        await page.getByText("Diferença fictícia de 4 h", { exact: false }).waitFor();
        await page.getByText("Página ilegível no arquivo de demonstração.", { exact: false }).waitFor();
        await page.goto(base + "/painel/pareceres/", { waitUntil: "domcontentloaded" });
        await page.getByText("Exemplo fictício:", { exact: false }).first().waitFor();
        assert.equal(await page.getByRole("button", { name: "Criar rascunho" }).isDisabled(), true);
      }
      if (role === "Gestor da contratante") {
        await page.getByRole("heading", { name: "Visão geral dos pareceres publicados." }).waitFor();
        await page.getByText("Cobertura nos pareceres", { exact: true }).waitFor();
        await page.getByRole("link", { name: "Pareceres publicados", exact: true }).click();
        await page.getByRole("heading", { name: /O que foi conferido/ }).waitFor();
        await page.goto(base + "/painel/", { waitUntil: "domcontentloaded" });
        await page.waitForURL((url) => url.pathname.startsWith("/contratante/"), { timeout: 15000 });
      }
      await page.goto(base + "/demo/", { waitUntil: "domcontentloaded" });
      assert.equal(await page.getByRole("radio").count(), 6);
    }
    assert.deepEqual(calls, [], "Modo demo nao deve acessar o backend");
    assert.deepEqual(runtimeErrors, [], "Nao deve haver erros JS");
    console.log("Offline demo smoke: PASSOU (6 perfis, 0 chamadas API)");
  } finally {
    await browser.close();
  }
}
run().catch((err) => { console.error("Offline demo smoke: FALHOU", err); process.exitCode = 1; });
