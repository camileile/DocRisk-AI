// Explicit, synthetic client-facing snapshots. No imports from internal analyses or documents.
export type PublicItem = {
  worker: string;
  state: "AVALIADO" | "BLOQUEADO" | "EM_REVISAO" | "AGUARDANDO";
  result:
    | "DIVERGENCIA_A_VERIFICAR"
    | "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS"
    | "DADOS_INSUFICIENTES"
    | "NAO_AVALIADO";
  note: string;
  evidence: {
    document: string;
    batch: string;
    page: number;
    version: number;
  }[];
};
export type PublishedReport = {
  id: string;
  series: string;
  version: number;
  contract: string;
  competence: string;
  client: string;
  supplier: string;
  approvedAt: string;
  approvedBy: string;
  rule: string;
  scope: string;
  limitations: string;
  items: PublicItem[];
};
export const publicStateLabels: Record<PublicItem["state"], string> = {
  AVALIADO: "Avaliado",
  BLOQUEADO: "Bloqueado",
  EM_REVISAO: "Em revisão",
  AGUARDANDO: "Aguardando documentos",
};
export const publicResultLabels: Record<PublicItem["result"], string> = {
  DIVERGENCIA_A_VERIFICAR: "Divergência a verificar",
  SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS:
    "Sem divergência nos campos comparados",
  DADOS_INSUFICIENTES: "Dados insuficientes",
  NAO_AVALIADO: "Não avaliado",
};
export const reportScope =
  "Conferência documental de ponto, folha e comprovantes vinculados, com comparação dos campos de horas extras por trabalhador e competência.";
export const reportLimitations =
  "O escopo se limita aos documentos e campos referenciados. Bloqueios e revisões permanecem no total acompanhado, sem serem tratados como regulares. Um indício requer conferência humana e não conclui infração ou ausência de pagamento. A coincidência dos campos não atesta regularidade trabalhista integral.";
export const publishedReports: PublishedReport[] = [
  {
    id: "PAR-001-V2",
    series: "PAR-001",
    version: 2,
    contract: "CTR-001",
    competence: "10/2026",
    client: "Contratante Alfa (demo)",
    supplier: "Fornecedora Alfa (demo)",
    approvedAt: "2026-11-05T18:00:00-03:00",
    approvedBy: "Analista de exemplo",
    rule: "HE-CMP-v1",
    scope: reportScope,
    limitations: reportLimitations,
    items: [
      {
        worker: "Pessoa exemplo 001",
        state: "EM_REVISAO",
        result: "NAO_AVALIADO",
        note: "O vínculo documental ainda está em conferência. A comparação não foi liberada.",
        evidence: [
          { document: "DOC-001", batch: "LOTE-001", page: 1, version: 1 },
          { document: "DOC-002", batch: "LOTE-001", page: 3, version: 1 },
        ],
      },
      {
        worker: "Pessoa exemplo 002",
        state: "BLOQUEADO",
        result: "NAO_AVALIADO",
        note: "Há correção documental pendente no ponto. O resultado permanece não avaliado.",
        evidence: [
          { document: "DOC-003", batch: "LOTE-001", page: 4, version: 1 },
          { document: "DOC-004", batch: "LOTE-002", page: 1, version: 1 },
        ],
      },
      {
        worker: "Pessoa exemplo 006",
        state: "BLOQUEADO",
        result: "NAO_AVALIADO",
        note: "A análise depende do documento de jornada e da conferência do agrupamento documental.",
        evidence: [
          { document: "DOC-008", batch: "LOTE-008", page: 1, version: 1 },
          { document: "DOC-009", batch: "LOTE-008", page: 4, version: 1 },
        ],
      },
      {
        worker: "Pessoa exemplo 007",
        state: "AVALIADO",
        result: "DIVERGENCIA_A_VERIFICAR",
        note: "Diferença de 4,00 h entre os campos de ponto e folha, a conferir no contexto da jornada.",
        evidence: [
          { document: "DOC-010", batch: "LOTE-009", page: 1, version: 1 },
          { document: "DOC-011", batch: "LOTE-009", page: 2, version: 1 },
          { document: "DOC-012", batch: "LOTE-009", page: 3, version: 1 },
        ],
      },
      {
        worker: "Pessoa exemplo 008",
        state: "AVALIADO",
        result: "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS",
        note: "Os campos de horas extras comparados coincidem no escopo documental considerado.",
        evidence: [
          { document: "DOC-013", batch: "LOTE-009", page: 4, version: 1 },
          { document: "DOC-014", batch: "LOTE-009", page: 5, version: 1 },
          { document: "DOC-015", batch: "LOTE-009", page: 6, version: 1 },
        ],
      },
      {
        worker: "Pessoa exemplo 009",
        state: "AVALIADO",
        result: "DADOS_INSUFICIENTES",
        note: "A referência em horas não está disponível na folha. Não foi calculada diferença de jornada.",
        evidence: [
          { document: "DOC-016", batch: "LOTE-009", page: 7, version: 1 },
          { document: "DOC-017", batch: "LOTE-009", page: 8, version: 1 },
        ],
      },
    ],
  },
  {
    id: "PAR-003-V1",
    series: "PAR-003",
    version: 1,
    contract: "CTR-001",
    competence: "09/2026",
    client: "Contratante Alfa (demo)",
    supplier: "Fornecedora Alfa (demo)",
    approvedAt: "2026-10-06T10:00:00-03:00",
    approvedBy: "Analista de exemplo",
    rule: "HE-CMP-v1",
    scope: reportScope,
    limitations: reportLimitations,
    items: [
      {
        worker: "Pessoa exemplo 003",
        state: "BLOQUEADO",
        result: "NAO_AVALIADO",
        note: "Há comprovante vinculado, mas faltam ponto e folha para comparar as horas extras.",
        evidence: [
          { document: "DOC-005", batch: "LOTE-003", page: 2, version: 1 },
        ],
      },
    ],
  },
];
export function summarizeReport(items: PublicItem[]) {
  return {
    total: items.length,
    evaluated: items.filter((i) => i.state === "AVALIADO").length,
    blocked: items.filter((i) => i.state === "BLOQUEADO").length,
    review: items.filter((i) => i.state === "EM_REVISAO").length,
    waiting: items.filter((i) => i.state === "AGUARDANDO").length,
    divergence: items.filter((i) => i.result === "DIVERGENCIA_A_VERIFICAR")
      .length,
    insufficient: items.filter((i) => i.result === "DADOS_INSUFICIENTES")
      .length,
    matching: items.filter(
      (i) => i.result === "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS",
    ).length,
  };
}
