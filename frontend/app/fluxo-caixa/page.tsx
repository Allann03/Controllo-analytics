"use client";
import { useEffect, useState, useCallback } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";
import GraficoComNome from "@/components/GraficoComNome";
import { useChartTheme } from "@/components/useChartTheme";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

interface Alerta { tipo: string; mensagem: string; }
interface HistoricoItem { mes: string; entradas: number; saidas: number; saldo: number; }
interface ProjecaoItem { mes_offset: number; saldo_projetado: number; }
interface FluxoData {
  historico: HistoricoItem[];
  projecoes: ProjecaoItem[];
  saldo_atual: number;
  saldo_proj_3m: number;
  media_entradas: number;
  media_saidas: number;
  alertas: Alerta[];
  sem_dados?: boolean;
}

function formatBRL(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatK(v: number) {
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(0)}k`;
  return String(v);
}

const DEMO_FLUXO: FluxoData = {
  historico: [
    { mes: "Jan/24", entradas: 115000, saidas: 90000,  saldo: 25000 },
    { mes: "Fev/24", entradas: 110000, saidas: 88000,  saldo: 22000 },
    { mes: "Mar/24", entradas: 125000, saidas: 95000,  saldo: 30000 },
    { mes: "Abr/24", entradas: 140000, saidas: 100000, saldo: 40000 },
    { mes: "Mai/24", entradas: 155000, saidas: 108000, saldo: 47000 },
    { mes: "Jun/24", entradas: 170000, saidas: 115000, saldo: 55000 },
    { mes: "Jul/24", entradas: 175000, saidas: 118000, saldo: 57000 },
    { mes: "Ago/24", entradas: 185000, saidas: 125000, saldo: 60000 },
    { mes: "Set/24", entradas: 180000, saidas: 122000, saldo: 58000 },
    { mes: "Out/24", entradas: 195000, saidas: 130000, saldo: 65000 },
    { mes: "Nov/24", entradas: 205000, saidas: 135000, saldo: 70000 },
    { mes: "Dez/24", entradas: 245000, saidas: 155000, saldo: 90000 },
  ],
  projecoes: [
    { mes_offset: 1, saldo_projetado: 68000 },
    { mes_offset: 2, saldo_projetado: 72000 },
    { mes_offset: 3, saldo_projetado: 76000 },
  ],
  saldo_atual: 90000,
  saldo_proj_3m: 76000,
  media_entradas: 158750,
  media_saidas: 115083,
  alertas: [],
};

function CustomTooltip({ active, payload, label, ct }: { active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string; ct?: ReturnType<typeof useChartTheme> }) {
  if (!active || !payload?.length) return null;
  const isLight = ct?.isLight ?? true;
  return (
    <div style={{ background: isLight ? "#FFFFFF" : "#1e293b", border: `1px solid ${isLight ? "#E2E8F0" : "#475569"}`, borderRadius: 8, padding: "10px 14px", boxShadow: isLight ? "0 4px 12px rgba(0,0,0,0.08)" : "0 4px 16px rgba(0,0,0,0.3)", minWidth: 160 }}>
      <p style={{ color: isLight ? "#64748b" : "#94a3b8", fontWeight: 500, marginBottom: 6, fontSize: 11 }}>{label}</p>
      {payload.map((p) =>
        p.value != null ? (
          <div key={p.name} style={{ display: "flex", justifyContent: "space-between", gap: 24, marginBottom: 3, alignItems: "center" }}>
            <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: isLight ? "#475569" : "#e2e8f0" }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: p.color, flexShrink: 0 }} />
              {p.name}
            </span>
            <span style={{ color: isLight ? "#0F172A" : "#f1f5f9", fontFamily: "monospace", fontWeight: 600, fontSize: 13 }}>{formatBRL(Number(p.value))}</span>
          </div>
        ) : null
      )}
    </div>
  );
}

function SkeletonFluxo() {
  return (
    <div className="space-y-6 page-enter">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="card-premium p-5 space-y-3">
            <div className="skeleton h-3 w-24 rounded" />
            <div className="skeleton h-7 w-32 rounded" />
            <div className="skeleton h-3 w-16 rounded" />
          </div>
        ))}
      </div>
      <div className="card-premium p-5">
        <div className="skeleton h-4 w-48 rounded mb-5" />
        <div className="skeleton h-72 w-full rounded-xl" />
      </div>
      <div className="card-premium overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-700/60">
          <div className="skeleton h-3 w-36 rounded" />
        </div>
        {[...Array(3)].map((_, i) => (
          <div key={i} className="px-5 py-4 flex justify-between border-b border-slate-700/30 last:border-0">
            <div className="space-y-2">
              <div className="skeleton h-4 w-28 rounded" />
              <div className="skeleton h-3 w-40 rounded" />
            </div>
            <div className="skeleton h-7 w-32 rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function FluxoCaixaPage() {
  const ct = useChartTheme();
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const [dados, setDados] = useState<FluxoData | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const h = () => ({ Authorization: `Bearer ${localStorage.getItem("controllo_token") || ""}` });

  const carregar = useCallback(async (signal?: AbortSignal) => {
    if (!empresaId) { setCarregando(false); return; }
    setCarregando(true); setErro(null); setDados(null);
    try {
      const r = await fetch(`${API}/api/financeiro/fluxo-caixa/${empresaId}`, { headers: h(), signal });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Erro ao carregar.");
      setDados(d);
    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") return;
      setErro((e as Error).message);
    }
    finally { setCarregando(false); }
  }, [empresaId]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60_000);
    carregar(controller.signal);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [carregar]);

  const isDemo = !empresaId || dados?.sem_dados || (!dados && !carregando);
  const dadosVisiveis = (dados && !dados.sem_dados) ? dados : (isDemo ? DEMO_FLUXO : null);

  const dadosGrafico = dadosVisiveis ? [
    ...dadosVisiveis.historico.map(h => ({
      periodo: h.mes,
      entradas: h.entradas,
      saidas: h.saidas,
      saldo: h.saldo,
      projecao: undefined,
    })),
    ...dadosVisiveis.projecoes.map((p) => ({
      periodo: `+${p.mes_offset}m`,
      entradas: undefined,
      saidas: undefined,
      saldo: undefined,
      projecao: p.saldo_projetado,
    })),
  ] : [];

  const kpis = dadosVisiveis ? [
    {
      label: "Saldo Atual",
      val: dadosVisiveis.saldo_atual,
      color: dadosVisiveis.saldo_atual >= 0 ? "text-emerald-400" : "text-rose-400",
      accent: dadosVisiveis.saldo_atual >= 0 ? "kpi-emerald" : "kpi-rose",
      sub: "Posição atual em caixa",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
        </svg>
      ),
    },
    {
      label: "Projeção 3 meses",
      val: dadosVisiveis.saldo_proj_3m,
      color: dadosVisiveis.saldo_proj_3m >= 0 ? "text-blue-400" : "text-rose-400",
      accent: dadosVisiveis.saldo_proj_3m >= 0 ? "kpi-blue" : "kpi-rose",
      sub: "Saldo estimado em 90 dias",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
    },
    {
      label: "Média Entradas",
      val: dadosVisiveis.media_entradas,
      color: "text-emerald-400",
      accent: "kpi-emerald",
      sub: "Por mês no período",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 11l5-5m0 0l5 5m-5-5v12" />
        </svg>
      ),
    },
    {
      label: "Média Saídas",
      val: dadosVisiveis.media_saidas,
      color: "text-rose-400",
      accent: "kpi-rose",
      sub: "Por mês no período",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 13l-5 5m0 0l-5-5m5 5V6" />
        </svg>
      ),
    },
  ] : [];

  return (
    <div className="min-h-full" style={{ background: "var(--bg-canvas)", color: "var(--text-primary)" }}>

      {/* HEADER */}
      <header className="page-header px-8 pt-8 pb-6 border-b border-slate-200 dark:border-slate-700">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-200 dark:bg-emerald-500/10 dark:border-emerald-500/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight">Fluxo de <span className="text-emerald-700 dark:text-emerald-400">Caixa</span></h1>
              <p className="text-slate-500 text-sm">Histórico de entradas e saídas + projeção dos próximos 3 meses</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isDemo && !carregando && (
              <span className="badge badge-amber">Demo</span>
            )}
            {!isDemo && (
              <span className="badge badge-emerald">Ao vivo</span>
            )}
          </div>
        </div>
      </header>

      <div className="px-8 py-8 space-y-6">

        {/* Demo banner */}
        {isDemo && !carregando && (
          <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30 rounded-xl text-amber-700 dark:text-amber-300 text-sm">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span><strong>Dados de Demonstração</strong> — Selecione uma empresa para visualizar seus dados reais.</span>
          </div>
        )}

        {/* Alertas críticos */}
        {dadosVisiveis && !carregando && dadosVisiveis.alertas.length > 0 && (
          <div className="space-y-3">
            {dadosVisiveis.alertas.map((a, i) => (
              <div key={i} className={`flex items-start gap-3 p-4 rounded-xl border ${
                a.tipo === "critico"
                  ? "bg-rose-500/5 border-rose-500/20"
                  : "bg-amber-500/5 border-amber-500/20"
              }`}>
                <span className={`w-2 h-2 mt-1.5 rounded-full flex-shrink-0 ${a.tipo === "critico" ? "bg-rose-500" : "bg-amber-400"}`} />
                <p className="text-sm text-slate-700 dark:text-slate-300">{a.mensagem}</p>
              </div>
            ))}
          </div>
        )}

        {/* Erro */}
        {erro && (
          <div className="p-4 bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 rounded-xl text-rose-600 dark:text-rose-300 text-sm flex items-center gap-3">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            {erro}
          </div>
        )}

        {/* Skeleton loading */}
        {carregando && <SkeletonFluxo />}

        {/* Conteúdo principal */}
        {dadosVisiveis && !carregando && (
          <div className="space-y-6 page-enter">

            {/* KPIs */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {kpis.map(k => (
                <div key={k.label} className={`card-premium ${k.accent} p-5`}>
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{k.label}</p>
                    <div className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-slate-700/60 flex items-center justify-center text-slate-500 dark:text-slate-400">
                      {k.icon}
                    </div>
                  </div>
                  <p className={`text-xl font-black font-mono ${k.color}`}>{formatBRL(k.val)}</p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-600 mt-1">{k.sub}</p>
                </div>
              ))}
            </div>

            {/* Gráfico principal */}
            <GraficoComNome>
              <div className="chart-container">
                <div className="chart-header">
                  <div>
                    <p className="section-title">Evolução do Caixa</p>
                    <p className="text-xs text-slate-600 mt-0.5">Histórico + projeção (tracejado)</p>
                  </div>
                  <div className="flex flex-wrap gap-4">
                    {[
                      { cor: "#10b981", label: "Entradas" },
                      { cor: "#f43f5e", label: "Saídas" },
                      { cor: "#3b82f6", label: "Saldo" },
                      { cor: "#3b82f6", label: "Projeção", dashed: true },
                    ].map(l => (
                      <span key={l.label} className="flex items-center gap-1.5 text-[11px] text-slate-500">
                        {l.dashed ? (
                          <span className="block w-5 h-[2px] border-t-2 border-dashed" style={{ borderColor: l.cor }} />
                        ) : (
                          <span className="block w-5 h-[2px]" style={{ background: l.cor }} />
                        )}
                        {l.label}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={dadosGrafico} margin={{ left: -10, right: 8, top: 4, bottom: 0 }}>
                      <defs>
                        <linearGradient id="gEnt" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="gSai" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.2} />
                          <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="gSaldo" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} vertical={false} />
                      <XAxis dataKey="periodo" tick={{ fill: ct.tickFill, fontSize: 9 }} tickLine={false} axisLine={false} />
                      <YAxis tick={{ fill: ct.tickFill, fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={formatK} />
                      <Tooltip content={<CustomTooltip ct={ct} />} />
                      <ReferenceLine y={0} stroke={ct.gridStroke} strokeDasharray="4 4" />
                      <Area type="monotone" dataKey="entradas" stroke="#10b981" fill="url(#gEnt)" strokeWidth={2} name="Entradas" connectNulls={false} dot={false} activeDot={{ r: 4, fill: "#10b981" }} />
                      <Area type="monotone" dataKey="saidas"   stroke="#f43f5e" fill="url(#gSai)" strokeWidth={2} name="Saídas"   connectNulls={false} dot={false} activeDot={{ r: 4, fill: "#f43f5e" }} />
                      <Area type="monotone" dataKey="saldo"    stroke="#3b82f6" fill="url(#gSaldo)" strokeWidth={2.5} name="Saldo"   connectNulls={false} dot={false} activeDot={{ r: 4, fill: "#a855f7" }} />
                      <Area type="monotone" dataKey="projecao" stroke="#3b82f6" fill="none" strokeWidth={2} strokeDasharray="6 3" name="Projeção" connectNulls={false} dot={false} activeDot={{ r: 4, fill: "#a855f7" }} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </GraficoComNome>

            {/* Projeções de saldo */}
            <div className="card-premium overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700/60 flex items-center gap-3">
                <div className="w-7 h-7 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                  <svg className="w-3.5 h-3.5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <p className="section-title">Projeção de Saldo</p>
                  <p className="text-xs text-slate-600">Estimativa baseada na média dos últimos 6 meses</p>
                </div>
              </div>
              <div className="divide-y divide-slate-100 dark:divide-slate-700/30">
                {dadosVisiveis.projecoes.map((p, i) => {
                  const pct = dadosVisiveis.saldo_atual > 0
                    ? Math.round((p.saldo_projetado / dadosVisiveis.saldo_atual) * 100)
                    : 0;
                  const positivo = p.saldo_projetado >= 0;
                  return (
                    <div key={i} className="px-6 py-4 flex items-center justify-between hover:bg-slate-700/10 transition-colors">
                      <div className="flex items-center gap-4">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-black text-sm ${
                          positivo ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"
                        }`}>
                          +{p.mes_offset}m
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-slate-800 dark:text-white">Em {p.mes_offset} {p.mes_offset === 1 ? "mês" : "meses"}</p>
                          <p className="text-xs text-slate-500">
                            {pct > 0 ? `${pct}% do saldo atual` : "Abaixo do saldo atual"}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={`text-lg font-black font-mono ${positivo ? "text-emerald-400" : "text-rose-400"}`}>
                          {formatBRL(p.saldo_projetado)}
                        </p>
                        {!positivo && (
                          <p className="text-[10px] text-rose-400 font-semibold mt-0.5">Risco de caixa negativo</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Tabela histórico */}
            {dadosVisiveis.historico.length > 0 && (
              <div className="card-premium overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700/60 flex items-center gap-3">
                  <div className="w-7 h-7 rounded-lg bg-slate-700/60 flex items-center justify-center">
                    <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div>
                    <p className="section-title">Histórico Detalhado</p>
                    <p className="text-xs text-slate-600">{dadosVisiveis.historico.length} períodos disponíveis</p>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="table-premium w-full text-sm">
                    <thead>
                      <tr>
                        <th className="text-left px-6 py-3">Período</th>
                        <th className="text-right px-6 py-3" style={{ color: "#10b981" }}>Entradas</th>
                        <th className="text-right px-6 py-3" style={{ color: "#f43f5e" }}>Saídas</th>
                        <th className="text-right px-6 py-3" style={{ color: "#3b82f6" }}>Saldo</th>
                        <th className="text-right px-6 py-3">Margem</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dadosVisiveis.historico.map((item, i) => {
                        const margem = item.entradas > 0 ? ((item.saldo / item.entradas) * 100).toFixed(1) : "0.0";
                        return (
                          <tr key={i}>
                            <td className="px-6 py-3 text-slate-700 dark:text-slate-300 font-semibold">{item.mes}</td>
                            <td className="px-6 py-3 text-right font-mono text-emerald-600 dark:text-emerald-400 text-xs">{formatBRL(item.entradas)}</td>
                            <td className="px-6 py-3 text-right font-mono text-rose-600 dark:text-rose-400 text-xs">{formatBRL(item.saidas)}</td>
                            <td className={`px-6 py-3 text-right font-mono text-xs font-semibold ${item.saldo >= 0 ? "text-blue-600 dark:text-blue-400" : "text-rose-600 dark:text-rose-400"}`}>
                              {formatBRL(item.saldo)}
                            </td>
                            <td className={`px-6 py-3 text-right text-xs font-semibold ${Number(margem) >= 20 ? "text-emerald-400" : Number(margem) >= 10 ? "text-amber-400" : "text-rose-400"}`}>
                              {margem}%
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
