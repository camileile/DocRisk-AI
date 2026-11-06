// Integração inicial com a API F1. O token é fornecido pelo usuário em ambiente
// local de testes e permanece apenas na memória do React (nunca em storage).
export type ApiUser = {
  id: string;
  nome: string;
  org_id: string;
  org_tipo: "BERNHOEFT" | "FORNECEDORA" | "CONTRATANTE";
  papel: "ADMIN_BH" | "ANALISTA_BH" | "GESTOR_FORN" | "OPERADOR_FORN" | "GESTOR_CONTR";
};

export type ApiContract = {
  id: string;
  nome: string;
  contratante_id: string;
  fornecedora_id: string;
  bernhoeft_id: string;
  prazo_correcao_dias: number;
};

export type ApiBatchStatus =
  | "RECEBIDO"
  | "PROCESSANDO"
  | "CONCLUIDO"
  | "FALHA_PROCESSAMENTO";

export type ApiBatch = {
  id: number;
  contract_id: string;
  uploaded_by: string;
  filename: string;
  tipo_arquivo: string;
  status: ApiBatchStatus;
  total_pages: number;
  issue_id: number | null;
  erro: string | null;
  created_at: string;
  finished_at: string | null;
  sha256?: string;
};

export type ApiDocument = {
  id: number;
  batch_id: number;
  contract_id: string;
  tipo: string;
  worker_id: string | null;
  competencia: string | null;
  status: string;
  versao: number;
  motivos_pendencia: string[];
  motivos_revisao?: string[];
};

export class ApiRequestError extends Error {
  constructor(message: string, readonly status: number | null = null) {
    super(message);
    this.name = "ApiRequestError";
  }
}

const configuredUrl = process.env.NEXT_PUBLIC_DOCRISK_API_URL?.trim() ?? "";

export function apiIsConfigured(): boolean {
  return configuredUrl.length > 0;
}

function apiOrigin(): string {
  if (!configuredUrl) {
    throw new ApiRequestError("A URL da API não está configurada neste frontend.");
  }
  let url: URL;
  try {
    url = new URL(configuredUrl);
  } catch {
    throw new ApiRequestError("NEXT_PUBLIC_DOCRISK_API_URL não é uma URL válida.");
  }
  const local = url.hostname === "localhost" || url.hostname === "127.0.0.1" || url.hostname === "[::1]";
  if (url.username || url.password || url.search || url.hash || url.pathname !== "/" ||
      !(url.protocol === "https:" || (local && url.protocol === "http:"))) {
    throw new ApiRequestError("A API deve usar HTTPS ou HTTP local (localhost/127.0.0.1), sem credenciais ou caminhos na URL.");
  }
  return url.origin;
}

async function apiGet<T>(path: string, token: string, signal?: AbortSignal): Promise<T> {
  if (!token.trim()) throw new ApiRequestError("Informe o token de teste.");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort, { once: true });
  try {
    const response = await fetch(apiOrigin() + path, {
      method: "GET",
      cache: "no-store",
      headers: { Authorization: "Bearer " + token.trim(), Accept: "application/json" },
      signal: controller.signal,
    });
    if (!response.ok) {
      if (response.status === 401) {
        throw new ApiRequestError("Token inválido, expirado ou usuário inativo.", 401);
      }
      if (response.status === 403) {
        throw new ApiRequestError("O perfil não tem acesso a esta operação.", 403);
      }
      if (response.status === 404) {
        throw new ApiRequestError("Recurso não encontrado ou não autorizado.", 404);
      }
      // Não refletir mensagens HTML/stack traces do servidor para o usuário.
      throw new ApiRequestError("A API retornou o status " + response.status + ".", response.status);
    }
    return await response.json() as T;
  } catch (error) {
    if (error instanceof ApiRequestError) throw error;
    if (controller.signal.aborted && !signal?.aborted) {
      throw new ApiRequestError("A API não respondeu dentro do limite de 15 segundos.");
    }
    if (signal?.aborted) throw error;
    throw new ApiRequestError("Não foi possível conectar à API de testes. Confira o servidor, a URL e o CORS.");
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener("abort", abort);
  }
}

export async function identifyWithApi(token: string): Promise<{
  user: ApiUser;
  contracts: ApiContract[];
}> {
  // /api/me determina o papel real. Nunca atribuir um papel a partir do seletor da interface.
  const user = await apiGet<ApiUser>("/api/me", token);
  if (!user || typeof user.id !== "string" || typeof user.nome !== "string") {
    throw new ApiRequestError("Identidade recebida da API é inválida.");
  }
  if (user.papel !== "ANALISTA_BH" && user.papel !== "OPERADOR_FORN" && user.papel !== "GESTOR_FORN") {
    throw new ApiRequestError("Este perfil ainda não participa da integração F1. Use a demonstração para as demais perspectivas.");
  }
  const contracts = await apiGet<ApiContract[]>("/api/contracts", token);
  if (!Array.isArray(contracts) || contracts.some(c => typeof c.id !== "string" || typeof c.nome !== "string")) {
    throw new ApiRequestError("A lista de contratos recebida da API é inválida.");
  }
  return { user, contracts };
}

export function fetchApiBatches(token: string, signal?: AbortSignal) {
  return apiGet<ApiBatch[]>("/api/batches", token, signal).then((items) => {
    if (!Array.isArray(items)) throw new ApiRequestError("A lista de lotes recebida é inválida.");
    return items;
  });
}

export function fetchApiBatch(token: string, id: number, signal?: AbortSignal) {
  if (!Number.isSafeInteger(id) || id <= 0) throw new ApiRequestError("Identificador de lote inválido.");
  return apiGet<ApiBatch>("/api/batches/" + id, token, signal);
}

export function fetchApiBatchDocuments(token: string, id: number, signal?: AbortSignal) {
  if (!Number.isSafeInteger(id) || id <= 0) throw new ApiRequestError("Identificador de lote inválido.");
  return apiGet<ApiDocument[]>("/api/batches/" + id + "/documents", token, signal).then((items) => {
    if (!Array.isArray(items)) throw new ApiRequestError("A lista de documentos recebida é inválida.");
    return items;
  });
}

// O backend armazena datetime ISO sem fuso explícito. Não atribuir um fuso
// arbitrário (Recife/UTC); mostrar o horário registrado pelo servidor.
export function formatApiDate(value: string | null): string {
  if (!value) return "Não informado";
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  return match ? match[3] + "/" + match[2] + "/" + match[1] + " " + match[4] + ":" + match[5] : "Não informado";
}
