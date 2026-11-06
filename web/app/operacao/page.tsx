import Link from "next/link";
import Access from "@/components/access-page";
import { clerkEnabled } from "@/lib/auth-mode";
export default function Page() {
  return clerkEnabled ? <main className="demo-gate"><h1>Acesso à sua conta</h1><Link className="button" href="/entrar">Entrar com segurança</Link></main> : <Access operational />;
}
