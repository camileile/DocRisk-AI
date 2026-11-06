"use client";
import Link from "next/link";
import { ArrowLeft, ArrowRight, ShieldCheck } from "lucide-react";
import { publishedReports } from "@/lib/published-reports";
import { useDemo } from "./demo-provider";
import { PageIntro } from "./report-ui";
import { ReportContent } from "./report-content";
export function PublicReportDetail({ id }: { id: string }) {
  const { role, competence, setCompetence } = useDemo();
  const report = publishedReports.find(
    (p) => p.id === id && p.contract === "CTR-001",
  );
  if (role !== "GESTOR_CONTR" || !report)
    return (
      <>
        <PageIntro
          eyebrow="PARECERES PUBLICADOS"
          title="Parecer indisponível."
          description="Este parecer não está disponível para consulta nesta perspectiva."
        />
        <Link href="/contratante" className="button secondary">
          Voltar ao portal
        </Link>
      </>
    );
  if (report.competence !== competence)
    return (
      <>
        <PageIntro
          eyebrow="CONTEXTO DA CONSULTA"
          title="Selecione a competência do parecer."
          description={`Este parecer pertence à competência ${report.competence}.`}
        />
        <button
          className="button"
          onClick={() => setCompetence(report.competence)}
        >
          Consultar esta competência <ArrowRight size={16} />
        </button>
      </>
    );
  return (
    <>
      <Link className="back-link batch-back" href="/contratante">
        <ArrowLeft size={15} /> Pareceres publicados
      </Link>
      <PageIntro
        eyebrow="VERSÃO APROVADA E PUBLICADA · EXEMPLO"
        title={report.id}
        description={`Competência ${report.competence} · versão ${report.version}`}
        action={
          <span className="status-badge success">
            <i />
            Consulta
          </span>
        }
      />
      <div className="inline-info">
        <ShieldCheck size={18} />
        <p>
          Exemplo aprovado por {report.approvedBy}, em{" "}
          {new Intl.DateTimeFormat("pt-BR", {
            timeZone: "America/Recife",
            dateStyle: "short",
            timeStyle: "short",
          }).format(new Date(report.approvedAt))}{" "}
          (Recife). O conteúdo desta versão é fixo; nenhuma publicação foi
          realizada nesta demonstração.
        </p>
      </div>
      <ReportContent report={report} />
    </>
  );
}
