"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, FileUp } from "lucide-react";
import { useSession } from "@/components/demo-provider";
import {
  EmptyState,
  ErrorState,
  IssueBadge,
  LoadingState,
  Notice,
  PageIntro,
} from "@/components/workspace-parts";
import { api, formatDate, issueCategoryLabels, issueStatusLabels, typeLabels, type Issue } from "@/lib/api";
import { validateApiUploadFile } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";

const OPEN = ["ABERTA", "NOTIFICADA", "REABERTA"];

export default function IssuesPage() {
  const { me, contract, isDemo } = useSession();
  const supplier = me?.org_tipo === "FORNECEDORA";
  const { data, error, loading, reload } = useApi<Issue[]>(supplier ? "/api/supplier/issues" : "/api/issues");
  const [filter, setFilter] = useState<"abertas" | "todas">("abertas");
  const [sent, setSent] = useState<{ issue: number; batch: number } | null>(null);
  const rows = (data ?? [])
    .filter((i) => !contract || i.contract_id === contract)
    .filter((i) => filter === "todas" || i.status !== "RESOLVIDA");
  return (
    <>
      <PageIntro
        eyebrow="PENDÊNCIAS DOCUMENTAIS"
        title={supplier ? "O que precisa ser corrigido." : "Devoluções à fornecedora."}
        description="Cada pendência traz motivo objetivo, evidência (lote e página), ação solicitada e prazo. O reenvio cria uma nova versão sem apagar o histórico."
      />
      {isDemo && <Notice>Os reenvios são desativados nesta demonstração fictícia.</Notice>}
      <div className="list-toolbar">
        <div className="segmented" role="group" aria-label="Filtrar pendências">
          <button className={filter === "abertas" ? "selected" : ""} onClick={() => setFilter("abertas")}>Em aberto</button>
          <button className={filter === "todas" ? "selected" : ""} onClick={() => setFilter("todas")}>Todas</button>
        </div>
      </div>
      {sent && (
        <Notice tone="success">
          Reenvio da pendência #{sent.issue} recebido (lote #{sent.batch}). A nova versão é processada e a pendência é
          resolvida ou reaberta automaticamente.{" "}
          <Link href={`/painel/lotes/detalhe?id=${sent.batch}`}>Acompanhar <ArrowUpRight size={13} /></Link>
        </Notice>
      )}
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : rows.length === 0 ? (
        <EmptyState title="Nenhuma pendência." text={filter === "abertas" ? "Não há pendências em aberto neste contrato." : "Nenhuma pendência registrada."} />
      ) : (
        <div className="issue-list">
          {rows.map((i) => (
            <IssueCard
              key={i.id}
              issue={i}
              canResubmit={!isDemo && supplier && OPEN.includes(i.status)}
              onSent={(batch) => {
                setSent({ issue: i.id, batch });
                void reload();
              }}
            />
          ))}
        </div>
      )}
    </>
  );
}

function IssueCard({ issue: i, canResubmit, onSent }: { issue: Issue; canResubmit: boolean; onSent: (batch: number) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  async function resubmit() {
    if (!file || busy) return;
    const invalid = validateApiUploadFile(file);
    if (invalid) { setFeedback(invalid); return; }
    setBusy(true);
    setFeedback(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const r = await api<{ batch_id: number }>(`/api/issues/${i.id}/resubmit`, { method: "POST", body: form });
      setFile(null);
      onSent(r.batch_id);
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : "Falha no reenvio");
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className="workspace-card issue-card">
      <header>
        <div>
          <span className="eyebrow">PENDÊNCIA #{i.id} · {issueCategoryLabels[i.categoria] ?? i.categoria}</span>
          <h2>
            {typeLabels[i.tipo_documento ?? ""] ?? i.tipo_documento ?? "Documento"} · {i.worker_id ?? "trabalhador não identificado"} ·{" "}
            {i.competencia ?? "—"}
          </h2>
        </div>
        <IssueBadge status={i.status} />
      </header>
      <dl className="detail-list">
        <dt>Motivo</dt>
        <dd>{i.motivo}</dd>
        <dt>Evidência</dt>
        <dd>{i.evidencia ?? "—"}</dd>
        <dt>Ação solicitada</dt>
        <dd>{i.acao}</dd>
        <dt>Prazo</dt>
        <dd>{i.prazo ? new Date(`${i.prazo.slice(0, 10)}T12:00:00`).toLocaleDateString("pt-BR") : "—"}</dd>
      </dl>
      {i.historico.length > 0 && (
        <details>
          <summary>Histórico ({i.historico.length})</summary>
          <ol className="plain-list">
            {i.historico.map((h, n) => (
              <li key={n}>
                {formatDate(h.em)} · <strong>{issueStatusLabels[h.status as keyof typeof issueStatusLabels] ?? h.status}</strong>
                {h.motivo ? ` — ${h.motivo}` : ""}
                {h.lote ? ` (lote #${h.lote})` : ""}
              </li>
            ))}
          </ol>
        </details>
      )}
      {canResubmit && (
        <div className="inline-form">
          <label className="filter-label">
            Documento corrigido
            <input type="file" accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.aej,.txt" disabled={busy} onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>
          <button className="button" disabled={!file || busy} onClick={resubmit}>
            <FileUp size={16} /> {busy ? "Enviando…" : "Reenviar"}
          </button>
        </div>
      )}
      {feedback && <Notice tone="error">{feedback}</Notice>}
    </article>
  );
}
