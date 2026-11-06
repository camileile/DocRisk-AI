import { documents, issues } from "./demo";
export type AnalysisStatus =
  | "AGUARDANDO_DOCUMENTOS"
  | "BLOQUEADA_PENDENCIA"
  | "REVISAO_HUMANA"
  | "ANALISADA";
export type AnalysisResult =
  | "NAO_AVALIADO"
  | "DADOS_INSUFICIENTES"
  | "DIVERGENCIA_A_VERIFICAR"
  | "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS";
export const analysisStatusLabels: Record<AnalysisStatus, string> = {
  AGUARDANDO_DOCUMENTOS: "Aguardando documentos",
  BLOQUEADA_PENDENCIA: "Bloqueada por pendência",
  REVISAO_HUMANA: "Revisão humana",
  ANALISADA: "Analisada",
};
export const analysisResultLabels: Record<AnalysisResult, string> = {
  NAO_AVALIADO: "Não avaliado",
  DADOS_INSUFICIENTES: "Dados insuficientes",
  DIVERGENCIA_A_VERIFICAR: "Divergência a verificar",
  SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS:
    "Sem divergência nos campos comparados",
};
export type Analysis = {
  id: string;
  contract: string;
  worker: string;
  competence: string;
  status: AnalysisStatus;
  result: AnalysisResult;
  documentIds: string[];
  hoursPoint: number | null;
  hoursPayroll: number | null;
  differenceHours: number | null;
  reason: string;
  nextStep: string;
  checkedAt: string | null;
  version: number;
  rule: "HE-CMP-v1";
};
export const analyses: Analysis[] = [
  {
    id: "ANA-001",
    contract: "CTR-001",
    worker: "Pessoa exemplo 001",
    competence: "10/2026",
    status: "REVISAO_HUMANA",
    result: "NAO_AVALIADO",
    documentIds: ["DOC-001", "DOC-002"],
    hoursPoint: 12,
    hoursPayroll: 8,
    differenceHours: null,
    reason:
      "O holerite ainda precisa de conferência da identificação e do vínculo. A diferença não foi avaliada.",
    nextStep:
      "Conferir DOC-002 na fila de revisão antes de prosseguir com a comparação.",
    checkedAt: "2026-11-05T15:10:00-03:00",
    version: 1,
    rule: "HE-CMP-v1",
  },
  {
    id: "ANA-002",
    contract: "CTR-001",
    worker: "Pessoa exemplo 002",
    competence: "10/2026",
    status: "BLOQUEADA_PENDENCIA",
    result: "NAO_AVALIADO",
    documentIds: ["DOC-003", "DOC-004"],
    hoursPoint: null,
    hoursPayroll: 8,
    differenceHours: null,
    reason:
      "O espelho de ponto está pendente de correção por página ausente. Apenas este trabalhador nesta competência fica bloqueado.",
    nextStep:
      "Acompanhar PEN-001 e conferir a versão completa do espelho de ponto.",
    checkedAt: "2026-11-05T15:10:00-03:00",
    version: 1,
    rule: "HE-CMP-v1",
  },
  {
    id: "ANA-003",
    contract: "CTR-001",
    worker: "Pessoa exemplo 003",
    competence: "09/2026",
    status: "BLOQUEADA_PENDENCIA",
    result: "NAO_AVALIADO",
    documentIds: ["DOC-005"],
    hoursPoint: null,
    hoursPayroll: null,
    differenceHours: null,
    reason:
      "Há comprovante de pagamento, mas faltam ponto e holerite para comparar horas extras.",
    nextStep:
      "Solicitar os documentos de jornada e folha da mesma competência. A pendência histórica resolvida não libera esta análise.",
    checkedAt: "2026-10-06T09:20:00-03:00",
    version: 1,
    rule: "HE-CMP-v1",
  },
  {
    id: "ANA-004",
    contract: "CTR-002",
    worker: "Pessoa exemplo 004",
    competence: "10/2026",
    status: "BLOQUEADA_PENDENCIA",
    result: "NAO_AVALIADO",
    documentIds: ["DOC-006"],
    hoursPoint: null,
    hoursPayroll: 6,
    differenceHours: null,
    reason:
      "O ponto está ausente e o holerite possui identificação em revisão. Não há insumos liberados para a comparação.",
    nextStep: "Providenciar o ponto e conferir o vínculo de DOC-006.",
    checkedAt: "2026-11-05T15:10:00-03:00",
    version: 1,
    rule: "HE-CMP-v1",
  },
  {
    id: "ANA-005",
    contract: "CTR-002",
    worker: "Pessoa exemplo 005",
    competence: "10/2026",
    status: "BLOQUEADA_PENDENCIA",
    result: "NAO_AVALIADO",
    documentIds: ["DOC-007"],
    hoursPoint: null,
    hoursPayroll: null,
    differenceHours: null,
    reason:
      "O ponto está ilegível e não há holerite vinculado. A análise depende da correção e do documento ausente.",
    nextStep: "Acompanhar PEN-004 e solicitar o holerite da competência.",
    checkedAt: "2026-11-05T15:10:00-03:00",
    version: 1,
    rule: "HE-CMP-v1",
  },
  {
    id: "ANA-006",
    contract: "CTR-001",
    worker: "Pessoa exemplo 006",
    competence: "10/2026",
    status: "BLOQUEADA_PENDENCIA",
    result: "NAO_AVALIADO",
    documentIds: ["DOC-008", "DOC-009"],
    hoursPoint: null,
    hoursPayroll: null,
    differenceHours: null,
    reason:
      "Falta o ponto e há fronteira documental em revisão entre os holerites de exemplo. Nenhum valor foi escolhido automaticamente.",
    nextStep:
      "Conferir o agrupamento de DOC-008 e providenciar o ponto antes de comparar.",
    checkedAt: "2026-11-05T15:10:00-03:00",
    version: 1,
    rule: "HE-CMP-v1",
  },
  {
    id: "ANA-007",
    contract: "CTR-001",
    worker: "Pessoa exemplo 007",
    competence: "10/2026",
    status: "ANALISADA",
    result: "DIVERGENCIA_A_VERIFICAR",
    documentIds: ["DOC-010", "DOC-011", "DOC-012"],
    hoursPoint: 12,
    hoursPayroll: 8,
    differenceHours: 4,
    reason:
      "Diferença de 4,00 h a conferir entre ponto e folha. Pode haver compensação ou banco de horas; este indício não conclui ausência de pagamento ou infração.",
    nextStep:
      "Conferir os documentos e o contexto da jornada antes de preparar uma conclusão.",
    checkedAt: "2026-11-05T16:05:00-03:00",
    version: 1,
    rule: "HE-CMP-v1",
  },
  {
    id: "ANA-008",
    contract: "CTR-001",
    worker: "Pessoa exemplo 008",
    competence: "10/2026",
    status: "ANALISADA",
    result: "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS",
    documentIds: ["DOC-013", "DOC-014", "DOC-015"],
    hoursPoint: 10,
    hoursPayroll: 10,
    differenceHours: 0,
    reason:
      "As horas extras em ponto e folha coincidem nos campos comparados. Isso não atesta regularidade trabalhista integral.",
    nextStep:
      "Revisar o alcance dos campos comparados e as evidências antes de preparar o parecer.",
    checkedAt: "2026-11-05T16:05:00-03:00",
    version: 1,
    rule: "HE-CMP-v1",
  },
  {
    id: "ANA-009",
    contract: "CTR-001",
    worker: "Pessoa exemplo 009",
    competence: "10/2026",
    status: "ANALISADA",
    result: "DADOS_INSUFICIENTES",
    documentIds: ["DOC-016", "DOC-017"],
    hoursPoint: 6,
    hoursPayroll: null,
    differenceHours: null,
    reason:
      "A folha apresenta o valor da rubrica em reais, mas não informa horas extras em horas. Reais não foram convertidos em horas.",
    nextStep:
      "Conferir a referência em horas no holerite ou solicitar esclarecimento documental.",
    checkedAt: "2026-11-05T16:05:00-03:00",
    version: 1,
    rule: "HE-CMP-v1",
  },
  {
    id: "ANA-010",
    contract: "CTR-002",
    worker: "Pessoa exemplo 010",
    competence: "09/2026",
    status: "AGUARDANDO_DOCUMENTOS",
    result: "NAO_AVALIADO",
    documentIds: [],
    hoursPoint: null,
    hoursPayroll: null,
    differenceHours: null,
    reason:
      "Exemplo de acompanhamento inicial, antes do recebimento dos documentos. A comparação ainda não foi iniciada.",
    nextStep:
      "Aguardar o envio inicial de ponto e folha para esta competência.",
    checkedAt: null,
    version: 1,
    rule: "HE-CMP-v1",
  },
];
export const financialExamples: Record<
  string,
  {
    payrollOvertimeBRL: number | null;
    netBRL: number | null;
    paidBRL: number | null;
  }
> = {
  "ANA-001": { payrollOvertimeBRL: 160, netBRL: 1760, paidBRL: null },
  "ANA-004": { payrollOvertimeBRL: 120, netBRL: null, paidBRL: null },
  "ANA-007": { payrollOvertimeBRL: 160, netBRL: 1760, paidBRL: 1760 },
  "ANA-008": { payrollOvertimeBRL: 200, netBRL: 1800, paidBRL: 1800 },
  "ANA-009": { payrollOvertimeBRL: 120, netBRL: 1720, paidBRL: null },
};
export function getAnalysisDocuments(analysis: Analysis) {
  return documents.filter(
    (d) =>
      analysis.documentIds.includes(d.id) &&
      d.contract === analysis.contract &&
      d.competence === analysis.competence &&
      d.worker === analysis.worker,
  );
}
export function getAnalysisIssues(analysis: Analysis) {
  return issues.filter(
    (i) =>
      i.contract === analysis.contract &&
      i.competence === analysis.competence &&
      i.worker === analysis.worker,
  );
}
export function formatHours(value: number | null) {
  return value === null
    ? "Não disponível"
    : `${new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)} h`;
}
export function formatBRL(value: number | null) {
  return value === null
    ? "Não informado"
    : new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: "BRL",
      }).format(value);
}
