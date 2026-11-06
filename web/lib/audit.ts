// Registros sintéticos no formato de GET /api/audit.
// Nenhum evento desta demonstração foi produzido pela API.
export type AuditResult = "OK" | "NEGADO";
export type AuditEvent = {
  id: number;
  user_id: string | null;
  org_id: string | null;
  acao: string;
  alvo: string;
  resultado: AuditResult;
  instante: string;
};

export const auditActionLabels: Record<string, string> = {
  LOTE_ENVIADO: "Envio de lote",
  DOCUMENTO_APROVAR: "Aprovação de documento",
  DOCUMENTO_SOLICITAR_CORRECAO: "Solicitação de correção",
  DOCUMENTO_DIVIDIR: "Divisão de documento",
  DOCUMENTO_UNIR: "União de documentos",
  PENDENCIA_REENVIADA: "Reenvio de pendência",
  PARECER_RASCUNHO_CRIADO: "Criação de rascunho",
  PARECER_PUBLICADO: "Publicação de parecer",
  CONTRATO_NEGADO: "Acesso negado a contrato",
};

export const auditOrganizations: Record<string, string> = {
  "ORG-BH": "Bernhoeft (demo)",
  "ORG-FORN-A": "Fornecedora Alfa (demo)",
  "ORG-FORN-B": "Fornecedora Beta (demo)",
};

export const auditEvents: AuditEvent[] = [
  { id: 112, user_id: "USR-BH-01", org_id: "ORG-BH", acao: "PARECER_PUBLICADO", alvo: "PAR-001-V2", resultado: "OK", instante: "2026-11-05T20:32:00-03:00" },
  { id: 111, user_id: "USR-FORN-02", org_id: "ORG-FORN-B", acao: "CONTRATO_NEGADO", alvo: "CTR-001", resultado: "NEGADO", instante: "2026-11-05T20:23:00-03:00" },
  { id: 110, user_id: "USR-BH-01", org_id: "ORG-BH", acao: "PARECER_RASCUNHO_CRIADO", alvo: "PAR-001-V3", resultado: "OK", instante: "2026-11-05T19:58:00-03:00" },
  { id: 109, user_id: "USR-BH-01", org_id: "ORG-BH", acao: "DOCUMENTO_APROVAR", alvo: "DOC-010", resultado: "OK", instante: "2026-11-05T19:40:00-03:00" },
  { id: 108, user_id: "USR-FORN-01", org_id: "ORG-FORN-A", acao: "PENDENCIA_REENVIADA", alvo: "PEN-002", resultado: "OK", instante: "2026-11-05T19:24:00-03:00" },
  { id: 107, user_id: "USR-BH-02", org_id: "ORG-BH", acao: "DOCUMENTO_SOLICITAR_CORRECAO", alvo: "DOC-003", resultado: "OK", instante: "2026-11-05T18:51:00-03:00" },
  { id: 106, user_id: "USR-FORN-01", org_id: "ORG-FORN-A", acao: "LOTE_ENVIADO", alvo: "LOTE-009", resultado: "OK", instante: "2026-11-05T18:22:00-03:00" },
  { id: 105, user_id: "USR-FORN-02", org_id: "ORG-FORN-B", acao: "LOTE_ENVIADO", alvo: "LOTE-004", resultado: "OK", instante: "2026-11-05T17:14:00-03:00" },
  { id: 104, user_id: "USR-BH-02", org_id: "ORG-BH", acao: "DOCUMENTO_DIVIDIR", alvo: "DOC-008", resultado: "OK", instante: "2026-11-05T16:45:00-03:00" },
  { id: 103, user_id: "USR-BH-02", org_id: "ORG-BH", acao: "DOCUMENTO_UNIR", alvo: "DOC-009", resultado: "OK", instante: "2026-11-05T16:13:00-03:00" },
  { id: 102, user_id: "USR-FORN-01", org_id: "ORG-FORN-A", acao: "CONTRATO_NEGADO", alvo: "CTR-002", resultado: "NEGADO", instante: "2026-11-04T16:55:00-03:00" },
  { id: 101, user_id: "USR-BH-01", org_id: "ORG-BH", acao: "PARECER_RASCUNHO_CRIADO", alvo: "PAR-002-V1", resultado: "OK", instante: "2026-11-04T13:10:00-03:00" },
];

export const auditDate = (value: string) =>
  new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Recife",
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
