export const clerkEnabled = process.env.NEXT_PUBLIC_AUTH_MODE === "clerk";
export function authEntry(): string { return clerkEnabled ? "/entrar" : "/acesso"; }
