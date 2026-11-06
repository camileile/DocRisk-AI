import type { Papel } from "./api-contracts";

export const DEMO_ROLES: Papel[] = [
  "ADMIN_PLATAFORMA", "ADMIN_BH", "ANALISTA_BH", "GESTOR_FORN", "OPERADOR_FORN", "GESTOR_CONTR",
];
const TOKEN_KEY = "docrisk.token";
const ROLE_KEY = "docrisk.offline-demo-role";
let activeToken: string | null | undefined;
let activeRole: Papel | null | undefined;
let clerkProvider: (() => Promise<string | null>) | null = null;
let clerkSessionId = "";
let activeLink = "";
const invalidationListeners = new Set<() => void>();
const contractListeners = new Set<() => void>();
export function onContractsChanged(listener: () => void) {
  contractListeners.add(listener);
  return () => { contractListeners.delete(listener); };
}
export function notifyContractsChanged() { contractListeners.forEach(listener => listener()); }
// Cancela respostas do escopo anterior sem encerrar a identidade ou outro vínculo.
export function refreshContractScope() { replaceSession(); }
export function onSessionInvalidated(listener: () => void) {
  invalidationListeners.add(listener);
  return () => { invalidationListeners.delete(listener); };
}
export function invalidateSession() {
  clearClerkSession(); setToken(null);
  invalidationListeners.forEach(listener => listener());
}
export function configureClerkSession(provider: () => Promise<string | null>, sessionId: string) {
  activeToken = null; write(TOKEN_KEY, null);
  clerkProvider = provider; clerkSessionId = sessionId; activeLink = ""; replaceSession();
}
export function selectClerkLink(id: string) { activeLink = id; replaceSession(); }
export function clearClerkSession() {
  clerkProvider = null; clerkSessionId = ""; activeLink = ""; replaceSession();
}
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
  if (clerkProvider) return `clerk:${clerkSessionId}:${activeLink}`;
  if (process.env.NEXT_PUBLIC_AUTH_MODE === "clerk") return null;
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
  return { token: getToken(), role: getDemoRole(), version, signal: controller.signal, clerkProvider, link: activeLink };
}
