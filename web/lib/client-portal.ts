import type { Report } from "./api";

export type ClientSummary = {
  trabalhadores: number;
  analisados: number;
  divergencias: number;
  dados_insuficientes: number;
  nao_avaliados: number;
  taxa_divergencias: number | null;
  cobertura: number | null;
};
export type ClientOverview = {
  filtros: {
    fornecedoras: { id: string; nome: string }[];
    contratos: { id: string; nome: string }[];
    competencias: string[];
    competencia_selecionada: string | null;
  };
  resumo: ClientSummary & { contratos: number; contratos_com_parecer: number };
  contratos: {
    id: string; nome: string; fornecedora_id: string; fornecedora_nome: string;
    parecer_id: number | null; versao: number | null; publicado_em: string | null;
    resumo: ClientSummary | null;
  }[];
  observacao: string;
};

// Mesmas contas do backend, exclusivamente sobre snapshots fictícios publicados.
export function demoClientPortal(url: URL, reports: Report[], view: "overview" | "reports"): ClientOverview | Report[] {
  const scope = [
    { id: "demo-001", nome: "Contrato fictício · Unidade Alfa", fornecedora_id: "demo-forn", fornecedora_nome: "Fornecedora Fictícia Beta" },
    { id: "demo-002", nome: "Contrato fictício · Unidade Gama", fornecedora_id: "demo-gama", fornecedora_nome: "Fornecedora Fictícia Gama" },
  ];
  const supplier = url.searchParams.get("fornecedora_id");
  const contract = url.searchParams.get("contract_id");
  const supplierScope = scope.filter((c) => !supplier || c.fornecedora_id === supplier);
  const selected = supplierScope.filter((c) => !contract || c.id === contract);
  const available = reports.filter((r) => selected.some((c) => c.id === r.contract_id));
  const months = [...new Set(available.map((r) => r.competencia))].sort((a, b) => (b.slice(3) + b.slice(0, 2)).localeCompare(a.slice(3) + a.slice(0, 2)));
  const month = url.searchParams.get("competencia") || months[0] || null;
  if (view === "reports") return available.filter((r) => !url.searchParams.get("competencia") || r.competencia === month);
  const current = available.filter((r) => r.competencia === month);
  const rows = selected.map((c) => {
    const report = current.find((r) => r.contract_id === c.id);
    const s = report?.conteudo_json.resumo;
    const valid = (s?.com_divergencia ?? 0) + (s?.sem_divergencia ?? 0);
    const summary: ClientSummary | null = s ? {
      trabalhadores: s.trabalhadores, analisados: valid, divergencias: s.com_divergencia,
      dados_insuficientes: s.dados_insuficientes,
      nao_avaliados: s.bloqueados + s.em_revisao + s.aguardando_documentos,
      taxa_divergencias: valid ? s.com_divergencia / valid : null,
      cobertura: s.trabalhadores ? valid / s.trabalhadores : null,
    } : null;
    return { ...c, parecer_id: report?.id ?? null, versao: report?.versao ?? null, publicado_em: report?.publicado_em ?? null, resumo: summary };
  });
  const total = rows.reduce((s, c) => ({
    trabalhadores: s.trabalhadores + (c.resumo?.trabalhadores ?? 0),
    analisados: s.analisados + (c.resumo?.analisados ?? 0),
    divergencias: s.divergencias + (c.resumo?.divergencias ?? 0),
    dados_insuficientes: s.dados_insuficientes + (c.resumo?.dados_insuficientes ?? 0),
    nao_avaliados: s.nao_avaliados + (c.resumo?.nao_avaliados ?? 0),
  }), { trabalhadores: 0, analisados: 0, divergencias: 0, dados_insuficientes: 0, nao_avaliados: 0 });
  return {
    filtros: {
      fornecedoras: scope.map((c) => ({ id: c.fornecedora_id, nome: c.fornecedora_nome })),
      contratos: supplierScope.map((c) => ({ id: c.id, nome: c.nome })),
      competencias: months, competencia_selecionada: month,
    },
    resumo: { ...total, contratos: selected.length, contratos_com_parecer: current.length,
      taxa_divergencias: total.analisados ? total.divergencias / total.analisados : null,
      cobertura: total.trabalhadores ? total.analisados / total.trabalhadores : null },
    contratos: rows,
    observacao: "Dados fictícios dos pareceres publicados. Trabalhadores são contados por vínculo contratual. Taxa = divergências / comparações válidas; cobertura = comparações válidas / vínculos nos pareceres. Dados insuficientes e contratos sem parecer não atestam regularidade. Divergências são indícios a conferir, não irregularidades comprovadas.",
  };
}
