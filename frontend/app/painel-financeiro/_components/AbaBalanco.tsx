"use client";

import GraficoComNome from "@/components/GraficoComNome";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { useChartTheme } from "@/components/useChartTheme";
import { fmt, fmtPct, n, MetricaRow, SectionTitle, InsightsList } from "./shared";
import type { BalancoResponse } from "./shared";

// Enterprise palette — navy/slate family, no purple
const COLORS_ATIVO = ["#0F2D4A", "#1E4976", "#2D6FA3", "#64748B", "#94A3B8"];

export default function AbaBalanco({ balanco }: { balanco: BalancoResponse }) {
  const ct = useChartTheme();
  const m = balanco.metricas;
  const ind = balanco.indicadores ?? {};

  const dadosAtivo = [
    { name: "Caixa",          value: n(m.caixa_equivalentes) },
    { name: "Contas Receber", value: n(m.contas_receber) },
    { name: "Estoques",       value: n(m.estoques) },
    { name: "Outros Circ.",   value: n(m.outros_ativo_circ) },
    { name: "Não Circulante", value: n(m.ativo_nao_circulante) },
  ].filter((d) => d.value > 0);

  const indicadoresConfig = [
    {
      label: "Liquidez Corrente",
      value: ind.liquidez_corrente != null ? ind.liquidez_corrente.toFixed(2) : "—",
      sub: "Ativo Circ. / Passivo Circ.",
      ok: ind.liquidez_corrente != null && ind.liquidez_corrente >= 1.2,
      atencao: ind.liquidez_corrente != null && ind.liquidez_corrente >= 0.8 && ind.liquidez_corrente < 1.2,
    },
    {
      label: "Imobilização",
      value: ind.grau_imobilizacao != null ? fmtPct(ind.grau_imobilizacao) : "—",
      sub: "Ativo NC / Patrimônio Líquido",
      ok: ind.grau_imobilizacao != null && ind.grau_imobilizacao <= 60,
      atencao: ind.grau_imobilizacao != null && ind.grau_imobilizacao > 60 && ind.grau_imobilizacao <= 80,
    },
    {
      label: "Passivo / PL",
      value: ind.passivo_pl != null ? ind.passivo_pl.toFixed(2) : "—",
      sub: "Passivo Total / Patrimônio Líquido",
      ok: ind.passivo_pl != null && ind.passivo_pl <= 1,
      atencao: ind.passivo_pl != null && ind.passivo_pl > 1 && ind.passivo_pl <= 2,
    },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

      {/* ── ATIVO ── */}
      <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden flex flex-col">
        <div className="h-1 w-full rounded-t-2xl" style={{ background: "#1E4976" }} />
        <div className="px-5 pt-5 pb-4 border-b border-slate-100 dark:border-slate-700/60">
          <SectionTitle>Ativo — {balanco.periodo}</SectionTitle>

          {/* Circulante */}
          <p className="text-[10px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-1 mt-1">Circulante</p>
          <MetricaRow label="Caixa e Equivalentes" value={fmt(n(m.caixa_equivalentes))} />
          <MetricaRow label="Contas a Receber"      value={fmt(n(m.contas_receber))} />
          <MetricaRow label="Estoques"               value={fmt(n(m.estoques))} />
          <MetricaRow label="Outros Ativos Circ."    value={fmt(n(m.outros_ativo_circ))} />

          {/* Não Circulante */}
          <p className="text-[10px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-1 mt-4">Não Circulante</p>
          <MetricaRow label="Ativo Não Circulante" value={fmt(n(m.ativo_nao_circulante))} />

          <div className="mt-3">
            <div className="flex items-center justify-between py-1.5">
              <span className="text-xs font-black uppercase tracking-wider text-slate-700 dark:text-slate-200">ATIVO TOTAL</span>
              <p className="text-base font-black font-mono tabular-nums" style={{ color: "#1E4976" }}>
                {fmt(n(m.ativo_total))}
              </p>
            </div>
          </div>
        </div>

        {/* Gráfico de composição */}
        {dadosAtivo.length > 0 && (
          <div className="flex-1 px-5 py-4">
            <p className="text-[10px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-3">Composição do Ativo</p>
            <GraficoComNome>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={dadosAtivo}
                    dataKey="value"
                    nameKey="name"
                    cx="40%"
                    cy="50%"
                    outerRadius={60}
                    innerRadius={28}
                    paddingAngle={2}
                  >
                    {dadosAtivo.map((_, i) => (
                      <Cell key={i} fill={COLORS_ATIVO[i % COLORS_ATIVO.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={ct.tooltipStyle}
                    labelStyle={ct.tooltipLabelStyle}
                    itemStyle={ct.tooltipItemStyle}
                    formatter={(v) => fmt(v as number)}
                  />
                  <text x="40%" y="45%" textAnchor="middle" className="text-[9px] font-bold fill-slate-400">Ativo Total</text>
                  <text x="40%" y="58%" textAnchor="middle" className="text-sm font-black font-mono fill-slate-200">{fmt(n(m.ativo_total))}</text>
                </PieChart>
              </ResponsiveContainer>
            </GraficoComNome>
            {/* Legenda manual */}
            <div className="flex flex-col gap-1.5 mt-2">
              {dadosAtivo.map((item, i) => {
                const total = dadosAtivo.reduce((acc, d) => acc + d.value, 0);
                const pct = total > 0 ? ((item.value / total) * 100).toFixed(0) : "0";
                return (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: COLORS_ATIVO[i % COLORS_ATIVO.length] }} />
                      <span className="text-[#475569] dark:text-slate-400">{item.name}</span>
                    </div>
                    <span className="font-mono font-semibold text-[#0F172A] dark:text-slate-200 tabular-nums">{pct}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* ── DIREITA: Passivo + PL + Indicadores ── */}
      <div className="space-y-4">

        {/* Passivo */}
        <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">
          <div className="h-1 w-full" style={{ background: "#B83030" }} />
          <div className="p-5">
            <SectionTitle accent="#B83030">Passivo</SectionTitle>
            <p className="text-[10px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-1">Circulante</p>
            <MetricaRow label="Fornecedores"          value={fmt(n(m.fornecedores))} />
            <MetricaRow label="Empréstimos C/P"        value={fmt(n(m.emprestimos_cp))} />
            <MetricaRow label="Tributos a Pagar"       value={fmt(n(m.tributos_pagar))} />
            <MetricaRow label="Outros Passivos Circ."  value={fmt(n(m.outros_passivo_circ))} />
            <p className="text-[10px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-1 mt-4">Não Circulante</p>
            <MetricaRow label="Passivo Não Circulante" value={fmt(n(m.passivo_nao_circulante))} />
            <div className="mt-3">
              <div className="flex items-center justify-between py-1.5">
                <span className="text-xs font-black uppercase tracking-wider text-slate-700 dark:text-slate-200">PASSIVO TOTAL</span>
                <p className="text-base font-black font-mono tabular-nums" style={{ color: "#B83030" }}>
                  {fmt(n(m.passivo_total))}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Patrimônio Líquido */}
        <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">
          <div className="h-1 w-full" style={{ background: "#1A6B3C" }} />
          <div className="p-5">
            <SectionTitle accent="#1A6B3C">Patrimônio Líquido</SectionTitle>
            <MetricaRow label="Capital Social"     value={fmt(n(m.capital_social))} />
            <MetricaRow label="Reservas"            value={fmt(n(m.reservas))} />
            <MetricaRow label="Lucros Acumulados"   value={fmt(n(m.lucros_acumulados))} />
            <div className="mt-3">
              <div className="flex items-center justify-between py-1.5">
                <span className="text-xs font-black uppercase tracking-wider text-slate-700 dark:text-slate-200">PATRIMÔNIO LÍQUIDO</span>
                <p className="text-base font-black font-mono tabular-nums" style={{ color: "#1A6B3C" }}>
                  {fmt(n(m.patrimonio_liquido))}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Indicadores — cards com semântica visual */}
        <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-5">
          <SectionTitle>Indicadores de Estrutura</SectionTitle>
          <div className="grid grid-cols-3 gap-3">
            {indicadoresConfig.map(({ label, value, sub, ok, atencao }) => {
              const textColor = value === "—" ? "text-[#94A3B8] dark:text-slate-600"
                : ok ? "text-emerald-700 dark:text-emerald-400"
                : atencao ? "text-amber-700 dark:text-amber-400"
                : "text-rose-700 dark:text-rose-400";
              const borderColor = value === "—" ? "border-slate-200 dark:border-slate-700"
                : ok ? "border-emerald-200 dark:border-emerald-500/30"
                : atencao ? "border-amber-200 dark:border-amber-500/30"
                : "border-rose-200 dark:border-rose-500/30";
              const bgColor = value === "—" ? "bg-slate-50 dark:bg-slate-800/60"
                : ok ? "bg-emerald-50 dark:bg-emerald-500/8"
                : atencao ? "bg-amber-50 dark:bg-amber-500/8"
                : "bg-rose-50 dark:bg-rose-500/8";
              return (
                <div key={label} className={`rounded-xl border p-3 ${bgColor} ${borderColor}`}>
                  <p className="text-[9px] font-black text-[#94A3B8] dark:text-slate-500 uppercase tracking-wider leading-tight mb-1.5">{label}</p>
                  <p className={`text-lg font-black font-mono tabular-nums ${textColor}`}>{value}</p>
                  <p className="text-[9px] text-[#94A3B8] dark:text-slate-600 mt-1 leading-snug">{sub}</p>
                  {value !== "—" && (
                    <p className="text-[9px] font-bold uppercase mt-1" style={{ color: ok ? "#1A6B3C" : atencao ? "#92400E" : "#B83030" }}>
                      {ok ? "Saudável" : atencao ? "Atenção" : "Crítico"}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Equação Patrimonial */}
        {(n(m.ativo_total) > 0 || n(m.passivo_total) > 0 || n(m.patrimonio_liquido) > 0) && (() => {
          const passivoVal = n(m.passivo_total);
          const plVal = n(m.patrimonio_liquido);
          const sumPassivoPL = passivoVal + plVal || 1;
          const pPassivo = passivoVal;
          const pPassivoOfTotal = (passivoVal / sumPassivoPL) * 100;
          const pPLOfTotal = (plVal / sumPassivoPL) * 100;
          return (
            <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-5">
              <SectionTitle>Equação Patrimonial</SectionTitle>

              {/* Top row: ATIVO */}
              <div className="mb-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "#1E4976" }}>Ativo</span>
                  <span className="text-sm font-mono font-bold" style={{ color: "#1E4976" }}>{fmt(n(m.ativo_total))}</span>
                </div>
                <div className="h-6 rounded-lg overflow-hidden" style={{ background: "#1E4976" }}>
                  <div className="h-full flex items-center justify-center">
                    <span className="text-[10px] font-bold text-white/80">100%</span>
                  </div>
                </div>
              </div>

              {/* Bottom row: PASSIVO + PL stacked */}
              <div>
                <div className="flex items-center gap-4 mb-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "#B83030" }}>Passivo</span>
                    <span className="text-xs font-mono font-semibold" style={{ color: "#B83030" }}>{fmt(n(m.passivo_total))}</span>
                  </div>
                  <span className="text-slate-400">+</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "#1A6B3C" }}>PL</span>
                    <span className="text-xs font-mono font-semibold" style={{ color: "#1A6B3C" }}>{fmt(n(m.patrimonio_liquido))}</span>
                  </div>
                </div>
                <div className="flex h-6 rounded-lg overflow-hidden gap-px">
                  {pPassivo > 0 && (
                    <div style={{ width: `${pPassivoOfTotal}%`, background: "#B83030" }} className="flex items-center justify-center">
                      {pPassivoOfTotal > 15 && <span className="text-[9px] font-bold text-white/80">{pPassivoOfTotal.toFixed(0)}%</span>}
                    </div>
                  )}
                  {pPLOfTotal > 0 && (
                    <div style={{ width: `${pPLOfTotal}%`, background: "#1A6B3C" }} className="flex items-center justify-center">
                      {pPLOfTotal > 15 && <span className="text-[9px] font-bold text-white/80">{pPLOfTotal.toFixed(0)}%</span>}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })()}

        <InsightsList insights={balanco.insights?.filter((i) => ["R7","R8","R9","R10"].includes(i.codigo)) ?? []} />
      </div>
    </div>
  );
}
