"use client";
/* Sessão autenticada na API. O perfil vem de GET /api/me (nunca do front) e os
 * contratos de GET /api/contracts; a interface só esconde o que a API já bloqueia. */
import { Fragment, createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api, ApiError, getToken, setToken, type Contract, type Me, type Papel } from "@/lib/api";
import { DEMO_CONTRACTS, demoUser, getDemoRole, setDemoRole } from "@/lib/offline-demo";

type Session = {
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
  /** Compatibilidade com os componentes da integração F1 (api-upload, api-client). */
  apiSession: ApiSession | null;
  connectApi: (token: string) => Promise<void>;
};

export type ApiSession = { token: string; user: Me; contracts: Contract[] };

const SessionContext = createContext<Session | null>(null);

export function DemoProvider({ children }: { children: ReactNode }) {
  const generation = useRef(0);
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
    void load();
  }, [load]);

  const login = useCallback(
    async (token: string) => {
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
    setToken(null);
    setDemoRole(null);
    setIsDemo(false);
    setMe(null);
    setContracts([]);
    setContract("");
  }, []);

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
        me,
        isDemo,
        enterDemo,
        role: me?.papel ?? null,
        loading,
        error,
        contracts,
        contract,
        setContract,
        competence,
        setCompetence,
        login,
        logout,
        apiSession,
        connectApi,
      }}
    >
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
