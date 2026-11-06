"use client";
import { useState } from "react";
import { Search } from "lucide-react";
import { EmptyState, ErrorState, LoadingState, PageIntro } from "@/components/workspace-parts";
import { formatDate, type AuditEvent, type Metrics } from "@/lib/api";
import { useApi } from "@/lib/use-api";

const actionLabels: Record<string, string> = {
  LOTE_ENVIADO: "Lote enviado",
  LOTE_REPROCESSADO: "Lote reprocessado",
  CONTRATO_NEGADO: "Acesso a contrato negado",
  PENDENCIA_REENVIADA: "Pendência reenviada",
  PARECER_RASCUNHO_CRIADO: "Rascunho de parecer criado",
  PARECER_PUBLICADO: "Parecer publicado",
  DOCUMENTO_APROVAR: "Documento aprovado",
  DOCUMENTO_DIVIDIR: "Documento dividido",
  DOCUMENTO_UNIR_PROXIMO: "Documentos unidos",
  DOCUMENTO_SOLICITAR_CORRECAO: "Correção solicitada",
};

export default function AuditPage() {
  const audit = useApi<AuditEvent[]>("/api/audit");
  const metrics = useApi<Metrics>("/api/bernhoeft/metrics");
  const [query, setQuery] = useState("");
  const [result, setResult] = useState("todos");
  const term = query.trim().toLocaleLowerCase("pt-BR");
  const rows = (audit.data ?? []).filter(
    (e) =>
      (result === "todos" || e.resultado === result) &&
      `${e.acao} ${actionLabels[e.acao] ?? ""} ${e.alvo ?? ""} ${e.user_id ?? ""} ${e.org_id ?? ""}`
        .toLocaleLowerCase("pt-BR")
        .includes(term),
  );
  const m = metrics.data;
  return (
    <>
      <PageIntro
        eyebrow="TRILHA DE AUDITORIA"
        title="Quem fez o quê, e quando."
        description="Registro das ações e dos acessos negados gravado pela API. A trilha nunca guarda conteúdo de documentos."
      />
      {m && (
        <div className="stat-grid">
          <div className="stat-card"><strong>{m.lotes.total}</strong><span>Lotes recebidos</span></div>
          <div className="stat-card"><strong>{m.documentos.logicos}</strong><span>Documentos lógicos</span></div>
          <div className="stat-card"><strong>{m.pendencias.em_aberto}</strong><span>Pendências em aberto</span></div>
          <div className="stat-card"><strong>{m.pareceres_publicados}</strong><span>Pareceres publicados</span></div>
        </div>
      )}
      <div className="list-toolbar">
        <label className="search-field">
          <Search size={18} />
          <span className="sr-only">Filtrar eventos</span>
          <input type="search" placeholder="Filtrar por ação, usuário, organização ou alvo" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        <label className="filter-label">
          Resultado
          <select value={result} onChange={(e) => setResult(e.target.value)}>
            <option value="todos">Todos</option>
            <option value="OK">Registradas</option>
            <option value="NEGADO">Negadas</option>
          </select>
        </label>
      </div>
      {audit.loading ? (
        <LoadingState />
      ) : audit.error ? (
        <ErrorState message={audit.error} onRetry={audit.reload} />
      ) : rows.length === 0 ? (
        <EmptyState title="Nenhum evento." text="As ações feitas na plataforma aparecem aqui." />
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Quando</th>
                <th>Ação</th>
                <th>Usuário</th>
                <th>Organização</th>
                <th>Alvo</th>
                <th>Resultado</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.id}>
                  <td>{formatDate(e.instante)}</td>
                  <td>{actionLabels[e.acao] ?? e.acao}</td>
                  <td>{e.user_id ?? "—"}</td>
                  <td>{e.org_id ?? "—"}</td>
                  <td>{e.alvo ?? "—"}</td>
                  <td>
                    <span className={`status-badge ${e.resultado === "OK" ? "success" : "warning"}`}>
                      <i />
                      {e.resultado === "OK" ? "Registrada" : e.resultado === "NEGADO" ? "Acesso negado" : e.resultado}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
