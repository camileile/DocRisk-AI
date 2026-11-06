import Access from "@/components/access-page";
import { ClerkAccess } from "@/components/clerk-access";
import { clerkEnabled } from "@/lib/auth-mode";

// Compatibilidade com links antigos: /acesso não expõe mais a demo fictícia.
export default function Page() { return clerkEnabled ? <ClerkAccess /> : <Access operational />; }
