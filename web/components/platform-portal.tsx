"use client";
import { useState, type FormEvent } from "react";
import { useSession } from "./demo-provider";
import { ErrorState, LoadingState, Notice, PageIntro } from "./workspace-parts";
import { api, formatDate } from "@/lib/api";
import { useApi } from "@/lib/use-api";

type Registry = {
  auditoras: { id: string; nome: string; contratos: number }[];
  administradores: { id: string; nome: string; org_id: string; ativo: number }[];
  modulos: { id: string; nome: string; status: string }[];
  configuracoes: { nome: string; contato: string };
  auditoria: { id: number; acao: string; alvo: string; resultado: string; instante: string }[];
};

export function PlatformPortal({ view }: { view: "overview" | "auditors" | "settings" }) {
  const { isDemo } = useSession();
  const { data, loading, error, reload } = useApi<Registry>("/api/platform/registry");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [failure, setFailure] = useState("");
  const [token, setToken] = useState("");
  async function mutate(path: string, method: string, body: object) {
    setBusy(true); setMessage(""); setFailure(""); setToken("");
    try {
      const result = await api<{ token_teste?: string }>(path, { method, body: JSON.stringify(body) });
      setToken(result.token_teste ?? ""); setMessage("Alteração salva no ambiente de testes."); await reload();
      return true;
    } catch (err) { setFailure(err instanceof Error ? err.message : "Falha ao salvar."); return false; }
    finally { setBusy(false); }
  }
  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={error ?? "Falha ao consultar a plataforma."} onRetry={reload} />;
  const disabled = isDemo || busy;
  return <>
    <PageIntro eyebrow="ADMINISTRAÇÃO GERAL" title={view === "overview" ? "Estrutura do DocRisk AI." : view === "auditors" ? "Organizações auditoras." : "Dados institucionais da plataforma."}
      description="Administração institucional independente da operação Bernhoeft. Documentos, análises e pareceres permanecem nas áreas operacionais autorizadas." />
    <Notice>{isDemo ? "Demonstração offline somente para consulta." : "Alterações disponíveis somente no modo de testes. Autenticação corporativa e convites ainda pendentes."}</Notice>
    {message && <Notice tone="success">{message}</Notice>}{failure && <Notice tone="error">{failure}</Notice>}
    {token && <section className="workspace-card"><h2>Acesso inicial do administrador da auditora</h2><p>Token exibido apenas neste cadastro. Use em “Conectar API de testes”.</p><label className="filter-label">Token de teste<input aria-label="Token do administrador da auditora" value={token} readOnly /></label><button className="button secondary" onClick={() => setToken("")}>Ocultar token</button></section>}
    {view === "overview" && <>
      <div className="stat-grid"><div className="stat-card"><strong>{data.auditoras.length}</strong><span>Organizações auditoras</span></div><div className="stat-card"><strong>{data.administradores.filter((u) => u.ativo).length}</strong><span>Administradores de auditoras ativos</span></div></div>
      <section className="workspace-card"><h2>Catálogo de módulos</h2><ul className="plain-list">{data.modulos.map((m) => <li key={m.id}><strong>{m.nome}</strong> · {m.status === "MVP" ? "MVP em desenvolvimento" : "Planejado — sem funcionalidade no MVP"}</li>)}</ul><p className="card-footnote">O catálogo é informativo. Não há liberação fictícia dos módulos futuros.</p></section>
      <section className="workspace-card"><h2>Auditoria da administração geral</h2>{data.auditoria.length ? <ul className="plain-list">{data.auditoria.map((e) => <li key={e.id}>{formatDate(e.instante)} · {e.acao} · {e.alvo} · {e.resultado}</li>)}</ul> : <p>Nenhuma alteração institucional registrada.</p>}</section>
    </>}
    {view === "auditors" && <>
      <AuditorForm disabled={disabled} onSave={(body) => mutate("/api/platform/auditors", "POST", body)} />
      {data.auditoras.map((o) => <section className="workspace-card" key={o.id}><h2>{o.nome}</h2><p>{o.contratos} contrato(s) vinculado(s). A gestão de empresas e contratos é feita pela própria auditora.</p><div className="table-scroll"><table className="data-table"><thead><tr><th>Administrador</th><th>Situação</th><th>Acesso</th></tr></thead><tbody>{data.administradores.filter((u) => u.org_id === o.id).map((u) => <tr key={u.id}><td>{u.nome}</td><td>{u.ativo ? "Ativo" : "Inativo"}</td><td><button className="button secondary" disabled={disabled} aria-label={`${u.ativo ? "Desativar" : "Reativar"} ${u.nome}`} onClick={() => void mutate(`/api/platform/administrators/${encodeURIComponent(u.id)}/status`, "PATCH", { ativo: !u.ativo })}>{u.ativo ? "Desativar" : "Reativar"}</button></td></tr>)}</tbody></table></div></section>)}
    </>}
    {view === "settings" && <SettingsForm key={JSON.stringify(data.configuracoes)} settings={data.configuracoes} disabled={disabled} onSave={(body) => mutate("/api/platform/settings", "PATCH", body)} />}
  </>;
}

function AuditorForm({ disabled, onSave }: { disabled: boolean; onSave: (body: object) => Promise<boolean> }) {
  const [name, setName] = useState(""); const [admin, setAdmin] = useState("");
  async function submit(e: FormEvent) { e.preventDefault(); if (await onSave({ nome: name.trim(), administrador: admin.trim() })) { setName(""); setAdmin(""); } }
  return <section className="workspace-card"><h2>Cadastrar auditora e administrador inicial</h2><form className="inline-form" onSubmit={(e) => void submit(e)}><label className="filter-label">Nome da auditora<input required minLength={2} maxLength={160} disabled={disabled} value={name} onChange={(e) => setName(e.target.value)} /></label><label className="filter-label">Administrador inicial<input required minLength={2} maxLength={140} disabled={disabled} value={admin} onChange={(e) => setAdmin(e.target.value)} /></label><button className="button" disabled={disabled || name.trim().length < 2 || admin.trim().length < 2}>Cadastrar auditora</button></form></section>;
}
function SettingsForm({ settings, disabled, onSave }: { settings: Registry["configuracoes"]; disabled: boolean; onSave: (body: object) => Promise<boolean> }) {
  const [name, setName] = useState(settings.nome); const [contact, setContact] = useState(settings.contato);
  return <section className="workspace-card"><h2>Cadastro institucional</h2><p>Esses dados identificam a plataforma neste cadastro. Não alteram marca, domínio, autenticação ou regras de análise.</p><form className="inline-form" onSubmit={(e) => { e.preventDefault(); void onSave({ nome: name.trim(), contato: contact.trim() }); }}><label className="filter-label">Nome institucional<input required minLength={2} maxLength={160} disabled={disabled} value={name} onChange={(e) => setName(e.target.value)} /></label><label className="filter-label">Contato de suporte<input maxLength={160} disabled={disabled} value={contact} onChange={(e) => setContact(e.target.value)} /></label><button className="button" disabled={disabled || name.trim().length < 2}>Salvar dados</button></form></section>;
}
