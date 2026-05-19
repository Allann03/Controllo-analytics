"use client";

import { useState } from "react";

// ── Formatters ───────────────────────────────────────────────────────
export const fmt = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v);
export const fmtPct = (v: number) => `${Number(v).toFixed(1)}%`;
export const n = (v: unknown) => (typeof v === "number" ? v : 0);

// ── Enterprise semantic colors ────────────────────────────────────────
export const COR_POSITIVO  = "#1A6B3C";
export const COR_NEGATIVO  = "#B83030";
export const COR_ATENCAO   = "#92400E";
export const COR_NEUTRO    = "#1E4976";

// ── Types ────────────────────────────────────────────────────────────
export interface MetricaFlat { [key: string]: number }

export interface DREResponse {
  periodo: string;
  cascata: { linha: string; valor: number; tipo: string; variacao_pct?: number | null }[];
  insights: Insight[];
  metricas: MetricaFlat;
  anterior?: MetricaFlat;
}

export interface FluxoResponse {
  historico: { mes: string; entradas: number; saidas: number; saldo: number }[];
  saldo_atual: number;
  saldo_proj_3m: number;
  media_entradas: number;
  media_saidas: number;
  alertas: { tipo: string; mensagem: string }[];
}

export interface BalancoResponse {
  periodo: string;
  metricas: MetricaFlat;
  indicadores: {
    liquidez_corrente?: number | null;
    grau_imobilizacao?: number | null;
    passivo_pl?: number | null;
  };
  insights: Insight[];
}

export interface HistoricoItem {
  mes_label: string;
  receita_bruta: number;
  receita_liquida: number;
  lucro_liquido: number;
  margem_liquida: number;
  carga_tributaria: number;
  [key: string]: number | string;
}

export interface Insight {
  codigo: string;
  titulo: string;
  descricao: string;
  severidade: "critico" | "atencao" | "info";
}

export interface IndicadorItem {
  valor: number | null;
  variacao_pct?: number | null;
  tooltip?: string;
  faixas?: { ok: number; atencao: number };
  invertido?: boolean;
}

export interface IndicadoresResponse {
  sem_dados?: boolean;
  periodo?: string;
  ebitda?: IndicadorItem;
  margem_ebitda?: IndicadorItem;
  capital_giro_liquido?: IndicadorItem;
  liquidez_corrente?: IndicadorItem & { faixas: { ok: number; atencao: number } };
  liquidez_seca?: IndicadorItem & { faixas: { ok: number; atencao: number } };
  roe?: IndicadorItem & { faixas: { ok: number; atencao: number } };
  roa?: IndicadorItem & { faixas: { ok: number; atencao: number } };
  endividamento_geral?: IndicadorItem & { faixas: { ok: number; atencao: number }; invertido: boolean };
  ciclo_financeiro?: IndicadorItem & { pmr: number | null; pme: number | null; pmp: number | null };
}

// ── Shared UI components ─────────────────────────────────────────────
export function MetricaRow({ label, value, destaque }: { label: string; value: string; destaque?: boolean }) {
  return (
    <div
      className={`flex items-center justify-between py-2.5 last:border-0 ${
        destaque ? "font-bold mt-1" : ""
      }`}
      style={{ borderBottom: "1px solid var(--border)" }}
    >
      <span
        className={`text-sm ${destaque ? "tracking-wide uppercase text-[10px]" : ""}`}
        style={{ color: destaque ? "var(--text-primary)" : "var(--text-secondary)" }}
      >
        {label}
      </span>
      <span
        className={`font-mono tabular-nums ${destaque ? "text-sm font-bold" : "text-sm"}`}
        style={{ color: destaque ? "var(--text-primary)" : "var(--text-secondary)" }}
      >
        {value}
      </span>
    </div>
  );
}

export function SectionTitle({ children, accent = "#1E4976" }: { children: React.ReactNode; accent?: string }) {
  return (
    <div className="flex items-center gap-2.5 mb-4 pb-2.5 border-b border-slate-100 dark:border-slate-700/60">
      <div className="w-0.5 h-5 rounded-full flex-shrink-0" style={{ background: accent }} />
      <h3 className="text-[11px] font-black uppercase tracking-widest text-[#64748B] dark:text-slate-400">{children}</h3>
    </div>
  );
}

export function InsightsList({ insights }: { insights: Insight[] }) {
  if (!insights?.length) return null;
  return (
    <div className="rounded-2xl p-4 mt-4 bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700">
      <p className="text-[10px] font-black uppercase tracking-widest mb-3 text-[#64748B] dark:text-slate-400">Alertas contextuais</p>
      <div className="space-y-2">
        {insights.map((ins) => (
          <div key={ins.codigo} className={`flex items-start gap-2.5 px-3 py-2.5 rounded-lg border text-sm ${
            ins.severidade === "critico"
              ? "border-red-200 dark:border-red-500/30 bg-red-50 dark:bg-red-500/8 text-red-700 dark:text-red-300"
              : ins.severidade === "atencao"
              ? "border-amber-200 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-500/8 text-amber-800 dark:text-amber-300"
              : "border-blue-200 dark:border-blue-500/30 bg-blue-50 dark:bg-blue-500/8 text-blue-700 dark:text-blue-300"
          }`}>
            <div className="flex-shrink-0 mt-0.5">
              {ins.severidade === "critico" ? (
                <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86l-8.6 14.86A1 1 0 002.56 20h18.88a1 1 0 00.87-1.28l-8.6-14.86a1 1 0 00-1.42 0z" />
                </svg>
              ) : ins.severidade === "atencao" ? (
                <svg className="w-4 h-4 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
            </div>
            <div>
              <span className="font-semibold">{ins.titulo}</span>
              <p className="text-xs mt-0.5 opacity-80">{ins.descricao}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Gauge (mini arc SVG) ─────────────────────────────────────────────
export function Gauge({
  valor, faixas, invertido, unidade = "",
}: {
  valor: number | null;
  faixas: { ok: number; atencao: number };
  invertido?: boolean;
  unidade?: string;
}) {
  if (valor === null || valor === undefined) {
    return (
      <div className="flex flex-col items-center justify-center h-24">
        <svg viewBox="0 0 120 65" className="w-32 h-16 opacity-20">
          <path d="M10,60 A50,50 0 0,1 110,60" fill="none" stroke="#CBD5E1" strokeWidth="10" strokeLinecap="round" />
        </svg>
        <p className="text-[11px] text-[#94A3B8] dark:text-slate-600 mt-1">Dados insuficientes</p>
      </div>
    );
  }

  const cor: string = (() => {
    if (invertido) {
      if (valor <= faixas.ok) return COR_POSITIVO;
      if (valor <= faixas.atencao) return COR_ATENCAO;
      return COR_NEGATIVO;
    } else {
      if (valor >= faixas.ok) return COR_POSITIVO;
      if (valor >= faixas.atencao) return COR_ATENCAO;
      return COR_NEGATIVO;
    }
  })();

  const norm = invertido
    ? Math.min(1, Math.max(0, 1 - (valor - 0) / (faixas.atencao * 1.5)))
    : Math.min(1, Math.max(0, valor / (faixas.ok * 1.5)));

  const R = 50; const cx = 60; const cy = 60;
  const startAngle = Math.PI;
  const endAngle = startAngle + norm * Math.PI;
  const x1 = cx + R * Math.cos(startAngle);
  const y1 = cy + R * Math.sin(startAngle);
  const x2 = cx + R * Math.cos(endAngle);
  const y2 = cy + R * Math.sin(endAngle);
  const largeArc = norm > 0.5 ? 1 : 0;

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 120 65" className="w-32 h-16">
        {/* Track — visible in both light and dark */}
        <path d="M10,60 A50,50 0 0,1 110,60" fill="none" stroke="#CBD5E1" strokeWidth="10" strokeLinecap="round" />
        {/* Zone arcs — green/yellow/red background segments */}
        {(() => {
          const zones = invertido
            ? [
                { end: faixas.ok / (faixas.atencao * 1.5), color: "rgba(26,107,60,0.15)" },
                { end: faixas.atencao / (faixas.atencao * 1.5), color: "rgba(146,64,14,0.15)" },
                { end: 1, color: "rgba(184,48,48,0.15)" },
              ]
            : [
                { end: faixas.atencao / (faixas.ok * 1.5), color: "rgba(184,48,48,0.15)" },
                { end: faixas.ok / (faixas.ok * 1.5), color: "rgba(146,64,14,0.15)" },
                { end: 1, color: "rgba(26,107,60,0.15)" },
              ];
          let prev = 0;
          return zones.map((z, i) => {
            const startA = Math.PI + prev * Math.PI;
            const endA = Math.PI + z.end * Math.PI;
            const sx = cx + R * Math.cos(startA);
            const sy = cy + R * Math.sin(startA);
            const ex = cx + R * Math.cos(endA);
            const ey = cy + R * Math.sin(endA);
            const la = (z.end - prev) > 0.5 ? 1 : 0;
            prev = z.end;
            return (
              <path key={i}
                d={`M${sx},${sy} A${R},${R} 0 ${la},1 ${ex},${ey}`}
                fill="none" stroke={z.color} strokeWidth="10" strokeLinecap="round"
              />
            );
          });
        })()}
        {norm > 0.01 && (
          <path
            d={`M${x1},${y1} A${R},${R} 0 ${largeArc},1 ${x2},${y2}`}
            fill="none" stroke={cor} strokeWidth="10" strokeLinecap="round"
          />
        )}
      </svg>
      <p className="text-xl font-black font-mono tabular-nums -mt-2" style={{ color: cor }}>
        {unidade === "R$" ? fmt(valor) : valor.toFixed(unidade === "%" ? 1 : 2)}{unidade !== "R$" ? unidade : ""}
      </p>
      <p className="text-[10px] font-bold uppercase tracking-wider mt-0.5" style={{ color: cor }}>
        {cor === COR_POSITIVO ? "Saudável" : cor === COR_ATENCAO ? "Atenção" : cor === COR_NEGATIVO ? "Crítico" : ""}
      </p>
    </div>
  );
}

// ── CardIndicador ────────────────────────────────────────────────────
export function CardIndicador({
  label, valor, variacao, tooltip, formato = "numero", cor,
}: {
  label: string;
  valor: number | null;
  variacao?: number | null;
  tooltip: string;
  formato?: "moeda" | "pct" | "numero" | "dias";
  cor?: string;
}) {
  const [showTip, setShowTip] = useState(false);

  const valorFmt = valor === null || valor === undefined
    ? null
    : formato === "moeda" ? fmt(valor)
    : formato === "pct" ? `${valor.toFixed(1)}%`
    : formato === "dias" ? `${Math.round(valor)} dias`
    : valor.toFixed(2);

  const variacaoPos = variacao !== null && variacao !== undefined && variacao > 0;
  const variacaoNeg = variacao !== null && variacao !== undefined && variacao < 0;

  return (
    <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-black text-[#64748B] dark:text-slate-500 uppercase tracking-widest">{label}</p>
        <button
          onMouseEnter={() => setShowTip(true)}
          onMouseLeave={() => setShowTip(false)}
          className="relative"
        >
          <svg className="w-3.5 h-3.5 text-[#94A3B8] dark:text-slate-600 hover:text-[#64748B] dark:hover:text-slate-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {showTip && (
            <div className="absolute right-0 bottom-full mb-2 w-56 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-xl p-3 text-xs text-[#475569] dark:text-slate-300 leading-relaxed z-20 shadow-xl">
              {tooltip}
            </div>
          )}
        </button>
      </div>

      {valorFmt === null ? (
        <div>
          <p className="text-2xl font-black text-slate-300 dark:text-slate-700">—</p>
          <p className="text-[10px] text-[#94A3B8] dark:text-slate-600 mt-1">Dados insuficientes</p>
        </div>
      ) : (
        <div>
          <p className="text-2xl font-black font-mono tabular-nums" style={{ color: cor || "var(--text-primary)" }}>{valorFmt}</p>
          {variacao !== null && variacao !== undefined && (
            <p className={`text-xs font-semibold mt-1 ${
              variacaoPos ? "text-emerald-700 dark:text-emerald-400"
              : variacaoNeg ? "text-rose-700 dark:text-rose-400"
              : "text-[#64748B] dark:text-slate-500"
            }`}>
              {variacaoPos ? "▲" : variacaoNeg ? "▼" : "—"} {Math.abs(variacao).toFixed(1)}% vs mês ant.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
