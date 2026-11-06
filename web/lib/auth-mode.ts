/** Build pública (Vercel): somente a demonstração offline; nenhum transporte operacional. */
export const publicDemoOnly = process.env.NEXT_PUBLIC_DOCRISK_PUBLIC_DEMO === "1";
export const clerkEnabled = !publicDemoOnly && process.env.NEXT_PUBLIC_AUTH_MODE === "clerk";
export function authEntry(): string { return clerkEnabled ? "/entrar" : "/operacao"; }
