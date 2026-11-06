"use client";
import { useEffect, useRef } from "react";
import { useAuth, useClerk } from "@docrisk/clerk";
import { usePathname } from "next/navigation";
import { useSession } from "./demo-provider";
import { getToken as connectedToken } from "@/lib/api-session";
import { getDemoRole } from "@/lib/offline-demo";

export function ClerkSessionBridge() {
  const { isLoaded, isSignedIn, sessionId, getToken } = useAuth();
  const clerk = useClerk();
  const { connectClerk, logout } = useSession();
  const path = usePathname();
  const connected = useRef("");
  const sdk = useRef({ getToken, signOut: () => clerk.signOut() });
  sdk.current = { getToken, signOut: () => clerk.signOut() };
  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn || !sessionId) { if (connected.current && connectedToken()) logout(); connected.current = ""; return; }
    if (getDemoRole() && path !== "/entrar" && path !== "/entrar/") return;
    if (connected.current === sessionId && path !== "/entrar" && path !== "/entrar/") return;
    connected.current = sessionId;
    void connectClerk(() => sdk.current.getToken(), sessionId, () => sdk.current.signOut());
  }, [isLoaded, isSignedIn, sessionId, connectClerk, logout, path]);
  return null;
}
