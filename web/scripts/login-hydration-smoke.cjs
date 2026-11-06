/* Login por token e seletor da demo não podem aceitar entrada antes da hidratação:
 * o React descartaria o valor digitado (campo controlado volta a vazio) e o botão
 * ficaria desabilitado. Não precisa de API. Rodar com o front em DOCRISK_WEB_URL. */
const assert = require("node:assert/strict");
const { chromium } = require("playwright");

const base = process.env.DOCRISK_WEB_URL || "http://127.0.0.1:4173";

async function run() {
  const browser = await chromium.launch({ headless: true });
  try {
    // 1. Sem JavaScript (hidratação nunca ocorre): HTML pré-renderizado bloqueia a entrada.
    const noJs = await browser.newContext();
    await noJs.route(/\.js(\?|$)/, (route) => route.abort());
    const raw = await noJs.newPage();
    await raw.goto(base + "/operacao/", { waitUntil: "domcontentloaded" });
    assert.equal(await raw.getByLabel("Token Bearer de teste").isDisabled(), true,
      "o campo de token deve vir desabilitado antes da hidratação");
    assert.equal(await raw.getByRole("button", { name: /Conectar API de testes/ }).isDisabled(), true);
    await raw.goto(base + "/demo/", { waitUntil: "domcontentloaded" });
    assert.equal(await raw.getByRole("button", { name: "Explorar demonstração" }).isDisabled(), true,
      "o seletor da demo deve vir desabilitado antes da hidratação");
    await noJs.close();

    // 2. Com JavaScript: preencher logo após a navegação não perde o valor.
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    for (let attempt = 0; attempt < 5; attempt++) {
      await page.goto(base + "/operacao/", { waitUntil: "domcontentloaded" });
      await page.getByLabel("Token Bearer de teste").fill("token-ficticio-de-teste");
      await page.waitForTimeout(400);
      assert.equal(await page.getByLabel("Token Bearer de teste").inputValue(), "token-ficticio-de-teste",
        "o valor digitado não pode ser descartado pela hidratação");
      assert.equal(await page.getByRole("button", { name: /Conectar API de testes/ }).isEnabled(), true);
    }
    // Perfil diferente do padrão (Analista): força mudança real de estado após a hidratação.
    await page.goto(base + "/demo/", { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => document.querySelector("button.access-enter")?.disabled === false,
      null, { timeout: 15000 });
    await page.getByRole("radio", { name: /Gestor da contratante/i }).check();
    await page.waitForTimeout(300);
    assert.equal(await page.getByRole("radio", { name: /Gestor da contratante/i }).isChecked(), true,
      "a escolha feita após a hidratação deve ser mantida");
    assert.equal(await page.getByRole("button", { name: "Explorar demonstração" }).isEnabled(), true);
    assert.deepEqual(errors, [], "não deve haver erros JS");
    console.log("Login hydration smoke: PASSOU");
  } finally {
    await browser.close();
  }
}

run().catch((error) => { console.error("Login hydration smoke: FALHOU\n", error); process.exitCode = 1; });
