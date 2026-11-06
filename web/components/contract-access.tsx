"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { EmptyState, ErrorState, LoadingState, Notice } from "./workspace-parts";

type Grant = { id: string; nome: string; ativo: boolean; expires_at: string | null };
type Access = { user_id: string; nome: string; contratos: Grant[] };

export function ContractAccess({ userId, enabled }: { userId: string; enabled: boolean }) {
  const base = `/api/contract-access/users/${encodeURIComponent(userId)}`;
  const access = useApi<Access>(enabled ? base : null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [failure, setFailure] = useState("");
  async function save(grant: Grant, active: boolean, expiry: string) {
    if (!enabled || busy) return;
    setBusy(true); setFeedback(""); setFailure("");
    try {
      await api(`${base}/contracts/${encodeURIComponent(grant.id)}`, {
        method: "PUT", body: JSON.stringify({ ativo: active,
          expires_at: active && expiry ? new Date(expiry).toISOString() : null }),
      });
      await access.reload();
      setFeedback(active ? "Contrato atribuído. A permissão vale para as próximas requisições."
        : "Acesso ao contrato revogado. O histórico documental foi preservado.");
    } catch (error) { setFailure(error instanceof Error ? error.message : "Não foi possível alterar o acesso."); }
    finally { setBusy(false); }
  }
  return <section className="workspace-card" aria-label="Atribuição de contratos">
    <h2>Contratos de {access.data?.nome ?? "usuário selecionado"}</h2>
    <p>Somente os contratos atribuídos ficam disponíveis. A validade é opcional; o horário informado é o do seu dispositivo.</p>
    {!enabled ? <Notice>Atribuição indisponível na demonstração offline.</Notice> : access.loading ? <LoadingState />
      : access.error ? <ErrorState message={access.error} onRetry={access.reload} />
      : !access.data?.contratos.length ? <EmptyState title="Nenhum contrato disponível." text="Cadastre os contratos da organização antes de atribuir acessos." />
      : <div className="table-scroll"><table className="data-table">
        <thead><tr><th>Contrato</th><th>Situação</th><th>Validade opcional</th><th>Ações</th></tr></thead>
        <tbody>{access.data.contratos.map(grant => <GrantRow key={`${userId}-${grant.id}-${grant.ativo}-${grant.expires_at}`}
          grant={grant} busy={busy} onSave={save} />)}</tbody>
      </table></div>}
    {feedback && <Notice tone="success">{feedback}</Notice>}
    {failure && <Notice tone="error">{failure}</Notice>}
  </section>;
}

function GrantRow({ grant, busy, onSave }: {
  grant: Grant; busy: boolean; onSave: (grant: Grant, active: boolean, expiry: string) => Promise<void>;
}) {
  const [expiry, setExpiry] = useState(() => {
    if (!grant.ativo || !grant.expires_at) return "";
    const date = new Date(grant.expires_at);
    return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  });
  return <tr>
    <td>{grant.nome}<small>{grant.id}</small></td><td>{grant.ativo ? "Atribuído" : "Sem acesso"}</td>
    <td><input type="datetime-local" aria-label={`Validade do acesso a ${grant.nome}`} value={expiry}
      disabled={busy} onChange={event => setExpiry(event.target.value)} /></td>
    <td><button className="button secondary" disabled={busy} onClick={() => void onSave(grant, true, expiry)}>
      {grant.ativo ? "Salvar validade" : "Atribuir contrato"}</button>
      {grant.ativo && <button className="button secondary" disabled={busy} onClick={() => void onSave(grant, false, "")}>
        Revogar contrato</button>}</td>
  </tr>;
}
