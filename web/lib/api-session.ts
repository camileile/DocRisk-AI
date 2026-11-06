import type { Papel } from "./api-contracts";

export const DEMO_ROLES: Papel[] = [
  "ADMIN_PLATAFORMA", "ADMIN_BH", "ANALISTA_BH", "GESTOR_FORN", "OPERADOR_FORN", "GESTOR_CONTR",
];
const TOKEN_KEY = "docrisk.token";
const ROLE_KEY = "docrisk.offline-demo-role";
let activeToken: string | null | undefined;
let activeRole: Papel | null | undefined;
let version = 0;
let controller = new AbortController();

function replaceSession() {
  const previous = controller;
  controller = new AbortController();
  version++;
  previous.abort();
}

function read(key: string): string | null {
  try { return sessionStorage.getItem(key); } catch { return null; }
}
function write(key: string, value: string | null) {
  try {
    if (value) sessionStorage.setItem(key, value);
    else sessionStorage.removeItem(key);
  } catch { /* Sessão em memória quando o storage é bloqueado. */ }
}

export function getToken(): string | null {
  if (activeToken === undefined) activeToken = read(TOKEN_KEY)?.trim() || null;
  return activeToken;
}
export function setToken(token: string | null): void {
  activeToken = token?.trim() || null;
  write(TOKEN_KEY, activeToken);
  replaceSession();
}
export function getDemoRole(): Papel | null {
  if (activeRole === undefined) activeRole = DEMO_ROLES.find(role => role === read(ROLE_KEY)) ?? null;
  return activeRole;
}
export function setDemoRole(role: Papel | null): void {
  activeRole = role;
  write(ROLE_KEY, role);
  replaceSession();
}
export function getSessionVersion(): number { return version; }
export function captureSession() {
  return { token: getToken(), role: getDemoRole(), version, signal: controller.signal };
}
