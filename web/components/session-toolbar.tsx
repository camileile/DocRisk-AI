"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSession } from "./demo-provider";
import { homeFor, roleLabels, type Papel } from "@/lib/api";
import { clerkEnabled, authEntry } from "@/lib/auth-mode";
import { DEMO_ROLES } from "@/lib/offline-demo";

export function SessionToolbar() {
  const { me, isDemo, loading, enterDemo, logout } = useSession();
  const router = useRouter();
  if (loading || !me) return null;
  function change(role: Papel) {
    enterDemo(role);
    router.push(homeFor(role));
  }
  return (
    <section className="session-toolbar" aria-label="Contexto da sessão">
      <div className="session-toolbar-controls">
        <strong>{isDemo ? "DEMO · somente consulta" : clerkEnabled ? "Conta autenticada" : "API de testes · conectada"}</strong>
        {isDemo ? <label>Perfil <select aria-label="Perfil da demonstração" value={me.papel} onChange={(event) => change(event.target.value as Papel)}>
          {DEMO_ROLES.map((role) => <option key={role} value={role}>{roleLabels[role]}</option>)}
        </select></label> : <span>{roleLabels[me.papel]}</span>}
        {!isDemo && clerkEnabled && <Link href="/vinculos">Vínculos e acessos</Link>}
        {isDemo && <button type="button" onClick={() => { change(me!.papel); router.refresh(); }}>Reiniciar demo</button>}
        <button type="button" onClick={() => { logout(); router.push(authEntry()); }}>Sair</button>
      </div>
      <small>{isDemo ? "Dados e documentos fictícios. Envios, correções e publicações não são executados. A demo funciona sem backend; recarregar com armazenamento bloqueado exige escolher o perfil novamente." : clerkEnabled ? "O acesso segue os vínculos e contratos autorizados da sua organização." : "Ambiente demonstrativo por token."}</small>
    </section>
  );
}
