"use client";
import { useState } from "react";
import Link from "next/link";
import { Search, ArrowRight, FileCheck2, ShieldCheck } from "lucide-react";
import { useDemo } from "@/components/demo-provider";
import { publishedReports, summarizeReport } from "@/lib/published-reports";
import { PageIntro, EmptyState } from "@/components/report-ui";
const date = (value: string) =>
  new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Recife",
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
export default function ContractorPage() {
  const { role, competence } = useDemo();
  const [query, setQuery] = useState("");
  if (role !== "GESTOR_CONTR") return null;
  const context = publishedReports.filter(
    (p) => p.contract === "CTR-001" && p.competence === competence,
  );
  const rows = context.filter((p) =>
    `${p.id} ${p.supplier}`
      .toLocaleLowerCase("pt-BR")
      .includes(query.trim().toLocaleLowerCase("pt-BR")),
  );
  return (
    <>
      <PageIntro
        eyebrow="GESTOR DA CONTRATANTE"
        title="Pareceres prontos para consulta."
        description="Consulte os exemplos aprovados e publicados do seu contrato, com escopo, limitações e referências de evidência."
      />
      <div className="contractor-intro">
        <div className="workspace-card">
          <FileCheck2 size={23} />
          <strong>{context.length}</strong>
          <span>Versão publicada nesta competência</span>
        </div>
        <div className="workspace-card">
          <ShieldCheck size={23} />
          <h2>Consulta do conteúdo autorizado.</h2>
          <p>
            Somente versões publicadas aparecem aqui. Um novo rascunho interno
            não substitui a versão disponível.
          </p>
        </div>
      </div>
      <section className="workspace-card">
        <label className="search-field">
          <Search size={18} />
          <input
            aria-label="Buscar pareceres publicados"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar parecer ou fornecedora…"
          />
        </label>
        <div className="list-summary" aria-live="polite">
          {rows.length} parecer{rows.length === 1 ? "" : "es"} encontrado
          {rows.length === 1 ? "" : "s"}
        </div>
        {rows.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Parecer / fornecedora</th>
                  <th>Publicação do exemplo (Recife)</th>
                  <th>Escopo</th>
                  <th>
                    <span className="sr-only">Consulta</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((report) => (
                  <tr key={report.id}>
                    <td>
                      <strong>{report.id}</strong>
                      <small>
                        {report.supplier} · versão {report.version}
                      </small>
                    </td>
                    <td>{date(report.approvedAt)}</td>
                    <td>
                      {summarizeReport(report.items).total} pares acompanhados
                      <small>Inclui bloqueios e revisões</small>
                    </td>
                    <td>
                      <Link
                        className="table-action"
                        href={`/contratante/${report.id}`}
                      >
                        Consultar <ArrowRight size={14} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Nenhum parecer publicado encontrado"
            text="Ajuste a busca ou a competência para consultar os exemplos disponíveis."
          />
        )}
      </section>
    </>
  );
}
