"use client";
/* Sessão autenticada na API. O perfil vem de GET /api/me (nunca do front) e os
 * contratos de GET /api/contracts; a interface só esconde o que a API já bloqueia. */
import { Fragment, createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api, ApiError, getToken, setToken, type Contract, type Me, type Papel } from "@/lib/api";
import { clerkEnabled } from "@/lib/auth-mode";
import { configureClerkSession, selectClerkLink, clearClerkSession, onSessionInvalidated } from "@/lib/api-session";
import { DEMO_CONTRACTS, demoUser, getDemoRole, setDemoRole } from "@/lib/offline-demo";

export type AuthLink = { id: string; nome: string; org_nome: string; papel: Papel };
type Session = {
  links: AuthLink[];
  activeLink: string;
  chooseLink: (id: string) => Promise<void>;
  connectClerk: (getToken: () => Promise<string | null>, sessionId: string, signOut: () => Promise<unknown>) => Promise<void>;

  me: Me | null;
  isDemo: boolean;
  enterDemo: (role: Papel) => Me;
  role: Papel | null;
  loading: boolean;
  error: string | null;
  contracts: Contract[];
  contract: string;
  setContract: (value: string) => void;
  competence: string;
  setCompetence: (value: string) => void;
  login: (token: string) => Promise<Me>;
  logout: () => void;
  /** Compatibilidade com os componentes da integração F1 (api-upload). */
  apiSession: ApiSession | null;
  connectApi: (token: string) => Promise<void>;
};

export type ApiSession = { token: string; user: Me; contracts: Contract[] };

const SessionContext = createContext<Session | null>(null);

export function DemoProvider({ children, identityBridge }: { children: ReactNode; identityBridge?: ReactNode }) {
  const generation = useRef(0);
  const signOutClerk = useRef<(() => Promise<unknown>) | null>(null);
  const [links, setLinks] = useState<AuthLink[]>([]);
  const [activeLink, setActiveLink] = useState("");
  const [sessionVersion, setSessionVersion] = useState(0);
  const [me, setMe] = useState<Me | null>(null);
  const [isDemo, setIsDemo] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [contract, setContract] = useState("");
  const [competence, setCompetence] = useState("10/2026");

  const load = useCallback(async (): Promise<Me | null> => {
    const attempt = ++generation.current;
    const offline = getDemoRole();
    if (offline) {
      const user = demoUser(offline);
      setMe(user);
      setIsDemo(true);
      setContracts(offline === "ADMIN_PLATAFORMA" ? [] : DEMO_CONTRACTS);
      setContract((current) => offline === "ADMIN_PLATAFORMA" ? "" : DEMO_CONTRACTS.some((c) => c.id === current) ? current : DEMO_CONTRACTS[0].id);
      setError(null);
      setLoading(false);
      return user;
    }
    setIsDemo(false);
    if (!getToken()) {
      setMe(null);
      setContracts([]);
      setContract("");
      setLoading(false);
      return null;
    }
    setLoading(true);
    try {
      const [user, list] = await Promise.all([api<Me>("/api/me"), api<Contract[]>("/api/contracts")]);
      if (attempt !== generation.current) return null;
      setMe(user);
      setContracts(list);
      setContract((current) => (list.some((c) => c.id === current) ? current : (list[0]?.id ?? "")));
      setError(null);
      return user;
    } catch (err) {
      if (attempt !== generation.current) return null;
      setContracts([]);
      setContract("");
      if (err instanceof ApiError && err.status === 401) setToken(null);
      setMe(null);
      setError(err instanceof Error ? err.message : "Falha ao carregar a sessão");
      return null;
    } finally {
      if (attempt === generation.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!clerkEnabled || getDemoRole()) void load();
    else setLoading(false);
  }, [load]);

  const login = useCallback(
    async (token: string) => {
      if (clerkEnabled) throw new Error("Use o login produtivo para entrar.");
      setSessionVersion((version) => version + 1);
      setMe(null);
      setContracts([]);
      setContract("");
      setDemoRole(null);
      setIsDemo(false);
      setToken(token);
      const user = await load();
      if (!user) throw new Error("Não foi possível entrar com este perfil.");
      return user;
    },
    [load],
  );

  const enterDemo = useCallback((role: Papel): Me => {
    generation.current++;
    setSessionVersion((version) => version + 1);
    setCompetence("10/2026");
    clearClerkSession();
    setLinks([]); setActiveLink("");
    setToken(null);
    setDemoRole(role);
    const user = demoUser(role);
    setMe(user);
    setIsDemo(true);
    setContracts(role === "ADMIN_PLATAFORMA" ? [] : DEMO_CONTRACTS);
    setContract(role === "ADMIN_PLATAFORMA" ? "" : DEMO_CONTRACTS[0].id);
    setError(null);
    setLoading(false);
    return user;
  }, []);

  const logout = useCallback(() => {
    generation.current++;
    setSessionVersion((version) => version + 1);
    setLoading(false);
    setError(null);
    clearClerkSession();
    setLinks([]); setActiveLink("");
    const signOut = signOutClerk.current;
    signOutClerk.current = null;
    if (signOut) void signOut().catch(() => setError("A sessão local foi encerrada. Confira sua conexão antes de entrar novamente."));
    setToken(null);
    setDemoRole(null);
    setIsDemo(false);
    setMe(null);
    setContracts([]);
    setContract("");
  }, []);

  useEffect(() => onSessionInvalidated(() => {
    logout();
    setError("Sua sessão foi encerrada ou expirou. Entre novamente.");
  }), [logout]);

  const connectClerk = useCallback(async (getBearer: () => Promise<string | null>, sessionId: string, signOut: () => Promise<unknown>) => {
    const attempt = ++generation.current;
    signOutClerk.current = signOut;
    setSessionVersion(value => value + 1);
    setMe(null); setContracts([]); setContract(""); setLinks([]); setActiveLink("");
    setDemoRole(null); setIsDemo(false); setLoading(true); setError(null);
    configureClerkSession(getBearer, sessionId);
    try {
      const available = await api<AuthLink[]>("/api/auth/links");
      if (attempt !== generation.current) return;
      setLinks(available);
      if (available.length === 1) {
        selectClerkLink(available[0].id); setActiveLink(available[0].id);
        await load();
      }
    } catch (reason) {
      if (attempt === generation.current) setError(reason instanceof Error ? reason.message : "Não foi possível carregar os vínculos.");
    } finally { if (attempt === generation.current) setLoading(false); }
  }, [load]);

  const chooseLink = useCallback(async (id: string) => {
    if (!links.some(link => link.id === id)) throw new Error("Vínculo não autorizado.");
    generation.current++;
    setMe(null); setContracts([]); setContract(""); setCompetence("10/2026");
    setSessionVersion(value => value + 1);
    selectClerkLink(id); setActiveLink(id);
    await load();
  }, [links, load]);

  const apiSession = useMemo<ApiSession | null>(() => {
    const token = me ? getToken() : null;
    return me && token ? { token, user: me, contracts } : null;
  }, [me, contracts]);
  const connectApi = useCallback(async (token: string) => {
    await login(token.trim());
  }, [login]);

  return (
    <SessionContext.Provider
      value={{
        links, activeLink, chooseLink, connectClerk,
        me,
        isDemo,
        enterDemo,
        role: me?.papel ?? null,
        loading,
        error,
        contracts,
        contract,
        setContract: value => { if (value === "" || contracts.some(item => item.id === value)) setContract(value); },
        competence,
        setCompetence,
        login,
        logout,
        apiSession,
        connectApi,
      }}
    >
      {identityBridge}
      <Fragment key={sessionVersion}>{children}</Fragment>
    </SessionContext.Provider>
  );
}

export function useDemo() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("DemoProvider não encontrado");
  return value;
}

export const useSession = useDemo;
