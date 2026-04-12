"use client";
import { createContext, useContext, useState, useEffect, ReactNode } from "react";

export interface EmpresaSimples {
  id: number;
  nome: string;
  nome_fantasia: string;
  cnpj: string;
}

interface EmpresaContextType {
  empresaSelecionada: EmpresaSimples | null;
  setEmpresaSelecionada: (e: EmpresaSimples | null) => void;
}

const EmpresaContext = createContext<EmpresaContextType>({
  empresaSelecionada: null,
  setEmpresaSelecionada: () => {},
});

export function EmpresaProvider({ children }: { children: ReactNode }) {
  const [empresaSelecionada, setEmpresaState] = useState<EmpresaSimples | null>(null);

  // Restaura empresa salva ao montar
  useEffect(() => {
    try {
      const saved = localStorage.getItem("controllo_empresa");
      if (saved) setEmpresaState(JSON.parse(saved));
    } catch {
      localStorage.removeItem("controllo_empresa");
    }
  }, []);

  const setEmpresaSelecionada = (e: EmpresaSimples | null) => {
    setEmpresaState(e);
    if (e) {
      localStorage.setItem("controllo_empresa", JSON.stringify(e));
    } else {
      localStorage.removeItem("controllo_empresa");
    }
  };

  return (
    <EmpresaContext.Provider value={{ empresaSelecionada, setEmpresaSelecionada }}>
      {children}
    </EmpresaContext.Provider>
  );
}

export function useEmpresa() {
  return useContext(EmpresaContext);
}
