/* Dados exclusivamente fictícios para navegação pública sem backend.
 * Não são credenciais, não representam contratos reais e nunca autorizam ações. */
import type {
  Analysis, AuditEvent, Batch, Contract, Doc, DocDetail, Issue, Me,
  Metrics, Papel, Report, ReportContent, SearchHit,
} from "./api";

export const DEMO_ROLES: Papel[] = [
  "ADMIN_BH", "ANALISTA_BH", "GESTOR_FORN", "OPERADOR_FORN", "GESTOR_CONTR",
];

const KEY = "docrisk.offline-demo-role";

export function getDemoRole(): Papel | null {
  try {
    const value = sessionStorage.getItem(KEY);
    return DEMO_ROLES.find((role) => role === value) ?? null;
  } catch {
    return null;
  }
}

export function setDemoRole(role: Papel | null): void {
  try {
    if (role) sessionStorage.setItem(KEY, role);
    else sessionStorage.removeItem(KEY);
  } catch {
    /* A demonstração ainda funciona na aba atual sem persistência. */
  }
}

const USERS: Record<Papel, Me> = {
  ADMIN_BH: { id: "demo-admin", nome: "Administrador (fictício)", org_id: "demo-bh", org_tipo: "BERNHOEFT", papel: "ADMIN_BH" },
  ANALISTA_BH: { id: "demo-analista", nome: "Analista (fictício)", org_id: "demo-bh", org_tipo: "BERNHOEFT", papel: "ANALISTA_BH" },
  GESTOR_FORN: { id: "demo-gestor-forn", nome: "Gestor (fictício)", org_id: "demo-forn", org_tipo: "FORNECEDORA", papel: "GESTOR_FORN" },
  OPERADOR_FORN: { id: "demo-operador-forn", nome: "Operador (fictício)", org_id: "demo-forn", org_tipo: "FORNECEDORA", papel: "OPERADOR_FORN" },
  GESTOR_CONTR: { id: "demo-gestor-contr", nome: "Gestor (fictício)", org_id: "demo-contr", org_tipo: "CONTRATANTE", papel: "GESTOR_CONTR" },
};

export function demoUser(role: Papel): Me {
  return USERS[role];
}

export const DEMO_CONTRACTS: Contract[] = [
  { id: "demo-001", nome: "Contrato fictício · Unidade Alfa", contratante_id: "demo-contr", fornecedora_id: "demo-forn", bernhoeft_id: "demo-bh", prazo_correcao_dias: 5 },
];

const date = "2026-10-31T13:00:00Z";
const pages = (id: number, order: number) => [{ page_id: id, ordem: order }];

const BATCHES: Batch[] = [
  { id: 101, contract_id: "demo-001", uploaded_by: "demo-operador-forn", filename: "lote_ficticio_outubro.pdf", tipo_arquivo: "PDF", status: "CONCLUIDO", total_pages: 6, issue_id: null, erro: null, created_at: date, finished_at: "2026-10-31T13:02:00Z" },
];

const DOCS: Doc[] = [
  { id: 201, batch_id: 101, contract_id: "demo-001", tipo: "ESPELHO_PONTO", worker_id: "T001", competencia: "10/2026", status: "APTO", confianca: 0.98, motivos_pendencia: [], motivos_revisao: [], campos: { horas_extras_h: 12 }, versao: 1, substitui_id: null, revisado_por: null, created_at: date, updated_at: date, paginas: pages(1001, 1) },
  { id: 202, batch_id: 101, contract_id: "demo-001", tipo: "HOLERITE", worker_id: "T001", competencia: "10/2026", status: "APTO", confianca: 0.97, motivos_pendencia: [], motivos_revisao: [], campos: { horas_extras_h: 8, horas_extras_valor: 160 }, versao: 1, substitui_id: null, revisado_por: null, created_at: date, updated_at: date, paginas: pages(1002, 2) },
  { id: 203, batch_id: 101, contract_id: "demo-001", tipo: "HOLERITE", worker_id: "T002", competencia: "10/2026", status: "PENDENTE_CORRECAO", confianca: 0.4, motivos_pendencia: ["Arquivo parcialmente ilegível"], motivos_revisao: [], campos: {}, versao: 1, substitui_id: null, revisado_por: null, created_at: date, updated_at: date, paginas: pages(1003, 3) },
  { id: 204, batch_id: 101, contract_id: "demo-001", tipo: "DESCONHECIDO", worker_id: "T003", competencia: "10/2026", status: "REVISAO_HUMANA", confianca: 0.55, motivos_pendencia: [], motivos_revisao: ["Classificação abaixo do limiar de confiança"], campos: { horas_extras_h: 3 }, versao: 1, substitui_id: null, revisado_por: null, created_at: date, updated_at: date, paginas: pages(1004, 4) },
  { id: 205, batch_id: 101, contract_id: "demo-001", tipo: "ESPELHO_PONTO", worker_id: "T004", competencia: "10/2026", status: "APTO", confianca: 0.99, motivos_pendencia: [], motivos_revisao: [], campos: { horas_extras_h: 5 }, versao: 1, substitui_id: null, revisado_por: null, created_at: date, updated_at: date, paginas: pages(1005, 5) },
  { id: 206, batch_id: 101, contract_id: "demo-001", tipo: "HOLERITE", worker_id: "T004", competencia: "10/2026", status: "APTO", confianca: 0.99, motivos_pendencia: [], motivos_revisao: [], campos: { horas_extras_h: 5, horas_extras_valor: 100 }, versao: 1, substitui_id: null, revisado_por: null, created_at: date, updated_at: date, paginas: pages(1006, 6) },
];

const ISSUES: Issue[] = [
  { id: 401, contract_id: "demo-001", document_id: 203, worker_id: "T002", competencia: "10/2026", tipo_documento: "HOLERITE", categoria: "ILEGIVEL", motivo: "Página ilegível no arquivo de demonstração.", evidencia: "Lote #101 · página 3 (fictícia)", acao: "Reenviar um holerite legível.", status: "ABERTA", prazo: "2026-11-10", created_at: date, updated_at: date, resolved_at: null, historico: [{ status: "ABERTA", em: date }] },
];

const analysis = (id: number, worker: string, status: Analysis["status"], tipo: string, hp: number | null, hf: number | null, detail: string, insumos: number[]): Analysis => ({
  id, contract_id: "demo-001", worker_id: worker, competencia: "10/2026", status,
  regra_versao: "demo-1", atual: 1, created_at: date,
  resultado: {
    tipo, detalhe: detail, horas_ponto: hp, horas_folha: hf,
    diferenca_h: hp == null || hf == null ? null : hp - hf,
    motivos: [], comprovante: { presente: false, doc_id: null, observacao: "Comprovante não incluído nesta amostra fictícia." },
  },
  insumos: insumos.map((id) => {
    const doc = DOCS.find((d) => d.id === id)!;
    return { doc_id: doc.id, tipo: doc.tipo, versao: doc.versao, batch_id: doc.batch_id, status: doc.status, paginas: doc.paginas.map((p) => p.ordem) };
  }),
});

const ANALYSES: Analysis[] = [
  analysis(501, "T001", "ANALISADA", "DIVERGENCIA_A_VERIFICAR", 12, 8, "Diferença fictícia de 4 h a conferir entre ponto e holerite.", [201, 202]),
  analysis(502, "T002", "BLOQUEADA_PENDENCIA", "NAO_AVALIADO", null, null, "Análise bloqueada: holerite ilegível.", [203]),
  analysis(503, "T003", "REVISAO_HUMANA", "NAO_AVALIADO", 3, null, "Classificação documental depende de revisão.", [204]),
  analysis(504, "T004", "ANALISADA", "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS", 5, 5, "Sem divergência nas horas extras informadas.", [205, 206]),
];

const REPORT_CONTENT: ReportContent = {
  contrato: { id: "demo-001", nome: DEMO_CONTRACTS[0].nome },
  contratante: "Contratante Fictícia Alfa", fornecedora: "Fornecedora Fictícia Beta",
  competencia: "10/2026", gerado_em: date, regra: "demo-1",
  escopo: "EXEMPLO FICTÍCIO — comparação ilustrativa de horas extras em ponto e holerite.",
  limitacoes: ["Documento inteiramente fictício; não constitui parecer profissional nem atesta conformidade.", "Comprovantes e documentos de suporte não integram esta amostra."],
  resumo: { trabalhadores: 4, avaliados: 2, com_divergencia: 1, dados_insuficientes: 0, sem_divergencia: 1, bloqueados: 1, em_revisao: 1, aguardando_documentos: 0 },
  itens: ANALYSES.map((a) => ({
    trabalhador_id: a.worker_id, situacao: a.status, resultado: a.resultado.tipo,
    detalhe: a.resultado.detalhe, horas_ponto: a.resultado.horas_ponto,
    horas_folha: a.resultado.horas_folha, diferenca_h: a.resultado.diferenca_h,
    comprovante_presente: false,
    evidencias: a.insumos.map((i) => ({ tipo: i.tipo, documento: i.doc_id, versao: i.versao, lote: i.batch_id, paginas: i.paginas })),
  })),
};

const REPORTS: Report[] = [
  { id: 601, contract_id: "demo-001", competencia: "10/2026", versao: 1, status: "APROVADO_PUBLICADO", conteudo_json: REPORT_CONTENT, observacoes: "Parecer de exemplo fictício.", autor_id: "demo-analista", created_at: date, publicado_em: "2026-11-01T15:00:00Z" },
];

const METRICS: Metrics = {
  documentos: { logicos: 6, versoes: 6, por_status: { APTO: 4, PENDENTE_CORRECAO: 1, REVISAO_HUMANA: 1 }, por_tipo: { ESPELHO_PONTO: 2, HOLERITE: 3, DESCONHECIDO: 1 }, substituidos: 0, taxa_revisao_humana: 1 / 6 },
  conciliacao: { pares: 4, aptos: 2, bloqueados: 1, em_revisao: 1, divergencias_a_verificar: 1, por_resultado: { DIVERGENCIA_A_VERIFICAR: 1, SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS: 1 }, observacao: "Indicadores ilustrativos, gerados exclusivamente para demonstração." },
  pendencias: { total: 1, em_aberto: 1, resolvidas: 0, por_categoria: { ILEGIVEL: 1 }, tempo_medio_regularizacao_h: null },
  lotes: { total: 1, por_status: { CONCLUIDO: 1 }, reenvios: 0 },
  paginas: { total: 6, lidas: 6, tempo_medio_ms: 120 }, pareceres_publicados: 1,
};

const AUDIT: AuditEvent[] = [
  { id: 701, user_id: "demo-operador-forn", org_id: "demo-forn", acao: "LOTE_ENVIADO", alvo: "lote #101", resultado: "OK", instante: date },
  { id: 702, user_id: "demo-analista", org_id: "demo-bh", acao: "PARECER_PUBLICADO", alvo: "parecer #601", resultado: "OK", instante: "2026-11-01T15:00:00Z" },
];

export function demoRead(path: string, role: Papel): unknown {
  const url = new URL(path, "https://demo.invalid");
  const route = url.pathname;
  if (route === "/api/me") return USERS[role];
  if (route === "/api/contracts") return DEMO_CONTRACTS;
  if (route === "/api/bernhoeft/metrics" && (role === "ADMIN_BH" || role === "ANALISTA_BH")) return METRICS;
  if (route === "/api/audit" && role === "ADMIN_BH") return AUDIT;
  if (role === "GESTOR_CONTR") {
    if (route === "/api/client/reports") return REPORTS;
    throw new Error("A contratante acessa apenas pareceres publicados.");
  }
  if (role === "ADMIN_BH") throw new Error("O administrador acessa somente a área administrativa nesta demonstração.");
  if (route === "/api/batches") return BATCHES;
  if (route === "/api/supplier/issues" && (role === "GESTOR_FORN" || role === "OPERADOR_FORN")) return ISSUES;
  if (route === "/api/issues" && role === "ANALISTA_BH") return ISSUES;
  if (route === "/api/documents") {
    return DOCS.filter((d) =>
      (!url.searchParams.get("tipo") || d.tipo === url.searchParams.get("tipo")) &&
      (!url.searchParams.get("status") || d.status === url.searchParams.get("status"))
    );
  }
  if (route === "/api/search") {
    const q = (url.searchParams.get("q") ?? "").toLowerCase();
    const hits: SearchHit[] = DOCS.filter((d) => q && (
      d.worker_id?.toLowerCase().includes(q) ||
      d.tipo.toLowerCase().includes(q) ||
      "horas extras fictícias documento".includes(q)
    )).map((d) => ({
      page_id: d.paginas[0].page_id, contract_id: d.contract_id,
      trecho: "Documento fictício de " + d.worker_id + " — horas extras em 10/2026.",
      document_id: d.id, ordem: d.paginas[0].ordem, batch_id: d.batch_id,
    }));
    return hits;
  }
  const batchDocs = route.match(/^\/api\/batches\/(\d+)\/documents$/);
  if (batchDocs) return Number(batchDocs[1]) === 101 ? DOCS : [];
  const batch = route.match(/^\/api\/batches\/(\d+)$/);
  if (batch) {
    const found = BATCHES.find((b) => b.id === Number(batch[1]));
    if (found) return found;
  }
  const doc = route.match(/^\/api\/documents\/(\d+)$/);
  if (doc) {
    const d = DOCS.find((item) => item.id === Number(doc[1]));
    if (d) {
      const detail: DocDetail = {
        ...d,
        paginas_detalhe: d.paginas.map((p) => ({ ...p, texto: "EXEMPLO FICTÍCIO — " + d.tipo + ", trabalhador " + (d.worker_id ?? "não identificado") + ", competência " + (d.competencia ?? "não informada") })),
        versoes: [{ id: d.id, versao: d.versao, status: d.status, batch_id: d.batch_id, created_at: d.created_at }],
      };
      return detail;
    }
  }
  if (route === "/api/review-queue" && role === "ANALISTA_BH") return DOCS.filter((d) => d.status === "REVISAO_HUMANA");
  if (route === "/api/analyses" && role === "ANALISTA_BH") return ANALYSES;
  if (route === "/api/reports" && role === "ANALISTA_BH") return REPORTS;
  if (/^\/api\/reports\/\d+\/preview$/.test(route) && role === "ANALISTA_BH") return REPORTS.find((r) => r.id === Number(route.split("/")[3]));
  if (/^\/api\/contracts\/[^/]+\/workers$/.test(route) && role === "ANALISTA_BH") return [
    { id: "T001", nome: "Pessoa fictícia 001" },
    { id: "T002", nome: "Pessoa fictícia 002" },
    { id: "T003", nome: "Pessoa fictícia 003" },
    { id: "T004", nome: "Pessoa fictícia 004" },
  ];
  throw new Error("Este recurso não está disponível na demonstração offline.");
}

export function demoPageImage(pageId: number): Blob {
  const id = Number.isFinite(pageId) ? String(pageId) : "—";
  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="780" viewBox="0 0 600 780">' +
    '<rect width="600" height="780" fill="#fafafa"/><rect x="40" y="40" width="520" height="700" rx="8" fill="#ffffff" stroke="#d4d4e0"/>' +
    '<text x="75" y="110" fill="#5545aa" font-size="20" font-family="sans-serif">DOCRISK AI • DEMONSTRAÇÃO</text>' +
    '<text x="75" y="165" fill="#222244" font-size="28" font-family="sans-serif">Documento fictício</text>' +
    '<text x="75" y="205" fill="#666688" font-size="18" font-family="sans-serif">Página de exemplo ' + id + '</text>' +
    '<path d="M75 260H520 M75 307H520 M75 354H480 M75 401H520 M75 448H450" stroke="#dddde9" stroke-width="13"/>' +
    '<text x="75" y="690" fill="#888899" font-size="16" font-family="sans-serif">Sem dados reais • Imagem ilustrativa</text></svg>';
  return new Blob([svg], { type: "image/svg+xml" });
}
