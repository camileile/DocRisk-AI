"use client";

import { useState } from "react";
import { useSession } from "@/components/demo-provider";
import { EmptyState, ErrorState, LoadingState, Notice, PageIntro } from "@/components/workspace-parts";
import { api, type AdminRegistry } from "@/lib/api";
import { useApi } from "@/lib/use-api";

type Tipo = "CONTRATANTE" | "FORNECEDORA";

export default function CompaniesPage() {
  const { isDemo } = useSession();
  const registry = useApi<AdminRegistry>("/api/admin/registry");
  const [tipo, setTipo] = useState<Tipo>("CONTRATANTE");
  const [nome, setNome] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [contratante, setContratante] = useState("");
  const [contratoNome, setContratoNome] = useState("");
  const [relContratante, setRelContratante] = useState("");
  const [relFornecedora, setRelFornecedora] = useState("");
  const [relNome, setRelNome] = useState("");
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [failed, setFailed] = useState<string | null>(null);

  const empresas = registry.data?.empresas ?? [];
  const clientes = empresas.filter((e) => e.tipo === "CONTRATANTE");
  const fornecedoras = empresas.filter((e) => e.tipo === "FORNECEDORA");
  const contratos = registry.data?.contratos ?? [];

  async function submitCompany() {
    if (isDemo || !nome.trim() || (tipo === "FORNECEDORA" && (!contratante || !contratoNome.trim()))) return;
    setBusy(true);
    setFeedback(null);
    setFailed(null);
    try {
      await api("/api/admin/companies", {
        method: "POST",
        body: JSON.stringify({
          tipo, nome: nome.trim(), cnpj: cnpj.trim() || null,
          contratante_id: tipo === "FORNECEDORA" ? contratante : null,
          contrato_nome: tipo === "FORNECEDORA" ? contratoNome.trim() : null,
        }),
      });
      setFeedback(tipo === "FORNECEDORA"
        ? "Fornecedora cadastrada com vínculo contratual inicial."
        : "Contratante cadastrada. Agora é possível vincular fornecedoras.");
      setNome("");
      setCnpj("");
      setContratoNome("");
      void registry.reload();
    } catch (e) {
      setFailed(e instanceof Error ? e.message : "Não foi possível cadastrar a empresa.");
    } finally {
      setBusy(false);
    }
  }

  async function submitContract() {
    if (isDemo || !relContratante || !relFornecedora || !relNome.trim()) return;
    setBusy(true);
    setFeedback(null);
    setFailed(null);
    try {
      await api("/api/admin/contracts", {
        method: "POST",
        body: JSON.stringify({
          nome: relNome.trim(), contratante_id: relContratante,
          fornecedora_id: relFornecedora, inicio: inicio || null, fim: fim || null,
        }),
      });
      setFeedback("Vínculo contratual criado entre as empresas existentes, sem duplicar cadastros.");
      setRelNome("");
      setInicio("");
      setFim("");
      void registry.reload();
    } catch (e) {
      setFailed(e instanceof Error ? e.message : "Não foi possível vincular as empresas.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageIntro
        eyebrow="ESTRUTURA CONTRATUAL"
        title="Empresas e Contratos."
        description="Cadastre contratantes e fornecedoras separadamente. Cada fornecedora começa vinculada a uma contratante e pode atuar em outros contratos sem criar uma segunda identidade empresarial."
      />
      {isDemo && <Notice>A demonstração offline permite navegar e consultar dados fictícios; cadastros ficam desativados.</Notice>}
      {feedback && <Notice tone="success">{feedback}</Notice>}
      {failed && <Notice tone="error">{failed}</Notice>}
      <div className="dashboard-grid admin-forms-grid">
        <section className="workspace-card">
          <h2>Cadastrar empresa</h2>
          <div className="admin-form">
            <label>Tipo de empresa
              <select aria-label="Tipo da empresa" value={tipo} onChange={(e) => setTipo(e.target.value as Tipo)}>
                <option value="CONTRATANTE">Contratante</option>
                <option value="FORNECEDORA">Fornecedora</option>
              </select>
            </label>
            <label>Razão social ou identificação empresarial
              <input aria-label="Nome da empresa" value={nome} maxLength={160} onChange={(e) => setNome(e.target.value)} placeholder="Nome da empresa" />
            </label>
            <label>CNPJ (opcional no MVP)
              <input aria-label="CNPJ" value={cnpj} maxLength={32} onChange={(e) => setCnpj(e.target.value)} placeholder="Identificação empresarial" />
            </label>
            {tipo === "FORNECEDORA" && (
              <>
                <label>Contratante vinculada
                  <select aria-label="Contratante vinculada" value={contratante} onChange={(e) => setContratante(e.target.value)}>
                    <option value="">Selecione uma contratante</option>
                    {clientes.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
                  </select>
                </label>
                <label>Nome do contrato inicial
                  <input aria-label="Contrato inicial" value={contratoNome} maxLength={160} onChange={(e) => setContratoNome(e.target.value)} placeholder="Objeto ou nome do contrato" />
                </label>
              </>
            )}
            <button className="button" disabled={isDemo || busy || nome.trim().length < 2 || (tipo === "FORNECEDORA" && (!contratante || contratoNome.trim().length < 3))} onClick={submitCompany}>
              {busy ? "Salvando…" : "Cadastrar empresa"}
            </button>
          </div>
        </section>
        <section className="workspace-card">
          <h2>Vincular empresas existentes</h2>
          <p className="muted admin-form-intro">Use este formulário quando uma fornecedora já cadastrada assumir outro contrato.</p>
          <div className="admin-form">
            <label>Contratante
              <select aria-label="Contratante para contrato" value={relContratante} onChange={(e) => setRelContratante(e.target.value)}>
                <option value="">Selecione uma contratante</option>
                {clientes.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
              </select>
            </label>
            <label>Fornecedora
              <select aria-label="Fornecedora para contrato" value={relFornecedora} onChange={(e) => setRelFornecedora(e.target.value)}>
                <option value="">Selecione uma fornecedora</option>
                {fornecedoras.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
              </select>
            </label>
            <label>Identificação do contrato
              <input aria-label="Nome do contrato" value={relNome} maxLength={160} onChange={(e) => setRelNome(e.target.value)} placeholder="Objeto ou contrato" />
            </label>
            <div className="admin-date-row">
              <label>Início (opcional)<input type="date" aria-label="Início do contrato" value={inicio} onChange={(e) => setInicio(e.target.value)} /></label>
              <label>Término (opcional)<input type="date" aria-label="Término do contrato" value={fim} min={inicio || undefined} onChange={(e) => setFim(e.target.value)} /></label>
            </div>
            <button className="button secondary" disabled={isDemo || busy || !relContratante || !relFornecedora || relNome.trim().length < 3 || Boolean(inicio && fim && inicio > fim)} onClick={submitContract}>
              {busy ? "Salvando…" : "Criar vínculo contratual"}
            </button>
          </div>
        </section>
      </div>
      {registry.loading ? <LoadingState /> : registry.error ? (
        <ErrorState message={registry.error} onRetry={registry.reload} />
      ) : (
        <>
          <section className="workspace-card">
            <div className="card-title"><h2>Contratantes ({clientes.length})</h2></div>
            {clientes.length === 0 ? <EmptyState title="Nenhuma contratante." text="Cadastre uma contratante para começar." /> : (
              <div className="table-scroll"><table className="data-table"><thead><tr><th>Empresa</th><th>Identificador</th><th>CNPJ</th></tr></thead><tbody>
                {clientes.map((c) => <tr key={c.id}><td>{c.nome}</td><td>{c.id}</td><td>{c.cnpj ?? "Não informado"}</td></tr>)}
              </tbody></table></div>
            )}
          </section>
          <section className="workspace-card">
            <div className="card-title"><h2>Fornecedoras ({fornecedoras.length})</h2></div>
            {fornecedoras.length === 0 ? <EmptyState title="Nenhuma fornecedora." text="Cadastre uma fornecedora e vincule uma contratante." /> : (
              <div className="table-scroll"><table className="data-table"><thead><tr><th>Empresa</th><th>Identificador</th><th>Contratantes vinculadas</th></tr></thead><tbody>
                {fornecedoras.map((f) => <tr key={f.id}>
                  <td>{f.nome}</td><td>{f.id}</td>
                  <td>{new Set(contratos.filter((c) => c.fornecedora_id === f.id).map((c) => c.contratante_id)).size}</td>
                </tr>)}
              </tbody></table></div>
            )}
          </section>
          <section className="workspace-card">
            <div className="card-title"><h2>Contratos ({contratos.length})</h2></div>
            {contratos.length === 0 ? <EmptyState title="Nenhum vínculo contratado." text="Crie um vínculo entre uma contratante e uma fornecedora." /> : (
              <div className="table-scroll"><table className="data-table"><thead><tr><th>Contrato</th><th>Contratante</th><th>Fornecedora</th><th>Situação</th><th>Término</th></tr></thead><tbody>
                {contratos.map((c) => <tr key={c.id}>
                  <td>{c.nome}<small>{c.id}</small></td><td>{c.contratante_nome}</td><td>{c.fornecedora_nome}</td>
                  <td>{c.status}</td><td>{c.fim ? new Date(c.fim + "T12:00:00").toLocaleDateString("pt-BR") : "Não informado"}</td>
                </tr>)}
              </tbody></table></div>
            )}
          </section>
        </>
      )}
    </>
  );
}
