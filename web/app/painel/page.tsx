"use client";
import Link from "next/link";
import { AnalystOverview } from "@/components/analyst-overview";
import {
  ArrowUpRight,
  CircleAlert,
  FileCheck2,
  Package,
  Timer,
  Upload,
  type LucideIcon,
} from "lucide-react";
import { useSession } from "@/components/demo-provider";
import { EmptyState, ErrorState, LoadingState, PageIntro } from "@/components/workspace-parts";
import { type Batch, type Issue } from "@/lib/api";
import { useApi } from "@/lib/use-api";

function Stat({ icon: Icon, label, value, hint, tone = "purple" }: {
  icon: LucideIcon;
  label: string;
  value: string | number;
  hint?: string;
  tone?: string;
}) {
  return (
    <div className="stat-card">
      <span className={`stat-icon ${tone}`}>
        <Icon size={20} />
      </span>
      <strong>{value}</strong>
      <span>{label}</span>
      {hint && <small className="stat-hint">{hint}</small>}
    </div>
  );
}

export default function Overview() {
  const { me } = useSession();
  if (!me) return null;
  return me.papel === "ANALISTA_BH" ? <AnalystOverview /> : <SupplierOverview />;
}

function SupplierOverview() {
  const batches = useApi<Batch[]>("/api/batches");
  const issues = useApi<Issue[]>("/api/supplier/issues");
  if (batches.loading || issues.loading) return <LoadingState />;
  const error = batches.error ?? issues.error;
  if (error) return <ErrorState message={error} onRetry={() => { void batches.reload(); void issues.reload(); }} />;
  const lotes = batches.data ?? [];
  const pend = issues.data ?? [];
  const abertas = pend.filter((i) => i.status !== "RESOLVIDA");
  return (
    <>
      <PageIntro
        eyebrow="ÁREA DA FORNECEDORA"
        title="Envios e correções em um só lugar."
        description="Envie lotes de documentos, acompanhe o processamento e responda às pendências com reenvio versionado."
        action={
          <Link className="button" href="/painel/envio">
            <Upload size={17} /> Enviar lote
          </Link>
        }
      />
      <div className="stat-grid">
        <Stat icon={Package} label="Lotes enviados" value={lotes.length} hint={`${lotes.filter((l) => l.status === "CONCLUIDO").length} concluídos`} />
        <Stat icon={Timer} label="Em processamento" value={lotes.filter((l) => l.status === "RECEBIDO" || l.status === "PROCESSANDO").length} />
        <Stat icon={CircleAlert} label="Pendências a responder" value={abertas.filter((i) => i.status !== "REENVIADA").length} tone="amber" />
        <Stat icon={FileCheck2} label="Pendências resolvidas" value={pend.length - abertas.length} tone="green" />
      </div>
      <section className="workspace-card">
        <div className="card-title">
          <h2>Pendências em aberto</h2>
          <Link href="/painel/pendencias" className="text-link">Responder <ArrowUpRight size={14} /></Link>
        </div>
        {abertas.length === 0 ? (
          <EmptyState title="Nenhuma pendência em aberto." text="Quando um documento precisar de correção, ele aparecerá aqui com motivo, evidência e prazo." />
        ) : (
          <ul className="plain-list">
            {abertas.slice(0, 5).map((i) => (
              <li key={i.id}>
                <strong>{i.worker_id ?? "—"} · {i.tipo_documento?.replaceAll("_", " ").toLowerCase()}</strong> — {i.motivo}
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
