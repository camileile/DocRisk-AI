"use client";
import Link from "next/link";
import { useSession } from "@/components/demo-provider";
import { AnalysisBadge, EmptyState, ErrorState, LoadingState, PageIntro } from "@/components/workspace-parts";
import { formatDate, formatHours, typeLabels, type Analysis } from "@/lib/api";
import { useApi } from "@/lib/use-api";

export default function AnalysesPage() {
  const { contract } = useSession();
  const { data, error, loading, reload } = useApi<Analysis[]>("/api/analyses");
  const rows = (data ?? []).filter((a) => !contract || a.contract_id === contract);
  return (
    <>
      <PageIntro
        eyebrow="CONCILIAÇÃO DE HORAS EXTRAS"
        title="Ponto e holerite, lado a lado."
        description="Comparação por trabalhador e competência, sempre horas com horas. Pares com pendência ficam bloqueados sem travar os demais. Divergência é indício a conferir."
      />
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : rows.length === 0 ? (
        <EmptyState title="Nenhuma análise ainda." text="As análises são criadas quando chegam ponto e holerite de um trabalhador." />
      ) : (
        <div className="analysis-list">
          {rows.map((a) => (
            <article key={a.id} className="workspace-card analysis-card">
              <header>
                <div>
                  <span className="eyebrow">{a.contract_id} · COMPETÊNCIA {a.competencia}</span>
                  <h2>Trabalhador {a.worker_id}</h2>
                </div>
                <AnalysisBadge status={a.status} result={a.resultado.tipo} />
              </header>
              {a.status === "ANALISADA" && (
                <div className="hours-comparison">
                  <div><span>Ponto</span><strong>{formatHours(a.resultado.horas_ponto)}</strong></div>
                  <div><span>Holerite</span><strong>{formatHours(a.resultado.horas_folha)}</strong></div>
                  <div><span>Diferença</span><strong>{formatHours(a.resultado.diferenca_h)}</strong></div>
                </div>
              )}
              <p>{a.resultado.detalhe}</p>
              <p className="muted">{a.resultado.comprovante.observacao}</p>
              <details>
                <summary>Evidências utilizadas ({a.insumos.length})</summary>
                <ul className="plain-list">
                  {a.insumos.map((i) => (
                    <li key={i.doc_id}>
                      <Link href={`/painel/documentos/detalhe?id=${i.doc_id}`}>
                        {typeLabels[i.tipo] ?? i.tipo} #{i.doc_id}
                      </Link>{" "}
                      · versão {i.versao} · lote #{i.batch_id} · páginas {i.paginas.join(", ")} · {i.status}
                    </li>
                  ))}
                </ul>
              </details>
              <small className="muted">Regra {a.regra_versao} · calculada em {formatDate(a.created_at)}</small>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
