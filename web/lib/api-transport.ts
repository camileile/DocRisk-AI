import { captureSession } from "./api-session";

export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_DOCRISK_API_URL || "http://127.0.0.1:8000"
).trim().replace(/\/$/, "");

export type ApiErrorKind = "http" | "network" | "timeout" | "cancelled" | "session" | "validation" | "invalid_response";
export class ApiError extends Error {
  constructor(public status: number, message: string, public kind: ApiErrorKind = "http") {
    super(message);
    this.name = "ApiError";
  }
  get retryable(): boolean {
    return this.kind === "network" || this.kind === "timeout" || (this.kind === "http" && this.status >= 500);
  }
}
export type ApiRequestInit = RequestInit & {
  timeoutMs?: number;
  /** Uma operação iniciada com um token antigo não pode usar outra sessão. */
  expectedToken?: string;
};

function endpoint(path: string): string {
  let origin: URL;
  try { origin = new URL(API_URL); } catch {
    throw new ApiError(0, "A URL da API configurada não é válida.", "validation");
  }
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(origin.hostname);
  if (origin.username || origin.password || origin.search || origin.hash || origin.pathname !== "/" ||
      !(origin.protocol === "https:" || (local && origin.protocol === "http:"))) {
    throw new ApiError(0, "A API deve usar HTTPS ou HTTP local, sem credenciais ou caminhos na URL.", "validation");
  }
  if (!path.startsWith("/api/") || /[\\#\r\n]/.test(path) ||
      new URL(path, origin).pathname !== path.split("?")[0]) {
    throw new ApiError(0, "Caminho da API inválido.", "validation");
  }
  return origin.origin + path;
}

/* As mensagens `detail` do backend são escritas para o usuário ("Somente rascunhos podem ser
 * publicados", motivo de arquivo recusado…). Só são exibidas quando são texto curto e simples;
 * HTML, várias linhas, rastros de erro ou listas de validação caem na mensagem controlada. */
async function apiDetail(response: Response): Promise<string | null> {
  try {
    if (!(response.headers.get("Content-Type") ?? "").includes("application/json")) return null;
    const detail = (await response.json())?.detail;
    if (typeof detail !== "string") return null;
    const text = detail.trim();
    if (!text || text.length > 300 || /[<>\r\n]/.test(text) || /traceback|exception/i.test(text)) return null;
    return text;
  } catch {
    return null;
  }
}

function httpError(status: number, detail: string | null = null): ApiError {
  if (detail) return new ApiError(status, detail);
  const messages: Record<number, string> = {
    401: "Token inválido, expirado ou usuário inativo.",
    403: "O perfil não tem acesso a esta operação.",
    404: "Recurso não encontrado ou não autorizado.",
    409: "A operação conflita com o estado atual. Atualize os dados antes de tentar novamente.",
    413: "O servidor recusou o tamanho do arquivo.",
    422: "A API rejeitou os dados enviados. Confira os campos e o arquivo.",
  };
  // Mensagens controladas: não apresentar HTML, dados internos ou stack traces.
  return new ApiError(status, messages[status] ?? `A API retornou o status ${status}.`);
}

/** Único ponto de rede: inclui a leitura do corpo no timeout e no vínculo de sessão. */
export async function request<T>(
  path: string, options: ApiRequestInit, consume: (response: Response) => Promise<T>,
): Promise<T> {
  const session = captureSession();
  if (session.role || !session.token ||
      (options.expectedToken !== undefined && options.expectedToken.trim() !== session.token)) {
    throw new ApiError(401, "Conecte uma sessão de testes para usar a API.", "session");
  }
  if (options.signal?.aborted) throw new ApiError(0, "Requisição cancelada.", "cancelled");
  const { timeoutMs = 15000, expectedToken: _expectedToken, signal, ...init } = options;
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0)
    throw new ApiError(0, "Limite de espera inválido.", "validation");
  const url = endpoint(path);
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${session.token}`);
  headers.set("Accept", "application/json");
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type"))
    headers.set("Content-Type", "application/json");
  // O navegador define o boundary de multipart; consumidores não podem sobrescrevê-lo.
  if (init.body instanceof FormData) headers.delete("Content-Type");
  const mutation = !["GET", "HEAD"].includes((init.method ?? "GET").toUpperCase());
  const controller = new AbortController();
  let timedOut = false;
  const check = () => {
    if (session.signal.aborted) throw new ApiError(0, mutation
      ? "A sessão mudou. Consulte o resultado antes de repetir a operação."
      : "A sessão mudou. Consulte novamente com o perfil atual.", "session");
    if (signal?.aborted) throw new ApiError(0, mutation
      ? "Operação cancelada sem confirmação. Consulte o resultado antes de repetir."
      : "Requisição cancelada.", "cancelled");
    if (timedOut) throw new ApiError(0, mutation
      ? "O tempo da operação terminou sem confirmação. Consulte o resultado ou a lista de lotes antes de reenviar."
      : "A API não respondeu dentro do limite de espera.", "timeout");
  };
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort, { once: true });
  session.signal.addEventListener("abort", abort, { once: true });
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
  try {
    const response = await fetch(url, {
      ...init, headers, cache: "no-store", redirect: "error", signal: controller.signal,
    });
    check();
    if (!response.ok) {
      const detail = await apiDetail(response);
      check();
      throw httpError(response.status, detail);
    }
    let result: T;
    try { result = await consume(response); } catch (error) {
      check();
      if (error instanceof SyntaxError) throw new ApiError(response.status, mutation
        ? "Resposta inválida da API. Consulte o resultado antes de repetir a operação."
        : "A API retornou uma resposta inválida.", "invalid_response");
      throw error;
    }
    check();
    return result;
  } catch (error) {
    check();
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, mutation
      ? "Não foi possível confirmar a operação. Verifique a conexão e consulte o resultado antes de repetir."
      : "Não foi possível conectar à API de testes. Confira o servidor, a URL e o CORS.", "network");
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", abort);
    session.signal.removeEventListener("abort", abort);
  }
}
