"use client";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { useSession } from "@/components/demo-provider";
import { SessionGate } from "@/components/workspace-shell";
import { DEMO_ROLES } from "@/lib/offline-demo";
import { clerkEnabled } from "@/lib/auth-mode";
import { api, homeFor, roleLabels, type Papel } from "@/lib/api";
import { useApi } from "@/lib/use-api";

type Invitation = { id: string; email: string; nome: string; org_id: string; role: Papel; status: string; expires_at: string };
type ManagedLink = { id: string; nome: string; org_nome: string; role: Papel; ativo: number };
type Org = { id: string; nome: string; tipo: string };
export default function Page() {
  return <SessionGate allowed={DEMO_ROLES}><AccessManagement /></SessionGate>;
}
function AccessManagement() {
  const { me, isDemo, links, activeLink, chooseLink } = useSession();
  const manager = !isDemo && clerkEnabled && !!me && ["ADMIN_PLATAFORMA", "ADMIN_BH", "GESTOR_FORN"].includes(me.papel);
  const invitations = useApi<Invitation[]>(manager ? "/api/auth/invitations" : null);
  const managed = useApi<ManagedLink[]>(manager ? "/api/auth/managed-links" : null);
  const registry = useApi<{ empresas?: Org[]; auditoras?: { id: string; nome: string }[] }>(manager && me?.papel === "ADMIN_BH" ? "/api/admin/registry" : manager && me?.papel === "ADMIN_PLATAFORMA" ? "/api/platform/registry" : null);
  const [email, setEmail] = useState("");
  const [nome, setNome] = useState("");
  const [orgId, setOrgId] = useState("");
  const [role, setRole] = useState<Papel | "">("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const orgs: Org[] = me?.papel === "ADMIN_PLATAFORMA" ? (registry.data?.auditoras ?? []).map(org => ({ ...org, tipo: "BERNHOEFT" }))
    : me?.papel === "ADMIN_BH" ? [{ id: me.org_id, nome: "Minha organização auditora", tipo: "BERNHOEFT" }, ...(registry.data?.empresas ?? [])]
    : me ? [{ id: me.org_id, nome: links.find(link => link.id === activeLink)?.org_nome ?? "Minha fornecedora", tipo: "FORNECEDORA" }] : [];
  const org = orgs.find(item => item.id === orgId);
  const roles: Papel[] = me?.papel === "ADMIN_PLATAFORMA" ? ["ADMIN_BH"] : me?.papel === "GESTOR_FORN" ? ["OPERADOR_FORN"]
    : org?.tipo === "BERNHOEFT" ? ["ADMIN_BH", "ANALISTA_BH"] : org?.tipo === "FORNECEDORA" ? ["GESTOR_FORN"] : org?.tipo === "CONTRATANTE" ? ["GESTOR_CONTR"] : [];
  async function mutate(action: () => Promise<unknown>, success: string) {
    if (busy) return;
    setBusy(true); setFeedback("");
    try { await action(); setFeedback(success); await Promise.all([invitations.reload(), managed.reload()]); }
    catch (reason) { setFeedback(reason instanceof Error ? reason.message : "Não foi possível concluir."); }
    finally { setBusy(false); }
  }
  function invite(event: FormEvent) {
    event.preventDefault();
    if (!manager || !roles.includes(role as Papel)) return;
    void mutate(() => api("/api/auth/invitations", { method: "POST", body: JSON.stringify({ email, nome, org_id: orgId, role }) }), "Convite emitido. O destinatário deve confirmar o e-mail e aceitar o acesso em até 72 horas.");
  }
  if (!me) return null;
  return <main className="demo-gate access-management">
    <Link href={homeFor(me.papel)}>Voltar à minha área</Link><h1>Vínculos e acessos</h1>
    {isDemo || !clerkEnabled ? <p>A gestão de acesso produtivo não está habilitada nesta demonstração.</p> : <>
      <section className="workspace-card"><h2>Meus vínculos autorizados</h2>{links.map(link => <button type="button" className="button secondary" key={link.id} disabled={link.id === activeLink || busy} onClick={() => void chooseLink(link.id)}>{link.org_nome} · {roleLabels[link.papel]}{link.id === activeLink ? " · atual" : ""}</button>)}</section>
      {manager && <>
        <section className="workspace-card"><h2>Convidar uma pessoa</h2><p>O acesso fica restrito à organização e ao perfil informados. O convite expira em 72 horas.</p>
          <form onSubmit={invite}><fieldset disabled={busy}>
            <label className="filter-label">Nome<input required minLength={2} maxLength={140} value={nome} onChange={event => setNome(event.target.value)} /></label>
            <label className="filter-label">E-mail<input type="email" required maxLength={254} value={email} onChange={event => setEmail(event.target.value)} /></label>
            <label className="filter-label">Organização<select required value={orgId} onChange={event => { setOrgId(event.target.value); setRole(""); }}><option value="">Selecione…</option>{orgs.map(item => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
            <label className="filter-label">Perfil<select required value={role} onChange={event => setRole(event.target.value as Papel)}><option value="">Selecione…</option>{roles.map(item => <option key={item} value={item}>{roleLabels[item]}</option>)}</select></label>
            <button type="submit" className="button" disabled={!org || !role}>Enviar convite</button>
          </fieldset></form>
        </section>
        <section className="workspace-card"><h2>Convites emitidos</h2>{invitations.error && <p role="alert">{invitations.error}</p>}{(invitations.data ?? []).map(item => <article key={item.id}><p>{item.nome} · {item.email} · {roleLabels[item.role]} · {item.status}</p><button className="button secondary" type="button" disabled={busy || item.status !== "PENDING"} onClick={() => void mutate(() => api(`/api/auth/invitations/${item.id}/revoke`, { method: "POST" }), "Convite revogado no DocRisk. O acesso não poderá ser ativado.")}>Revogar convite</button></article>)}</section>
        <section className="workspace-card"><h2>Acessos autorizados</h2>{managed.error && <p role="alert">{managed.error}</p>}{(managed.data ?? []).map(item => <article key={item.id}><p>{item.nome} · {item.org_nome} · {roleLabels[item.role]}</p><button className="button secondary" type="button" disabled={busy || item.id === activeLink} onClick={() => void mutate(() => api(`/api/auth/links/${item.id}`, { method: "PATCH", body: JSON.stringify({ ativo: !item.ativo }) }), "Vínculo atualizado. A autorização passa a valer na próxima requisição.")}>{item.ativo ? "Revogar acesso" : "Reativar acesso"}</button></article>)}</section>
      </>}
    </>}
    {feedback && <p role="status">{feedback}</p>}
  </main>;
}
