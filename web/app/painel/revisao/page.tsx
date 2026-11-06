"use client";
import { useState } from "react";
import Link from "next/link";
import {
  Search,
  ArrowRight,
  ScanLine,
  Files,
  UserCheck,
  Layers3,
} from "lucide-react";
import { useDemo } from "@/components/demo-provider";
import { getReviewQueue, getReviewExample } from "@/lib/review";
import {
  PageIntro,
  EmptyState,
  DocumentBadge,
} from "@/components/workspace-parts";
export default function ReviewQueue() {
  const { role, contract, competence } = useDemo();
  const [query, setQuery] = useState("");
  const [reason, setReason] = useState("todos");
  if (role !== "ANALISTA_BH")
    return (
      <>
        <PageIntro
          eyebrow="REVISÃO DOCUMENTAL"
          title="Área do analista."
          description="A fila e os motivos internos de revisão pertencem à perspectiva de analista Bernhoeft."
        />
        <Link className="button secondary" href="/painel">
          Voltar ao painel
        </Link>
      </>
    );
  const queue = getReviewQueue(contract, competence);
  const rows = queue.filter(
    (d) =>
      `${d.id} ${d.worker} ${d.batch} ${d.type}`
        .toLocaleLowerCase("pt-BR")
        .includes(query.toLocaleLowerCase("pt-BR").trim()) &&
      (reason === "todos" ||
        (reason === "agrupamento"
          ? (getReviewExample(d.id)?.pages.length ?? 0) > 1
          : (getReviewExample(d.id)?.pages.length ?? 0) === 1)),
  );
  return (
    <>
      <PageIntro
        eyebrow="ANALISTA BERNHOEFT"
        title="Revisar é dar contexto."
        description="Confira identidade, competência e agrupamento dos documentos sinalizados para revisão humana."
      />
      <div className="stat-grid review-stats">
        {[
          { icon: UserCheck, value: queue.length, label: "Documentos na fila" },
          {
            icon: Files,
            value: new Set(queue.map((d) => d.batch)).size,
            label: "Lotes envolvidos",
          },
          {
            icon: Layers3,
            value: queue.filter(
              (d) => (getReviewExample(d.id)?.pages.length ?? 0) > 1,
            ).length,
            label: "Agrupamentos multipágina",
          },
        ].map(({ icon: Icon, value, label }) => (
          <article className="stat-card" key={label}>
            <div className="stat-icon purple">
              <Icon size={20} />
            </div>
            <strong>{value}</strong>
            <span>{label}</span>
          </article>
        ))}
      </div>
      <div className="inline-info">
        <ScanLine size={18} />
        <p>
          A revisão organiza as evidências para as próximas análises. Aprovação
          documental não equivale à conclusão da conciliação ou à publicação de
          um parecer.
        </p>
      </div>
      <section className="workspace-card">
        <div className="list-toolbar">
          <label className="search-field">
            <Search size={18} />
            <input
              aria-label="Buscar revisão"
              placeholder="Buscar documento, trabalhador ou lote…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <label className="filter-label">
            Conferência
            <select value={reason} onChange={(e) => setReason(e.target.value)}>
              <option value="todos">Todas</option>
              <option value="identificacao">Identificação e vínculo</option>
              <option value="agrupamento">Agrupamento multipágina</option>
            </select>
          </label>
        </div>
        <div className="list-summary" aria-live="polite">
          {rows.length} documento{rows.length === 1 ? "" : "s"} para revisar
        </div>
        {rows.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Documento</th>
                  <th>Trabalhador</th>
                  <th>Conferência necessária</th>
                  <th>
                    <span className="sr-only">Ação</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <strong>{doc.type}</strong>
                      <small>
                        {doc.id} · {doc.batch}
                      </small>
                    </td>
                    <td>
                      {doc.worker}
                      <small>{doc.competence}</small>
                    </td>
                    <td>
                      <div className="review-reason-cell">
                        <DocumentBadge status={doc.status} />
                        <p>{getReviewExample(doc.id)?.reason ?? doc.note}</p>
                      </div>
                    </td>
                    <td>
                      <Link
                        className="table-action"
                        href={`/painel/revisao/${doc.id}`}
                        aria-label={`Revisar ${doc.id}`}
                      >
                        Revisar <ArrowRight size={14} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Nenhum documento nesta fila"
            text="Altere a busca, o tipo de conferência ou o contexto para explorar os exemplos disponíveis."
          />
        )}
      </section>
    </>
  );
}
