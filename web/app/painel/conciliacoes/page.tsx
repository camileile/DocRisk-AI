"use client";
import { useState } from "react";
import Link from "next/link";
import {
  Search,
  ArrowRight,
  CircleAlert,
  GitCompareArrows,
  ShieldCheck,
  Clock3,
  LockKeyhole,
} from "lucide-react";
import { useDemo } from "@/components/demo-provider";
import { PageIntro, EmptyState } from "@/components/workspace-parts";
import {
  AnalysisStatusBadge,
  AnalysisResultBadge,
} from "@/components/analysis-badges";
import {
  analyses,
  analysisStatusLabels,
  analysisResultLabels,
  formatHours,
  type AnalysisStatus,
  type AnalysisResult,
} from "@/lib/analyses";
export default function AnalysesPage() {
  const { role, contract, competence } = useDemo();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("todos");
  const [result, setResult] = useState("todos");
  if (role !== "ANALISTA_BH")
    return (
      <>
        <PageIntro
          eyebrow="CONCILIAÇÕES"
          title="Área de análise Bernhoeft."
          description="As conciliações e seus insumos pertencem à perspectiva do analista nesta demonstração."
        />
        <Link href="/painel" className="button secondary">
          Voltar ao painel
        </Link>
      </>
    );
  const context = analyses.filter(
    (a) => a.contract === contract && a.competence === competence,
  );
  const rows = context.filter(
    (a) =>
      (status === "todos" || a.status === status) &&
      (result === "todos" || a.result === result) &&
      `${a.id} ${a.worker}`
        .toLocaleLowerCase("pt-BR")
        .includes(query.trim().toLocaleLowerCase("pt-BR")),
  );
  return (
    <>
      <PageIntro
        eyebrow="ANALISTA BERNHOEFT · TRABALHISTA"
        title="Cruzar dados. Conferir contextos."
        description="Compare horas extras por trabalhador e competência, com as evidências e limitações de cada exemplo."
      />
      <div className="stat-grid">
        {[
          {
            icon: GitCompareArrows,
            value: context.length,
            label: "Pares em acompanhamento",
            tone: "purple",
          },
          {
            icon: CircleAlert,
            value: context.filter((a) => a.result === "DIVERGENCIA_A_VERIFICAR")
              .length,
            label: "Indícios a conferir",
            tone: "amber",
          },
          {
            icon: LockKeyhole,
            value: context.filter(
              (a) =>
                a.status === "BLOQUEADA_PENDENCIA" ||
                a.status === "REVISAO_HUMANA" ||
                a.status === "AGUARDANDO_DOCUMENTOS",
            ).length,
            label: "Dependem de documentos",
            tone: "purple",
          },
          {
            icon: ShieldCheck,
            value: context.filter(
              (a) => a.result === "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS",
            ).length,
            label: "Sem divergência nos campos",
            tone: "green",
          },
        ].map(({ icon: Icon, value, label, tone }) => (
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
          Horas são comparadas com horas. Valores em reais não são convertidos
          em jornada. Um bloqueio afeta apenas o trabalhador e a competência
          dependentes do documento.
        </p>
      </div>
      <section className="workspace-card">
        <div className="analysis-toolbar">
          <label className="search-field">
            <Search size={18} />
            <input
              aria-label="Buscar conciliações"
              placeholder="Buscar trabalhador ou análise…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <div>
            <label className="filter-label">
              Situação
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="todos">Todas</option>
                {(Object.keys(analysisStatusLabels) as AnalysisStatus[]).map(
                  (key) => (
                    <option key={key} value={key}>
                      {analysisStatusLabels[key]}
                    </option>
                  ),
                )}
              </select>
            </label>
            <label className="filter-label">
              Resultado
              <select
                value={result}
                onChange={(e) => setResult(e.target.value)}
              >
                <option value="todos">Todos</option>
                {(Object.keys(analysisResultLabels) as AnalysisResult[]).map(
                  (key) => (
                    <option key={key} value={key}>
                      {analysisResultLabels[key]}
                    </option>
                  ),
                )}
              </select>
            </label>
          </div>
        </div>
        <div className="list-summary" aria-live="polite">
          {rows.length} análise{rows.length === 1 ? "" : "s"} encontrada
          {rows.length === 1 ? "" : "s"}
        </div>
        {rows.length ? (
          <div className="table-scroll">
            <table className="data-table analysis-table">
              <thead>
                <tr>
                  <th>Trabalhador / análise</th>
                  <th>Situação e resultado</th>
                  <th>Ponto · h</th>
                  <th>Folha · h</th>
                  <th>Diferença · h</th>
                  <th>
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <strong>{a.worker}</strong>
                      <small>
                        {a.id} · {a.competence}
                      </small>
                    </td>
                    <td>
                      <div className="analysis-status-stack">
                        <AnalysisStatusBadge status={a.status} />
                        <AnalysisResultBadge result={a.result} />
                      </div>
                    </td>
                    <td>{formatHours(a.hoursPoint)}</td>
                    <td>{formatHours(a.hoursPayroll)}</td>
                    <td>
                      {a.differenceHours === null ? (
                        <span className="unavailable-value">Não comparada</span>
                      ) : (
                        formatHours(a.differenceHours)
                      )}
                    </td>
                    <td>
                      <Link
                        className="table-action"
                        href={`/painel/conciliacoes/${a.id}`}
                        aria-label={`Abrir ${a.id}`}
                      >
                        Conferir <ArrowRight size={14} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Nenhuma análise encontrada"
            text="Altere a busca, os filtros ou o contexto para consultar os exemplos."
          />
        )}
        <p className="card-footnote">
          Resultados demonstrativos fixos. “Analisada” não significa
          regularidade integral nem parecer publicado.
        </p>
      </section>
      <section className="workspace-card analysis-explainer">
        <Clock3 size={21} />
        <div>
          <h2>Cada análise tem seu próprio caminho.</h2>
          <p>
            Documentos ausentes, em correção ou em revisão impedem a comparação
            dependente. Os demais pares podem seguir. Valores não disponíveis
            continuam sem valor, sem preenchimento com zero.
          </p>
        </div>
      </section>
    </>
  );
}
