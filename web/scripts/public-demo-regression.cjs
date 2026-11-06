/* Build pública (NEXT_PUBLIC_DOCRISK_PUBLIC_DEMO=1): nenhum transporte operacional,
 * nem para 127.0.0.1, com ou sem token; a demonstração offline continua funcionando. */
const assert = require("node:assert/strict");
const { environment } = require("./regression-env.cjs");

function build(publicDemo, extraEnv = {}) {
  const calls = [];
  const env = environment(false, {
    process: { env: { ...process.env, NEXT_PUBLIC_DOCRISK_PUBLIC_DEMO: publicDemo ? "1" : "", ...extraEnv } },
    fetch: async (url) => { calls.push(String(url)); return new Response('{"ok":true}', { status: 200, headers: { "Content-Type": "application/json" } }); },
  });
  return { ...env, api: env.load("./lib/api.ts"), upload: env.load("./lib/api-upload.ts"),
    mode: env.load("./lib/auth-mode.ts"), calls };
}

async function run() {
  // Controle: sem o flag, a mesma chamada chega ao fetch (o teste distingue os dois modos).
  const control = build(false);
  control.api.setToken("token-local");
  await control.api.api("/api/me");
  assert.deepEqual(control.calls, ["http://127.0.0.1:8000/api/me"]);

  const pub = build(true, { NEXT_PUBLIC_AUTH_MODE: "clerk", NEXT_PUBLIC_API_URL: "http://127.0.0.1:8000" });
  assert.equal(pub.mode.publicDemoOnly, true);
  assert.equal(pub.mode.clerkEnabled, false, "a build pública nunca habilita login Clerk");
  pub.api.setToken("token-colado-por-visitante");
  const blocked = (e) => e instanceof pub.api.ApiError && e.kind === "session" && /somente a demonstração offline/.test(e.message);
  const file = new File(["%PDF-1.4"], "lote.pdf", { type: "application/pdf" });
  for (const action of [
    () => pub.api.api("/api/me"),
    () => pub.api.api("/api/supplier/batches", { method: "POST", body: "{}" }),
    () => pub.api.apiBlob("/api/pages/1/image"),
    () => pub.api.downloadBatchSource(1),
    () => pub.api.downloadReportPdf(1, 1),
    () => pub.upload.uploadApiBatch("token-colado-por-visitante", "CT-001", file),
    () => pub.upload.fetchApiBatch("token-colado-por-visitante", 1),
  ]) await assert.rejects(action(), blocked);
  assert.deepEqual(pub.calls, [], "nenhuma requisição pode sair da build pública");

  // A demonstração offline segue respondendo sem rede.
  const session = pub.load("./lib/api-session.ts");
  session.setDemoRole("ANALISTA_BH");
  assert.ok(Array.isArray(await pub.api.api("/api/review-queue")));
  assert.deepEqual(pub.calls, []);
  console.log("Public demo regression: PASSOU (0 requisições na build pública)");
}

run().catch((error) => { console.error("Public demo regression: FALHOU\n", error); process.exitCode = 1; });
