"use client";
import { useState, type FormEvent } from "react";
import { useSession } from "@/components/demo-provider";
import { SessionGate } from "@/components/workspace-shell";
import { EmptyState, ErrorState, LoadingState, Notice, PageIntro } from "@/components/workspace-parts";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { clerkEnabled } from "@/lib/auth-mode";
import { ContractAccess } from "@/components/contract-access";

type ManagedLink = { id: string; user_id: string; org_id: string; role: string; ativo: number };

type Operator = { id: string; nome: string; org_id: string; papel: "OPERADOR_FORN"; ativo: number };

export default function OperatorsPage() {
  return <SessionGate allowed={["GESTOR_FORN"]}><Operators /></SessionGate>;
}

function Operators() {
  const { isDemo, me } = useSession();
  const { data, loading, error, reload } = useApi<Operator[]>("/api/supplier/operators");
  const managedLinks = useApi<ManagedLink[]>(clerkEnabled ? "/api/auth/managed-links" : null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [failure, setFailure] = useState("");
  const [token, setToken] = useState("");
  const [accessUser, setAccessUser] = useState<string | null>(null);

  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    setBusy(true); setFailure(""); setMessage(""); setToken("");
    try {
      if (clerkEnabled) {
        await api("/api/auth/invitations", {
          method: "POST",
          body: JSON.stringify({ nome: name.trim(), email: email.trim(), org_id: me?.org_id, role: "OPERADOR_FORN" }),
        });
        setEmail(""); setName("");
        setMessage("Convite enviado. O operador será vinculado após validar o e-mail e aceitar o convite.");
      } else {
        const result = await api<Operator & { token_teste: string }>("/api/supplier/operators", {
          method: "POST", body: JSON.stringify({ nome: name.trim() }),
        });
        setToken(result.token_teste); setName("");
        setMessage("Operador de teste criado e vinculado à fornecedora.");
        await reload();
      }
    } catch (err) { setFailure(err instanceof Error ? err.message : "Falha ao cadastrar."); }
    finally { setBusy(false); }
  }
  async function change(operator: Operator) {
    if (busy) return;
    const link = managedLinks.data?.find(item => item.user_id === operator.id && item.org_id === operator.org_id);
    if (clerkEnabled && !link) { setFailure("Vínculo indisponível. Recarregue a lista."); return; }
    setBusy(true); setFailure(""); setMessage(""); setToken("");
    try {
      if (clerkEnabled && link) {
        await api(`/api/auth/links/${encodeURIComponent(link.id)}`, {
          method: "PATCH", body: JSON.stringify({ ativo: !link.ativo }),
        });
        await managedLinks.reload();
        setMessage(link.ativo ? "Vínculo revogado. O histórico dos envios foi preservado." : "Vínculo reativado.");
      } else {
        await api(`/api/supplier/operators/${encodeURIComponent(operator.id)}/status`, {
          method: "PATCH", body: JSON.stringify({ ativo: !operator.ativo }),
        });
        setMessage(operator.ativo ? "Operador desativado. O histórico de envios foi preservado." : "Operador reativado.");
        await reload();
      }
    } catch (err) { setFailure(err instanceof Error ? err.message : "Falha ao alterar acesso."); }
    finally { setBusy(false); }
  }
  return <>
    <PageIntro eyebrow="GESTÃO DA FORNECEDORA" title="Operadores da sua empresa."
      description="Gerencie quem envia documentos pela fornecedora. Os operadores consultam os envios da organização nos contratos autorizados, independentemente de quem enviou cada arquivo." />
    <Notice>{isDemo ? "Demonstração offline somente para consulta." : clerkEnabled
      ? "Ambiente autenticado: o gestor convida operadores por e-mail e administra os vínculos ativos. Nenhum token de teste é emitido."
      : "Ambiente local de testes: cadastro por token demonstrativo."}</Notice>
    {message && <Notice tone="success">{message}</Notice>}
    {failure && <Notice tone="error">{failure}</Notice>}
    {token && <section className="workspace-card"><h2>Acesso de teste do novo operador</h2>
      <p>Copie o token para entrar em “Conectar API de testes”. Ele é exibido apenas neste cadastro.</p>
      <label className="filter-label">Token de teste<input aria-label="Token de teste do operador" value={token} readOnly /></label>
      <button className="button secondary" onClick={() => setToken("")}>Ocultar token</button>
    </section>}
    <section className="workspace-card"><h2>{clerkEnabled ? "Convidar operador" : "Cadastrar operador de teste"}</h2>
      <form onSubmit={create} className="inline-form">
        <label className="filter-label">Nome do operador<input required minLength={2} maxLength={140} value={name} onChange={(e) => setName(e.target.value)} disabled={isDemo || busy} /></label>
        {clerkEnabled && <label className="filter-label">E-mail do operador
          <input type="email" required maxLength={254} value={email} onChange={e => setEmail(e.target.value)} disabled={isDemo || busy} />
        </label>}
        <button className="button" disabled={isDemo || busy || name.trim().length < 2 || (clerkEnabled && !email.includes("@"))}>
          {clerkEnabled ? "Enviar convite" : "Cadastrar operador"}
        </button>
      </form>
    </section>
    {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : !data?.length ? <EmptyState title="Nenhum operador cadastrado." text="Cadastre o primeiro operador da sua fornecedora." /> : <section className="workspace-card"><h2>Equipe operacional</h2><div className="table-scroll"><table className="data-table">
      <thead><tr><th>Nome</th><th>Situação</th><th>Acesso</th></tr></thead>
      <tbody>{data.map((o) => {
        const link = managedLinks.data?.find(item => item.user_id === o.id && item.org_id === o.org_id);
        const active = clerkEnabled ? Boolean(o.ativo && link?.ativo) : Boolean(o.ativo);
        return <tr key={o.id}><td>{o.nome}</td><td>{active ? "Ativo" : "Inativo"}</td>
          <td><button className="button secondary" disabled={isDemo}
            onClick={() => setAccessUser(o.id)}>Gerenciar contratos de {o.nome}</button><button className="button secondary"
            disabled={isDemo || busy || (clerkEnabled && (!link || managedLinks.loading))}
            onClick={() => void change(o)} aria-label={`${active ? "Desativar" : "Reativar"} ${o.nome}`}>
              {active ? "Desativar" : "Reativar"}
            </button></td></tr>;
      })}</tbody>
    </table></div></section>}
    {accessUser && <ContractAccess key={accessUser} userId={accessUser} enabled={!isDemo} />}
  </>;
}
