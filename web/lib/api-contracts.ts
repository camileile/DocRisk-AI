/* Contratos compartilhados pelo frontend; permissões continuam no backend. */
export type Papel = "ADMIN_PLATAFORMA" | "ADMIN_BH" | "ANALISTA_BH" | "GESTOR_FORN" | "OPERADOR_FORN" | "GESTOR_CONTR";
export type OrgTipo = "PLATAFORMA" | "BERNHOEFT" | "FORNECEDORA" | "CONTRATANTE";

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
  aej?: { origem: "AEJ"; worker_link_id: string; calculation_status: string; p7s_validated: false };
};
export type DocDetail = Doc & {
  paginas_detalhe: { page_id: number; ordem: number; texto: string }[];
  versoes: { id: number; versao: number; status: DocStatus; batch_id: number; created_at: string }[];
  aej?: {
    worker_link_id: string;
    worker_id: string | null;
    competencia: string;
    calculation_status: string;
    hours: number | null;
    method: string;
    warnings: string[];
    validation_warnings: string[];
    p7s_validated: false;
    days: {
      date: string;
      schedule_code: string | null;
      schedule_line?: number | null;
      contract_minutes: number | null;
      worked_minutes: number | null;
      observed_daily_excess_minutes: number | null;
      source_lines: number[];
      markings: { line_number: number; at: string; type: string; sequence: string; source: string }[];
      excluded_markings: { line_number: number; at: string; type: string; sequence: string; source: string }[];
    }[];
  };
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
  evidencias: {
    tipo: string; documento: number; versao: number; lote: number; paginas: number[];
    origem?: string; vinculo_aej?: string; linhas_origem?: number[];
  }[];
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
export type AdminCompany = {
  id: string;
  nome: string;
  tipo: "CONTRATANTE" | "FORNECEDORA";
  cnpj: string | null;
};
export type AdminContract = Contract & {
  contratante_nome: string;
  fornecedora_nome: string;
  inicio: string | null;
  fim: string | null;
  status: "ATIVO" | "ENCERRADO";
};
export type AdminUser = {
  id: string;
  nome: string;
  org_id: string;
  org_nome: string;
  papel: "ADMIN_BH" | "ANALISTA_BH" | "GESTOR_CONTR" | "GESTOR_FORN";
  ativo: number;
};
export type AdminRegistry = {
  empresas: AdminCompany[];
  contratos: AdminContract[];
  usuarios: AdminUser[];
};
export type AdminOverview = {
  contratantes: number;
  fornecedoras: number;
  contratos_ativos: number;
  contratos_vencendo_30d: number;
  contratos_sem_prazo: number;
  operacao: Metrics;
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

