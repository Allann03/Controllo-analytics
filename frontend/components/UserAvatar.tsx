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
  /** Override explicito do avatar id. Quando passado (string ou null), tem
   *  prioridade sobre a leitura do localStorage. Use para renderizar avatar
   *  de OUTRO usuario (ex: lista de admin lendo cada Usuario.avatar_id do
   *  payload). null/undefined faz cair no fallbackIniciais. */
  avatarIdOverride?: string | null;
}

/** Componente de avatar.
 *  - Se `avatarIdOverride` for passado (incluindo null), usa ele direto.
 *  - Caso contrario, le `controllo_avatar` do localStorage (avatar do usuario
 *    logado) com polling 2s + storage event listener.
 *  - Fallback: se nao houver avatar e `fallbackIniciais` veio, renderiza as
 *    iniciais sobre fundo accent. Senao, icone Users default em bg-inset. */
export function UserAvatar({
  size = 32,
  className = "",
  fallbackIniciais,
  rounded = "default",
  avatarIdOverride,
}: UserAvatarProps) {
  const [avatarId, setAvatarId] = useState("");

  // Polling do localStorage so faz sentido quando NAO ha override explicito.
  // Quando override e passado, o componente deve renderizar exatamente o que
  // veio do parent (geralmente do backend) sem se preocupar com localStorage.
  const usaOverride = avatarIdOverride !== undefined;

  useEffect(() => {
    if (usaOverride) return; // override fixo, sem polling
    setAvatarId(getAvatarId());
    const handler = () => setAvatarId(getAvatarId());
    window.addEventListener("storage", handler);
    const interval = setInterval(handler, 2000);
    return () => { window.removeEventListener("storage", handler); clearInterval(interval); };
  }, [usaOverride]);

  const efetivo = usaOverride ? (avatarIdOverride ?? "") : avatarId;
  const Icon = FLAT_ICONS_MAP[efetivo];
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
