import { analyses, getAnalysisDocuments } from "./analyses";
import {
  publishedReports,
  reportScope,
  reportLimitations,
  type PublicItem,
} from "./published-reports";
export type ReportStatus =
  "RASCUNHO" | "EM_REVISAO" | "APROVADO_PUBLICADO" | "SUBSTITUIDO_POR_VERSAO";
export type InternalReport = {
  id: string;
  series: string;
  version: number;
  contract: string;
  competence: string;
  status: ReportStatus;
  recordedAt: string;
  supersededBy?: string;
};
export const reportStatusLabels: Record<ReportStatus, string> = {
  RASCUNHO: "Rascunho",
  EM_REVISAO: "Em revisão",
  APROVADO_PUBLICADO: "Aprovado e publicado",
  SUBSTITUIDO_POR_VERSAO: "Substituído por nova versão",
};
export const reports: InternalReport[] = [
  {
    id: "PAR-001-V3",
    series: "PAR-001",
    version: 3,
    contract: "CTR-001",
    competence: "10/2026",
    status: "RASCUNHO",
    recordedAt: "2026-11-05T18:10:00-03:00",
  },
  {
    id: "PAR-001-V2",
    series: "PAR-001",
    version: 2,
    contract: "CTR-001",
    competence: "10/2026",
    status: "APROVADO_PUBLICADO",
    recordedAt: "2026-11-05T18:00:00-03:00",
  },
  {
    id: "PAR-001-V1",
    series: "PAR-001",
    version: 1,
    contract: "CTR-001",
    competence: "10/2026",
    status: "SUBSTITUIDO_POR_VERSAO",
    recordedAt: "2026-11-05T17:00:00-03:00",
    supersededBy: "PAR-001-V2",
  },
  {
    id: "PAR-002-V1",
    series: "PAR-002",
    version: 1,
    contract: "CTR-002",
    competence: "10/2026",
    status: "EM_REVISAO",
    recordedAt: "2026-11-05T18:00:00-03:00",
  },
  {
    id: "PAR-003-V1",
    series: "PAR-003",
    version: 1,
    contract: "CTR-001",
    competence: "09/2026",
    status: "APROVADO_PUBLICADO",
    recordedAt: "2026-10-06T10:00:00-03:00",
  },
  {
    id: "PAR-004-V1",
    series: "PAR-004",
    version: 1,
    contract: "CTR-002",
    competence: "09/2026",
    status: "RASCUNHO",
    recordedAt: "2026-11-05T18:00:00-03:00",
  },
];
export function getReportContent(report: InternalReport) {
  const published = publishedReports.find((p) => p.id === report.id);
  if (published) return published;
  if (report.status === "SUBSTITUIDO_POR_VERSAO") return null;
  const scoped = analyses.filter(
    (a) => a.contract === report.contract && a.competence === report.competence,
  );
  const items: PublicItem[] = scoped.map((a) => ({
    worker: a.worker,
    state:
      a.status === "ANALISADA"
        ? "AVALIADO"
        : a.status === "REVISAO_HUMANA"
          ? "EM_REVISAO"
          : a.status === "BLOQUEADA_PENDENCIA"
            ? "BLOQUEADO"
            : "AGUARDANDO",
    result: a.result,
    note:
      a.result === "DIVERGENCIA_A_VERIFICAR"
        ? "Há diferença entre os campos de horas extras que requer conferência."
        : a.result === "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS"
          ? "Os campos comparados coincidem no escopo considerado."
          : a.result === "DADOS_INSUFICIENTES"
            ? "Há campos insuficientes para comparar as horas extras."
            : "A comparação ainda depende do recebimento, da correção ou da revisão dos documentos.",
    evidence: getAnalysisDocuments(a).map((d) => ({
      document: d.id,
      batch: d.batch,
      page: d.page,
      version: 1,
    })),
  }));
  return {
    id: report.id,
    series: report.series,
    version: report.version,
    contract: report.contract,
    competence: report.competence,
    client:
      report.contract === "CTR-001"
        ? "Contratante Alfa (demo)"
        : "Contratante Beta (demo)",
    supplier:
      report.contract === "CTR-001"
        ? "Fornecedora Alfa (demo)"
        : "Fornecedora Beta (demo)",
    approvedAt: null,
    approvedBy: null,
    rule: "HE-CMP-v1",
    scope: reportScope,
    limitations: reportLimitations,
    items,
  };
}
