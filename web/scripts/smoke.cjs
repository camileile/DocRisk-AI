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
  const roles = {
    "Administrador geral da plataforma": "ADMIN_PLATAFORMA",
    "Operador da fornecedora": "OPERADOR_FORN",
    "Gestor da fornecedora": "GESTOR_FORN",
    "Analista Bernhoeft": "ANALISTA_BH",
    "Gestor da contratante": "GESTOR_CONTR",
    "Administrador Bernhoeft": "ADMIN_BH",
  };
  const url = process.env.DOCRISK_API_URL || "http://127.0.0.1:8000";
  const response = await fetch(url + "/api/demo/users");
  assert.equal(response.status, 200, "API local deve habilitar DOCRISK_DEMO_MODE=1");
  const users = await response.json();
  const user = users.find((item) => (item.role || item.papel) === roles[roleLabel]);
  assert.ok(user?.token, "Perfil de testes nao encontrado: " + roleLabel);
  await page.evaluate(() => sessionStorage.clear()).catch(() => {});
  await go(page, "/operacao/");
  await page.getByLabel("Token Bearer de teste").waitFor();
  await page.getByLabel("Token Bearer de teste").fill(user.token);
  await page.getByRole("button", { name: /Conectar API de testes/ }).click();
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
    await page.getByRole("link", { name: /Acessar plataforma/ }).click();
    await page.getByLabel("Token Bearer de teste").waitFor();
    await go(page, "/");
    await go(page, "/painel/");
    await page.getByText("Entre com um perfil para continuar.").waitFor();

    console.log("[equipe] Gestor gerencia operadores no backend conectado");
    await login(page, "Gestor da fornecedora", "/painel");
    await page.getByRole("link", { name: "Operadores", exact: true }).click();
    await page.getByLabel("Nome do operador", { exact: true }).fill("Operador Navegador");
    await page.getByRole("button", { name: "Cadastrar operador", exact: true }).click();
    const operatorRow = page.getByRole("row", { name: /Operador Navegador/ });
    await operatorRow.waitFor();
    await operatorRow.getByRole("button", { name: "Desativar Operador Navegador", exact: true }).click();
    await operatorRow.getByRole("cell", { name: "Inativo", exact: true }).waitFor();
    const [reactivation] = await Promise.all([
      page.waitForResponse((r) => r.url().includes("/api/supplier/operators/") && r.url().endsWith("/status") && r.request().method() === "PATCH"),
      operatorRow.getByRole("button", { name: "Reativar Operador Navegador", exact: true }).click(),
    ]);
    assert.equal(reactivation.status(), 200, "A API precisa confirmar a reativação");
    assert.equal((await reactivation.json()).ativo, true);
    await operatorRow.getByRole("cell", { name: "Ativo", exact: true }).waitFor();

    console.log("[2/7] Fornecedora envia o lote sintético e acompanha o processamento");
    await login(page, "Operador da fornecedora", "/painel");
    assert.equal(await page.getByRole("link", { name: "Fila de Exceções", exact: true }).count(), 0);
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
    await go(page, "/painel/");
    await page.getByRole("heading", { name: "Visão geral das divergências." }).waitFor();
    await page.getByRole("combobox", { name: "Contratante" }).selectOption("ORG-ALFA");
    await page.getByRole("combobox", { name: "Fornecedora" }).selectOption("ORG-BETA");
    await page.getByRole("combobox", { name: "Competência" }).selectOption("10/2026");
    await page.getByText("Taxa de divergências trabalhistas").waitFor();
    await page.getByText("Cobertura da análise").waitFor();
    await page.getByText("Evolução mensal das divergências").waitFor();
    await go(page, "/painel/conciliacoes/");
    await page.getByText(/diferença de 4 h a conferir/).waitFor({ timeout: 30000 });
    await page.locator(".analysis-card", { hasText: "Trabalhador T002" }).locator(".status-badge", { hasText: "Sem divergência" }).waitFor({ timeout: 30000 });
    await go(page, "/painel/revisao/");
    await page.getByRole("link", { name: /Conferir/ }).first().click();
    await page.getByRole("combobox", { name: /^Tipo/ }).selectOption("OUTRO");
    await page.getByRole("button", { name: /Aprovar classificação/ }).click();
    // Mesmo após resolver a revisão documental, conciliações e pendências
    // continuam na fila; a navegação reduzida não as descarta.
    await page.getByRole("heading", { name: "Fila de Exceções" }).waitFor();
    await page.getByText("Nenhum documento aguardando revisão.").waitFor();
    await page.getByText("Conciliações que exigem atenção", { exact: false }).waitFor();
    await go(page, "/painel/documentos/");
    console.log("[analista] Revisão manual iniciada voluntariamente em documento apto");
    const aptRow = page.locator("table.data-table tbody tr")
      .filter({ has: page.locator(".status-badge", { hasText: "Apto" }) }).first();
    await aptRow.getByRole("link", { name: "Abrir" }).click();
    await page.getByRole("button", { name: "Iniciar revisão manual" }).click();
    await page.getByLabel("Motivo para iniciar a revisão manual")
      .fill("Conferência voluntária por divergência verificada no documento.");
    await page.getByRole("button", { name: "Confirmar revisão manual" }).click();
    await page.getByRole("heading", { name: /Conferir:/ }).waitFor();
    await page.getByRole("button", { name: /Aprovar classificação/ }).click();
    await page.getByRole("heading", { name: "Fila de Exceções" }).waitFor();
    await go(page, "/painel/documentos/");
    await page.getByRole("searchbox").fill("T001");
    await page.getByRole("button", { name: "Buscar" }).click();
    await page.locator(".search-results mark").first().waitFor();

    console.log("[5/7] Analista publica o parecer");
    await go(page, "/painel/pareceres/");
    await page.getByRole("button", { name: /Criar rascunho/ }).click();
    await page.getByText("PRÉVIA DO RASCUNHO").waitFor();
    await page.getByRole("checkbox", { name: /Conferi autoria/ }).check();
    await page.getByRole("button", { name: "Publicar" }).click();
    await page.getByText(/Parecer publicado/).waitFor();

    console.log("[6/7] Contratante vê somente o publicado");
    await login(page, "Gestor da contratante", "/contratante");
    await page.getByRole("link", { name: "Pareceres publicados", exact: true }).click();
    await page.getByText("Com divergência a verificar").waitFor();
    assert.equal(await page.getByText("PRÉVIA DO RASCUNHO").count(), 0);
    await go(page, "/painel/");
    await page.waitForURL((url) => url.pathname.startsWith("/contratante"), { timeout: 20000 });

    console.log("[7/7] Administrador consulta gestao e auditoria; navegação no celular");
    await login(page, "Administrador Bernhoeft", "/administracao");
    await page.getByRole("heading", { name: "Visão geral da organização." }).waitFor();
    await page.getByText("Contratos ativos").waitFor();
    await go(page, "/administracao/empresas/");
    await page.getByRole("heading", { name: "Empresas e Contratos." }).waitFor();
    await page.locator("table.data-table").getByText("Contratante Alfa S.A. (fictícia)").first().waitFor();
    await go(page, "/administracao/usuarios/");
    await page.getByRole("heading", { name: "Gestão de Usuários." }).waitFor();
    await go(page, "/administracao/auditoria/");
    await page.getByText("Parecer publicado").first().waitFor();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole("button", { name: "Abrir navegação" }).click();
    await page.locator("aside.workspace-sidebar.visible").waitFor({ state: "visible" });
    await page.getByRole("button", { name: "Fechar navegação" }).first().click();
    assert.equal(await page.locator("aside.workspace-sidebar.visible").count(), 0);

    console.log("[plataforma] Admin Geral cadastra auditora e persiste dados institucionais");
    await page.setViewportSize({ width: 1365, height: 900 });
    await login(page, "Administrador geral da plataforma", "/plataforma");
    await page.getByRole("heading", { name: "Estrutura do DocRisk AI." }).waitFor();
    await page.getByRole("link", { name: "Organizações Auditoras", exact: true }).click();
    await page.getByLabel("Nome da auditora", { exact: true }).fill("Auditora Navegador");
    await page.getByLabel("Administrador inicial", { exact: true }).fill("Admin Navegador");
    await page.getByRole("button", { name: "Cadastrar organização auditora", exact: true }).click();
    await page.getByRole("heading", { name: "Auditora Navegador", exact: true }).waitFor();
    await page.getByRole("link", { name: "Dados da Plataforma", exact: true }).click();
    await page.getByLabel("Contato de suporte", { exact: true }).fill("Suporte de integração");
    await page.getByRole("button", { name: "Salvar dados", exact: true }).click();
    await page.getByText("Alteração salva no ambiente de testes.", { exact: true }).waitFor();
    await page.reload();
    assert.equal(await page.getByLabel("Contato de suporte", { exact: true }).inputValue(), "Suporte de integração");
    await go(page, "/painel/");
    await page.waitForURL((url) => url.pathname.startsWith("/plataforma"));
    await page.getByRole("heading", { name: "Estrutura do DocRisk AI." }).waitFor();

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
