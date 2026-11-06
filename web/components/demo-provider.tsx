"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import type { DemoRole } from "@/lib/demo";
import {
  identifyWithApi, type ApiContract, type ApiUser,
} from "@/lib/api-client";

export type ApiSession = {
  // Credencial de DEMONSTRAÇÃO: somente memória e apenas contra API local de testes.
  token: string;
  user: ApiUser;
  contracts: ApiContract[];
};

type WorkspaceContext = {
  role: DemoRole | null;
  setRole: (role: DemoRole | null) => void;
  contract: string;
  setContract: (value: string) => void;
  competence: string;
  setCompetence: (value: string) => void;
  apiSession: ApiSession | null;
  connectApi: (token: string) => Promise<void>;
};

const DemoContext = createContext<WorkspaceContext | null>(null);

export function DemoProvider({ children }: { children: ReactNode }) {
  const [role, updateRole] = useState<DemoRole | null>(null);
  const [contract, setContract] = useState("CTR-001");
  const [competence, setCompetence] = useState("10/2026");
  const [apiSession, setApiSession] = useState<ApiSession | null>(null);

  function setRole(value: DemoRole | null) {
    // Trocar de perspectiva desconecta a sessão real; não mistura dados sintéticos e API.
    setApiSession(null);
    updateRole(value);
    setContract("CTR-001");
    setCompetence("10/2026");
  }

  async function connectApi(rawToken: string): Promise<void> {
    const token = rawToken.trim();
    const { user, contracts } = await identifyWithApi(token);
    // GESTOR_FORN compartilha a perspectiva visual da fornecedora, mas mantém o
    // papel original para autorização em todas as chamadas da API.
    const viewRole: DemoRole = user.papel === "ANALISTA_BH" ? "ANALISTA_BH" : "OPERADOR_FORN";
    setApiSession({ user, contracts, token });
    updateRole(viewRole);
    setContract(contracts[0]?.id ?? "");
    setCompetence("");
  }

  return (
    <DemoContext.Provider value={{
      role, setRole, contract, setContract, competence, setCompetence,
      apiSession, connectApi,
    }}>
      {children}
    </DemoContext.Provider>
  );
}

export function useDemo() {
  const value = useContext(DemoContext);
  if (!value) throw new Error("DemoProvider não encontrado");
  return value;
}
