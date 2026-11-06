import { demoPageImage, demoRead } from "./offline-demo";
import { getDemoRole } from "./api-session";
import { ApiError, request, type ApiRequestInit } from "./api-transport";
import type { Papel, DocStatus, BatchStatus, IssueStatus, Report, PageRef } from "./api-contracts";

export * from "./api-contracts";
export { getToken, setToken } from "./api-session";
export { API_URL, ApiError } from "./api-transport";

/* A demo nunca delega ao transporte conectado, mesmo com storage bloqueado. */
export async function api<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  if (init.signal?.aborted) throw new ApiError(0, "Requisição cancelada.", "cancelled");
  const role = getDemoRole();
  if (role) {
    if (init.expectedToken !== undefined || (init.method ?? "GET").toUpperCase() !== "GET")
      throw new ApiError(403, "Demonstração somente para consulta: nenhuma alteração foi enviada ao servidor.");
    try {
      return demoRead(path, role) as T;
    } catch (error) {
      throw new ApiError(403, error instanceof Error ? error.message : "Recurso indisponível na demonstração.");
    }
  }
  return request(path, init, response => response.json() as Promise<T>);
}

export async function apiBlob(path: string, init: ApiRequestInit = {}): Promise<Blob> {
  if (init.signal?.aborted) throw new ApiError(0, "Requisição cancelada.", "cancelled");
  if (getDemoRole()) {
    if (init.expectedToken !== undefined || (init.method ?? "GET").toUpperCase() !== "GET")
      throw new ApiError(403, "Demonstração somente para consulta.");
    const match = path.match(/^\/api\/pages\/(\d+)\/image$/);
    if (!match) throw new ApiError(404, "Imagem indisponível na demonstração.");
    return demoPageImage(Number(match[1]));
  }
  return request(path, init, response => response.blob());
}

export async function downloadBatchSource(batchId: number, init: ApiRequestInit = {}): Promise<void> {
  if (getDemoRole()) throw new ApiError(403, "Arquivos originais não estão disponíveis na demonstração.");
  if (!Number.isSafeInteger(batchId) || batchId <= 0) throw new ApiError(0, "Identificador de lote inválido.", "validation");
  const file = await request(`/api/batches/${batchId}/source`, init, async response => ({
    blob: await response.blob(),
    disposition: response.headers.get("content-disposition") ?? "",
  }));
  const filename = file.disposition.match(/filename="?([^";]+)"?/i)?.[1] ?? `lote-${batchId}-original.aej`;
  const url = URL.createObjectURL(file.blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function downloadReportPdf(id: number, version: number, previewHash?: string): Promise<void> {
  if (getDemoRole()) throw new ApiError(403, "Exportar PDF exige um ambiente operacional.");
  if (!Number.isSafeInteger(id) || id <= 0 || !Number.isSafeInteger(version) || version <= 0)
    throw new ApiError(0, "Parecer inválido.", "validation");
  const query = previewHash ? "?conteudo_sha256=" + encodeURIComponent(previewHash) : "";
  const blob = await apiBlob(`/api/reports/${id}/pdf${query}`);
  if (blob.type.split(";")[0] !== "application/pdf") throw new ApiError(0, "O servidor não retornou um PDF válido.", "invalid_response");
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = `parecer-${id}-v${version}${previewHash ? "-previa" : ""}.pdf`;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/* ------------------------------------------------------------------ rótulos */
export const roleLabels: Record<Papel, string> = {
  ADMIN_PLATAFORMA: "Administrador geral da plataforma",
  ADMIN_BH: "Administrador Bernhoeft",
  ANALISTA_BH: "Analista Bernhoeft",
  GESTOR_FORN: "Gestor da fornecedora",
  OPERADOR_FORN: "Operador da fornecedora",
  GESTOR_CONTR: "Gestor da contratante",
};
export const typeLabels: Record<string, string> = {
  ESPELHO_PONTO: "Espelho de ponto",
  HOLERITE: "Holerite",
  COMPROVANTE_PAGAMENTO: "Comprovante de pagamento",
  CONTRATO: "Contrato",
  DOCUMENTO_IDENTIFICACAO: "Documento de identificação",
  NOTA_FISCAL: "Nota fiscal",
  OUTRO: "Outro",
  DESCONHECIDO: "Não identificado",
};
export const docStatusLabels: Record<DocStatus, string> = {
  APTO: "Apto",
  PENDENTE_CORRECAO: "Pendente de correção",
  REVISAO_HUMANA: "Revisão humana",
  SUBSTITUIDO: "Substituído",
  EM_ANALISE: "Em análise",
};
export const batchStatusLabels: Record<BatchStatus, string> = {
  RECEBIDO: "Recebido",
  PROCESSANDO: "Processando",
  CONCLUIDO: "Concluído",
  FALHA_PROCESSAMENTO: "Falha técnica",
};
export const issueStatusLabels: Record<IssueStatus, string> = {
  ABERTA: "Aberta",
  NOTIFICADA: "Notificada",
  REENVIADA: "Reenviada",
  RESOLVIDA: "Resolvida",
  REABERTA: "Reaberta",
};
export const issueCategoryLabels: Record<string, string> = {
  ILEGIVEL: "Página ilegível",
  PAGINA_FALTANTE: "Página faltante",
  DOCUMENTO_AUSENTE: "Documento ausente",
  ARQUIVO_INVALIDO: "Arquivo inválido",
  SOLICITADA_NA_REVISAO: "Correção solicitada na revisão",
};
export const analysisStatusLabels: Record<string, string> = {
  AGUARDANDO_DOCUMENTOS: "Aguardando documentos",
  BLOQUEADA_PENDENCIA: "Bloqueada por pendência",
  REVISAO_HUMANA: "Em revisão humana",
  ANALISADA: "Analisada",
};
export const resultLabels: Record<string, string> = {
  NAO_AVALIADO: "Não avaliado",
  DADOS_INSUFICIENTES: "Dados insuficientes",
  DIVERGENCIA_A_VERIFICAR: "Divergência a verificar",
  SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS: "Sem divergência nos campos comparados",
};
export const reportStatusLabels: Record<Report["status"], string> = {
  RASCUNHO: "Rascunho",
  EM_REVISAO: "Em revisão",
  APROVADO_PUBLICADO: "Publicado",
  SUBSTITUIDO_POR_VERSAO: "Substituído por nova versão",
};

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function formatHours(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} h`;
}

export function pageList(pages: PageRef[] | number[]): string {
  const ordens = pages.map((p) => (typeof p === "number" ? p : p.ordem));
  if (!ordens.length) return "—";
  return ordens.length > 1 ? `p. ${ordens[0]}–${ordens[ordens.length - 1]}` : `p. ${ordens[0]}`;
}

export function homeFor(role: Papel): string {
  if (role === "ADMIN_PLATAFORMA") return "/plataforma";
  if (role === "GESTOR_CONTR") return "/contratante";
  if (role === "ADMIN_BH") return "/administracao";
  return "/painel";
}
