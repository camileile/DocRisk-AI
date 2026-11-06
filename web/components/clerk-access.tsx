"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { SignIn, useAuth, useClerk } from "@docrisk/clerk";
import { useRouter } from "next/navigation";
import { api, getToken as connectedToken, homeFor, roleLabels, type Papel } from "@/lib/api";
import { useSession } from "./demo-provider";

type Invitation = { id: string; nome: string; org_nome: string; role: Papel; expires_at: string };
export function ClerkAccess() {
  const { isLoaded, isSignedIn, getToken, sessionId } = useAuth();
  const clerk = useClerk();
  const { me, links, chooseLink, loading, error, connectClerk } = useSession();
  const router = useRouter();
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!isLoaded || !isSignedIn || loading || !connectedToken()) return;
    const controller = new AbortController();
    void api<Invitation[]>("/api/auth/invitations/pending", { signal: controller.signal }).then(items => { setInvitations(items); setFeedback(""); }).catch(reason => {
      if (!controller.signal.aborted) setFeedback(reason instanceof Error ? reason.message : "Não foi possível consultar os convites.");
    });
    return () => controller.abort();
  }, [isLoaded, isSignedIn, loading]);
  async function accept(id: string) {
    if (busy || !sessionId) return;
    setBusy(true); setFeedback("");
    try {
      await api(`/api/auth/invitations/${id}/accept`, { method: "POST" });
      await connectClerk(() => getToken(), sessionId, () => clerk.signOut());
    } catch (reason) { setFeedback(reason instanceof Error ? reason.message : "Não foi possível aceitar o convite."); }
    finally { setBusy(false); }
  }
  return <main className="demo-gate">
    <Link href="/" aria-label="DocRisk AI — início"><img src="/brand/logo-horizontal-claro.svg" width="200" height="52" alt="DocRisk AI" /></Link>
    <h1>Entrar na sua conta</h1>
    {!isLoaded ? <p role="status">Verificando identificação…</p> : !isSignedIn ? <><SignIn routing="hash" /><p>Use “Esqueci minha senha” no formulário para recuperar seu acesso.</p></> : <>
      {loading ? <p role="status">Consultando vínculos autorizados…</p> : <>
        {links.length ? <><h2>Selecione seu vínculo</h2>{links.map(link => <button key={link.id} className="button secondary" type="button" onClick={() => void chooseLink(link.id).then(() => router.push(homeFor(link.papel))).catch(reason => setFeedback(String(reason)))}>{link.org_nome} · {roleLabels[link.papel]}</button>)}</> : <p>Seu acesso está pendente. Aceite um convite válido ou procure o responsável pela sua organização.</p>}
        {invitations.map(invite => <section key={invite.id}><p>{invite.org_nome} · {roleLabels[invite.role]}</p><button type="button" className="button" disabled={busy} onClick={() => void accept(invite.id)}>Aceitar convite</button></section>)}
      </>}
      {me && <Link className="button" href={homeFor(me.papel)}>Acessar minha área</Link>}
      <button type="button" className="button secondary" onClick={() => void clerk.signOut()}>Sair da conta</button>
    </>}
    {(error || feedback) && <p role="alert">{error || feedback}</p>}
    <Link href="/acesso">Explorar a demonstração fictícia</Link>
  </main>;
}
