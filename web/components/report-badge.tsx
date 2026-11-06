import { reportStatusLabels, type ReportStatus } from "@/lib/reports";
export function ReportBadge({ status }: { status: ReportStatus }) {
  return (
    <span
      className={`status-badge ${status === "APROVADO_PUBLICADO" ? "success" : status === "EM_REVISAO" ? "review" : "neutral"}`}
    >
      <i />
      {reportStatusLabels[status]}
    </span>
  );
}
