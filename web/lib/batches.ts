import { documents, issues, type DemoRole } from "./demo";
export type BatchStatus =
  "RECEBIDO" | "PROCESSANDO" | "CONCLUIDO" | "FALHA_PROCESSAMENTO";
export type Batch = {
  id: string;
  contract: string;
  competence: string;
  filename: string;
  format: "PDF" | "IMAGEM" | "AEJ";
  sizeLabel: string;
  receivedAt: string;
  status: BatchStatus;
  totalPages: number | null;
  readPages: number;
  stage: string;
  events: {
    title: string;
    time: string;
    description: string;
    kind: "done" | "current" | "error";
  }[];
};
export const batchLabels: Record<BatchStatus, string> = {
  RECEBIDO: "Recebido",
  PROCESSANDO: "Processando",
  CONCLUIDO: "Concluído",
  FALHA_PROCESSAMENTO: "Falha no processamento",
};
const completedEvents = (received: string, time: string): Batch["events"] => [
  {
    title: "Arquivo recebido",
    time: received,
    description: "Recebimento registrado no cenário demonstrativo.",
    kind: "done",
  },
  {
    title: "Leitura e organização concluídas",
    time,
    description: "Documentos de exemplo identificados e vinculados ao lote.",
    kind: "done",
  },
  {
    title: "Disponível para acompanhamento",
    time,
    description:
      "O processamento terminou. Situações documentais e pendências seguem seu próprio fluxo.",
    kind: "done",
  },
];
export const batches: Batch[] = [
  {
    id: "LOTE-007",
    contract: "CTR-001",
    competence: "10/2026",
    filename: "documentos-sinteticos-07.pdf",
    format: "PDF",
    sizeLabel: "1,8 MB",
    receivedAt: "2026-11-05T14:40:00-03:00",
    status: "FALHA_PROCESSAMENTO",
    totalPages: 4,
    readPages: 2,
    stage: "Interrompido durante a leitura",
    events: [
      {
        title: "Arquivo recebido",
        time: "14:40",
        description: "Arquivo de exemplo recebido para processamento.",
        kind: "done",
      },
      {
        title: "Leitura iniciada",
        time: "14:41",
        description: "Duas de quatro páginas lidas no cenário demonstrativo.",
        kind: "done",
      },
      {
        title: "Processamento interrompido",
        time: "14:42",
        description:
          "Falha técnica na etapa de leitura. Resultados ainda não consolidados.",
        kind: "error",
      },
    ],
  },
  {
    id: "LOTE-006",
    contract: "CTR-001",
    competence: "10/2026",
    filename: "documentos-sinteticos-06.pdf",
    format: "PDF",
    sizeLabel: "850 KB",
    receivedAt: "2026-11-05T14:35:00-03:00",
    status: "PROCESSANDO",
    totalPages: 2,
    readPages: 1,
    stage: "Leitura documental",
    events: [
      {
        title: "Arquivo recebido",
        time: "14:35",
        description: "Arquivo de exemplo recebido para processamento.",
        kind: "done",
      },
      {
        title: "Leitura documental",
        time: "14:36",
        description: "Uma de duas páginas lida neste retrato demonstrativo.",
        kind: "current",
      },
    ],
  },
  {
    id: "LOTE-005",
    contract: "CTR-001",
    competence: "10/2026",
    filename: "jornada-sintetica-05.aej",
    format: "AEJ",
    sizeLabel: "48 KB",
    receivedAt: "2026-11-05T14:30:00-03:00",
    status: "RECEBIDO",
    totalPages: null,
    readPages: 0,
    stage: "Aguardando processamento estruturado",
    events: [
      {
        title: "Arquivo recebido",
        time: "14:30",
        description:
          "AEJ de exemplo recebido. O conteúdo estruturado ainda aguarda processamento.",
        kind: "done",
      },
      {
        title: "Leitura dos registros",
        time: "Aguardando",
        description:
          "O AEJ será tratado como dado estruturado de jornada, sem OCR ou contagem de páginas.",
        kind: "current",
      },
    ],
  },
  {
    id: "LOTE-004",
    contract: "CTR-002",
    competence: "10/2026",
    filename: "documentos-sinteticos-04.pdf",
    format: "PDF",
    sizeLabel: "1,4 MB",
    receivedAt: "2026-11-05T11:10:00-03:00",
    status: "CONCLUIDO",
    totalPages: 3,
    readPages: 3,
    stage: "Processamento concluído",
    events: completedEvents("11:10", "11:12"),
  },
  {
    id: "LOTE-002",
    contract: "CTR-001",
    competence: "10/2026",
    filename: "holerite-sintetico-02.png",
    format: "IMAGEM",
    sizeLabel: "320 KB",
    receivedAt: "2026-11-05T10:20:00-03:00",
    status: "CONCLUIDO",
    totalPages: 1,
    readPages: 1,
    stage: "Processamento concluído",
    events: completedEvents("10:20", "10:21"),
  },
  {
    id: "LOTE-001",
    contract: "CTR-001",
    competence: "10/2026",
    filename: "documentos-sinteticos-01.pdf",
    format: "PDF",
    sizeLabel: "2,1 MB",
    receivedAt: "2026-11-05T09:00:00-03:00",
    status: "CONCLUIDO",
    totalPages: 4,
    readPages: 4,
    stage: "Processamento concluído",
    events: completedEvents("09:00", "09:03"),
  },
  {
    id: "LOTE-003",
    contract: "CTR-001",
    competence: "09/2026",
    filename: "comprovante-sintetico-03.pdf",
    format: "PDF",
    sizeLabel: "410 KB",
    receivedAt: "2026-10-06T09:15:00-03:00",
    status: "CONCLUIDO",
    totalPages: 2,
    readPages: 2,
    stage: "Processamento concluído",
    events: completedEvents("09:15", "09:16"),
  },
];
export function getBatchDocuments(id: string) {
  return documents.filter((d) => d.batch === id);
}
export function getBatchIssues(id: string) {
  const ids = new Set(getBatchDocuments(id).map((d) => d.id));
  return issues.filter(
    (issue) => Boolean(issue.document) && ids.has(issue.document),
  );
}
export function canExploreBatch(batch: Batch, role: DemoRole | null) {
  return (
    role === "ANALISTA_BH" ||
    (role === "OPERADOR_FORN" && batch.contract === "CTR-001")
  );
}
export function formatReceivedAt(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Recife",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
