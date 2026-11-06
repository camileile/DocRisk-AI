"use client";
import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, ArrowUpRight, Download } from "lucide-react";
import { useSession } from "@/components/demo-provider";
import {
  DocumentBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  PageIntro,
} from "@/components/workspace-parts";
import { downloadBatchSource, formatHours, pageList, typeLabels, type DocDetail } from "@/lib/api";
import { DocumentViewer } from "@/components/document-viewer";
import { useApi } from "@/lib/use-api";
import { useState } from "react";

export default function Page() {
  return (
    <Suspense fallback={<LoadingState />}>
      <DocumentDetail />
    </Suspense>
  );
}

function money(value: number | null | undefined) {
  return value === null || value === undefined
    ? "—"
    : value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function DocumentDetail() {
  const id = useSearchParams().get("id");
  const { me, setContract } = useSession();
  const [sourceBusy, setSourceBusy] = useState(false);
  const [sourceError, setSourceError] = useState("");
  const { data: d, error, loading, reload } = useApi<DocDetail>(id ? `/api/documents/${id}?include_page_text=false` : null);
  if (!id) return <EmptyState title="Documento não informado." text="Abra um documento a partir da lista." />;
  if (loading) return <LoadingState />;
  if (error || !d) return <ErrorState message={error ?? "Documento não encontrado"} onRetry={reload} />;
  const bernhoeft = me?.org_tipo === "BERNHOEFT";
  const batchId = d.batch_id;
  async function downloadSource() {
    setSourceBusy(true);
    setSourceError("");
    try {
      await downloadBatchSource(batchId);
    } catch (err) {
      setSourceError(err instanceof Error ? err.message : "Falha ao baixar o arquivo original");
    } finally {
      setSourceBusy(false);
    }
  }
  return (
    <>
      <Link href="/painel/documentos" className="batch-back">
        <ArrowLeft size={16} /> Documentos
      </Link>
      <PageIntro
        eyebrow={`DOCUMENTO #${d.id} · LOTE #${d.batch_id} · ${d.aej ? `AEJ vínculo ${d.aej.worker_link_id}` : pageList(d.paginas)}`}
        title={typeLabels[d.tipo] ?? d.tipo}
        description={`Trabalhador ${d.worker_id ?? "não identificado"} · competência ${d.competencia ?? "não identificada"} · versão ${d.versao}`}
        action={<DocumentBadge status={d.status} />}
      />
      {d.aej && (me?.org_tipo === "BERNHOEFT" || me?.org_tipo === "FORNECEDORA") && (
        <section className="workspace-card">
          <h2>Documento estruturado AEJ</h2>
          <p>O arquivo original e as linhas de origem foram preservados. Assinatura P7S não validada.</p>
          <button className="button secondary" disabled={sourceBusy} onClick={() => void downloadSource()}>
            <Download size={16} /> {sourceBusy ? "Baixando…" : "Baixar arquivo AEJ original"}
          </button>
          {sourceError && <p className="api-error" role="alert">{sourceError}</p>}
          {bernhoeft && d.aej.days?.map((day) => (
            <div key={day.date} className="aej-day">
              <h3>{day.date} · horário {day.schedule_code ?? "não identificado"}</h3>
              <p className="muted">Jornada: {day.contract_minutes ?? "—"} min · trabalhado: {day.worked_minutes ?? "—"} min · excedente diário: {day.observed_daily_excess_minutes ?? "não calculado"} min</p>
              <p>Linhas de origem: {day.source_lines.join(", ") || "—"}</p>
            </div>
          ))}
        </section>
      )}
      {me?.org_tipo === "FORNECEDORA" && d.status === "PENDENTE_CORRECAO" && (
        <Link className="button secondary" href="/painel/pendencias" onClick={() => setContract(d.contract_id)}>
          Consultar correções deste contrato <ArrowUpRight size={16} />
        </Link>
      )}
      <div className="dashboard-grid">
        <section className="workspace-card">
          <h2>Leitura do documento</h2>
          <dl className="detail-list">
            {bernhoeft && d.confianca !== undefined && (
              <>
                <dt>Confiança da classificação</dt>
                <dd>{Math.round(d.confianca * 100)}%</dd>
              </>
            )}
            {bernhoeft && (
              <>
                <dt>Horas extras (h)</dt>
                <dd>{formatHours(d.campos.horas_extras_h)}</dd>
                <dt>Horas extras (R$)</dt>
                <dd>{money(d.campos.horas_extras_valor)}</dd>
                <dt>Líquido / valor pago</dt>
                <dd>{money(d.campos.valor_liquido ?? d.campos.valor_pago)}</dd>
                {d.campos.data_pagamento && (
                  <>
                    <dt>Data do pagamento</dt>
                    <dd>{d.campos.data_pagamento}</dd>
                  </>
                )}
              </>
            )}
            <dt>Motivos de pendência</dt>
            <dd>{d.motivos_pendencia.length ? d.motivos_pendencia.join("; ") : "—"}</dd>
            {bernhoeft && (
              <>
                <dt>Motivos de revisão (interno)</dt>
                <dd>{d.motivos_revisao?.length ? d.motivos_revisao.join("; ") : "—"}</dd>
              </>
            )}
          </dl>
          {bernhoeft && d.status === "REVISAO_HUMANA" && (
            <Link className="button" href={`/painel/revisao/detalhe?id=${d.id}`}>
              Revisar documento <ArrowUpRight size={16} />
            </Link>
          )}
        </section>
        <section className="workspace-card">
          <h2>Versões</h2>
          {d.versoes.length <= 1 ? (
            <p className="muted">Versão única deste documento.</p>
          ) : (
            <ol className="plain-list">
              {d.versoes.map((v) => (
                <li key={v.id}>
                  {v.id === d.id ? <strong>Versão {v.versao} (esta)</strong> : (
                    <Link href={`/painel/documentos/detalhe?id=${v.id}`}>Versão {v.versao}</Link>
                  )}{" "}
                  · lote #{v.batch_id} · <DocumentBadge status={v.status} />
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
      <DocumentViewer key={d.id} documentId={d.id} pages={d.paginas} />
    </>
  );
}
