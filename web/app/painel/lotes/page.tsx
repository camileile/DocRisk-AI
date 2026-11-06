"use client";
import { useState } from "react";
import Link from "next/link";
import {
  Search,
  ArrowUpRight,
  Upload,
  Package,
  Clock3,
  CircleAlert,
  CheckCheck,
} from "lucide-react";
import { useDemo } from "@/components/demo-provider";
import { ApiBatches } from "@/components/api-batches";
import { PageIntro, EmptyState } from "@/components/workspace-parts";
import { BatchBadge } from "@/components/batch-badge";
import {
  batches,
  batchLabels,
  canExploreBatch,
  getBatchDocuments,
  formatReceivedAt,
  type BatchStatus,
} from "@/lib/batches";
export default function BatchesPage() {
  const { apiSession } = useDemo();
  return apiSession ? <ApiBatches /> : <DemoBatchesPage />;
}

function DemoBatchesPage() {
  const { role, contract, competence } = useDemo();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("todos");
  const context = batches.filter(
    (b) =>
      canExploreBatch(b, role) &&
      b.contract === contract &&
      b.competence === competence,
  );
  const rows = context.filter(
    (b) =>
      (status === "todos" || b.status === status) &&
      `${b.id} ${b.filename} ${b.format}`
        .toLocaleLowerCase("pt-BR")
        .includes(query.toLocaleLowerCase("pt-BR").trim()),
  );
  return (
    <>
      <PageIntro
        eyebrow="HISTÓRICO DE ENVIO"
        title="Cada lote, um caminho claro."
        description="Acompanhe o recebimento, o processamento e os documentos de cada lote de exemplo."
        action={
          role === "OPERADOR_FORN" ? (
            <Link className="button" href="/painel/envio">
              <Upload size={17} /> Preparar envio
            </Link>
          ) : undefined
        }
      />
      <div className="stat-grid">
        {[
          {
            icon: Package,
            label: "Lotes no contexto",
            value: context.length,
            tone: "purple",
          },
          {
            icon: Clock3,
            label: "Recebidos ou processando",
            value: context.filter(
              (b) => b.status === "RECEBIDO" || b.status === "PROCESSANDO",
            ).length,
            tone: "purple",
          },
          {
            icon: CheckCheck,
            label: "Processamento concluído",
            value: context.filter((b) => b.status === "CONCLUIDO").length,
            tone: "green",
          },
          {
            icon: CircleAlert,
            label: "Com falha técnica",
            value: context.filter((b) => b.status === "FALHA_PROCESSAMENTO")
              .length,
            tone: "amber",
          },
        ].map(({ icon: Icon, label, value, tone }) => (
          <article className="stat-card" key={label}>
            <div className={`stat-icon ${tone}`}>
              <Icon size={20} />
            </div>
            <strong>{value}</strong>
            <span>{label}</span>
          </article>
        ))}
      </div>
      <div className="inline-info">
        <CircleAlert size={18} />
        <p>
          “Concluído” indica o término do processamento do lote. Documentos
          ainda podem precisar de revisão ou correção. Os estados abaixo são
          exemplos fixos, sem atualização em tempo real.
        </p>
      </div>
      <section className="workspace-card">
        <div className="list-toolbar">
          <label className="search-field">
            <Search size={18} />
            <input
              aria-label="Buscar lotes"
              placeholder="Buscar lote, arquivo ou formato…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <label className="filter-label">
            Processamento
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="todos">Todas as situações</option>
              {(Object.keys(batchLabels) as BatchStatus[]).map((key) => (
                <option key={key} value={key}>
                  {batchLabels[key]}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="list-summary" aria-live="polite">
          {rows.length} lote{rows.length === 1 ? "" : "s"} encontrado
          {rows.length === 1 ? "" : "s"}
        </div>
        {rows.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Lote / arquivo</th>
                  <th>Recebimento (Recife)</th>
                  <th>Processamento</th>
                  <th>Documentos</th>
                  <th>
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((batch) => (
                  <tr key={batch.id}>
                    <td>
                      <strong>{batch.id}</strong>
                      <small className="batch-file-name">
                        {batch.filename}
                      </small>
                      <small>
                        {batch.format} · {batch.sizeLabel}
                      </small>
                    </td>
                    <td>{formatReceivedAt(batch.receivedAt)}</td>
                    <td>
                      <BatchBadge status={batch.status} />
                    </td>
                    <td>
                      {batch.status === "CONCLUIDO"
                        ? getBatchDocuments(batch.id).length
                        : "Aguardando consolidação"}
                    </td>
                    <td>
                      <Link
                        className="table-action"
                        href={`/painel/lotes/${batch.id}`}
                        aria-label={`Abrir ${batch.id}`}
                      >
                        Abrir lote <ArrowUpRight size={14} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Nenhum lote encontrado"
            text="Ajuste a busca, a situação ou o contexto da análise para explorar outros lotes."
          />
        )}
      </section>
    </>
  );
}
