export type DemoRole = "ANALISTA_BH" | "OPERADOR_FORN";
export type DocumentStatus = "APTO" | "PENDENTE_CORRECAO" | "REVISAO_HUMANA";
export type IssueStatus = "ABERTA" | "REENVIADA" | "RESOLVIDA";
export const contracts = [
  { id: "CTR-001", name: "Contrato Alfa", supplier: "Fornecedora Alfa (demo)" },
  { id: "CTR-002", name: "Contrato Beta", supplier: "Fornecedora Beta (demo)" },
];
export const documents: {
  id: string;
  contract: string;
  worker: string;
  type: string;
  competence: string;
  batch: string;
  status: DocumentStatus;
  page: number;
  note: string;
}[] = [
  {
    id: "DOC-001",
    contract: "CTR-001",
    worker: "Pessoa exemplo 001",
    type: "Espelho de ponto",
    competence: "10/2026",
    batch: "LOTE-001",
    status: "APTO",
    page: 1,
    note: "Documento sintético de jornada, associado à competência informada.",
  },
  {
    id: "DOC-002",
    contract: "CTR-001",
    worker: "Pessoa exemplo 001",
    type: "Holerite",
    competence: "10/2026",
    batch: "LOTE-001",
    status: "REVISAO_HUMANA",
    page: 3,
    note: "Conferir a associação do documento ao trabalhador antes de prosseguir.",
  },
  {
    id: "DOC-003",
    contract: "CTR-001",
    worker: "Pessoa exemplo 002",
    type: "Espelho de ponto",
    competence: "10/2026",
    batch: "LOTE-001",
    status: "PENDENTE_CORRECAO",
    page: 4,
    note: "Página 2 de 2 não localizada no documento de exemplo.",
  },
  {
    id: "DOC-004",
    contract: "CTR-001",
    worker: "Pessoa exemplo 002",
    type: "Holerite",
    competence: "10/2026",
    batch: "LOTE-002",
    status: "APTO",
    page: 1,
    note: "Campos de exemplo organizados para conferência posterior.",
  },
  {
    id: "DOC-005",
    contract: "CTR-001",
    worker: "Pessoa exemplo 003",
    type: "Comprovante de pagamento",
    competence: "09/2026",
    batch: "LOTE-003",
    status: "APTO",
    page: 2,
    note: "Comprovante sintético vinculado à competência de setembro.",
  },
  {
    id: "DOC-006",
    contract: "CTR-002",
    worker: "Pessoa exemplo 004",
    type: "Holerite",
    competence: "10/2026",
    batch: "LOTE-004",
    status: "REVISAO_HUMANA",
    page: 2,
    note: "Identificação ambígua no exemplo. Conferir a associação do trabalhador.",
  },
  {
    id: "DOC-007",
    contract: "CTR-002",
    worker: "Pessoa exemplo 005",
    type: "Espelho de ponto",
    competence: "10/2026",
    batch: "LOTE-004",
    status: "PENDENTE_CORRECAO",
    page: 3,
    note: "A página de exemplo está ilegível. Solicitar uma versão legível.",
  },
  {
    id: "DOC-008",
    contract: "CTR-001",
    worker: "Pessoa exemplo 006",
    type: "Holerite",
    competence: "10/2026",
    batch: "LOTE-008",
    status: "REVISAO_HUMANA",
    page: 1,
    note: "Fronteira documental incerta entre as páginas 2 e 3. Conferir o agrupamento.",
  },
  {
    id: "DOC-009",
    contract: "CTR-001",
    worker: "Pessoa exemplo 006",
    type: "Holerite",
    competence: "10/2026",
    batch: "LOTE-008",
    status: "APTO",
    page: 4,
    note: "Página de exemplo contígua ao agrupamento anterior, disponível para conferência de continuidade.",
  },
];
export const issues: {
  id: string;
  contract: string;
  worker: string;
  competence: string;
  title: string;
  category: string;
  status: IssueStatus;
  document: string;
  instruction: string;
}[] = [
  {
    id: "PEN-001",
    contract: "CTR-001",
    worker: "Pessoa exemplo 002",
    competence: "10/2026",
    title: "Página de ponto ausente",
    category: "PAGINA_FALTANTE",
    status: "ABERTA",
    document: "DOC-003",
    instruction:
      "Encaminhar o espelho de ponto completo, incluindo a página 2 de 2 da competência 10/2026.",
  },
  {
    id: "PEN-002",
    contract: "CTR-001",
    worker: "Pessoa exemplo 001",
    competence: "10/2026",
    title: "Comprovante solicitado",
    category: "DOCUMENTO_AUSENTE",
    status: "REENVIADA",
    document: "",
    instruction:
      "Exemplo de reenvio aguardando conferência da equipe responsável. O reenvio não resolve automaticamente a pendência.",
  },
  {
    id: "PEN-003",
    contract: "CTR-001",
    worker: "Pessoa exemplo 003",
    competence: "09/2026",
    title: "Comprovante conferido",
    category: "SOLICITADA_NA_REVISAO",
    status: "RESOLVIDA",
    document: "DOC-005",
    instruction:
      "Exemplo de pendência resolvida após conferência humana do documento substituto.",
  },
  {
    id: "PEN-004",
    contract: "CTR-002",
    worker: "Pessoa exemplo 005",
    competence: "10/2026",
    title: "Documento ilegível",
    category: "ILEGIVEL",
    status: "ABERTA",
    document: "DOC-007",
    instruction:
      "Encaminhar uma versão legível do espelho de ponto. A identificação e os registros de jornada devem estar visíveis.",
  },
];
export const documentLabels: Record<DocumentStatus, string> = {
  APTO: "Apto",
  PENDENTE_CORRECAO: "Pendente de correção",
  REVISAO_HUMANA: "Revisão humana",
};
export const issueLabels: Record<IssueStatus, string> = {
  ABERTA: "Aberta",
  REENVIADA: "Reenviada",
  RESOLVIDA: "Resolvida",
};
