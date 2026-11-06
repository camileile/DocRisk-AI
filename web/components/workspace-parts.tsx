import {
  documentLabels,
  issueLabels,
  type DocumentStatus,
  type IssueStatus,
} from "@/lib/demo";
export function DocumentBadge({
  status,
  supplier = false,
}: {
  status: DocumentStatus;
  supplier?: boolean;
}) {
  return (
    <span
      className={`status-badge ${status === "APTO" ? "success" : status === "PENDENTE_CORRECAO" ? "warning" : "review"}`}
    >
      <i />
      {supplier && status === "REVISAO_HUMANA"
        ? "Em análise"
        : documentLabels[status]}
    </span>
  );
}
export function IssueBadge({ status }: { status: IssueStatus }) {
  return (
    <span
      className={`status-badge ${status === "RESOLVIDA" ? "success" : status === "ABERTA" ? "warning" : "review"}`}
    >
      <i />
      {issueLabels[status]}
    </span>
  );
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
  action?: React.ReactNode;
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
