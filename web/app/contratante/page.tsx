"use client";
import { useState } from "react";
import { ReportView } from "@/components/report-view";
import { EmptyState, ErrorState, LoadingState, PageIntro } from "@/components/workspace-parts";
import { formatDate, type Report, type ReportContent } from "@/lib/api";
import { useApi } from "@/lib/use-api";

export default function ContractorPage() {
  const { data, error, loading, reload } = useApi<Report[]>("/api/client/reports");
  const [selected, setSelected] = useState<number | null>(null);
  const rows = data ?? [];
  const current = rows.find((r) => r.id === selected) ?? rows[0];
  return (
    <>
      <PageIntro
        eyebrow="PARECERES PUBLICADOS"
        title="O que foi conferido, com as limitações claras."
        description="Aqui aparecem somente pareceres revisados e publicados pela Bernhoeft. Rascunhos, imagens de documentos e valores em reais não são exibidos."
      />
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : rows.length === 0 ? (
        <EmptyState title="Nenhum parecer publicado ainda." text="Quando a Bernhoeft publicar um parecer do seu contrato, ele aparecerá aqui." />
      ) : (
        <>
          <div className="list-toolbar">
            <label className="filter-label">
              Parecer
              <select value={current?.id} onChange={(e) => setSelected(Number(e.target.value))}>
                {rows.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.contract_id} · {r.competencia} · versão {r.versao} · publicado em {formatDate(r.publicado_em)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {current && "resumo" in current.conteudo_json && (
            <section className="workspace-card">
              <ReportView content={current.conteudo_json as ReportContent} />
            </section>
          )}
        </>
      )}
    </>
  );
}
