/* Somente o build estático usa este módulo; o build Clerk usa o SDK oficial. */
import type { ReactNode } from "react";
export function ClerkProvider({ children }: { children: ReactNode }) { return children; }
export function SignIn() { return null; }
export function SignUp() { return null; }
export function useAuth(): never { throw new Error("Login produtivo indisponível no build da demonstração."); }
export function useClerk(): never { throw new Error("Login produtivo indisponível no build da demonstração."); }
