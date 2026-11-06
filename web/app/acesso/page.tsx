"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  FileCheck2,
  Layers3,
  LockKeyhole,
  ShieldCheck,
  UserCog,
  type LucideIcon,
} from "lucide-react";
import { useSession } from "@/components/demo-provider";
import { api, roleLabels, type DemoUser, type Papel } from "@/lib/api";
import { ErrorState, LoadingState } from "@/components/workspace-parts";

const icons: Record<Papel, LucideIcon> = {
  ANALISTA_BH: ShieldCheck,
  ADMIN_BH: LockKeyhole,
  GESTOR_FORN: UserCog,
  OPERADOR_FORN: Building2,
  GESTOR_CONTR: FileCheck2,
};
const descriptions: Record<Papel, string> = {
  ANALISTA_BH: "Revisar documentos, conciliações, pendências e publicar pareceres.",
  ADMIN_BH: "Consultar a trilha de auditoria e os indicadores da operação.",
  GESTOR_FORN: "Enviar lotes, acompanhar processamento e responder pendências.",
  OPERADOR_FORN: "Enviar lotes e reenviar documentos corrigidos.",
  GESTOR_CONTR: "Consultar somente os pareceres publicados do contrato.",
};

function destinationFor(role: Papel): string {
  if (role === "GESTOR_CONTR") return "/contratante";
  if (role === "ADMIN_BH") return "/administracao";
  return "/painel";
}

export default function Access() {
  const [users, setUsers] = useState<DemoUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string>("u-analista");
  const [entering, setEntering] = useState(false);
  const { login } = useSession();
  const router = useRouter();

  async function load() {
    setError(null);
    try {
      setUsers(await api<DemoUser[]>("/api/demo/users"));
    } catch (err) {
      setError(
        err instanceof Error && err.message.startsWith("Rota")
          ? "A API não está em modo demonstração (DOCRISK_DEMO_MODE=1)."
          : err instanceof Error
            ? err.message
            : "Falha ao carregar os perfis",
      );
    }
  }
  useEffect(() => {
    void load();
  }, []);

  async function enter() {
    const user = users?.find((u) => u.id === selected);
    if (!user) return;
    setEntering(true);
    setError(null);
    try {
      const me = await login(user.token);
      router.push(destinationFor(me.papel));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao entrar");
      setEntering(false);
    }
  }

  return (
    <main className="access-page">
      <div className="access-story">
        <Link href="/" aria-label="DocRisk AI — início">
          <img src="/brand/logo-horizontal-claro.svg" alt="DocRisk AI" width="200" height="52" />
        </Link>
        <div>
          <span className="eyebrow">DO DOCUMENTO À DECISÃO</span>
          <h1>
            Mais contexto.
            <br />
            Menos incerteza.
            <br />
            <em>Pessoas no controle.</em>
          </h1>
          <p>Cada perfil enxerga apenas os contratos e as ações que a API autoriza.</p>
          <div className="access-principle">
            <Layers3 size={28} />
            <span>
              Uma base de inteligência.
              <br />
              <strong>Um fluxo para cada responsabilidade.</strong>
            </span>
          </div>
        </div>
        <small>Hack Garanhuns Tech 2026 · MVP com dados sintéticos</small>
      </div>
      <div className="access-content">
        <Link href="/" className="back-link">
          <ArrowLeft size={16} /> Voltar ao site
        </Link>
        <div className="access-form">
          <span className="pill light">AMBIENTE DE DEMONSTRAÇÃO</span>
          <h2>Entrar na plataforma.</h2>
          <p>Escolha um perfil de demonstração. A sessão usa o token do perfil e todas as permissões são verificadas pela API.</p>
          {error && <ErrorState message={error} onRetry={users ? undefined : load} />}
          {!users && !error && <LoadingState text="Carregando perfis da API…" />}
          {users && (
            <fieldset className="persona-options">
              <legend>Perfil de acesso</legend>
              {users.map((user) => {
                const Icon = icons[user.role] ?? ShieldCheck;
                return (
                  <label key={user.id} className={selected === user.id ? "persona selected" : "persona"}>
                    <input
                      type="radio"
                      name="perfil"
                      value={user.id}
                      checked={selected === user.id}
                      onChange={() => setSelected(user.id)}
                    />
                    <Icon size={25} />
                    <span>
                      <strong>{roleLabels[user.role]}</strong>
                      <small>
                        {user.nome} · {descriptions[user.role]}
                      </small>
                    </span>
                    <span className="persona-check">{selected === user.id && <Check size={14} />}</span>
                  </label>
                );
              })}
            </fieldset>
          )}
          <button className="button access-enter" onClick={enter} disabled={!users || entering}>
            {entering ? "Entrando…" : "Entrar"} <ArrowRight size={18} />
          </button>
          <p className="demo-disclosure">
            Perfis e documentos são fictícios. Em produção, o acesso seria por SSO/OIDC; aqui o token de demonstração só é
            exposto com DOCRISK_DEMO_MODE=1 em ambiente local.
          </p>
        </div>
      </div>
    </main>
  );
}
