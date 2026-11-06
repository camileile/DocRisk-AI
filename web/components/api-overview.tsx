"use client";

import Link from "next/link";
import { CheckCheck, Clock3, Package, RefreshCw, CircleAlert, ArrowRight, Upload } from "lucide-react";
import { PageIntro, EmptyState } from "@/components/workspace-parts";
import { BatchBadge } from "@/components/batch-badge";
import { useDemo } from "@/components/demo-provider";
import { useApiBatches } from "@/hooks/use-api-batches";
import { formatApiDate } from "@/lib/api-client";

export function ApiOverview() {
  const { apiSession, contract } = useDemo();
  const { items, loading, error, refresh } = useApiBatches(apiSession?.token ?? "");
  if (!apiSession) return null;

  const context = items.filter((item) =>
    item.contract_id === contract &&
    apiSession.contracts.some((entry) => entry.id === item.contract_id)
  );
  const waiting = context.filter((item) => item.status === "RECEBIDO" || item.status === "PROCESSANDO").length;
  const done = context.filter((item) => item.status === "CONCLUIDO").length;
  const failed = context.filter((item) => item.status === "FALHA_PROCESSAMENTO").length;

  return (
    <>
      <PageIntro
        eyebrow="API F1 · AMBIENTE DE TESTES"
        title="Seu contrato, seus lotes."
        description={"Acesso confirmado como " + apiSession.user.nome + ". Os indicadores abaixo são derivados de registros consultados na API."}
        action={
          <div className="api-page-actions">
            {apiSession.user.org_tipo === "FORNECEDORA" && (
              <Link className="button" href="/painel/envio"><Upload size={17}/> Enviar arquivo</Link>
            )}
            <button type="button" className="button secondary" disabled={loading} onClick={refresh}>
              <RefreshCw size={17} /> {loading ? "Atualizando…" : "Atualizar dados"}
            </button>
          </div>
        }
      />
      {apiSession.contracts.length === 0 && (
        <div className="inline-info"><CircleAlert size={18}/><p>A API não retornou contratos autorizados para este usuário. Entre com outro usuário de teste ou cadastre um contrato no backend.</p></div>
      )}
      <div className="stat-grid">
        {[
          { icon: Package, label: "Lotes no contrato", value: context.length, tone: "purple" },
          { icon: Clock3, label: "Em fila ou processamento", value: waiting, tone: "purple" },
          { icon: CheckCheck, label: "Concluídos", value: done, tone: "green" },
          { icon: CircleAlert, label: "Falhas técnicas", value: failed, tone: "amber" },
        ].map(({ icon: Icon, label, value, tone }) => (
          <article className="stat-card" key={label}>
            <div className={"stat-icon " + tone}><Icon size={20}/></div>
            <strong>{loading ? "—" : value}</strong><span>{label}</span>
          </article>
        ))}
      </div>
      <div className="inline-info">
        <CircleAlert size={18} />
        <p>Indicadores de processamento documental da API F1. Não representam conciliação, conformidade ou parecer final. O envio real, a revisão e a F3 serão integrados em etapas posteriores.</p>
      </div>
      <section className="workspace-card">
        <div className="card-title">
          <h2>Últimos lotes do contrato</h2>
          <Link href="/painel/lotes">Ver todos <ArrowRight size={15}/></Link>
        </div>
        {loading && <p className="api-status" role="status">Carregando informações da API…</p>}
        {error && <p className="api-error" role="alert">{error}</p>}
        {!loading && !error && (!context.length ? (
          <EmptyState title="Ainda não há lotes" text="Quando o backend receber arquivos neste contrato, eles aparecerão aqui." />
        ) : (
          <div className="api-overview-list">
            {context.slice(0, 5).map((batch) => (
              <div className="api-overview-row" key={batch.id}>
                <div><strong>#{batch.id} · {batch.filename}</strong><small>{formatApiDate(batch.created_at)} · {batch.tipo_arquivo}</small></div>
                <BatchBadge status={batch.status}/>
              </div>
            ))}
          </div>
        ))}
      </section>
    </>
  );
}
