import Link from "next/link";
import Access from "@/components/access-page";
import { clerkEnabled, publicDemoOnly } from "@/lib/auth-mode";
export default function Page() {
  if (publicDemoOnly) return <main className="demo-gate">
    <h1>Ambiente conectado indisponível nesta versão</h1>
    <p>Esta publicação não se conecta a nenhuma API. O fluxo operacional é apresentado pela equipe em ambiente local, com dados sintéticos.</p>
    <Link className="button" href="/demo">Abrir a demonstração ilustrativa</Link>
  </main>;
  return clerkEnabled ? <main className="demo-gate"><h1>Acesso à sua conta</h1><Link className="button" href="/entrar">Entrar com segurança</Link></main> : <Access operational />;
}
