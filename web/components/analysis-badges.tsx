import {
  analysisStatusLabels,
  analysisResultLabels,
  type AnalysisStatus,
  type AnalysisResult,
} from "@/lib/analyses";
export function AnalysisStatusBadge({ status }: { status: AnalysisStatus }) {
  return (
    <span
      className={`status-badge ${status === "ANALISADA" ? "neutral" : status === "BLOQUEADA_PENDENCIA" ? "warning" : status === "REVISAO_HUMANA" ? "review" : "neutral"}`}
    >
      <i />
      {analysisStatusLabels[status]}
    </span>
  );
}
export function AnalysisResultBadge({ result }: { result: AnalysisResult }) {
  return (
    <span
      className={`status-badge result-badge ${result === "SEM_DIVERGENCIA_NOS_CAMPOS_COMPARADOS" ? "success" : result === "DIVERGENCIA_A_VERIFICAR" || result === "DADOS_INSUFICIENTES" ? "warning" : "neutral"}`}
    >
      <i />
      {analysisResultLabels[result]}
    </span>
  );
}
