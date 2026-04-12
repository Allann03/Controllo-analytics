"use client";

import GraficoComNome from "@/components/GraficoComNome";
import { useChartTheme } from "@/components/useChartTheme";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, ReferenceLine,
} from "recharts";

const fmt = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v);
const fmtPct = (v: number) => `${Number(v).toFixed(2)}%`;

const COLORS = ["#B83030", "#1E4976", "#1A6B3C"];

export default function AbaCarga({ dados }: { dados: Record<string, unknown> | null }) {
  const ct = useChartTheme();
  if (!dados) return (
    <div className="flex flex-col items-center gap-3 py-20 text-slate-600">
      <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z" />
      </svg>
      <p className="text-sm">Importe dados para calcular a carga tributária.</p>
    </div>
  );

  const kpis = dados.kpis as Record<string, number> ?? {};
  const hist = (dados.historico as Record<string, unknown>[]) ?? [];

  const pieData = [
    { name: "Impostos s/ Receita", value: Math.abs(kpis.deducoes_receita ?? 0) },
    { name: "IR + CSLL", value: Math.abs(kpis.ir_csll ?? 0) },
    { name: "Receita Líquida", value: Math.abs(kpis.receita_liquida ?? 0) },
  ].filter((d) => d.value > 0);

  const carga = kpis.carga_tributaria ?? 0;
  const cargaCor = carga <= 15 ? "#1A6B3C" : carga <= 25 ? "#92400E" : "#B83030";
  const cargaLabel = carga <= 15 ? "Saudável" : carga <= 25 ? "Atenção" : "Alta";
  const cargaBg = carga <= 15
    ? "bg-emerald-50 dark:bg-emerald-500/8 border-emerald-200 dark:border-emerald-500/20"
    : carga <= 25
    ? "bg-amber-50 dark:bg-amber-500/8 border-amber-200 dark:border-amber-500/20"
    : "bg-rose-50 dark:bg-rose-500/8 border-rose-200 dark:border-rose-500/20";

  // Variação vs mês anterior (se houver histórico)
  const histArr = (dados.historico as Record<string, unknown>[]) ?? [];
  const prevCarga = histArr.length >= 2 ? (histArr[histArr.length - 2] as Record<string, number>).carga_tributaria : null;
  const varCarga = prevCarga != null ? carga - prevCarga : null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-0 divide-y lg:divide-y-0 lg:divide-x divide-slate-200 dark:divide-slate-700/40">

      {/* KPIs tributários */}
      <div className="lg:col-span-1 space-y-0 p-6">
        {/* Carga total — destaque com semáforo */}
        <div className={`rounded-2xl p-4 mb-5 border ${cargaBg}`}>
          <div className="flex items-center justify-between mb-1">
            <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: cargaCor }}>
              Carga Tributária Total
            </p>
            <span className="text-[9px] font-bold px-2 py-0.5 rounded-full border" style={{ color: cargaCor, borderColor: `${cargaCor}40`, background: `${cargaCor}10` }}>
              {cargaLabel}
            </span>
          </div>
          <p className="text-4xl font-mono font-extrabold" style={{ color: cargaCor }}>
            {fmtPct(carga)}
          </p>
          <div className="flex items-center justify-between mt-2">
            <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>sobre receita bruta</p>
            {varCarga !== null && (
              <span className={`text-[11px] font-bold ${varCarga > 0 ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"}`}>
                {varCarga > 0 ? "▲" : "▼"} {Math.abs(varCarga).toFixed(1)}pp vs anterior
              </span>
            )}
          </div>
          {/* Benchmark bar with colored zones */}
          <div className="mt-3">
            <div className="flex h-5 rounded-lg overflow-hidden gap-px">
              <div className="flex items-center justify-center" style={{ width: "37.5%", background: "rgba(26,107,60,0.15)" }}>
                <span className="text-[8px] font-bold" style={{ color: "#1A6B3C" }}>≤15%</span>
              </div>
              <div className="flex items-center justify-center" style={{ width: "25%", background: "rgba(146,64,14,0.15)" }}>
                <span className="text-[8px] font-bold" style={{ color: "#92400E" }}>15-25%</span>
              </div>
              <div className="flex items-center justify-center" style={{ width: "37.5%", background: "rgba(184,48,48,0.15)" }}>
                <span className="text-[8px] font-bold" style={{ color: "#B83030" }}>&gt;25%</span>
              </div>
            </div>
            {/* Marker for current value */}
            <div className="relative h-0 mt-0.5">
              <div className="absolute" style={{ left: `${Math.min(100, (carga / 40) * 100)}%`, transform: "translateX(-50%)" }}>
                <div className="w-0 h-0 border-l-[4px] border-r-[4px] border-b-[6px] border-transparent border-b-slate-400" />
              </div>
            </div>
          </div>
        </div>

        {/* Breakdown tributário */}
        <div className="rounded-2xl p-4" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">Resumo Tributário</p>
          {[
            { label: "Receita Bruta", value: fmt(kpis.receita_bruta ?? 0) },
            { label: "Impostos s/ Receita", value: fmt(kpis.deducoes_receita ?? 0), neg: true },
            { label: "Receita Líquida", value: fmt(kpis.receita_liquida ?? 0), dest: true },
            { label: "IR + CSLL", value: fmt(kpis.ir_csll ?? 0), neg: true },
            { label: "Total de Tributos", value: fmt(kpis.total_tributos ?? 0), dest: true },
          ].map(({ label, value, neg, dest }) => (
            <div key={label} className={`flex justify-between py-2.5 ${dest ? "font-semibold" : ""}`}
              style={{ borderBottom: "1px solid rgba(79,106,255,0.07)" }}>
              <span className="text-sm" style={{ color: dest ? "var(--text-primary)" : "var(--text-secondary)" }}>{label}</span>
              <span className={`text-sm font-mono ${neg ? "text-red-400" : dest ? "text-slate-100" : ""}`}
                style={!neg && !dest ? { color: "var(--text-secondary)" } : {}}>{value}</span>
            </div>
          ))}
        </div>

        {/* Pie */}
        {pieData.length > 0 && (
          <GraficoComNome>
          <div className="rounded-2xl p-5" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">Composição da Receita</p>
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={60}>
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={ct.tooltipStyle} labelStyle={ct.tooltipLabelStyle} itemStyle={ct.tooltipItemStyle} formatter={(v) => fmt(v as number)} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          </GraficoComNome>
        )}
      </div>

      {/* Histórico tributário */}
      <div className="lg:col-span-2 p-6 space-y-5">
        {hist.length > 1 && (
          <>
            <GraficoComNome>
            <div className="rounded-2xl p-5" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">Evolução da Carga Tributária (%)</p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={hist.slice(-12)}>
                  <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} strokeOpacity={0.08} />
                  <XAxis dataKey="mes_label" tick={{ fill: ct.tickFill, fontSize: 11 }} />
                  <YAxis tick={{ fill: ct.tickFill, fontSize: 11 }} tickFormatter={(v) => `${v.toFixed(0)}%`} />
                  <Tooltip
                    contentStyle={ct.tooltipStyle}
                    formatter={(v) => `${(v as number).toFixed(1)}%`}
                    labelStyle={ct.tooltipLabelStyle}
                    itemStyle={ct.tooltipItemStyle}
                  />
                  <ReferenceLine y={15} stroke="#64748b" strokeDasharray="5 5" strokeWidth={1} label={{ value: "Ref: 15%", position: "right", fill: "#64748b", fontSize: 10 }} />
                  <Bar dataKey="carga_tributaria" name="Carga Tributária %" fill={ct.lineStroke} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            </GraficoComNome>

            <GraficoComNome>
            <div className="rounded-2xl p-5" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">Total de Tributos (R$)</p>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={hist.slice(-12)} barGap={3}>
                  <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} strokeOpacity={0.08} />
                  <XAxis dataKey="mes_label" tick={{ fill: ct.tickFill, fontSize: 11 }} />
                  <YAxis tick={{ fill: ct.tickFill, fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <Tooltip contentStyle={ct.tooltipStyle} formatter={(v) => fmt(v as number)} labelStyle={ct.tooltipLabelStyle} itemStyle={ct.tooltipItemStyle} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="deducoes_receita" name="Impostos s/ Receita" fill="#B83030" radius={[3, 3, 0, 0]} stackId="a" />
                  <Bar dataKey="ir_csll" name="IR + CSLL" fill="#3b6ea5" radius={[3, 3, 0, 0]} stackId="a" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            </GraficoComNome>
          </>
        )}
        {hist.length <= 1 && (
          <div className="flex flex-col items-center justify-center h-40 gap-3 rounded-2xl"
            style={{ border: "1px dashed rgba(239,68,68,0.2)", background: "rgba(239,68,68,0.02)" }}>
            <svg className="w-8 h-8 opacity-30" style={{ color: "#ef4444" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Dados históricos insuficientes para gráficos.</p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>Importe dados de pelo menos 2 períodos para visualizar a evolução.</p>
          </div>
        )}

        {/* Alertas tributários */}
        <div className="rounded-2xl p-5" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-bold uppercase tracking-widest mb-3" style={{ color: "var(--text-muted)" }}>Alertas Tributários</p>
          <div className="space-y-2">
            {(() => {
              const alertas: { tipo: "ok" | "atencao" | "risco"; msg: string }[] = [];
              if (carga <= 15) alertas.push({ tipo: "ok", msg: `Carga tributária saudável (${fmtPct(carga)}) — abaixo de 15%` });
              else if (carga <= 25) alertas.push({ tipo: "atencao", msg: `Carga tributária na faixa de atenção (${fmtPct(carga)}) — entre 15% e 25%` });
              else alertas.push({ tipo: "risco", msg: `Carga tributária elevada (${fmtPct(carga)}) — acima de 25%. Considere revisar o regime tributário.` });

              if (varCarga !== null && varCarga > 1) alertas.push({ tipo: "atencao", msg: `Carga subiu ${varCarga.toFixed(1)}pp vs mês anterior — verifique se há tributo duplicado.` });
              if (varCarga !== null && varCarga < -2) alertas.push({ tipo: "ok", msg: `Carga reduziu ${Math.abs(varCarga).toFixed(1)}pp vs mês anterior.` });

              const totalTrib = kpis.total_tributos ?? 0;
              const recBruta = kpis.receita_bruta ?? 0;
              if (recBruta > 0 && totalTrib > 0) {
                alertas.push({ tipo: "ok", msg: `Total de tributos no período: ${fmt(totalTrib)} (${fmtPct((totalTrib / recBruta) * 100)} da receita)` });
              }

              return alertas.map((a, i) => (
                <div key={i} className={`flex items-start gap-2 px-3 py-2 rounded-lg border text-xs ${
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
        </div>
      </div>
    </div>
  );
}
