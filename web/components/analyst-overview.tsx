"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowUpRight, ChartNoAxesCombined, CircleAlert, ClipboardCheck,
  Clock3, ShieldCheck, Users,
} from "lucide-react";
import { EmptyState, ErrorState, LoadingState, PageIntro } from "./workspace-parts";
import { type AnalystOverviewData } from "@/lib/api";
import { useApi } from "@/lib/use-api";

const percent = (value: number | null) =>
  value === null ? "—" : (value * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + "%";

const numero = (value: number) =>
  value.toLocaleString("pt-BR", { maximumFractionDigits: 2 });

function Indicador({
  label, value, hint, icon: Icon, tone = "purple",
}: {
  label: string;
  value: string;
  hint: string;
  icon: typeof Users;
  tone?: "purple" | "amber" | "green";
}) {
  return (
    <div className="stat-card">
      <span className={"stat-icon " + tone}><Icon size={20} /></span>
      <strong>{value}</strong>
      <span>{label}</span>
      <small className="stat-hint">{hint}</small>
    </div>
  );
}

export function AnalystOverview() {
  const [contratante, setContratante] = useState("");
  const [fornecedora, setFornecedora] = useState("");
  const [competencia, setCompetencia] = useState("");
  const [contrato, setContrato] = useState("");

  const params = new URLSearchParams();
  if (contratante) params.set("contratante_id", contratante);
  if (fornecedora) params.set("fornecedora_id", fornecedora);
  if (competencia) params.set("competencia", competencia);
  if (contrato) params.set("contract_id", contrato);
  const path = "/api/analyst/overview" + (params.size ? "?" + params.toString() : "");
  const { data, error, loading, reload } = useApi<AnalystOverviewData>(path);

  return (
    <>
      <PageIntro
        eyebrow="INTELIGÊNCIA TRABALHISTA"
        title="Visão geral das divergências."
        description="Priorize casos com base nas conciliações efetivamente realizadas. Os indicadores expressam indícios e limitações documentais, não irregularidades comprovadas."
        action={
          <Link className="button" href="/painel/revisao">
            <ClipboardCheck size={17} /> Abrir Fila de Exceções
          </Link>
        }
      />
      <section className="workspace-card analyst-filters" aria-label="Filtros de análise">
        <h2>Filtrar resultados</h2>
        <div className="analyst-filter-grid">
          <label className="filter-label">
            Contratante
            <select aria-label="Contratante" value={contratante} onChange={(e) => {
              setContratante(e.target.value);
              setFornecedora("");
              setContrato("");
              setCompetencia("");
            }}>
              <option value="">Todas as contratantes</option>
              {(data?.filtros.contratantes ?? []).map((item) => (
                <option key={item.id} value={item.id}>{item.nome}</option>
              ))}
            </select>
          </label>
          <label className="filter-label">
            Fornecedora
            <select aria-label="Fornecedora" value={fornecedora} onChange={(e) => {
              setFornecedora(e.target.value);
              setContrato("");
              setCompetencia("");
            }}>
              <option value="">Todas as fornecedoras</option>
              {(data?.filtros.fornecedoras ?? []).map((item) => (
                <option key={item.id} value={item.id}>{item.nome}</option>
              ))}
            </select>
          </label>
          <label className="filter-label">
            Competência
            <select aria-label="Competência" value={competencia} onChange={(e) => setCompetencia(e.target.value)}>
              <option value="">Mais recente disponível</option>
              {(data?.filtros.competencias ?? []).map((mes) => (
                <option key={mes} value={mes}>{mes}</option>
              ))}
            </select>
          </label>
          <label className="filter-label">
            Contrato (opcional)
            <select aria-label="Contrato (opcional)" value={contrato} onChange={(e) => {
              setContrato(e.target.value);
              setCompetencia("");
            }}>
              <option value="">Todos os contratos</option>
              {(data?.filtros.contratos ?? []).map((item) => (
                <option key={item.id} value={item.id}>{item.nome}</option>
              ))}
            </select>
          </label>
        </div>
        <p className="card-footnote">Os resultados são consolidados somente sobre os contratos aos quais o Analista tem acesso.</p>
      </section>
      {loading ? (
        <LoadingState text="Calculando indicadores trabalhistas…" />
      ) : error || !data ? (
        <ErrorState message={error ?? "Não foi possível obter os indicadores."} onRetry={reload} />
      ) : (
        <AnalystResults data={data} />
      )}
    </>
  );
}

function AnalystResults({ data }: { data: AnalystOverviewData }) {
  const m = data.resumo;
  const mes = data.filtros.competencia_selecionada;
  return (
    <>
      <p className="analyst-period">
        <Clock3 size={16} />
        {mes ? "Competência exibida: " + mes : "Nenhuma competência com conciliações disponíveis"}
        {" · " + m.cadastrados + " trabalhador(es) cadastrado(s) no escopo"}
      </p>
      <div className="stat-grid analyst-stat-grid">
        <Indicador
          icon={ChartNoAxesCombined}
          label="Taxa de divergências trabalhistas"
          value={percent(m.taxa_divergencias)}
          hint={m.divergencias + " com divergência entre " + m.avaliados + " analisado(s) validamente"}
          tone="amber"
        />
        <Indicador
          icon={ShieldCheck}
          label="Cobertura da análise"
          value={percent(m.cobertura)}
          hint={m.avaliados + " analisado(s) entre " + m.cadastrados + " cadastrado(s)"}
          tone="green"
        />
        <Indicador
          icon={Clock3}
          label="Horas extras divergentes"
          value={m.divergencias_sem_horas > 0 && m.horas_divergentes === 0 ? "—" : numero(m.horas_divergentes) + " h"}
          hint={m.divergencias_sem_horas > 0
            ? m.divergencias_sem_horas + " divergência(s) sem diferença numérica; total parcial"
            : "Soma dos módulos das diferenças em horas, sem conversão para R$"}
        />
        <Indicador
          icon={CircleAlert}
          label="Pendências críticas"
          value={numero(m.pendencias_criticas)}
          hint={"Análises bloqueadas ou em revisão; " + m.pendencias_abertas + " pendência(s) documental(is) aberta(s)"}
          tone="amber"
        />
      </div>
      <section className="workspace-card">
        <div className="card-title">
          <h2>Evolução mensal das divergências</h2>
          <span>Taxa entre trabalhadores analisados validamente</span>
        </div>
        {data.evolucao.length === 0 ? (
          <EmptyState
            title="Sem histórico de conciliações."
            text="A evolução aparecerá quando houver análises por competência."
          />
        ) : (
          <>
            {data.evolucao.length === 1 && (
              <p className="muted">Há apenas uma competência disponível; ainda não é possível avaliar uma tendência.</p>
            )}
            <div className="analyst-evolution">
              {data.evolucao.map((item) => (
                <div className="analyst-evolution-row" key={item.competencia}>
                  <strong>{item.competencia}</strong>
                  <div
                    className="analyst-meter"
                    role="meter"
                    aria-label={"Taxa de divergências em " + item.competencia}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={item.taxa_divergencias === null ? undefined : item.taxa_divergencias * 100}
                  >
                    <span style={{ width: (item.taxa_divergencias ?? 0) * 100 + "%" }} />
                  </div>
                  <span>{percent(item.taxa_divergencias)}</span>
                  <small>{item.divergencias}/{item.avaliados} analisados</small>
                </div>
              ))}
            </div>
          </>
        )}
      </section>
      {data.comparacao.length > 1 && (
        <section className="workspace-card">
          <h2>Comparação entre fornecedoras</h2>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr><th>Fornecedora</th><th>Analisados</th><th>Divergências</th><th>Taxa</th><th>Cobertura</th></tr>
              </thead>
              <tbody>
                {data.comparacao.map((item) => (
                  <tr key={item.id}>
                    <td>{item.nome}</td>
                    <td>{item.avaliados}</td>
                    <td>{item.divergencias}</td>
                    <td>{percent(item.taxa_divergencias)}</td>
                    <td>{percent(item.cobertura)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      <div className="next-step-card analyst-next">
        <p>{data.observacao} Quando não há trabalhadores analisados, a taxa é exibida como indisponível (—), nunca como zero.</p>
        <Link className="text-link" href="/painel/revisao">
          Consultar evidências e exceções <ArrowUpRight size={14} />
        </Link>
      </div>
    </>
  );
}
