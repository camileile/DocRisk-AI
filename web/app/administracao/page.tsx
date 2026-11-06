"use client";

import { useState } from "react";
import {
  Activity, AlertTriangle, Building2, ClipboardList,
  Search, ShieldCheck, UsersRound, X,
} from "lucide-react";
import { useDemo } from "@/components/demo-provider";
import { EmptyState, PageIntro } from "@/components/workspace-parts";
import {
  auditActionLabels, auditDate, auditEvents, auditOrganizations,
  type AuditEvent, type AuditResult,
} from "@/lib/audit";

const actionOptions = [...new Set(auditEvents.map((event) => event.acao))].sort(
  (a, b) => (auditActionLabels[a] ?? a).localeCompare(auditActionLabels[b] ?? b, "pt-BR"),
);
const organizationOptions = [...new Set(auditEvents.map((event) => event.org_id))]
  .filter((id): id is string => id !== null);

function ResultBadge({ result }: { result: AuditResult }) {
  return (
    <span className={"status-badge " + (result === "OK" ? "success" : "warning")}>
      <i /> {result === "OK" ? "Registrada" : "Acesso negado"}
    </span>
  );
}

export default function AuditPage() {
  const { role } = useDemo();
  const [query, setQuery] = useState("");
  const [action, setAction] = useState("todas");
  const [result, setResult] = useState("todos");
  const [organization, setOrganization] = useState("todas");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  if (role !== "ADMIN_BH") return null;

  const term = query.trim().toLocaleLowerCase("pt-BR");
  const filtered = auditEvents.filter((event) => {
    const searchable = [
      event.id,
      event.acao,
      auditActionLabels[event.acao] ?? "",
      event.alvo,
      event.org_id ?? "",
      auditOrganizations[event.org_id ?? ""] ?? "",
      event.user_id ?? "",
      event.resultado,
    ].join(" ").toLocaleLowerCase("pt-BR");
    return (!term || searchable.includes(term)) &&
      (action === "todas" || event.acao === action) &&
      (result === "todos" || event.resultado === result) &&
      (organization === "todas" || event.org_id === organization);
  });
  const selected: AuditEvent | undefined = filtered.find((event) => event.id === selectedId);
  const denied = auditEvents.filter((event) => event.resultado === "NEGADO").length;
  const actors = new Set(auditEvents.map((event) => event.user_id).filter(Boolean)).size;
  const hasFilters = Boolean(query || action !== "todas" || result !== "todos" || organization !== "todas");

  function clearFilters() {
    setQuery("");
    setAction("todas");
    setResult("todos");
    setOrganization("todas");
    setSelectedId(null);
  }

  return (
    <>
      <PageIntro
        eyebrow="ADMINISTRAÇÃO · RASTREABILIDADE"
        title="Auditoria de ações."
        description="Explore quem realizou uma ação, em qual organização, sobre qual referência e qual foi o resultado registrado no exemplo."
      />
      <div className="stat-grid admin-stat-grid" aria-label="Indicadores dos registros de exemplo">
        {[
          { icon: ClipboardList, label: "Eventos do exemplo", value: auditEvents.length, tone: "purple" },
          { icon: AlertTriangle, label: "Acessos negados", value: denied, tone: "amber" },
          { icon: UsersRound, label: "Identificadores de usuários", value: actors, tone: "purple" },
          { icon: Building2, label: "Organizações representadas", value: organizationOptions.length, tone: "green" },
        ].map(({ icon: Icon, label, value, tone }) => (
          <article className="stat-card" key={label}>
            <div className={"stat-icon " + tone}><Icon size={20} /></div>
            <strong>{value}</strong>
            <span>{label}</span>
          </article>
        ))}
      </div>
      <div className="admin-disclosure">
        <ShieldCheck size={20} aria-hidden="true" />
        <div>
          <strong>Exemplo de trilha de auditoria — não é uma consulta real.</strong>
          <p>Os registros abaixo são fictícios e somente de leitura. A API possui a rota autenticada GET /api/audit para ADMIN_BH, mas a integração desta interface ainda é pendente. Este painel não executa ações nem garante a integridade de logs em produção.</p>
        </div>
      </div>
      <section className="workspace-card admin-audit-card" aria-labelledby="auditoria-tabela-titulo">
        <div className="admin-section-heading">
          <div>
            <span className="eyebrow">HISTÓRICO DO EXEMPLO</span>
            <h2 id="auditoria-tabela-titulo">Eventos registrados</h2>
            <p>Filtre por referência, tipo de ação, resultado ou organização.</p>
          </div>
          <span className="admin-count"><Activity size={16} /> {filtered.length} de {auditEvents.length} eventos</span>
        </div>
        <div className="admin-filters">
          <label className="admin-filter-search">
            <span>Pesquisar eventos</span>
            <div className="search-field">
              <Search size={18} aria-hidden="true" />
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="ID, usuário, ação ou referência…"
                aria-label="Pesquisar eventos de auditoria"
              />
            </div>
          </label>
          <label>
            <span>Ação</span>
            <select value={action} onChange={(event) => setAction(event.target.value)}>
              <option value="todas">Todas as ações</option>
              {actionOptions.map((value) => (
                <option key={value} value={value}>{auditActionLabels[value] ?? value}</option>
              ))}
            </select>
          </label>
          <label>
            <span>Resultado</span>
            <select value={result} onChange={(event) => setResult(event.target.value)}>
              <option value="todos">Todos</option>
              <option value="OK">Registrada</option>
              <option value="NEGADO">Acesso negado</option>
            </select>
          </label>
          <label>
            <span>Organização</span>
            <select value={organization} onChange={(event) => setOrganization(event.target.value)}>
              <option value="todas">Todas</option>
              {organizationOptions.map((id) => (
                <option key={id} value={id}>{auditOrganizations[id] ?? id}</option>
              ))}
            </select>
          </label>
        </div>
        {hasFilters && (
          <button type="button" className="admin-clear" onClick={clearFilters}>
            <X size={14} /> Limpar filtros
          </button>
        )}
        {filtered.length ? (
          <div className="table-scroll">
            <table className="data-table admin-audit-table">
              <thead>
                <tr>
                  <th scope="col">Data e hora (Recife)</th>
                  <th scope="col">Evento</th>
                  <th scope="col">Organização / usuário</th>
                  <th scope="col">Referência</th>
                  <th scope="col">Resultado</th>
                  <th scope="col"><span className="sr-only">Detalhes</span></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((event) => (
                  <tr key={event.id} className={selectedId === event.id ? "admin-row-selected" : undefined}>
                    <td><strong>{auditDate(event.instante)}</strong><small>Registro #{event.id}</small></td>
                    <td><strong>{auditActionLabels[event.acao] ?? event.acao}</strong><small>{event.acao}</small></td>
                    <td><strong>{auditOrganizations[event.org_id ?? ""] ?? "Não informada"}</strong><small>{event.user_id ?? "Não informado"}</small></td>
                    <td><span className="admin-target">{event.alvo}</span></td>
                    <td><ResultBadge result={event.resultado} /></td>
                    <td>
                      <button
                        type="button"
                        className="table-action admin-row-button"
                        aria-expanded={selectedId === event.id}
                        aria-controls="detalhe-registro-auditoria"
                        onClick={() => setSelectedId(selectedId === event.id ? null : event.id)}
                      >
                        {selectedId === event.id ? "Ocultar" : "Detalhes"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="Nenhum evento encontrado" text="Revise os filtros para visualizar os registros sintéticos." />
        )}
        <div className="admin-results-note" aria-live="polite">
          Registros fixos, ordenados do mais recente para o mais antigo. Não existe atualização automática nesta demonstração.
        </div>
      </section>
      {selected && (
        <section id="detalhe-registro-auditoria" className="workspace-card admin-event-detail" aria-labelledby="admin-event-title">
          <div className="admin-section-heading">
            <div>
              <span className="eyebrow">REFERÊNCIA DO EVENTO</span>
              <h2 id="admin-event-title">Registro #{selected.id}</h2>
              <p>{auditActionLabels[selected.acao] ?? selected.acao}</p>
            </div>
            <ResultBadge result={selected.resultado} />
          </div>
          <dl className="admin-detail-grid">
            <div><dt>Data e hora (Recife)</dt><dd>{auditDate(selected.instante)}</dd></div>
            <div><dt>Identificador do usuário</dt><dd>{selected.user_id ?? "Não informado"}</dd></div>
            <div><dt>Organização</dt><dd>{auditOrganizations[selected.org_id ?? ""] ?? "Não informada"} <small>{selected.org_id}</small></dd></div>
            <div><dt>Código da ação</dt><dd>{selected.acao}</dd></div>
            <div><dt>Referência da ação</dt><dd>{selected.alvo}</dd></div>
            <div><dt>Resultado registrado</dt><dd>{selected.resultado}</dd></div>
          </dl>
          <p className="admin-detail-footnote">A trilha apresenta apenas metadados sintéticos. Não inclui conteúdo de documentos, texto de OCR, valores financeiros ou justificativas internas.</p>
          <button type="button" className="button secondary admin-close" onClick={() => setSelectedId(null)}>
            Fechar detalhes
          </button>
        </section>
      )}
    </>
  );
}
