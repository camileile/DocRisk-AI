"use client";

import { useState } from "react";
import { useSession } from "@/components/demo-provider";
import { EmptyState, ErrorState, LoadingState, Notice, PageIntro } from "@/components/workspace-parts";
import { api, type AdminRegistry, type AdminUser } from "@/lib/api";
import { useApi } from "@/lib/use-api";

type PapelAdministrativo = AdminUser["papel"];
const labels: Record<PapelAdministrativo, string> = {
  ADMIN_BH: "Administrador Bernhoeft",
  ANALISTA_BH: "Analista Bernhoeft",
  GESTOR_CONTR: "Gestor da Contratante",
  GESTOR_FORN: "Gestor da Fornecedora",
};

export default function AdminUsersPage() {
  const { isDemo, me } = useSession();
  const registry = useApi<AdminRegistry>("/api/admin/registry");
  const [nome, setNome] = useState("");
  const [papel, setPapel] = useState<PapelAdministrativo>("GESTOR_CONTR");
  const [orgId, setOrgId] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [issued, setIssued] = useState<{ name: string; token: string } | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const empresas = registry.data?.empresas ?? [];
  const available = empresas.filter((org) =>
    (papel === "GESTOR_CONTR" && org.tipo === "CONTRATANTE") ||
    (papel === "GESTOR_FORN" && org.tipo === "FORNECEDORA"));
  const internal = papel === "ADMIN_BH" || papel === "ANALISTA_BH";
  const selection = internal ? me?.org_id ?? "" : orgId;

  async function createUser() {
    if (isDemo || busyId || !nome.trim() || !selection) return;
    setBusyId("create");
    setIssued(null);
    setFeedback(null);
    setError(null);
    try {
      const created = await api<{ nome: string; token_teste: string }>("/api/admin/users", {
        method: "POST",
        body: JSON.stringify({ nome: nome.trim(), papel, org_id: selection }),
      });
      setIssued({ name: created.nome, token: created.token_teste });
      setNome("");
      setFeedback("Acesso de teste criado. O token é exibido uma única vez nesta tela.");
      void registry.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível criar o usuário.");
    } finally {
      setBusyId(null);
    }
  }

  async function toggleStatus(user: AdminUser) {
    if (isDemo || busyId || user.id === me?.id) return;
    setBusyId(user.id);
    setFeedback(null);
    setError(null);
    setIssued(null);
    try {
      await api("/api/admin/users/" + encodeURIComponent(user.id) + "/status", {
        method: "PATCH",
        body: JSON.stringify({ ativo: !user.ativo }),
      });
      setFeedback("Situação do acesso atualizada.");
      void registry.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível atualizar o usuário.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <PageIntro
        eyebrow="ACESSOS E PERMISSÕES"
        title="Gestão de Usuários."
        description="Crie gestores depois de cadastrar as empresas e seus vínculos. Os operadores são administrados pelo gestor da própria fornecedora, em uma etapa separada."
      />
      {isDemo && <Notice>Na demonstração offline, os acessos são fictícios e nenhuma conta pode ser criada ou alterada.</Notice>}
      {feedback && <Notice tone="success">{feedback}</Notice>}
      {error && <Notice tone="error">{error}</Notice>}
      <section className="workspace-card">
        <h2>Criar acesso</h2>
        <div className="admin-form admin-user-form">
          <label>Nome do usuário
            <input aria-label="Nome do usuário" value={nome} maxLength={140} onChange={(e) => setNome(e.target.value)} placeholder="Nome completo" />
          </label>
          <label>Perfil
            <select aria-label="Perfil do usuário" value={papel} onChange={(e) => { setPapel(e.target.value as PapelAdministrativo); setOrgId(""); }}>
              {Object.entries(labels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select>
          </label>
          <label>Organização
            {internal ? (
              <input aria-label="Organização do usuário" readOnly value="Organização auditora (Bernhoeft)" />
            ) : (
              <select aria-label="Organização do usuário" value={orgId} onChange={(e) => setOrgId(e.target.value)}>
                <option value="">Selecione a empresa vinculada</option>
                {available.map((org) => <option key={org.id} value={org.id}>{org.nome}</option>)}
              </select>
            )}
          </label>
          <button className="button" disabled={isDemo || Boolean(busyId) || nome.trim().length < 2 || !selection} onClick={createUser}>
            {busyId === "create" ? "Criando…" : "Criar acesso de teste"}
          </button>
        </div>
        <p className="card-footnote">No MVP, os acessos usam tokens de teste. A autenticação corporativa e os convites por e-mail devem ser implementados antes de qualquer uso em produção.</p>
        {issued && (
          <div className="admin-issued-token">
            <strong>Credencial de teste de {issued.name}</strong>
            <p>Copie e guarde agora. Por segurança, este token não volta a aparecer na listagem.</p>
            <code>{issued.token}</code>
            <button className="button secondary" onClick={() => void navigator.clipboard.writeText(issued.token)}>Copiar token de teste</button>
            <button className="button secondary" onClick={() => setIssued(null)}>Ocultar token</button>
          </div>
        )}
      </section>
      {registry.loading ? <LoadingState /> : registry.error ? (
        <ErrorState message={registry.error} onRetry={registry.reload} />
      ) : (
        <section className="workspace-card">
          <div className="card-title"><h2>Usuários vinculados ({registry.data?.usuarios.length ?? 0})</h2></div>
          {(registry.data?.usuarios.length ?? 0) === 0 ? (
            <EmptyState title="Nenhum usuário." text="Cadastre gestores e analistas para iniciar a operação." />
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead><tr><th>Nome</th><th>Perfil</th><th>Organização</th><th>Situação</th><th>Ações</th></tr></thead>
                <tbody>
                  {registry.data?.usuarios.map((u) => (
                    <tr key={u.id}>
                      <td>{u.nome}<small>{u.id}</small></td>
                      <td>{labels[u.papel]}</td>
                      <td>{u.org_nome}</td>
                      <td><span className={"status-badge " + (u.ativo ? "success" : "warning")}><i />{u.ativo ? "Ativo" : "Inativo"}</span></td>
                      <td>
                        <button className="admin-row-button button secondary" disabled={isDemo || Boolean(busyId) || u.id === me?.id} onClick={() => void toggleStatus(u)}>
                          {busyId === u.id ? "Atualizando…" : u.ativo ? "Desativar" : "Reativar"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </>
  );
}
