// Design system UI primitives — ContabilControlloBPO
// Rules: zero inline styles, zero hex colors, light-first + dark: prefix

"use client";
import { ReactNode, SelectHTMLAttributes, InputHTMLAttributes } from "react";

function cn(...c: (string | undefined | false | null)[]) {
  return c.filter(Boolean).join(" ");
}

// ─── Card ──────────────────────────────────────────────────────────────
interface CardProps { children: ReactNode; className?: string }

export function Card({ children, className }: CardProps) {
  return (
    <div className={cn(
      "rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800",
      "shadow-sm ring-1 ring-slate-200/50 dark:ring-slate-700/30",
      className,
    )}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className }: CardProps) {
  return (
    <div className={cn(
      "px-5 py-4 bg-slate-50 dark:bg-slate-700/50",
      "border-b border-slate-200 dark:border-slate-700",
      className,
    )}>
      {children}
    </div>
  );
}

export function CardContent({ children, className }: CardProps) {
  return <div className={cn("px-5 py-4", className)}>{children}</div>;
}

// ─── Badge (non-interactive — label/tag only) ──────────────────────────
export type BadgeVariant = "default" | "primary" | "success" | "warning" | "danger" | "muted";

const BADGE_CLS: Record<BadgeVariant, string> = {
  default: "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:border-slate-600",
  primary: "bg-navy-100 text-navy-800 border-navy-200 dark:bg-navy-900/40 dark:text-navy-300 dark:border-navy-800/60",
  success: "bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800/40",
  warning: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800/40",
  danger:  "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800/40",
  muted:   "bg-slate-50 text-slate-500 border-slate-100 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700",
};

const DOT_CLS: Record<BadgeVariant, string> = {
  default: "bg-slate-400",
  primary: "bg-navy-500",
  success: "bg-emerald-600",
  warning: "bg-amber-500",
  danger:  "bg-red-500",
  muted:   "bg-slate-400",
};

interface BadgeProps { children: ReactNode; variant?: BadgeVariant; dot?: boolean; className?: string }

export function Badge({ children, variant = "default", dot, className }: BadgeProps) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border",
      "text-xs font-semibold cursor-default select-none whitespace-nowrap",
      BADGE_CLS[variant],
      className,
    )}>
      {dot && <span className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0", DOT_CLS[variant])} />}
      {children}
    </span>
  );
}

// ─── Avatar (initials, deterministic bg, always white text) ───────────
// Paleta institucional — 10 cores escuras, branco sobre cada uma ✓ WCAG AA
const AVATAR_BG = [
  "bg-blue-900",    // #1e3a8a  contrast ~12:1 ✓
  "bg-slate-700",   // #334155  contrast ~7.5:1 ✓
  "bg-emerald-800", // #065f46  contrast ~11:1 ✓
  "bg-amber-700",   // #b45309  contrast ~4.7:1 ✓
  "bg-rose-800",    // #9f1239  contrast ~8.5:1 ✓
  "bg-indigo-900",  // #312e81  contrast ~13:1 ✓
  "bg-teal-800",    // #115e59  contrast ~10:1 ✓
  "bg-orange-800",  // #9a3412  contrast ~7.1:1 ✓
  "bg-cyan-800",    // #155e75  contrast ~9.5:1 ✓
  "bg-violet-900",  // #4c1d95  contrast ~13:1 ✓
];

function avatarBg(name: string) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h);
  return AVATAR_BG[Math.abs(h) % AVATAR_BG.length];
}

type AvatarSize = "sm" | "md" | "lg";
const AVATAR_SIZE: Record<AvatarSize, string> = {
  sm: "w-6 h-6 text-[9px]",
  md: "w-9 h-9 text-sm",
  lg: "w-11 h-11 text-base",
};

interface AvatarProps { name: string; size?: AvatarSize; className?: string }

export function Avatar({ name, size = "md", className }: AvatarProps) {
  const initials = (name || "?").split(" ").filter(Boolean)
    .map(n => n[0]).join("").substring(0, 2).toUpperCase();
  return (
    <div data-notheme className={cn(
      "rounded-lg flex items-center justify-center font-bold flex-shrink-0 text-white",
      avatarBg(name), AVATAR_SIZE[size], className,
    )}>
      {initials}
    </div>
  );
}

// ─── PageHeader ────────────────────────────────────────────────────────
interface PageHeaderProps {
  section?: string;
  title: string;
  titleAccent?: string;
  subtitle?: string;
  actions?: ReactNode;
  icon?: ReactNode;
}

export function PageHeader({ section, title, titleAccent, subtitle, actions, icon }: PageHeaderProps) {
  return (
    <div className="px-6 pt-6 pb-4 bg-white dark:bg-slate-900 border-b border-slate-100 dark:border-slate-800">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-start gap-3">
          {icon && (
            <div className="w-6 h-6 text-slate-400 dark:text-slate-500 mt-0.5 flex-shrink-0">{icon}</div>
          )}
          <div>
            {section && (
              <p className="text-xs font-bold uppercase tracking-widest text-navy-500 dark:text-navy-400 mb-1">{section}</p>
            )}
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 leading-tight">
              {title}{titleAccent && <span className="text-navy-600 dark:text-navy-400"> {titleAccent}</span>}
            </h1>
            {subtitle && <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">{subtitle}</p>}
          </div>
        </div>
        {actions && <div className="flex items-center gap-3 flex-shrink-0">{actions}</div>}
      </div>
    </div>
  );
}

// ─── Input (theme-aware) ───────────────────────────────────────────────
interface InputProps extends InputHTMLAttributes<HTMLInputElement> { label?: string }

export function Input({ label, className, ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
          {label}
        </label>
      )}
      <input className={cn(
        "rounded-xl px-3 py-2 text-xs outline-none transition-all",
        "bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700",
        "text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500",
        "focus:border-navy-500 focus:ring-2 focus:ring-navy-500/20",
        className,
      )} {...props} />
    </div>
  );
}

// ─── Select (theme-aware) ──────────────────────────────────────────────
interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> { label?: string; children: ReactNode }

export function Select({ label, className, children, ...props }: SelectProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
          {label}
        </label>
      )}
      <select className={cn(
        "rounded-xl px-3 py-2 text-xs outline-none transition-all",
        "bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700",
        "text-slate-900 dark:text-slate-100",
        "focus:border-navy-500 focus:ring-2 focus:ring-navy-500/20",
        className,
      )} {...props}>
        {children}
      </select>
    </div>
  );
}

// ─── EmptyState ────────────────────────────────────────────────────────
interface EmptyStateProps { icon?: ReactNode; title: string; description?: string; action?: ReactNode }

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-8 text-center gap-3
                    rounded-xl border border-dashed border-slate-200 dark:border-slate-700
                    bg-slate-50/50 dark:bg-slate-800/30">
      {icon && (
        <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-1
                        bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500">
          {icon}
        </div>
      )}
      <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">{title}</p>
      {description && <p className="text-xs text-slate-400 dark:text-slate-500 max-w-xs">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
