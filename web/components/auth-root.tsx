"use client";
import { ClerkProvider } from "@docrisk/clerk";
import type { ReactNode } from "react";
import { DemoProvider } from "./demo-provider";
import { ClerkSessionBridge } from "./clerk-session";
import { clerkEnabled } from "@/lib/auth-mode";

export function AuthRoot({ children }: { children: ReactNode }) {
  if (!clerkEnabled) return <DemoProvider>{children}</DemoProvider>;
  return <ClerkProvider signInUrl="/entrar" signUpUrl="/cadastro" signInFallbackRedirectUrl="/entrar" signUpFallbackRedirectUrl="/entrar">
    <DemoProvider identityBridge={<ClerkSessionBridge />}>{children}</DemoProvider>
  </ClerkProvider>;
}
