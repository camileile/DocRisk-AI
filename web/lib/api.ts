import { demoPageImage, demoRead, getDemoRole } from "./offline-demo";
/* Cliente da API DocRisk (FastAPI em api/). O token fica só em sessionStorage e
 * vai no cabeçalho Authorization; imagens de página são baixadas como blob. */

export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_DOCRISK_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

export type Papel = "ADMIN_BH" | "ANALISTA_BH" | "GESTOR_FORN" | "OPERADOR_FORN" | "GESTOR_CONTR";
export type OrgTipo = "BERNHOEFT" | "FORNECEDORA" | "CONTRATANTE";

export type Me = { id: string; nome: string; org_id: string; org_tipo: OrgTipo; papel: Papel };
export type DemoUser = Me & { role: Papel; token: string };
export type Contract = {
  id: string;
  nome: string;
  contratante_id: string;
  fornecedora_id: string;
  bernhoeft_id: string;
  prazo_correcao_dias: number;
};
export type BatchStatus = "RECEBIDO" | "PROCESSANDO" | "CONCLUIDO" | "FALHA_PROCESSAMENTO";
export type Batch = {
  id: number;
  contract_id: string;
  uploaded_by: string;
  filename: string;
  tipo_arquivo: string;
  status: BatchStatus;
  total_pages: number;
  issue_id: number | null;
  erro: string | null;
  created_at: string;
  finished_at: string | null;
};
export type DocStatus = "APTO" | "PENDENTE_CORRECAO" | "REVISAO_HUMANA" | "SUBSTITUIDO" | "EM_ANALISE";
export type PageRef = { page_id: number; ordem: number };
export type Campos = {
  horas_extras_h?: number | null;
  horas_extras_valor?: number | null;
  valor_liquido?: number | null;
  valor_pago?: number | null;
  data_pagamento?: string | null;
};
export type Doc = {
  id: number;
  batch_id: number;
  contract_id: string;
  tipo: string;
  worker_id: string | null;
  competencia: string | null;
  status: DocStatus;
  confianca?: number;
  motivos_pendencia: string[];
  motivos_revisao?: string[];
  campos: Campos;
  versao: number;
  substitui_id: number | null;
  revisado_por: string | null;
  created_at: string;
  updated_at: string;
  paginas: PageRef[];
};
export type DocDetail = Doc & {
  paginas_detalhe: { page_id: number; ordem: number; texto: string }[];
  versoes: { id: number; versao: number; status: DocStatus; batch_id: number; created_at: string }[];
};
export type IssueStatus = "ABERTA" | "NOTIFICADA" | "REENVIADA" | "RESOLVIDA" | "REABERTA";
export type Issue = {
  id: number;
  contract_id: string;
  document_id: number | null;
  worker_id: string | null;
  competencia: string | null;
  tipo_documento: string | null;
  categoria: string;
  motivo: string;
  evidencia: string | null;
  acao: string;
  status: IssueStatus;
  prazo: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  historico: { status: string; em: string; motivo?: string; lote?: number }[];
};
export type Analysis = {
  id: number;
  contract_id: string;
  worker_id: string;
  competencia: string;
  status: "AGUARDANDO_DOCUMENTOS" | "BLOQUEADA_PENDENCIA" | "REVISAO_HUMANA" | "ANALISADA";
  regra_versao: string;
  atual: number;
  created_at: string;
  resultado: {
    tipo: string;
    detalhe: string;
    horas_ponto: number | null;
    horas_folha: number | null;
    diferenca_h: number | null;
    motivos: string[];
    comprovante: { presente: boolean; doc_id: number | null; observacao: string };
  };
  insumos: { doc_id: number; tipo: string; versao: number; batch_id: number; status: string; paginas: number[] }[];
};
export type ReportItem = {
  trabalhador_id: string;
  situacao: string;
  resultado: string;
  detalhe: string;
  horas_ponto: number | null;
  horas_folha: number | null;
  diferenca_h: number | null;
  comprovante_presente: boolean;
  evidencias: { tipo: string; documento: number; versao: number; lote: number; paginas: number[] }[];
};
export type ReportContent = {
  contrato: { id: string; nome: string };
  contratante: string;
  fornecedora: string;
  competencia: string;
  gerado_em: string;
  regra: string;
  escopo: string;
  limitacoes: string[];
  resumo: Record<string, number>;
  itens: ReportItem[];
};
export type Report = {
  id: number;
  contract_id: string;
  competencia: string;
  versao: number;
  status: "RASCUNHO" | "EM_REVISAO" | "APROVADO_PUBLICADO" | "SUBSTITUIDO_POR_VERSAO";
  conteudo_json: ReportContent | Record<string, never>;
  observacoes?: string | null;
  autor_id?: string;
  created_at?: string;
  publicado_em: string | null;
};
export type AnalystOverviewData = {
  filtros: {
    contratantes: { id: string; nome: string }[];
    fornecedoras: { id: string; nome: string }[];
    contratos: { id: string; nome: string }[];
    competencias: string[];
    competencia_selecionada: string | null;
  };
  resumo: {
    cadastrados: number;
    avaliados: number;
    divergencias: number;
    taxa_divergencias: number | null;
    cobertura: number | null;
    horas_divergentes: number;
    divergencias_sem_horas: number;
    pendencias_criticas: number;
    pendencias_abertas: number;
  };
  evolucao: {
    competencia: string;
    avaliados: number;
    divergencias: number;
    taxa_divergencias: number | null;
    cobertura: number | null;
  }[];
  comparacao: {
    id: string;
    nome: string;
    avaliados: number;
    divergencias: number;
    taxa_divergencias: number | null;
    cobertura: number | null;
  }[];
  observacao: string;
};

export type Metrics = {
  documentos: {
    logicos: number;
    versoes: number;
    por_status: Record<string, number>;
    por_tipo: Record<string, number>;
    substituidos: number;
    taxa_revisao_humana: number | null;
  };
  conciliacao: {
    pares: number;
    aptos: number;
    bloqueados: number;
    em_revisao: number;
    divergencias_a_verificar: number;
    por_resultado: Record<string, number>;
    observacao: string;
  };
  pendencias: {
    total: number;
    em_aberto: number;
    resolvidas: number;
    por_categoria: Record<string, number>;
    tempo_medio_regularizacao_h: number | null;
  };
  lotes: { total: number; por_status: Record<string, number>; reenvios: number };
  paginas: { total: number; lidas: number; tempo_medio_ms: number | null };
  pareceres_publicados: number;
};
export type SearchHit = {
  page_id: number;
  contract_id: string;
  trecho: string;
  document_id: number | null;
  ordem: number;
  batch_id: number;
};
export type AuditEvent = {
  id: number;
  user_id: string | null;
  org_id: string | null;
  acao: string;
  alvo: string | null;
  resultado: string;
  instante: string;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

const TOKEN_KEY = "docrisk.token";

export function getToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* navegação privada: a sessão vale só enquanto a página estiver aberta */
  }
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) return "Dados inválidos na requisição.";
  } catch {
    /* corpo não é JSON */
  }
  return `Erro ${response.status}`;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const demoRole = getDemoRole();
  if (demoRole) {
    if ((init.method ?? "GET").toUpperCase() !== "GET")
      throw new ApiError(403, "Demonstração somente para consulta: nenhuma alteração foi enviada ao servidor.");
    return demoRead(path, demoRole) as T;
  }
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type"))
    headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, `Não foi possível conectar à API em ${API_URL}. Verifique se ela está em execução.`);
  }
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  return (await response.json()) as T;
}

export async function apiBlob(path: string): Promise<Blob> {
  if (getDemoRole()) {
    const match = path.match(/^\/api\/pages\/(\d+)\/image$/);
    if (!match) throw new ApiError(404, "Imagem indisponível na demonstração.");
    return demoPageImage(Number(match[1]));
  }
  const token = getToken();
  const response = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  return response.blob();
}

/* ------------------------------------------------------------------ rótulos */
export const roleLabels: Record<Papel, string> = {
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
  if (role === "GESTOR_CONTR") return "/contratante";
  if (role === "ADMIN_BH") return "/administracao";
  return "/painel";
}
