import Link from "next/link";
import { clerkEnabled } from "@/lib/auth-mode";
import { ClerkAccess } from "@/components/clerk-access";
export default function Page() {
  return clerkEnabled ? <ClerkAccess /> : <main className="demo-gate"><h1>Entrar no DocRisk AI</h1><p>O login com Clerk não está habilitado neste ambiente. Utilize a API local de testes ou configure a autenticação operacional.</p><Link href="/operacao" className="button">Acesso à API local de testes</Link></main>;
}
