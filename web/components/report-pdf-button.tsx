"use client";
import { useRef, useState } from "react";
import { Download } from "lucide-react";
import { downloadReportPdf, type Report } from "@/lib/api";
import { useSession } from "./demo-provider";
export function ReportPdfButton({ report, disabled = false }: { report: Report; disabled?: boolean }) {
  const { isDemo } = useSession();
  const running = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function download() {
    if (running.current) return;
    running.current = true; setBusy(true); setError("");
    try { await downloadReportPdf(report.id,report.versao,report.status === "RASCUNHO" ? report.conteudo_sha256 : undefined); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível exportar o PDF."); }
    finally { running.current = false; setBusy(false); }
  }
  return <div><button type="button" className="button secondary" disabled={isDemo || disabled || busy} onClick={() => void download()}><Download size={16} />{busy ? "Gerando PDF…" : report.status === "RASCUNHO" ? "PDF da prévia" : "Baixar PDF"}</button>{error && <p role="alert" className="api-error">{error}</p>}</div>;
}
