"use client";
import { useState } from "react";
import Link from "next/link";
import {
  Search,
  ArrowRight,
  FileCheck2,
  FilePenLine,
  UserCheck,
  Layers3,
  CircleAlert,
} from "lucide-react";
import { useDemo } from "@/components/demo-provider";
import { reports, reportStatusLabels, type ReportStatus } from "@/lib/reports";
import { formatReceivedAt } from "@/lib/batches";
import { PageIntro, EmptyState } from "@/components/workspace-parts";
import { ReportBadge } from "@/components/report-badge";
export default function ReportsPage() {
  const { role, contract, competence } = useDemo();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("todos");
  if (role !== "ANALISTA_BH")
    return (
      <>
        <PageIntro
          eyebrow="PARECERES"
          title="Área do analista."
          description="A preparação e revisão de pareceres pertencem à perspectiva Bernhoeft."
        />
        <Link className="button secondary" href="/painel">
          Voltar ao painel
        </Link>
      </>
    );
  const context = reports.filter(
    (r) => r.contract === contract && r.competence === competence,
  );
  const rows = context.filter(
    (r) =>
      (status === "todos" || r.status === status) &&
      r.id.toLowerCase().includes(query.trim().toLowerCase()),
  );
  return (
    <>
      <PageIntro
        eyebrow="ANALISTA BERNHOEFT"
        title="Da conferência ao parecer."
        description="Acompanhe rascunhos, revisão e versões publicadas dos pareceres de exemplo."
      />
      <div className="stat-grid">
        {[
          {
            icon: FilePenLine,
            label: "Rascunhos",
            value: context.filter((r) => r.status === "RASCUNHO").length,
            tone: "purple",
          },
          {
            icon: UserCheck,
            label: "Em revisão",
            value: context.filter((r) => r.status === "EM_REVISAO").length,
            tone: "purple",
          },
          {
            icon: FileCheck2,
            label: "Aprovados e publicados",
            value: context.filter((r) => r.status === "APROVADO_PUBLICADO")
              .length,
            tone: "green",
          },
          {
            icon: Layers3,
            label: "Versões substituídas",
            value: context.filter((r) => r.status === "SUBSTITUIDO_POR_VERSAO")
              .length,
            tone: "purple",
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
          Um rascunho novo não substitui o parecer publicado. A contratante só
          consulta versões aprovadas e publicadas; a publicação real exige
          revisão humana e um retrato imutável na API.
        </p>
      </div>
      <section className="workspace-card">
        <div className="list-toolbar">
          <label className="search-field">
            <Search size={18} />
            <input
              aria-label="Buscar pareceres"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar identificador do parecer…"
            />
          </label>
          <label className="filter-label">
            Situação
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="todos">Todas as situações</option>
              {(Object.keys(reportStatusLabels) as ReportStatus[]).map(
                (key) => (
                  <option key={key} value={key}>
                    {reportStatusLabels[key]}
                  </option>
                ),
              )}
            </select>
          </label>
        </div>
        <div className="list-summary" aria-live="polite">
          {rows.length}{" "}
          {rows.length === 1 ? "versão encontrada" : "versões encontradas"}
        </div>
        {rows.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Parecer</th>
                  <th>Situação</th>
                  <th>Registro do exemplo (Recife)</th>
                  <th>
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((report) => (
                  <tr key={report.id}>
                    <td>
                      <strong>{report.id}</strong>
                      <small>
                        Versão {report.version} · {report.competence}
                      </small>
                    </td>
                    <td>
                      <ReportBadge status={report.status} />
                    </td>
                    <td>{formatReceivedAt(report.recordedAt)}</td>
                    <td>
                      <Link
                        className="table-action"
                        href={`/painel/pareceres/${report.id}`}
                        aria-label={`Abrir ${report.id}`}
                      >
                        Abrir parecer <ArrowRight size={14} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Nenhum parecer encontrado"
            text="Ajuste a busca, os filtros ou o contexto para consultar os exemplos."
          />
        )}
      </section>
    </>
  );
}
