"use client";
import { ReactNode } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";

interface Props {
  children: ReactNode;
  /** Sobrescreve o nome da empresa (use em páginas com estado local de empresa). */
  nome?: string;
  className?: string;
}

/**
 * Wrapper para cards de gráfico.
 * Exibe o nome da empresa selecionada como overlay elegante no canto inferior direito.
 * Lê do EmpresaContext por padrão; use a prop `nome` para páginas com estado local.
 */
export default function GraficoComNome({ children, nome, className = "" }: Props) {
  const { empresaSelecionada } = useEmpresa();
  const nomeEfetivo = nome ?? empresaSelecionada?.nome ?? "";

  return (
    <div className={`relative ${className}`}>
      {children}
      {nomeEfetivo && (
        <div
          className="absolute bottom-3 right-4 flex items-center gap-2 pointer-events-none select-none"
          style={{ zIndex: 10 }}
        >
          <div
            style={{
              width: 1,
              height: 20,
              background: "linear-gradient(to bottom, transparent, rgba(79,106,255,0.45), transparent)",
            }}
          />
          <span
            style={{
              fontSize: 9,
              letterSpacing: "0.18em",
              color: "rgba(148,163,184,0.45)",
              fontWeight: 700,
              textTransform: "uppercase",
              fontFamily: "'Calibri', 'Inter', sans-serif",
              whiteSpace: "nowrap",
            }}
          >
            {nomeEfetivo}
          </span>
        </div>
      )}
    </div>
  );
}
