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

/** Componente de avatar que lê automaticamente do localStorage */
export function UserAvatar({ size = 32, className = "" }: { size?: number; className?: string }) {
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

  const Icon = FLAT_ICONS_MAP[avatarId] ?? Users;
  const iconSize = Math.max(14, Math.round(size * 0.55));
  const hasIcon = !!FLAT_ICONS_MAP[avatarId];

  return (
    <div
      className={`flex items-center justify-center flex-shrink-0 ${className}`}
      style={{
        width: size, height: size,
        borderRadius: size > 28 ? 12 : 8,
        background: hasIcon ? "var(--accent-subtle)" : "var(--bg-inset)",
        border: `1px solid ${hasIcon ? "var(--accent-border)" : "var(--border-subtle)"}`,
        color: hasIcon ? "var(--accent)" : "var(--text-secondary)",
      }}
    >
      <Icon size={iconSize} strokeWidth={1.75} />
    </div>
  );
}
