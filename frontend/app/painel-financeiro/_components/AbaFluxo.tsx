"use client";

import GraficoComNome from "@/components/GraficoComNome";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { useChartTheme } from "@/components/useChartTheme";
import { fmt, SectionTitle } from "./shared";
import type { FluxoResponse } from "./shared";

export default function AbaFluxo({ fluxo }: { fluxo: FluxoResponse }) {
  const ct = useChartTheme();
  const hist = fluxo.historico ?? [];
  const saldoAtual = fluxo.saldo_atual ?? 0;
  const proj3m = fluxo.saldo_proj_3m ?? 0;
  const projTrend = proj3m >= saldoAtual;
  const currentMonth = new Date().toLocaleString("pt-BR", { month: "short" }).replace(".", "");

  return (
    <div className="space-y-6">
      {/* Cards de resumo — 4 cards responsivos */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-4">
          <div className="flex items-center justify-between mb-2">
            <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M7 11l5-5m0 0l5 5m-5-5v12" />
            </svg>
            <p className="text-[10px] font-bold text-emerald-600 dark:text-emerald-500 uppercase tracking-wider">Méd. Entradas</p>
          </div>
          <p className="text-lg font-mono font-bold text-emerald-600 dark:text-emerald-400">{fmt(fluxo.media_entradas ?? 0)}</p>
        </div>
        <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-4">
          <div className="flex items-center justify-between mb-2">
            <svg className="w-5 h-5 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 13l-5 5m0 0l-5-5m5 5V6" />
            </svg>
            <p className="text-[10px] font-bold text-rose-600 dark:text-red-400 uppercase tracking-wider">Méd. Saídas</p>
          </div>
          <p className="text-lg font-mono font-bold text-rose-600 dark:text-red-400">{fmt(fluxo.media_saidas ?? 0)}</p>
        </div>
        <div className={`border rounded-2xl p-4 ${saldoAtual >= 0 ? "bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-500/20" : "bg-rose-50 dark:bg-red-950/20 border-rose-200 dark:border-red-500/20"}`}>
          <div className="flex items-center justify-between mb-2">
            <svg className="w-5 h-5" style={{ color: saldoAtual >= 0 ? "#3b6ea5" : "#ef4444" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
            <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Saldo Atual</p>
          </div>
          <p className={`text-lg font-mono font-bold ${saldoAtual >= 0 ? "text-blue-700 dark:text-blue-400" : "text-rose-600 dark:text-red-400"}`}>{fmt(saldoAtual)}</p>
        </div>
        <div className={`border rounded-2xl p-4 ${proj3m >= 0 ? "bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-500/20" : "bg-rose-50 dark:bg-red-950/20 border-rose-200 dark:border-red-500/20"}`}>
          <div className="flex items-center justify-between mb-2">
            <svg className="w-5 h-5" style={{ color: proj3m >= 0 ? "#10b981" : "#ef4444" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Projeção 3M</p>
          </div>
          <p className={`text-lg font-mono font-bold ${proj3m >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-red-400"}`}>
            {projTrend ? "▲ " : "▼ "}{fmt(proj3m)}
          </p>
        </div>
      </div>

      {/* Alertas */}
      {fluxo.alertas?.length > 0 && (
        <div className="space-y-2">
          {fluxo.alertas.map((a, i) => (
            <div key={i} className={`px-4 py-3 rounded-xl border text-sm ${
              a.tipo === "critico" ? "border-red-200 dark:border-red-500/20 bg-red-50 dark:bg-red-950/20 text-red-700 dark:text-red-300"
              : "border-amber-200 dark:border-amber-500/20 bg-amber-50 dark:bg-amber-950/20 text-amber-800 dark:text-amber-300"
            }`}>{a.mensagem}</div>
          ))}
        </div>
      )}

      {/* Gráfico — saldo azul em vez de roxo */}
      {hist.length > 0 && (
        <GraficoComNome>
        <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-5">
          <SectionTitle>Entradas × Saídas × Saldo</SectionTitle>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={hist} barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} strokeOpacity={0.08} />
              <XAxis dataKey="mes" tick={{ fill: ct.tickFill, fontSize: 11 }} />
              <YAxis tick={{ fill: ct.tickFill, fontSize: 11 }} tickFormatter={(v) => `${((v as number) / 1000).toFixed(0)}k`} />
              <Tooltip contentStyle={ct.tooltipStyle} labelStyle={ct.tooltipLabelStyle} itemStyle={ct.tooltipItemStyle} formatter={(v) => fmt(v as number)} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="entradas" name="Entradas" fill="#10b981" radius={[3, 3, 0, 0]} />
              <Bar dataKey="saidas" name="Saídas" fill="#ef4444" radius={[3, 3, 0, 0]} />
              <Bar dataKey="saldo" name="Saldo" fill="#3b6ea5" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        </GraficoComNome>
      )}

      {/* Tabela detalhada */}
      {hist.length > 0 && (
        <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">
          <div className="px-5 pt-4 pb-2">
            <SectionTitle>Detalhamento Mensal</SectionTitle>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <th className="text-left px-5 py-2 text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Mês</th>
                <th className="text-right px-4 py-2 text-[10px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-500">Entradas</th>
                <th className="text-right px-4 py-2 text-[10px] font-bold uppercase tracking-wider text-rose-600 dark:text-red-400">Saídas</th>
                <th className="text-right px-4 py-2 text-[10px] font-bold uppercase tracking-wider" style={{ color: "#3b6ea5" }}>Saldo</th>
                <th className="text-right px-5 py-2 text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Var. %</th>
                <th className="text-center px-3 py-2 text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Tend.</th>
              </tr>
            </thead>
            <tbody>
              {hist.map((h, i) => {
                const prev = i > 0 ? hist[i - 1].saldo : null;
                const varPct = prev && prev !== 0 ? ((h.saldo - prev) / Math.abs(prev)) * 100 : null;
                const isCurrentMonth = h.mes.toLowerCase().startsWith(currentMonth.toLowerCase());
                return (
                  <tr key={i} className={isCurrentMonth ? "bg-blue-50/50 dark:bg-blue-500/5" : ""} style={{ borderTop: i > 0 ? "1px solid var(--border)" : undefined }}>
                    <td className="px-5 py-2 font-medium" style={{ color: "var(--text-primary)" }}>{h.mes}</td>
                    <td className="px-4 py-2 text-right font-mono text-emerald-600 dark:text-emerald-400">{fmt(h.entradas)}</td>
                    <td className="px-4 py-2 text-right font-mono text-rose-600 dark:text-red-400">{fmt(h.saidas)}</td>
                    <td className="px-4 py-2 text-right font-mono font-semibold" style={{ color: "#3b6ea5" }}>{fmt(h.saldo)}</td>
                    <td className={`px-5 py-2 text-right font-mono ${varPct !== null && varPct > 0 ? "text-emerald-600 dark:text-emerald-400" : varPct !== null && varPct < 0 ? "text-rose-600 dark:text-red-400" : ""}`} style={{ color: varPct === null ? "var(--text-muted)" : undefined }}>
                      {varPct !== null ? `${varPct > 0 ? "+" : ""}${varPct.toFixed(1)}%` : "—"}
                      {varPct !== null && Math.abs(varPct) > 20 && (
                        <span className="ml-1 text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20">!</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-center">
                      {varPct !== null ? (
                        <span className={`text-sm ${varPct > 0 ? "text-emerald-500" : "text-rose-500"}`}>
                          {varPct > 0 ? "▲" : "▼"}
                        </span>
                      ) : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
