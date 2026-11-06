// Synthetic fields for interface review only. No OCR or API extraction is represented.
export type DocumentFieldExample = {
  hoursExtra?: number | null;
  overtimeBRL?: number | null;
  netBRL?: number | null;
  paidBRL?: number | null;
};
export const documentFieldExamples: Record<string, DocumentFieldExample> = {
  "DOC-001": { hoursExtra: 12 },
  "DOC-002": { hoursExtra: 8, overtimeBRL: 160, netBRL: 1760 },
  "DOC-004": { hoursExtra: 8 },
  "DOC-006": { hoursExtra: 6, overtimeBRL: 120 },
  "DOC-008": { hoursExtra: 10, overtimeBRL: 200 },
  "DOC-010": { hoursExtra: 12 },
  "DOC-011": { hoursExtra: 8, overtimeBRL: 160, netBRL: 1760 },
  "DOC-012": { paidBRL: 1760 },
  "DOC-013": { hoursExtra: 10 },
  "DOC-014": { hoursExtra: 10, overtimeBRL: 200, netBRL: 1800 },
  "DOC-015": { paidBRL: 1800 },
  "DOC-016": { hoursExtra: 6 },
  "DOC-017": { hoursExtra: null, overtimeBRL: 120, netBRL: 1720 },
};
export function documentFieldRows(id: string) {
  const fields = documentFieldExamples[id];
  if (!fields) return [];
  const labels: Record<keyof DocumentFieldExample, string> = {
    hoursExtra: "Horas extras · referência em horas",
    overtimeBRL: "Rubrica de horas extras · reais",
    netBRL: "Valor líquido · reais",
    paidBRL: "Valor do comprovante · reais",
  };
  return (Object.keys(fields) as (keyof DocumentFieldExample)[]).map((key) => ({
    label: labels[key],
    value:
      fields[key] === null || fields[key] === undefined
        ? "Não informado"
        : key === "hoursExtra"
          ? `${new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(fields[key])} h`
          : new Intl.NumberFormat("pt-BR", {
              style: "currency",
              currency: "BRL",
            }).format(fields[key]),
  }));
}
