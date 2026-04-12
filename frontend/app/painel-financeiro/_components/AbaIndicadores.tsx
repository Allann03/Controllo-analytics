"use client";

import { useState } from "react";
import { n, CardIndicador, Gauge, COR_POSITIVO, COR_NEGATIVO, COR_ATENCAO, COR_NEUTRO } from "./shared";
import type { IndicadoresResponse, IndicadorItem, MetricaFlat } from "./shared";

// ── Section header ────────────────────────────────────────────────────
function SectionHeader({ children, accent, extra }: { children: React.ReactNode; accent: string; extra?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-5">
      <div className="flex items-center gap-3">
        <div className="w-0.5 h-6 rounded-full flex-shrink-0" style={{ background: accent }} />
        <h3 className="text-xs font-black uppercase tracking-widest text-[#475569] dark:text-slate-300">{children}</h3>
      </div>
      {extra}
    </div>
  );
}

// ── Gauge card wrapper (Liquidez) ────────────────────────────────────
function GaugeCard({ label, tooltip, variacao, valor, faixas, invertido = false, children }: {
  label: string; tooltip?: string; variacao?: number | null;
  valor?: number | null; faixas?: { ok: number; atencao: number }; invertido?: boolean;
  children: React.ReactNode;
}) {
  // Compute zone label & color
  const gaugeZone = (() => {
    if (valor === null || valor === undefined || !faixas) return null;
    if (invertido) {
      if (valor <= faixas.ok) return { label: "Saudavel", color: COR_POSITIVO };
      if (valor <= faixas.atencao) return { label: "Atencao", color: COR_ATENCAO };
      return { label: "Critico", color: COR_NEGATIVO };
    } else {
      if (valor >= faixas.ok) return { label: "Saudavel", color: COR_POSITIVO };
      if (valor >= faixas.atencao) return { label: "Atencao", color: COR_ATENCAO };
      return { label: "Critico", color: COR_NEGATIVO };
    }
  })();

  return (
    <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-5 flex flex-col items-center gap-1">
      <p className="text-[11px] font-black text-[#64748B] dark:text-slate-500 uppercase tracking-widest self-start mb-1">{label}</p>
      {children}
      {/* Status label below gauge */}
      {gaugeZone && (
        <p className="text-[10px] font-bold uppercase tracking-wider mt-1" style={{ color: gaugeZone.color }}>
          {gaugeZone.label}
        </p>
      )}
      {variacao !== null && variacao !== undefined && (
        <p className={`text-xs font-semibold ${(variacao ?? 0) > 0 ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"}`}>
          {(variacao ?? 0) > 0 ? "▲" : "▼"} {Math.abs(variacao ?? 0).toFixed(1)}% vs mês ant.
        </p>
      )}
      {tooltip && <p className="text-[10px] text-[#94A3B8] dark:text-slate-600 text-center leading-snug mt-0.5">{tooltip}</p>}
    </div>
  );
}

// ── Zone bar component ────────────────────────────────────────────────
function ZoneBar({ valor, faixas, invertido = false, unidade = "%" }: {
  valor: number | null;
  faixas: { ok: number; atencao: number };
  invertido?: boolean;
  unidade?: string;
}) {
  if (valor === null || valor === undefined) {
    return (
      <div className="mt-3">
        <div className="h-6 rounded-lg bg-slate-100 dark:bg-slate-700/40 flex items-center justify-center">
          <span className="text-[10px] text-[#94A3B8] dark:text-slate-600">Dados insuficientes</span>
        </div>
      </div>
    );
  }

  // Display range: 0 → maxDisplay
  const maxDisplay = invertido
    ? faixas.atencao * 1.5
    : faixas.ok * 1.8;

  const clampedVal = Math.min(maxDisplay, Math.max(0, valor));
  const pointerPct = (clampedVal / maxDisplay) * 100;

  // Three zone segments (widths as % of maxDisplay)
  const zones = invertido
    ? [
        { label: "Ideal",   w: (faixas.ok / maxDisplay) * 100,                          bg: "#DCFCE7", darkBg: "rgba(20,83,45,0.25)",  textColor: "#1A6B3C" },
        { label: "Atenção", w: ((faixas.atencao - faixas.ok) / maxDisplay) * 100,        bg: "#FEF3C7", darkBg: "rgba(69,26,3,0.25)",   textColor: "#92400E" },
        { label: "Risco",   w: ((maxDisplay - faixas.atencao) / maxDisplay) * 100,       bg: "#FEE2E2", darkBg: "rgba(69,10,10,0.25)",  textColor: "#B83030" },
      ]
    : [
        { label: "Baixo",   w: (faixas.atencao / maxDisplay) * 100,                      bg: "#FEE2E2", darkBg: "rgba(69,10,10,0.25)",  textColor: "#B83030" },
        { label: "Atenção", w: ((faixas.ok - faixas.atencao) / maxDisplay) * 100,        bg: "#FEF3C7", darkBg: "rgba(69,26,3,0.25)",   textColor: "#92400E" },
        { label: "Ideal",   w: ((maxDisplay - faixas.ok) / maxDisplay) * 100,            bg: "#DCFCE7", darkBg: "rgba(20,83,45,0.25)",  textColor: "#1A6B3C" },
      ];

  return (
    <div className="mt-3 w-full select-none">
      {/* Segmented bar with pointer */}
      <div className="relative">
        <div className="flex h-7 rounded-lg overflow-hidden gap-px">
          {zones.map((z, i) => (
            <div
              key={i}
              style={{ width: `${z.w}%`, background: z.bg }}
              className="flex items-center justify-center dark:opacity-80"
            >
              <span className="text-[9px] font-black uppercase tracking-wider hidden sm:block" style={{ color: z.textColor }}>
                {z.label}
              </span>
            </div>
          ))}
        </div>

        {/* Marker line */}
        <div
          className="absolute top-0 bottom-0 flex flex-col items-center pointer-events-none"
          style={{ left: `${pointerPct}%`, transform: "translateX(-50%)" }}
        >
          <div className="w-0.5 h-7 bg-[#0F2D4A] dark:bg-white rounded-full" />
        </div>
      </div>

      {/* Value label positioned under marker */}
      <div className="relative h-5 mt-1">
        <div
          className="absolute -translate-x-1/2 text-[10px] font-black tabular-nums whitespace-nowrap"
          style={{
            left: `clamp(16px, ${pointerPct}%, calc(100% - 16px))`,
            color: "var(--text-primary)",
          }}
        >
          {valor.toFixed(unidade === "%" ? 1 : 2)}{unidade}
        </div>
      </div>

      {/* Scale labels */}
      <div className="flex justify-between mt-0.5">
        <span className="text-[9px] text-[#94A3B8] dark:text-slate-600 tabular-nums">0{unidade}</span>
        <span className="text-[9px] text-[#94A3B8] dark:text-slate-600 tabular-nums">
          {invertido ? faixas.ok : faixas.atencao}{unidade}
        </span>
        <span className="text-[9px] text-[#94A3B8] dark:text-slate-600 tabular-nums">
          {invertido ? faixas.atencao : faixas.ok}{unidade}
        </span>
        <span className="text-[9px] text-[#94A3B8] dark:text-slate-600 tabular-nums">{maxDisplay.toFixed(0)}{unidade}</span>
      </div>
    </div>
  );
}

// ── Métrica Financeira card (Rentabilidade) ───────────────────────────
function MetricaFinanceira({ label, valor, variacao, faixas, invertido = false, unidade = "%", tooltip, explicacao }: {
  label: string;
  valor: number | null;
  variacao?: number | null;
  faixas: { ok: number; atencao: number };
  invertido?: boolean;
  unidade?: string;
  tooltip?: string;
  explicacao?: React.ReactNode;
}) {
  const [showTip, setShowTip] = useState(false);

  const getStatus = () => {
    if (valor === null) return "sem-dados";
    if (invertido) {
      if (valor <= faixas.ok) return "ideal";
      if (valor <= faixas.atencao) return "atencao";
      return "risco";
    } else {
      if (valor >= faixas.ok) return "ideal";
      if (valor >= faixas.atencao) return "atencao";
      return "risco";
    }
  };

  const status = getStatus();

  const statusCfg = {
    ideal:     { label: "Ideal",    bg: "bg-emerald-50 dark:bg-emerald-500/10",  border: "border-emerald-200 dark:border-emerald-500/30",  text: "text-emerald-700 dark:text-emerald-400",  accentBorder: "#1A6B3C", valueCor: COR_POSITIVO },
    atencao:   { label: "Atenção",  bg: "bg-amber-50 dark:bg-amber-500/10",      border: "border-amber-200 dark:border-amber-500/30",      text: "text-amber-700 dark:text-amber-400",      accentBorder: "#92400E", valueCor: COR_ATENCAO },
    risco:     { label: "Risco",    bg: "bg-rose-50 dark:bg-rose-500/10",        border: "border-rose-200 dark:border-rose-500/30",        text: "text-rose-700 dark:text-rose-400",        accentBorder: "#B83030", valueCor: COR_NEGATIVO },
    "sem-dados": { label: "—",      bg: "bg-slate-50 dark:bg-slate-800/40",      border: "border-slate-200 dark:border-slate-700",        text: "text-[#94A3B8]",                          accentBorder: "#CBD5E1", valueCor: "#94A3B8" },
  }[status];

  const variacaoPos = variacao !== null && variacao !== undefined && variacao > 0;
  const variacaoNeg = variacao !== null && variacao !== undefined && variacao < 0;

  return (
    <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">
      {/* Accent top bar */}
      <div className="h-1 w-full" style={{ background: statusCfg.accentBorder }} />

      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <p className="text-[11px] font-black text-[#64748B] dark:text-slate-500 uppercase tracking-widest">{label}</p>
          <div className="flex items-center gap-2">
            {/* Status badge */}
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${statusCfg.bg} ${statusCfg.border} ${statusCfg.text}`}>
              <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: statusCfg.accentBorder }} />
              {statusCfg.label}
            </span>
            {/* Info icon */}
            <button
              onMouseEnter={() => setShowTip(true)}
              onMouseLeave={() => setShowTip(false)}
              className="relative flex-shrink-0"
            >
              <svg className="w-3.5 h-3.5 text-[#94A3B8] dark:text-slate-600 hover:text-[#64748B] dark:hover:text-slate-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {showTip && tooltip && (
                <div className="absolute right-0 bottom-full mb-2 w-56 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-xl p-3 text-xs text-[#475569] dark:text-slate-300 leading-relaxed z-20 shadow-xl">
                  {tooltip}
                </div>
              )}
            </button>
          </div>
        </div>

        {/* Value + trend */}
        <div className="flex items-baseline gap-3 mb-1">
          <p className="text-3xl font-black font-mono tabular-nums leading-none" style={{ color: statusCfg.valueCor }}>
            {valor !== null ? `${valor.toFixed(1)}${unidade}` : "—"}
          </p>
          {variacao !== null && variacao !== undefined && (
            <span className={`text-xs font-bold ${variacaoPos ? "text-emerald-700 dark:text-emerald-400" : variacaoNeg ? "text-rose-700 dark:text-rose-400" : "text-[#94A3B8]"}`}>
              {variacaoPos ? "▲" : variacaoNeg ? "▼" : "—"} {Math.abs(variacao).toFixed(1)}% vs mês ant.
            </span>
          )}
        </div>

        {/* Mini explanation */}
        {explicacao}

        {/* Zone bar */}
        <ZoneBar valor={valor} faixas={faixas} invertido={invertido} unidade={unidade} />

        {/* Benchmark reference */}
        <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-slate-100 dark:border-slate-700/60">
          <svg className="w-3 h-3 text-[#94A3B8] dark:text-slate-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <span className="text-[10px] text-[#94A3B8] dark:text-slate-600">
            Benchmark: <span className="font-bold">{invertido ? `≤ ${faixas.ok}${unidade}` : `≥ ${faixas.ok}${unidade}`}</span>
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────
export default function AbaIndicadores({ ind, metricas }: { ind: IndicadoresResponse; metricas: MetricaFlat }) {
  const [showTipCiclo, setShowTipCiclo] = useState(false);

  const ebitdaPositivo  = (ind.ebitda?.valor ?? 0) > 0;
  const cglPositivo     = (ind.capital_giro_liquido?.valor ?? 0) >= 0;
  const margemEbitda    = ind.margem_ebitda?.valor ?? 0;
  const cicloNeg        = (ind.ciclo_financeiro?.valor ?? 1) < 0;
  const corMargemEbitda = margemEbitda >= 15 ? COR_POSITIVO : margemEbitda >= 8 ? COR_ATENCAO : COR_NEGATIVO;

  return (
    <div className="space-y-8">

      {/* ── EBITDA & Margens ── */}
      <section>
        <SectionHeader accent={COR_NEUTRO}>EBITDA e Margens</SectionHeader>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="rounded-2xl overflow-hidden">
            <div className="h-1 w-full" style={{ background: ebitdaPositivo ? COR_POSITIVO : COR_NEGATIVO }} />
            <CardIndicador label="EBITDA" valor={ind.ebitda?.valor ?? null} variacao={ind.ebitda?.variacao_pct}
              tooltip={ind.ebitda?.tooltip ?? "EBIT + Depreciacao e Amortizacao"} formato="moeda"
              cor={ebitdaPositivo ? COR_POSITIVO : COR_NEGATIVO} />
          </div>
          <div className="rounded-2xl overflow-hidden">
            <div className="h-1 w-full" style={{ background: corMargemEbitda }} />
            <CardIndicador label="Margem EBITDA" valor={ind.margem_ebitda?.valor ?? null} variacao={ind.margem_ebitda?.variacao_pct}
              tooltip={ind.margem_ebitda?.tooltip ?? "EBITDA / Receita Liquida x 100"} formato="pct"
              cor={corMargemEbitda} />
          </div>
          <div className="rounded-2xl overflow-hidden">
            <div className="h-1 w-full" style={{ background: cglPositivo ? COR_POSITIVO : COR_NEGATIVO }} />
            <CardIndicador label="Capital de Giro Liquido" valor={ind.capital_giro_liquido?.valor ?? null} variacao={ind.capital_giro_liquido?.variacao_pct}
              tooltip={ind.capital_giro_liquido?.tooltip ?? "Ativo Circulante - Passivo Circulante"} formato="moeda"
              cor={cglPositivo ? COR_POSITIVO : COR_NEGATIVO} />
          </div>
        </div>
        {n(metricas.depreciacao_amortizacao) === 0 && (
          <p className="text-[11px] text-amber-700 dark:text-amber-400/80 mt-3 flex items-center gap-1.5">
            <svg className="w-3 h-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            D&A informado como R$ 0. Para EBITDA preciso, informe a Depreciação/Amortização no lançamento mensal.
          </p>
        )}
      </section>

      <div className="border-t border-slate-100 dark:border-slate-800" />

      {/* ── Liquidez ── */}
      <section>
        <SectionHeader accent={COR_POSITIVO}>Liquidez</SectionHeader>
        <div className="grid grid-cols-2 gap-5">
          {([
            { key: "liquidez_corrente" as keyof IndicadoresResponse, label: "Liquidez Corrente", faixas: { ok: 1.2, atencao: 0.8 } },
            { key: "liquidez_seca"     as keyof IndicadoresResponse, label: "Liquidez Seca",     faixas: { ok: 1.0, atencao: 0.7 } },
          ] as Array<{ key: keyof IndicadoresResponse; label: string; faixas: { ok: number; atencao: number } }>).map(({ key, label, faixas }) => {
            const item = ind[key] as IndicadorItem | undefined;
            return (
              <GaugeCard key={key} label={label} tooltip={item?.tooltip} variacao={item?.variacao_pct} valor={item?.valor ?? null} faixas={faixas}>
                <Gauge valor={item?.valor ?? null} faixas={faixas} />
              </GaugeCard>
            );
          })}
        </div>
      </section>

      <div className="border-t border-slate-100 dark:border-slate-800" />

      {/* ── Rentabilidade & Endividamento ── */}
      <section>
        <SectionHeader accent={COR_NEUTRO}>Rentabilidade e Endividamento</SectionHeader>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricaFinanceira
            label="ROE — Retorno sobre PL"
            valor={ind.roe?.valor ?? null}
            variacao={ind.roe?.variacao_pct}
            faixas={{ ok: 15, atencao: 5 }}
            unidade="%"
            tooltip={ind.roe?.tooltip ?? "Lucro Líquido / Patrimônio Líquido"}
            explicacao={ind.roe?.valor != null ? (
              <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1 leading-snug">
                A cada R$ 1 investido, retorno de R$ {(ind.roe.valor / 100).toFixed(2)}
              </p>
            ) : undefined}
          />
          <MetricaFinanceira
            label="ROA — Retorno sobre Ativo"
            valor={ind.roa?.valor ?? null}
            variacao={ind.roa?.variacao_pct}
            faixas={{ ok: 8, atencao: 3 }}
            unidade="%"
            tooltip={ind.roa?.tooltip ?? "Lucro Líquido / Ativo Total"}
            explicacao={ind.roa?.valor != null ? (
              <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1 leading-snug">
                Os ativos geram {ind.roa.valor.toFixed(1)}% de retorno
              </p>
            ) : undefined}
          />
          <MetricaFinanceira
            label="Endividamento Geral"
            valor={ind.endividamento_geral?.valor ?? null}
            variacao={ind.endividamento_geral?.variacao_pct}
            faixas={{ ok: 40, atencao: 70 }}
            invertido
            unidade="%"
            tooltip={ind.endividamento_geral?.tooltip ?? "Passivo Total / Ativo Total"}
            explicacao={ind.endividamento_geral?.valor != null ? (
              <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1 leading-snug">
                {ind.endividamento_geral.valor <= 50 ? "Endividamento controlado" : ind.endividamento_geral.valor <= 70 ? "Atencao ao nivel de divida" : "Endividamento elevado"}
              </p>
            ) : undefined}
          />
        </div>

        {/* Tabela comparativa rápida */}
        <div className="mt-4 bg-[#F8FAFC] dark:bg-slate-800/30 border border-slate-200 dark:border-slate-700/60 rounded-xl overflow-hidden">
          <div className="grid grid-cols-4 text-[10px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700/60">
            <span>Indicador</span>
            <span className="text-right">Valor atual</span>
            <span className="text-right">Benchmark</span>
            <span className="text-right">Distância</span>
          </div>
          {[
            { label: "ROE", valor: ind.roe?.valor ?? null,                  benchmark: 15, invertido: false, unidade: "%" },
            { label: "ROA", valor: ind.roa?.valor ?? null,                  benchmark: 8,  invertido: false, unidade: "%" },
            { label: "Endividamento", valor: ind.endividamento_geral?.valor ?? null, benchmark: 40, invertido: true, unidade: "%" },
          ].map(({ label, valor, benchmark, invertido, unidade }) => {
            const dist = valor !== null ? valor - benchmark : null;
            const distOk = invertido ? (dist !== null && dist <= 0) : (dist !== null && dist >= 0);
            const distColor = dist === null ? "text-[#94A3B8]"
              : distOk ? "text-emerald-700 dark:text-emerald-400"
              : "text-rose-700 dark:text-rose-400";
            return (
              <div key={label} className="grid grid-cols-4 items-center px-4 py-2.5 border-b border-slate-100 dark:border-slate-700/40 last:border-0 hover:bg-white dark:hover:bg-slate-800/40 transition-colors">
                <span className="text-xs font-semibold text-[#475569] dark:text-slate-400">{label}</span>
                <span className="text-right text-xs font-mono font-bold text-[#0F172A] dark:text-slate-200 tabular-nums">
                  {valor !== null ? `${valor.toFixed(1)}${unidade}` : "—"}
                </span>
                <span className="text-right text-xs font-mono text-[#64748B] dark:text-slate-500 tabular-nums">
                  {invertido ? `≤ ${benchmark}${unidade}` : `≥ ${benchmark}${unidade}`}
                </span>
                <span className={`text-right text-xs font-mono font-bold tabular-nums ${distColor}`}>
                  {dist !== null ? `${dist >= 0 ? "+" : ""}${dist.toFixed(1)}${unidade}` : "—"}
                </span>
              </div>
            );
          })}
        </div>
      </section>

      <div className="border-t border-slate-100 dark:border-slate-800" />

      {/* ── Ciclo Financeiro ── */}
      <section>
        <SectionHeader accent={COR_ATENCAO}>
          Ciclo Financeiro
          <button
            onMouseEnter={() => setShowTipCiclo(true)}
            onMouseLeave={() => setShowTipCiclo(false)}
            className="relative ml-1"
          >
            <svg className="w-3.5 h-3.5 text-[#94A3B8] dark:text-slate-600 hover:text-[#64748B] dark:hover:text-slate-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {showTipCiclo && (
              <div className="absolute left-0 bottom-full mb-2 w-72 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-xl p-3 text-xs text-[#475569] dark:text-slate-300 leading-relaxed z-20 shadow-xl">
                {ind.ciclo_financeiro?.tooltip}
              </div>
            )}
          </button>
        </SectionHeader>

        {ind.ciclo_financeiro?.valor === null ? (
          <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-8 text-center text-[#94A3B8] dark:text-slate-600 text-sm">
            Dados insuficientes — informe Contas a Receber, Estoques e Fornecedores no balanço.
          </div>
        ) : (
          <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60 rounded-2xl p-6">
            <div className="flex items-center justify-center gap-2 flex-wrap mb-6">
              {([
                { key: "PMR",   val: ind.ciclo_financeiro?.pmr,   desc: "Prazo Médio de Recebimento", cor: "border-[#1E4976]/30 dark:border-[#1E4976]/40 bg-[#1E4976]/5 dark:bg-[#1E4976]/10 text-[#1E4976] dark:text-blue-400" },
                { key: "+",     val: null, desc: "", cor: "" },
                { key: "PME",   val: ind.ciclo_financeiro?.pme,   desc: "Prazo Médio de Estocagem",   cor: "border-amber-300 dark:border-amber-400/30 bg-amber-50 dark:bg-amber-400/10 text-amber-800 dark:text-amber-400" },
                { key: "−",     val: null, desc: "", cor: "" },
                { key: "PMP",   val: ind.ciclo_financeiro?.pmp,   desc: "Prazo Médio de Pagamento",   cor: "border-emerald-300 dark:border-emerald-400/30 bg-emerald-50 dark:bg-emerald-400/10 text-emerald-800 dark:text-emerald-400" },
                { key: "=",     val: null, desc: "", cor: "" },
                { key: "Ciclo", val: ind.ciclo_financeiro?.valor, desc: "Ciclo Financeiro Total",     cor: cicloNeg ? "border-emerald-300 dark:border-emerald-400/30 bg-emerald-50 dark:bg-emerald-400/10 text-emerald-800 dark:text-emerald-400" : "border-rose-300 dark:border-rose-400/30 bg-rose-50 dark:bg-rose-400/10 text-rose-800 dark:text-rose-400" },
              ] as Array<{ key: string; val: number | null | undefined; desc: string; cor: string }>).map((item, idx) => (
                item.val === null && item.desc === "" ? (
                  <span key={idx} className="text-2xl font-black text-[#94A3B8] dark:text-slate-500 select-none">{item.key}</span>
                ) : (
                  <div key={idx} className={`flex flex-col items-center px-4 py-3 rounded-xl border ${item.cor}`}>
                    <p className="text-[9px] font-black uppercase tracking-widest opacity-70 mb-1">{item.key}</p>
                    <p className="text-2xl font-black font-mono tabular-nums">
                      {item.val !== null && item.val !== undefined ? `${Math.round(item.val)}d` : "—"}
                    </p>
                    <p className="text-[9px] opacity-60 text-center max-w-[80px] mt-0.5 leading-snug">{item.desc}</p>
                  </div>
                )
              ))}
            </div>
            <div className={`px-4 py-3 rounded-xl border text-sm leading-relaxed ${
              cicloNeg
                ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-500/20 text-emerald-800 dark:text-emerald-300"
                : "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-500/20 text-amber-800 dark:text-amber-300"
            }`}>
              {cicloNeg
                ? `Ciclo financeiro negativo (${Math.round(ind.ciclo_financeiro?.valor ?? 0)} dias): empresa financia suas operações com recursos de fornecedores. Posição saudável.`
                : `Ciclo financeiro positivo (${Math.round(ind.ciclo_financeiro?.valor ?? 0)} dias): empresa precisa de capital de giro para cobrir o gap entre pagar fornecedores e receber clientes.`
              }
            </div>
          </div>
        )}
      </section>

      <div className="border-t border-slate-100 dark:border-slate-800" />

      {/* ── Alertas Automáticos ── */}
      <section>
        <SectionHeader accent={COR_ATENCAO}>Alertas Automáticos</SectionHeader>
        <div className="space-y-2">
          {(() => {
            const alertas: { tipo: "ok" | "atencao" | "risco"; msg: string }[] = [];
            // ROE
            const roe = ind.roe?.valor ?? null;
            if (roe !== null) {
              if (roe >= 15) alertas.push({ tipo: "ok", msg: `ROE saudável (${roe.toFixed(1)}%) — acima do benchmark de 15%` });
              else if (roe >= 5) alertas.push({ tipo: "atencao", msg: `ROE na faixa de atenção (${roe.toFixed(1)}%) — benchmark: 15%` });
              else alertas.push({ tipo: "risco", msg: `ROE abaixo do ideal (${roe.toFixed(1)}%) — benchmark do setor: 15%` });
            }
            // ROA
            const roa = ind.roa?.valor ?? null;
            if (roa !== null) {
              if (roa >= 8) alertas.push({ tipo: "ok", msg: `ROA saudável (${roa.toFixed(1)}%) — acima do benchmark de 8%` });
              else if (roa >= 3) alertas.push({ tipo: "atencao", msg: `ROA na faixa de atenção (${roa.toFixed(1)}%) — benchmark: 8%` });
              else alertas.push({ tipo: "risco", msg: `ROA abaixo do ideal (${roa.toFixed(1)}%) — benchmark do setor: 8%` });
            }
            // Endividamento
            const endiv = ind.endividamento_geral?.valor ?? null;
            if (endiv !== null) {
              if (endiv <= 40) alertas.push({ tipo: "ok", msg: `Endividamento controlado (${endiv.toFixed(1)}%)` });
              else if (endiv <= 70) alertas.push({ tipo: "atencao", msg: `Endividamento na faixa de atenção (${endiv.toFixed(1)}%)` });
              else alertas.push({ tipo: "risco", msg: `Endividamento elevado (${endiv.toFixed(1)}%) — risco financeiro` });
            }
            // Liquidez
            const lc = ind.liquidez_corrente?.valor ?? null;
            if (lc !== null) {
              if (lc >= 1.2) alertas.push({ tipo: "ok", msg: `Liquidez corrente saudável (${lc.toFixed(2)})` });
              else if (lc >= 0.8) alertas.push({ tipo: "atencao", msg: `Liquidez corrente na faixa de atenção (${lc.toFixed(2)})` });
              else alertas.push({ tipo: "risco", msg: `Liquidez corrente crítica (${lc.toFixed(2)}) — risco de insolvência` });
            }
            if (alertas.length === 0) alertas.push({ tipo: "ok", msg: "Sem alertas — dados insuficientes para análise" });
            return alertas.map((a, i) => (
              <div key={i} className={`flex items-start gap-2.5 px-4 py-3 rounded-xl border text-sm ${
                a.tipo === "ok" ? "bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-500/20 text-emerald-800 dark:text-emerald-300"
                : a.tipo === "atencao" ? "bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-500/20 text-amber-800 dark:text-amber-300"
                : "bg-rose-50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-500/20 text-rose-800 dark:text-rose-300"
              }`}>
                <span className="flex-shrink-0 mt-0.5">{a.tipo === "ok" ? "✓" : a.tipo === "atencao" ? "⚠" : "✕"}</span>
                <span>{a.msg}</span>
              </div>
            ));
          })()}
        </div>
      </section>
    </div>
  );
}
