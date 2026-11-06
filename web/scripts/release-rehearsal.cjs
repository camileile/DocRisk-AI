/* D4-03 — ensaio cronometrado e reproduzível do roteiro de apresentação.
 *
 * Em portas livres, com banco NOVO em diretório temporário e leitor offline
 * (AI_PROVIDER=textlayer: não é IA, nenhuma chamada ao Gemini):
 *   E1  build + exportação estática apontando para a API do ensaio
 *   E2  demonstração offline sem API (offline-smoke + contractor-smoke)
 *   E3  API real até /health
 *   E4  roteiro conectado completo por perfil (smoke.cjs)
 *   E5  portal da contratante conectado
 *   E6  contingência: queda abrupta da API, confirmação de indisponibilidade, reinício
 *   E7  navegador contra FastAPI/SQLite após o reinício (live-api-smoke)
 *
 * Uso (na pasta web): node scripts/release-rehearsal.cjs [--json saida.json] [--skip-build]
 * Python da API: DOCRISK_PYTHON (padrão ../api/.venv) ou "python".
 * Orquestrado em Node de propósito: no Windows o Python da Microsoft Store virtualiza
 * AppData e esconde os navegadores do Playwright dos processos filhos.
 */
const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const net = require("node:net");
const os = require("node:os");
const path = require("node:path");

const WEB = path.resolve(__dirname, "..");
const API = path.resolve(WEB, "../api");
const args = process.argv.slice(2);
const jsonOut = args.includes("--json") ? args[args.indexOf("--json") + 1] : null;
const skipBuild = args.includes("--skip-build");
const venvPy = path.join(API, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const PY = process.env.DOCRISK_PYTHON || (fs.existsSync(venvPy) ? venvPy : "python");
const NPM = process.platform === "win32" ? "npm.cmd" : "npm";
const steps = [];

const freePort = () => new Promise((resolve) => {
  const s = net.createServer().listen(0, "127.0.0.1", () => { const { port } = s.address(); s.close(() => resolve(port)); });
});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitHttp(url, limitMs = 40000) {
  const t = Date.now();
  while (Date.now() - t < limitMs) {
    try { if ((await fetch(url, { signal: AbortSignal.timeout(1000) })).ok) return (Date.now() - t) / 1000; } catch { /* */ }
    await sleep(200);
  }
  throw new Error("sem resposta: " + url);
}

function run(cmd, argv, env, log, opts = {}) {
  const r = spawnSync(cmd, argv, { cwd: WEB, env, encoding: "utf8", timeout: 900000, shell: opts.shell || false });
  fs.writeFileSync(log, (r.stdout || "") + (r.stderr || ""));
  if (r.status !== 0) {
    const tail = fs.readFileSync(log, "utf8").trim().split(/\r?\n/).slice(-6).join(" | ");
    throw new Error(`${path.basename(argv[0] || cmd)} saiu ${r.status}: ${tail.slice(0, 400)}`);
  }
  return fs.readFileSync(log, "utf8");
}

async function step(id, name, fn) {
  const t = Date.now();
  let error = null, detail = {};
  try { detail = (await fn()) || {}; } catch (e) { error = String(e.message || e).slice(0, 400); }
  const seconds = Math.round((Date.now() - t) / 100) / 10;
  steps.push({ id, etapa: name, ok: !error, segundos: seconds, erro: error, ...detail });
  console.log(`${error ? "FAIL" : "OK  "} ${id} ${name} (${seconds}s)${error ? " — " + error : ""}`);
  return !error;
}

async function main() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "docrisk-ensaio-"));
  const [pApi, pWeb, pLive] = [await freePort(), await freePort(), await freePort()];
  const apiUrl = `http://127.0.0.1:${pApi}`, webUrl = `http://127.0.0.1:${pWeb}`, liveUrl = `http://localhost:${pLive}`;
  console.log(`ensaio em ${tmp} api=${apiUrl} web=${webUrl}\n`);
  const envWeb = { ...process.env, NEXT_PUBLIC_API_URL: apiUrl, DOCRISK_API_URL: apiUrl, DOCRISK_WEB_URL: webUrl,
    DOCRISK_LIVE_API_URL: apiUrl, DOCRISK_LIVE_WEB_URL: liveUrl, DOCRISK_UPLOAD_DIR: tmp };
  const envApi = Object.fromEntries(Object.entries(process.env).filter(([k]) => !/^(GEMINI|DOCRISK|CORS|AI_)/.test(k)));
  Object.assign(envApi, { AI_PROVIDER: "textlayer", GEMINI_API_KEY: "", DOCRISK_DEMO_MODE: "1", DOCRISK_SYNC: "1",
    DOCRISK_DATA_DIR: path.join(tmp, "data"), CORS_ORIGINS: `${webUrl},${liveUrl}`, PYTHONIOENCODING: "utf-8" });
  const procs = [];
  let api = null;
  const startApi = async (log) => {
    api = spawn(PY, ["-m", "uvicorn", "docrisk_core.api:app", "--host", "127.0.0.1", "--port", String(pApi)],
      { cwd: API, env: envApi, stdio: ["ignore", fs.openSync(path.join(tmp, log), "w"), fs.openSync(path.join(tmp, log), "a")] });
    return { segundos_ate_health: await waitHttp(apiUrl + "/health") };
  };

  try {
    const built = await step("E1", "build e exportação estática", async () => {
      if (!skipBuild) run(NPM, ["run", "build"], envWeb, path.join(tmp, "build.log"), { shell: process.platform === "win32" });
      if (!fs.existsSync(path.join(WEB, "out/acesso/index.html"))) throw new Error("exportação ausente");
      // Next 16.4.5 exportado NO WINDOWS grava os payloads RSC como __next.painel/revisao/__PAGE__.txt,
      // mas o cliente pede __next.painel.revisao.__PAGE__.txt -> 404 e navegação cliente quebrada.
      // Builds Linux (CI/Vercel) não têm o problema. Cópia explícita e registrada, nunca silenciosa.
      const rscCopiados = process.platform === "win32" && !args.includes("--no-rsc-fix") ? fixWindowsRsc(path.join(WEB, "out")) : 0;
      for (const p of [pWeb, pLive]) {
        procs.push(spawn(PY, ["-m", "http.server", String(p), "--bind", "127.0.0.1", "--directory", path.join(WEB, "out")],
          { stdio: "ignore" }));
      }
      await waitHttp(webUrl + "/");
      await waitHttp(liveUrl + "/acesso/");
      return { rsc_compat_windows_copiados: rscCopiados };
    });
    if (!built) return finish(tmp);
    await step("E2", "demonstração offline (6 perfis, sem API)", async () => {
      run(process.execPath, ["scripts/offline-smoke.cjs"], envWeb, path.join(tmp, "offline.log"));
      run(process.execPath, ["scripts/contractor-smoke.cjs"], envWeb, path.join(tmp, "contractor-offline.log"));
    });
    if (await step("E3", "API real até /health (banco novo)", () => startApi("api-1.log"))) {
      await step("E4", "roteiro conectado completo por perfil", async () => {
        const out = run(process.execPath, ["scripts/smoke.cjs"], envWeb, path.join(tmp, "smoke.log"));
        return { passos: out.split(/\r?\n/).filter((l) => l.startsWith("[")).length };
      });
      await step("E5", "portal da contratante conectado", async () => {
        run(process.execPath, ["scripts/contractor-smoke.cjs"], { ...envWeb, DOCRISK_CONNECTED: "1" }, path.join(tmp, "contractor-connected.log"));
      });
      const restarted = await step("E6", "contingência: queda abrupta e reinício da API", async () => {
        api.kill("SIGKILL");
        await sleep(500);
        let down = false;
        try { await fetch(apiUrl + "/health", { signal: AbortSignal.timeout(1000) }); } catch { down = true; }
        if (!down) throw new Error("API ainda responde após kill");
        const t = Date.now();
        const r = await startApi("api-2.log");
        return { api_indisponivel_confirmado: down, segundos_reinicio: (Date.now() - t) / 1000, ...r };
      });
      if (restarted) {
        await step("E7", "navegador contra FastAPI/SQLite após reinício", async () => {
          run(PY, ["-c", SYNTHETIC_UPLOADS, tmp], { ...process.env, PYTHONIOENCODING: "utf-8" }, path.join(tmp, "uploads.log"));
          run(process.execPath, ["scripts/live-api-smoke.cjs"], envWeb, path.join(tmp, "live.log"));
        });
      }
    }
  } finally {
    if (api) api.kill("SIGKILL");
    for (const p of procs) p.kill("SIGKILL");
  }
  return finish(tmp);
}

function fixWindowsRsc(out) {
  let n = 0;
  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, e.name);
      if (e.isDirectory() && e.name.startsWith("__next.")) {
        const copy = (d, rel) => {
          for (const f of fs.readdirSync(d, { withFileTypes: true })) {
            const r = rel.concat(f.name);
            if (f.isDirectory()) copy(path.join(d, f.name), r);
            else if (f.name.endsWith(".txt")) {
              const flat = path.join(dir, [e.name, ...r].join("."));
              if (!fs.existsSync(flat)) { fs.copyFileSync(path.join(d, f.name), flat); n++; }
            }
          }
        };
        copy(full, []);
      } else if (e.isDirectory()) walk(full);
    }
  };
  walk(out);
  return n;
}

function finish(tmp) {
  const total = Math.round(steps.reduce((a, s) => a + s.segundos, 0) * 10) / 10;
  const failed = steps.filter((s) => !s.ok);
  console.log(`\n${steps.length - failed.length}/${steps.length} etapas OK; total ${total}s; logs em ${tmp}`);
  if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify({ node: process.version, plataforma: process.platform,
    total_segundos: total, etapas: steps, logs: tmp }, null, 2));
  process.exitCode = failed.length ? 1 : 0;
}

// Mesmos artefatos fictícios que o CI gera para o live-api-smoke.
const SYNTHETIC_UPLOADS = `
import sys
from io import BytesIO
from pathlib import Path
import pymupdf as fitz
from PIL import Image, ImageDraw
out = Path(sys.argv[1])
doc = fitz.open(); pg = doc.new_page(width=595, height=842)
for i, l in enumerate(["DEMONSTRATIVO DE PAGAMENTO DE SALARIO", "Matricula: T001", "Competencia: 10/2026",
                       "Horas extras 50% | Ref.: 8,00 h | R$ 160,00", "Pagina 1 de 1"]):
    pg.insert_text((50, 60 + i * 18), l, fontsize=10)
(out / "docrisk-browser-upload.pdf").write_bytes(doc.tobytes())
img = Image.new("RGB", (640, 400), "white")
ImageDraw.Draw(img).text((30, 50), "DOCUMENTO FICTICIO - TESTE DE IMAGEM", fill="black")
b = BytesIO(); img.save(b, format="PNG"); (out / "docrisk-browser-upload.png").write_bytes(b.getvalue())
`;

main().catch((e) => { console.error(e); process.exit(1); });
