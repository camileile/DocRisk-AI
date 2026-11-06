"use client";
import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { authEntry } from "@/lib/auth-mode";

// Compatibilidade com links antigos: /acesso redireciona ao login operacional.
// /demo é a única rota que apresenta o seletor de perfis fictícios.
export default function Page() {
  const router = useRouter();
  const login = authEntry();
  useEffect(() => { router.replace(login); }, [router, login]);
  return <main className="demo-gate">
    <h1>Redirecionando para o acesso...</h1>
    <Link className="button" href={login}>Ir para o login</Link>
  </main>;
}
