import { clerkEnabled, publicDemoOnly } from "./auth-mode";
import { API_URL } from "./api-transport";
import type { Papel } from "./api-contracts";

export const demoApiEnabled = !publicDemoOnly && !clerkEnabled && process.env.NEXT_PUBLIC_DEMO_API_ENABLED === "1";

/** Bootstrap somente da API demo local. A sessão e os contratos são validados pelo login normal. */
export async function demoApiToken(role: Papel): Promise<string> {
  if (!demoApiEnabled) throw new Error("A conexão da demo com a API não está habilitada.");
  const url = new URL(API_URL);
  if (!["localhost", "127.0.0.1", "[::1]"].includes(url.hostname) ||
      !["http:", "https:"].includes(url.protocol) || url.username || url.password ||
      url.pathname !== "/" || url.search || url.hash) {
    throw new Error("Configure a API da demonstração em localhost ou 127.0.0.1.");
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(`${url.origin}/api/demo/users`, {
      signal: controller.signal, cache: "no-store", credentials: "omit", redirect: "error",
    });
    if (!response.ok) throw new Error("Inicie a API local com DOCRISK_AUTH_MODE=token e DOCRISK_DEMO_MODE=1.");
    const users: unknown = await response.json();
    if (!Array.isArray(users)) throw new Error("A API não retornou os perfis de demonstração.");
    const user = users.find(item => item && item.role === role && typeof item.token === "string" && item.token.trim());
    if (!user) throw new Error("O perfil escolhido não está disponível na API local.");
    return user.token;
  } finally {
    clearTimeout(timeout);
  }
}
