"use client";
import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Search, ArrowRight, CircleAlert, X } from "lucide-react";
import { issues } from "@/lib/demo";
import { useDemo } from "@/components/demo-provider";
import {
  IssueBadge,
  EmptyState,
  PageIntro,
} from "@/components/workspace-parts";
export default function Issues() {
  return (
    <Suspense fallback={<p>Carregando pendências…</p>}>
      <IssuesContent />
    </Suspense>
  );
}
function IssuesContent() {
  const searchParams = useSearchParams();
  const { role, contract, competence } = useDemo();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("todos");
  const [expandedId, setSelectedId] = useState<string | null | undefined>(
    undefined,
  );
  const selectedId =
    expandedId === undefined ? searchParams.get("pendencia") : expandedId;
  const rows = issues.filter(
    (d) =>
      d.contract === contract &&
      d.competence === competence &&
      (status === "todos" || d.status === status) &&
      `${d.id} ${d.worker} ${d.title}`
        .toLocaleLowerCase("pt-BR")
        .includes(query.toLocaleLowerCase("pt-BR")),
  );
  const selected = rows.find((d) => d.id === selectedId);
  return (
    <>
      <PageIntro
        eyebrow="ACOMPANHAMENTO DOCUMENTAL"
        title="Pendências com direção."
        description="Entenda o que precisa ser corrigido e acompanhe a situação de cada solicitação."
      />
      <div className="inline-info">
        <CircleAlert size={18} />
        <p>
          Um reenvio precisa ser conferido antes da resolução. Nenhuma pendência
          é encerrada automaticamente nesta demonstração.
        </p>
      </div>
      <section className="workspace-card">
        <div className="list-toolbar">
          <label className="search-field">
            <Search size={18} />
            <input
              aria-label="Buscar pendências"
              placeholder="Buscar trabalhador, solicitação ou ID…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <label className="filter-label">
            Situação
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="todos">Todas as situações</option>
              <option value="ABERTA">Aberta</option>
              <option value="REENVIADA">Reenviada</option>
              <option value="RESOLVIDA">Resolvida</option>
            </select>
          </label>
        </div>
        <div className="list-summary" aria-live="polite">
          {rows.length} pendência{rows.length !== 1 ? "s" : ""} encontrada
          {rows.length !== 1 ? "s" : ""}
        </div>
        {rows.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Solicitação</th>
                  <th>Trabalhador</th>
                  <th>Situação</th>
                  <th>
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.title}</strong>
                      <small>
                        {item.id} · {item.competence}
                      </small>
                    </td>
                    <td>{item.worker}</td>
                    <td>
                      <IssueBadge status={item.status} />
                    </td>
                    <td>
                      <button
                        className="table-action"
                        aria-expanded={selectedId === item.id}
                        onClick={() =>
                          setSelectedId(selectedId === item.id ? null : item.id)
                        }
                      >
                        Ver orientação <ArrowRight size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Nenhuma pendência encontrada"
            text="Altere os filtros ou o contexto para consultar outros exemplos."
          />
        )}
      </section>
      {selected && (
        <section
          className="workspace-card issue-detail"
          aria-label={`Orientação de ${selected.id}`}
        >
          <div className="card-title">
            <div>
              <span className="eyebrow">
                {selected.id} · {selected.worker}
              </span>
              <h2>{selected.title}</h2>
            </div>
            <button
              className="icon-button"
              aria-label="Fechar orientação"
              onClick={() => setSelectedId(null)}
            >
              <X size={19} />
            </button>
          </div>
          <IssueBadge status={selected.status} />
          <h3>Orientação para a fornecedora</h3>
          <p>{selected.instruction}</p>
          <dl className="detail-list">
            <div>
              <dt>Contrato</dt>
              <dd>{selected.contract}</dd>
            </div>
            <div>
              <dt>Competência</dt>
              <dd>{selected.competence}</dd>
            </div>
            {selected.document && (
              <div>
                <dt>Documento de referência</dt>
                <dd>{selected.document}</dd>
              </div>
            )}
          </dl>
          {selected.status === "ABERTA" && role === "OPERADOR_FORN" && (
            <Link href="/painel/envio" className="button">
              Conferir como preparar o reenvio <ArrowRight size={16} />
            </Link>
          )}
          {selected.status === "ABERTA" && role === "ANALISTA_BH" && (
            <p className="integration-note">
              Exemplo de solicitação à fornecedora. Notificações e resolução
              dependem da integração com o backend.
            </p>
          )}
        </section>
      )}
    </>
  );
}
