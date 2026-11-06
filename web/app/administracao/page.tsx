"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowUpRight, Building2, ClipboardList, Users } from "lucide-react";
import { EmptyState, ErrorState, LoadingState, PageIntro } from "@/components/workspace-parts";
import { type AdminOverview, type AdminRegistry } from "@/lib/api";
import { useApi } from "@/lib/use-api";

export default function AdminOverviewPage() {
  const [contratante, setContratante] = useState("");
  const registry = useApi<AdminRegistry>("/api/admin/registry");
  const params = new URLSearchParams();
  if (contratante) params.set("contratante_id", contratante);
  const report = useApi<AdminOverview>("/api/admin/overview" + (params.size ? "?" + params.toString() : ""));
  const data = report.data;
  const clients = (registry.data?.empresas ?? []).filter((e) => e.tipo === "CONTRATANTE");

  return (
    <>
      <PageIntro
        eyebrow="GESTÃO OPERACIONAL"
        title="Visão geral da organização."
        description="Acompanhe vínculos empresariais, contratos e desempenho da operação, sem dados de faturamento ou acesso aos documentos de trabalho dos analistas."
      />
      <section className="workspace-card">
        <label className="filter-label">
          Contratante
          <select aria-label="Filtrar contratante" value={contratante} onChange={(e) => setContratante(e.target.value)}>
            <option value="">Todas as contratantes</option>
            {clients.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
          </select>
        </label>
      </section>
      {registry.error && <ErrorState message={registry.error} onRetry={registry.reload} />}
      {report.loading || registry.loading ? <LoadingState /> : report.error || !data ? (
        <ErrorState message={report.error ?? "Não foi possível obter os indicadores."} onRetry={report.reload} />
      ) : (
        <>
          <div className="stat-grid admin-stat-grid">
            <div className="stat-card"><strong>{data.contratantes}</strong><span>Contratantes vinculadas</span></div>
            <div className="stat-card"><strong>{data.fornecedoras}</strong><span>Fornecedoras vinculadas</span></div>
            <div className="stat-card"><strong>{data.contratos_ativos}</strong><span>Contratos ativos</span></div>
            <div className="stat-card">
              <strong>{data.contratos_vencendo_30d}</strong>
              <span>Contratos vencendo em 30 dias</span>
              <small className="stat-hint">{data.contratos_sem_prazo} contrato(s) sem data de término informada</small>
            </div>
          </div>
          <div className="dashboard-grid">
            <section className="workspace-card">
              <div className="card-title"><h2>Desempenho operacional</h2></div>
              <table className="data-table compact">
                <tbody>
                  <tr><th scope="row">Documentos lógicos</th><td>{data.operacao.documentos.logicos}</td></tr>
                  <tr><th scope="row">Conciliações analisadas</th><td>{data.operacao.conciliacao.aptos}</td></tr>
                  <tr><th scope="row">Análises bloqueadas</th><td>{data.operacao.conciliacao.bloqueados}</td></tr>
                  <tr><th scope="row">Páginas lidas</th><td>{data.operacao.paginas.lidas}</td></tr>
                  <tr><th scope="row">Tempo médio por página</th><td>{data.operacao.paginas.tempo_medio_ms === null ? "—" : data.operacao.paginas.tempo_medio_ms + " ms"}</td></tr>
                </tbody>
              </table>
            </section>
            <section className="workspace-card">
              <div className="card-title"><h2>Qualidade e eficiência</h2></div>
              <table className="data-table compact">
                <tbody>
                  <tr><th scope="row">Divergências a verificar</th><td>{data.operacao.conciliacao.divergencias_a_verificar}</td></tr>
                  <tr><th scope="row">Pendências abertas</th><td>{data.operacao.pendencias.em_aberto}</td></tr>
                  <tr><th scope="row">Pareceres publicados</th><td>{data.operacao.pareceres_publicados}</td></tr>
                  <tr><th scope="row">Taxa de revisão humana</th><td>{data.operacao.documentos.taxa_revisao_humana === null ? "—" : (data.operacao.documentos.taxa_revisao_humana * 100).toFixed(1) + "%"}</td></tr>
                  <tr><th scope="row">Tempo médio de regularização</th><td>{data.operacao.pendencias.tempo_medio_regularizacao_h === null ? "—" : data.operacao.pendencias.tempo_medio_regularizacao_h.toFixed(1) + " h"}</td></tr>
                </tbody>
              </table>
            </section>
          </div>
          <section className="workspace-card">
            <div className="card-title"><h2>Atalhos administrativos</h2></div>
            {clients.length === 0 ? (
              <EmptyState title="Nenhuma contratante cadastrada." text="Cadastre a primeira contratante em Empresas e Contratos." />
            ) : (
              <p className="muted">Os indicadores acima se referem exclusivamente às relações contratuais da organização auditora.</p>
            )}
            <div className="admin-actions">
              <Link className="button secondary" href="/administracao/empresas"><Building2 size={16} /> Empresas e Contratos <ArrowUpRight size={14}/></Link>
              <Link className="button secondary" href="/administracao/usuarios"><Users size={16} /> Gestão de Usuários <ArrowUpRight size={14}/></Link>
              <Link className="button secondary" href="/administracao/auditoria"><ClipboardList size={16} /> Auditoria <ArrowUpRight size={14}/></Link>
            </div>
          </section>
        </>
      )}
    </>
  );
}
