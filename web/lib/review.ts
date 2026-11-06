import { documents } from "./demo";
export const documentTypes = [
  "Espelho de ponto",
  "Holerite",
  "Comprovante de pagamento",
  "Contrato",
  "Documento de identificação",
  "Nota fiscal",
  "Outro",
  "Desconhecido",
] as const;
export type ReviewAction =
  "aprovar" | "solicitar_correcao" | "dividir" | "unir_proximo";
export const actionLabels: Record<ReviewAction, string> = {
  aprovar: "Aprovar documento",
  solicitar_correcao: "Solicitar correção",
  dividir: "Dividir documento",
  unir_proximo: "Unir ao próximo",
};
export type ReviewExample = {
  documentId: string;
  reason: string;
  pages: {
    order: number;
    heading: string;
    worker: string;
    competence: string;
    text: string;
    lines: { label: string; value: string }[];
  }[];
  nextDocumentId?: string;
};
export const reviewExamples: ReviewExample[] = [
  {
    documentId: "DOC-002",
    reason:
      "Conferir a identificação do trabalhador e a associação do holerite à competência.",
    pages: [
      {
        order: 3,
        heading: "Holerite · exemplo sintético",
        worker: "Pessoa exemplo 001",
        competence: "10/2026",
        text: "Exemplo de conteúdo documental para conferência visual. Não corresponde a arquivo original ou leitura de IA.",
        lines: [
          { label: "Horas extras · referência em horas", value: "8,00 h" },
          { label: "Horas extras · valor da rubrica", value: "R$ 160,00" },
          { label: "Valor líquido ilustrativo", value: "R$ 1.760,00" },
        ],
      },
    ],
  },
  {
    documentId: "DOC-006",
    reason:
      "Identificação ambígua no exemplo. Conferir o trabalhador antes de liberar a análise dependente.",
    pages: [
      {
        order: 2,
        heading: "Holerite · exemplo sintético",
        worker: "Pessoa exemplo 004",
        competence: "10/2026",
        text: "A identificação é apresentada para conferência humana. O motivo interno de revisão não aparece na perspectiva da fornecedora.",
        lines: [
          { label: "Horas extras · referência em horas", value: "6,00 h" },
          { label: "Horas extras · valor da rubrica", value: "R$ 120,00" },
        ],
      },
    ],
  },
  {
    documentId: "DOC-008",
    reason:
      "Fronteira documental incerta. Conferir se a página 3 inicia outro documento ou continua o agrupamento.",
    nextDocumentId: "DOC-009",
    pages: [
      {
        order: 1,
        heading: "Holerite · página de exemplo 1",
        worker: "Pessoa exemplo 006",
        competence: "10/2026",
        text: "Primeira página do agrupamento sintético. A continuidade entre páginas precisa ser conferida.",
        lines: [
          { label: "Identificação de exemplo", value: "T006" },
          { label: "Tipo proposto", value: "Holerite" },
        ],
      },
      {
        order: 2,
        heading: "Holerite · página de exemplo 2",
        worker: "Pessoa exemplo 006",
        competence: "10/2026",
        text: "Página intermediária do agrupamento sintético. Confira a sequência e a identidade do documento.",
        lines: [
          { label: "Horas extras · referência em horas", value: "10,00 h" },
          { label: "Horas extras · valor da rubrica", value: "R$ 200,00" },
        ],
      },
      {
        order: 3,
        heading: "Continuação ou novo documento?",
        worker: "Pessoa exemplo 006",
        competence: "10/2026",
        text: "Página com fronteira incerta criada para demonstrar a preparação de divisão e união. A decisão exige conferência humana.",
        lines: [
          { label: "Continuidade do documento", value: "A conferir" },
          { label: "Tipo proposto", value: "Holerite" },
        ],
      },
    ],
  },
];
export function getReviewExample(id: string) {
  return reviewExamples.find((example) => example.documentId === id);
}
export function getReviewQueue(contract: string, competence: string) {
  return documents.filter(
    (d) =>
      d.status === "REVISAO_HUMANA" &&
      d.contract === contract &&
      d.competence === competence,
  );
}
export function getMergeCandidate(id: string) {
  const doc = documents.find((d) => d.id === id);
  const example = getReviewExample(id);
  const next = documents.find((d) => d.id === example?.nextDocumentId);
  if (!doc || !next || !example) return null;
  const last = example.pages.at(-1)?.order;
  return next.batch === doc.batch &&
    next.contract === doc.contract &&
    next.competence === doc.competence &&
    next.worker === doc.worker &&
    next.type === doc.type &&
    last !== undefined &&
    next.page === last + 1
    ? next
    : null;
}
