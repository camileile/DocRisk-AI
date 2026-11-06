import Link from "next/link";
import { SignUp } from "@docrisk/clerk";
import { clerkEnabled } from "@/lib/auth-mode";
export default function Page() {
  return <main className="demo-gate"><h1>Ativar sua identificação</h1>{clerkEnabled ? <><p>Ative sua identificação após receber um convite. O acesso aos dados depende de um vínculo autorizado.</p><SignUp routing="hash" /></> : <Link href="/operacao">Acessar ambiente de testes</Link>}</main>;
}
