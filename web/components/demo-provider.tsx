"use client";
/* Sessão autenticada na API. O perfil vem de GET /api/me (nunca do front) e os
 * contratos de GET /api/contracts; a interface só esconde o que a API já bloqueia. */
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError, getToken, setToken, type Contract, type Me, type Papel } from "@/lib/api";

type Session = {
  me: Me | null;
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
};

const SessionContext = createContext<Session | null>(null);

export function DemoProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [contract, setContract] = useState("");
  const [competence, setCompetence] = useState("10/2026");

  const load = useCallback(async (): Promise<Me | null> => {
    if (!getToken()) {
      setMe(null);
      setLoading(false);
      return null;
    }
    setLoading(true);
    try {
      const [user, list] = await Promise.all([api<Me>("/api/me"), api<Contract[]>("/api/contracts")]);
      setMe(user);
      setContracts(list);
      setContract((current) => (list.some((c) => c.id === current) ? current : (list[0]?.id ?? "")));
      setError(null);
      return user;
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setToken(null);
      setMe(null);
      setError(err instanceof Error ? err.message : "Falha ao carregar a sessão");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const login = useCallback(
    async (token: string) => {
      setToken(token);
      const user = await load();
      if (!user) throw new Error("Não foi possível entrar com este perfil.");
      return user;
    },
    [load],
  );

  const logout = useCallback(() => {
    setToken(null);
    setMe(null);
    setContracts([]);
    setContract("");
  }, []);

  return (
    <SessionContext.Provider
      value={{
        me,
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
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useDemo() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("DemoProvider não encontrado");
  return value;
}

export const useSession = useDemo;
