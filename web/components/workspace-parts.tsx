"use client";
import { useEffect, useState, type ReactNode } from "react";
import { LoaderCircle, TriangleAlert } from "lucide-react";
import {
  analysisStatusLabels,
  apiBlob,
  batchStatusLabels,
  docStatusLabels,
  issueStatusLabels,
  resultLabels,
  type BatchStatus,
  type DocStatus,
  type IssueStatus,
} from "@/lib/api";

type Tone = "success" | "warning" | "review" | "danger" | "neutral";

function Badge({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span className={`status-badge ${tone}`}>
      <i />
      {children}
    </span>
  );
}

export function DocumentBadge({ status }: { status: DocStatus }) {
  const tone: Tone =
    status === "APTO" ? "success" : status === "PENDENTE_CORRECAO" ? "warning" : status === "SUBSTITUIDO" ? "neutral" : "review";
  return <Badge tone={tone}>{docStatusLabels[status] ?? status}</Badge>;
}

export function IssueBadge({ status }: { status: IssueStatus }) {
  const tone: Tone =
    status === "RESOLVIDA" ? "success" : status === "REENVIADA" ? "review" : "warning";
  return <Badge tone={tone}>{issueStatusLabels[status] ?? status}</Badge>;
}

export function BatchBadge({ status }: { status: BatchStatus }) {
  const tone: Tone =
    status === "CONCLUIDO" ? "success" : status === "FALHA_PROCESSAMENTO" ? "warning" : "review";
  return <Badge tone={tone}>{batchStatusLabels[status] ?? status}</Badge>;
}

export function AnalysisBadge({ status, result }: { status: string; result?: string }) {
  if (status !== "ANALISADA")
    return <Badge tone={status === "BLOQUEADA_PENDENCIA" ? "warning" : "review"}>{analysisStatusLabels[status] ?? status}</Badge>;
  const tone: Tone =
    result === "DIVERGENCIA_A_VERIFICAR" ? "warning" : result === "DADOS_INSUFICIENTES" ? "review" : "success";
  return <Badge tone={tone}>{resultLabels[result ?? ""] ?? result}</Badge>;
}

export function PageIntro({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-intro">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}

export function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="workspace-empty">
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}

export function LoadingState({ text = "Carregando dados da API…" }: { text?: string }) {
  return (
    <div className="workspace-empty" role="status" aria-live="polite">
      <LoaderCircle className="spin" size={22} />
      <p>{text}</p>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="workspace-empty api-error" role="alert">
      <TriangleAlert size={22} />
      <strong>Não foi possível carregar.</strong>
      <p>{message}</p>
      {onRetry && (
        <button className="button secondary" onClick={onRetry}>
          Tentar novamente
        </button>
      )}
    </div>
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "success" | "error"; children: ReactNode }) {
  return (
    <div className={`api-notice ${tone}`} role={tone === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

/* Imagem de página protegida: baixada com o token e exibida como blob. */
export function PageImage({ pageId, alt, className }: { pageId: number; alt: string; className?: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl: string | null = null;
    let active = true;
    setUrl(null);
    setFailed(false);
    apiBlob(`/api/pages/${pageId}/image`, { signal: controller.signal })
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => active && setFailed(true));
    return () => {
      active = false;
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [pageId]);
  if (failed) return <div className={`page-image placeholder ${className ?? ""}`}>Imagem indisponível</div>;
  if (!url) return <div className={`page-image placeholder ${className ?? ""}`}>Carregando página…</div>;
  return <img className={`page-image ${className ?? ""}`} src={url} alt={alt} />;
}

/* Trecho da busca: o backend marca o termo com [[ ]] e já escapa o HTML; aqui o
 * texto é dividido e renderizado como texto puro (nunca dangerouslySetInnerHTML). */
export function Snippet({ text }: { text: string }) {
  const decoded = text
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&amp;/g, "&");
  const parts = decoded.split(/(\[\[.*?\]\])/g);
  return (
    <span>
      {parts.map((part, i) =>
        part.startsWith("[[") && part.endsWith("]]") ? <mark key={i}>{part.slice(2, -2)}</mark> : <span key={i}>{part}</span>,
      )}
    </span>
  );
}
