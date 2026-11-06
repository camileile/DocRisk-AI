import Link from "next/link";
import { clerkEnabled } from "@/lib/auth-mode";
import { ClerkAccess } from "@/components/clerk-access";
export default function Page() {
  return clerkEnabled ? <ClerkAccess /> : <main className="demo-gate"><h1>Entrar no DocRisk AI</h1><p>O login produtivo não está habilitado nesta demonstração.</p><Link href="/operacao" className="button">Acesso à API local de testes</Link></main>;
}
