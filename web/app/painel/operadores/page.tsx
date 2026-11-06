"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { clerkEnabled } from "@/lib/auth-mode";
import { useSession } from "@/components/demo-provider";
import { SessionGate } from "@/components/workspace-shell";
import { EmptyState, ErrorState, LoadingState, Notice, PageIntro } from "@/components/workspace-parts";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";

type Operator = { id: string; nome: string; org_id: string; papel: "OPERADOR_FORN"; ativo: number };

export default function OperatorsPage() {
  return <SessionGate allowed={["GESTOR_FORN"]}><Operators /></SessionGate>;
}

function Operators() {
  const { isDemo } = useSession();
  const { data, loading, error, reload } = useApi<Operator[]>("/api/supplier/operators");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [failure, setFailure] = useState("");
  const [token, setToken] = useState("");

  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    setBusy(true); setFailure(""); setMessage(""); setToken("");
    try {
      const result = await api<Operator & { token_teste: string }>("/api/supplier/operators", { method: "POST", body: JSON.stringify({ nome: name.trim() }) });
      setToken(result.token_teste); setName(""); setMessage("Operador criado e vinculado à sua fornecedora.");
      await reload();
    } catch (err) { setFailure(err instanceof Error ? err.message : "Falha ao cadastrar."); }
    finally { setBusy(false); }
  }
  async function change(operator: Operator) {
    if (busy) return;
    setBusy(true); setFailure(""); setMessage(""); setToken("");
    try {
      await api(`/api/supplier/operators/${encodeURIComponent(operator.id)}/status`, { method: "PATCH", body: JSON.stringify({ ativo: !operator.ativo }) });
      setMessage(operator.ativo ? "Operador desativado. O histórico de envios foi preservado." : "Operador reativado.");
      await reload();
    } catch (err) { setFailure(err instanceof Error ? err.message : "Falha ao alterar acesso."); }
    finally { setBusy(false); }
  }
  return <>
    <PageIntro eyebrow="GESTÃO DA FORNECEDORA" title="Operadores da sua empresa."
      description="Gerencie quem envia documentos pela fornecedora. Os operadores consultam os envios da organização nos contratos autorizados, independentemente de quem enviou cada arquivo." />
    <Notice>{isDemo ? "Demonstração offline somente para consulta." : clerkEnabled ? "Acesso operacional com Clerk: operadores são convidados pelo Gestor da Fornecedora e ativados após confirmar o e-mail." : "Ambiente de testes: cadastro usa token demonstrativo."}</Notice>
    {message && <Notice tone="success">{message}</Notice>}
    {failure && <Notice tone="error">{failure}</Notice>}
    {token && <section className="workspace-card"><h2>Acesso de teste do novo operador</h2>
      <p>Copie o token para entrar em “Conectar API de testes”. Ele é exibido apenas neste cadastro.</p>
      <label className="filter-label">Token de teste<input aria-label="Token de teste do operador" value={token} readOnly /></label>
      <button className="button secondary" onClick={() => setToken("")}>Ocultar token</button>
    </section>}
    {clerkEnabled && !isDemo ? (
      <section className="workspace-card">
        <h2>Convidar operador por e-mail</h2>
        <p>O operador é vinculado à fornecedora somente após aceitar o convite do Clerk. Não são criados usuários por token neste ambiente.</p>
        <Link className="button" href="/vinculos">Convidar e gerenciar operadores</Link>
      </section>
    ) : (
      <section className="workspace-card"><h2>Cadastrar operador</h2>
        <form onSubmit={create} className="inline-form">
          <label className="filter-label">Nome do operador<input required minLength={2} maxLength={140} value={name} onChange={(e) => setName(e.target.value)} disabled={isDemo || busy} /></label>
          <button className="button" disabled={isDemo || busy || name.trim().length < 2}>Cadastrar operador</button>
        </form>
      </section>
    )}
    {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : !data?.length ? <EmptyState title="Nenhum operador cadastrado." text="Cadastre o primeiro operador da sua fornecedora." /> : <section className="workspace-card"><h2>Equipe operacional</h2><div className="table-scroll"><table className="data-table">
      <thead><tr><th>Nome</th><th>Situação</th><th>Acesso</th></tr></thead>
      <tbody>{data.map((o) => <tr key={o.id}><td>{o.nome}</td><td>{o.ativo ? "Ativo" : "Inativo"}</td><td>{clerkEnabled && !isDemo ? <Link className="text-link" href="/vinculos">Gerenciar vínculo</Link> : <button className="button secondary" disabled={isDemo || busy} onClick={() => void change(o)} aria-label={`${o.ativo ? "Desativar" : "Reativar"} ${o.nome}`}>{o.ativo ? "Desativar" : "Reativar"}</button>}</td></tr>)}</tbody>
    </table></div></section>}
  </>;
}
