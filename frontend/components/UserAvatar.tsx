"use client";
import { useState, useEffect } from "react";
import {
  Calculator, Users, Briefcase, BriefcaseBusiness, ShieldCheck, Shield,
  Wallet, Crown, Award, Scale,
  type LucideIcon,
} from "lucide-react";

// Registry deve casar com FLAT_ICONS em app/configuracoes/page.tsx.
const FLAT_ICONS_MAP: Record<string, LucideIcon> = {
  cont:     Calculator,
  dp:       Users,
  gestor:   Briefcase,
  gestora:  BriefcaseBusiness,
  diretor:  ShieldCheck,
  diretora: Shield,
  fin:      Wallet,
  socio:    Crown,
  socia:    Award,
  fiscal:   Scale,
};

/** Lê o avatar ID salvo no localStorage */
export function getAvatarId(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("controllo_avatar") ?? "";
}

interface UserAvatarProps {
  size?: number;
  className?: string;
  /** Iniciais (2 letras) usadas como fallback se nenhum avatar foi selecionado. */
  fallbackIniciais?: string;
  /** Border radius (default: rounded-full quando size <= 28, senao 12px). Pass "full" para sempre full. */
  rounded?: "default" | "full";
}

/** Componente de avatar que lê automaticamente do localStorage.
 *  Quando `controllo_avatar` esta vazio e `fallbackIniciais` foi passado,
 *  renderiza as iniciais sobre fundo accent. Caso contrario, mostra o
 *  icone Users default sobre fundo inset. */
export function UserAvatar({ size = 32, className = "", fallbackIniciais, rounded = "default" }: UserAvatarProps) {
  const [avatarId, setAvatarId] = useState("");

  useEffect(() => {
    setAvatarId(getAvatarId());
    // Re-check when storage changes (e.g., after saving in configuracoes)
    const handler = () => setAvatarId(getAvatarId());
    window.addEventListener("storage", handler);
    // Also poll for same-tab changes
    const interval = setInterval(handler, 2000);
    return () => { window.removeEventListener("storage", handler); clearInterval(interval); };
  }, []);

  const Icon = FLAT_ICONS_MAP[avatarId];
  const hasIcon = !!Icon;
  const showIniciais = !hasIcon && !!fallbackIniciais;

  const radiusValue = rounded === "full" ? "9999px" : (size > 28 ? "12px" : "8px");

  let background: string;
  let borderColor: string;
  let color: string;
  if (hasIcon) {
    background = "var(--accent-subtle)";
    borderColor = "var(--accent-border)";
    color = "var(--accent)";
  } else if (showIniciais) {
    background = "var(--accent)";
    borderColor = "var(--accent)";
    color = "var(--text-inverse)";
  } else {
    background = "var(--bg-inset)";
    borderColor = "var(--border-subtle)";
    color = "var(--text-secondary)";
  }

  const iconSize = Math.max(14, Math.round(size * 0.55));
  const fontSize = Math.max(10, Math.round(size * 0.36));

  return (
    <div
      className={`flex items-center justify-center flex-shrink-0 select-none leading-none ${className}`}
      style={{
        width: size,
        height: size,
        borderRadius: radiusValue,
        background,
        border: `1px solid ${borderColor}`,
        color,
      }}
    >
      {hasIcon ? (
        <Icon size={iconSize} strokeWidth={1.75} />
      ) : showIniciais ? (
        <span style={{ fontSize, fontWeight: 600 }}>{fallbackIniciais}</span>
      ) : (
        <Users size={iconSize} strokeWidth={1.75} />
      )}
    </div>
  );
}
