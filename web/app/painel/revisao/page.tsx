"use client";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { useSession } from "@/components/demo-provider";
import { EmptyState, ErrorState, LoadingState, PageIntro } from "@/components/workspace-parts";
import { formatDate, pageList, typeLabels, type Doc } from "@/lib/api";
import { useApi } from "@/lib/use-api";

export default function ReviewQueue() {
  const { contract } = useSession();
  const { data, error, loading, reload } = useApi<Doc[]>("/api/review-queue");
  const rows = (data ?? []).filter((d) => !contract || d.contract_id === contract);
  return (
    <>
      <PageIntro
        eyebrow="REVISÃO HUMANA"
        title="Incertezas passam por pessoas."
        description="Documentos com tipo desconhecido, baixa confiança, fronteira incerta ou trabalhador não identificado aguardam conferência antes de seguir para a conciliação."
      />
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : rows.length === 0 ? (
        <EmptyState title="Fila vazia." text="Nenhum documento aguardando revisão neste contrato." />
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Documento</th>
                <th>Classificação sugerida</th>
                <th>Confiança</th>
                <th>Motivos</th>
                <th>Recebido</th>
                <th><span className="sr-only">Ações</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => (
                <tr key={d.id}>
                  <td>#{d.id}<small className="muted block">lote #{d.batch_id} · {pageList(d.paginas)}</small></td>
                  <td>
                    {typeLabels[d.tipo] ?? d.tipo}
                    <small className="muted block">{d.worker_id ?? "sem trabalhador"} · {d.competencia ?? "sem competência"}</small>
                  </td>
                  <td>{d.confianca !== undefined ? `${Math.round(d.confianca * 100)}%` : "—"}</td>
                  <td className="review-reason-cell">{(d.motivos_revisao ?? []).join("; ") || "—"}</td>
                  <td>{formatDate(d.created_at)}</td>
                  <td>
                    <Link className="table-action" href={`/painel/revisao/detalhe?id=${d.id}`}>
                      Conferir <ArrowUpRight size={14} />
                    </Link>
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
