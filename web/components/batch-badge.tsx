import { batchLabels, type BatchStatus } from "@/lib/batches";
export function BatchBadge({ status }: { status: BatchStatus }) {
  return (
    <span
      className={`status-badge ${status === "CONCLUIDO" ? "success" : status === "FALHA_PROCESSAMENTO" ? "danger" : status === "RECEBIDO" ? "neutral" : "review"}`}
    >
      <i />
      {batchLabels[status]}
    </span>
  );
}
