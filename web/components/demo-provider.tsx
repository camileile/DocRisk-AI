"use client";
import { createContext, useContext, useState, type ReactNode } from "react";
import type { DemoRole } from "@/lib/demo";
const DemoContext = createContext<{
  role: DemoRole | null;
  setRole: (role: DemoRole | null) => void;
  contract: string;
  setContract: (value: string) => void;
  competence: string;
  setCompetence: (value: string) => void;
} | null>(null);
export function DemoProvider({ children }: { children: ReactNode }) {
  const [role, updateRole] = useState<DemoRole | null>(null);
  const [contract, setContract] = useState("CTR-001");
  const [competence, setCompetence] = useState("10/2026");
  function setRole(value: DemoRole | null) {
    updateRole(value);
    setContract("CTR-001");
    setCompetence("10/2026");
  }
  return (
    <DemoContext.Provider
      value={{
        role,
        setRole,
        contract,
        setContract,
        competence,
        setCompetence,
      }}
    >
      {children}
    </DemoContext.Provider>
  );
}
export function useDemo() {
  const value = useContext(DemoContext);
  if (!value) throw new Error("DemoProvider não encontrado");
  return value;
}
