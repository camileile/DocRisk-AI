"use client";
import Link from "next/link";
import { ArrowUpRight, Upload } from "lucide-react";
import { useSession } from "@/components/demo-provider";
import { BatchBadge, EmptyState, ErrorState, LoadingState, PageIntro } from "@/components/workspace-parts";
import { formatDate, type Batch } from "@/lib/api";
import { useApi } from "@/lib/use-api";

export default function BatchesPage() {
  const { me, contract } = useSession();
  const { data, error, loading, reload } = useApi<Batch[]>("/api/batches", {
    pollMs: 3000,
    shouldPoll: (rows) => rows.some((b) => b.status === "RECEBIDO" || b.status === "PROCESSANDO"),
  });
  const rows = (data ?? []).filter((b) => !contract || b.contract_id === contract);
  return (
    <>
      <PageIntro
        eyebrow="HISTÓRICO DE ENVIO"
        title="Cada lote, um caminho claro."
        description="Acompanhe o recebimento, o processamento e os documentos separados em cada lote."
        action={
          me?.org_tipo === "FORNECEDORA" ? (
            <Link className="button" href="/painel/envio">
              <Upload size={17} /> Enviar lote
            </Link>
          ) : undefined
        }
      />
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : rows.length === 0 ? (
        <EmptyState title="Nenhum lote neste contrato." text="Os lotes enviados pela fornecedora aparecem aqui." />
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Lote</th>
                <th>Arquivo</th>
                <th>Páginas</th>
                <th>Situação</th>
                <th>Recebido</th>
                <th><span className="sr-only">Ações</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((b) => (
                <tr key={b.id}>
                  <td>
                    <strong>#{b.id}</strong>
                    {b.issue_id && <small className="muted"> · reenvio da pendência {b.issue_id}</small>}
                  </td>
                  <td>{b.filename}</td>
                  <td>{b.tipo_arquivo === "AEJ" ? "AEJ estruturado" : b.total_pages}</td>
                  <td>
                    <BatchBadge status={b.status} />
                    {b.erro && <small className="muted block">{b.erro}</small>}
                  </td>
                  <td>{formatDate(b.created_at)}</td>
                  <td>
                    <Link className="table-action" href={`/painel/lotes/detalhe?id=${b.id}`}>
                      Abrir <ArrowUpRight size={14} />
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
