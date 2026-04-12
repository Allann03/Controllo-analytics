"use client";
import { useEffect, useState, useCallback } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";
import GraficoComNome from "@/components/GraficoComNome";
import { useChartTheme } from "@/components/useChartTheme";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");
const MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
const ANO_ATUAL = new Date().getFullYear();

interface InsightItem { id: string; categoria: string; severidade: string; titulo: string; mensagem: string; valor_atual?: number; valor_referencia?: number; }
interface DREItem { linha: string; valor: number; tipo: string; variacao_pct?: number | null; }
interface NarrativaData {
  resumo_executivo?: string;
  analise_receita?: string;
  analise_despesas?: string;
  analise_margens?: string;
  analise_caixa?: string;
  analise_endividamento?: string;
  conclusao?: string;
  alertas?: string[];
}
interface DREData { periodo: string; cascata: DREItem[]; insights: InsightItem[]; metricas: Record<string, number>; sem_dados?: boolean; narrativa?: NarrativaData; }

function formatBRL(v: number) {
  return Math.abs(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: { value: number; payload: { tipo: string } }[]; label?: string }) => {
  const ct = useChartTheme();
  if (!active || !payload?.length) return null;
  const tipo = payload[0]?.payload?.tipo;
  const cor = colorMap[tipo] || "#64748b";
  return (
    <div style={{ ...ct.tooltipStyle, minWidth: 160 }}>
      <p style={{ ...ct.tooltipLabelStyle, marginBottom: 6 }}>{label}</p>
      <p style={{ color: cor, fontFamily: "monospace", fontSize: 13, fontWeight: 600 }}>{formatBRL(payload[0]?.value ?? 0)}</p>
    </div>
  );
};

const colorMap: Record<string, string> = {
  positivo:       "#10b981",
  negativo:       "#f43f5e",
  resultado:      "#3b82f6",
  resultado_final:"#0F2D4A",
};

const DEMO_DRE: DREData = {
  periodo: "Demonstração",
  sem_dados: false,
  cascata: [
    { linha: "Receita Bruta",           valor: 200000, tipo: "positivo" },
    { linha: "(-) Deduções",            valor: -18000, tipo: "negativo" },
    { linha: "(=) Receita Líquida",     valor: 182000, tipo: "resultado" },
    { linha: "(-) Custo dos Serviços",  valor: -72000, tipo: "negativo" },
    { linha: "(=) Lucro Bruto",         valor: 110000, tipo: "resultado" },
    { linha: "(-) Despesas Adm.",       valor: -24000, tipo: "negativo" },
    { linha: "(-) Despesas Comerciais", valor: -18000, tipo: "negativo" },
    { linha: "(-) Despesas Financeiras",valor: -8000,  tipo: "negativo" },
    { linha: "(=) EBIT",                valor: 60000,  tipo: "resultado" },
    { linha: "(-) IR/CSLL",             valor: -9000,  tipo: "negativo" },
    { linha: "= Lucro Líquido",         valor: 51000,  tipo: "resultado_final" },
  ],
  insights: [
    { id: "1", categoria: "margem", severidade: "info", titulo: "Margem líquida de 25,5%", mensagem: "Resultado saudável. A margem líquida está acima da média setorial.", valor_atual: 25.5, valor_referencia: 15 },
  ],
  metricas: { margem_bruta: 55, margem_liquida: 25.5, ebitda: 68000, receita_bruta: 200000, lucro_liquido: 51000 },
};

function SkeletonDRE() {
  return (
    <div className="space-y-6 page-enter">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="card-premium p-4 space-y-3">
            <div className="skeleton h-3 w-20 rounded" />
            <div className="skeleton h-7 w-32 rounded" />
            <div className="skeleton h-2 w-16 rounded" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card-premium p-5"><div className="skeleton h-72 rounded-xl" /></div>
        <div className="card-premium p-5"><div className="skeleton h-72 rounded-xl" /></div>
      </div>
    </div>
  );
}

export default function DrePage() {
  const ct = useChartTheme();
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const [ano, setAno] = useState(ANO_ATUAL);
  const [mes, setMes] = useState(new Date().getMonth() + 1);
  const [dados, setDados] = useState<DREData | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const h = () => ({ Authorization: `Bearer ${localStorage.getItem("controllo_token") || ""}` });

  const carregar = useCallback(async (signal?: AbortSignal) => {
    if (!empresaId) { setCarregando(false); return; }
    setCarregando(true); setErro(null); setDados(null);
    try {
      const r = await fetch(`${API}/api/financeiro/dre/${empresaId}?ano=${ano}&mes=${mes}`, { headers: h(), signal });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Erro ao carregar.");
      setDados(d);
    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") return;
      setErro(e instanceof Error ? e.message : "Erro desconhecido.");
    }
    finally { setCarregando(false); }
  }, [empresaId, ano, mes]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60_000);
    carregar(controller.signal);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [carregar]);

  const isDemo = !empresaId || dados?.sem_dados || (!dados && !carregando);
  const dadosVisiveis = (dados && !dados.sem_dados) ? dados : (isDemo ? DEMO_DRE : null);

  const chartData = dadosVisiveis?.cascata.map(item => ({
    nome: item.linha.replace("(-) ", "").replace("(=) ","").replace("= ",""),
    valor: item.valor,
    abs: Math.abs(item.valor),
    tipo: item.tipo,
  })) ?? [];

  const kpis = dadosVisiveis ? [
    {
      label: "Receita Bruta",
      val: dadosVisiveis.metricas.receita_bruta ?? 0,
      color: "text-emerald-400",
      bg: "bg-emerald-500/5",
      border: "kpi-emerald",
      icon: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
      sub: "Total faturado no período",
    },
    {
      label: "Receita Líquida",
      val: dadosVisiveis.metricas.receita_liquida ?? 0,
      color: "text-blue-400",
      bg: "bg-blue-500/5",
      border: "kpi-blue",
      icon: "M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5",
      sub: "Após deduções fiscais",
    },
    {
      label: "Lucro Líquido",
      val: dadosVisiveis.metricas.lucro_liquido ?? 0,
      color: (dadosVisiveis.metricas.lucro_liquido ?? 0) >= 0 ? "text-blue-600 dark:text-blue-400" : "text-rose-400",
      bg: (dadosVisiveis.metricas.lucro_liquido ?? 0) >= 0 ? "bg-blue-500/5" : "bg-rose-500/5",
      border: (dadosVisiveis.metricas.lucro_liquido ?? 0) >= 0 ? "kpi-blue" : "kpi-rose",
      icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
      sub: "Resultado final do período",
    },
    {
      label: "Margem Líquida",
      val: dadosVisiveis.metricas.margem_liquida ?? 0,
      color: (dadosVisiveis.metricas.margem_liquida ?? 0) >= 10 ? "text-emerald-400" : "text-amber-400",
      bg: (dadosVisiveis.metricas.margem_liquida ?? 0) >= 10 ? "bg-emerald-500/5" : "bg-amber-500/5",
      border: (dadosVisiveis.metricas.margem_liquida ?? 0) >= 10 ? "kpi-emerald" : "kpi-amber",
      icon: "M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z",
      sub: `Referência setorial: ~15%`,
      pct: true,
    },
  ] : [];

  return (
    <div className="min-h-full page-enter" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>

      {/* ── HEADER ── */}
      <header className="page-header">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 mb-3">
              <span className="badge badge-indigo">Análise Financeira</span>
              {isDemo && <span className="badge badge-amber">Demonstração</span>}
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight" style={{ color: "var(--text-primary)" }}>
              DRE{" "}
              <span className="text-navy-600 dark:text-navy-400">Visual</span>
            </h1>
            <p className="text-sm mt-1.5" style={{ color: "var(--text-muted)" }}>
              Demonstração do Resultado do Exercício com insights automáticos
            </p>
          </div>

          {/* Filtros inline no header */}
          <div className="flex items-end gap-3 flex-wrap">
            <div className="flex flex-col gap-1">
              <label className="section-title">Mês</label>
              <select
                value={mes}
                onChange={e => setMes(Number(e.target.value))}
                className="px-3 py-2 rounded-xl text-sm outline-none transition-all"
                style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", color: "var(--text-primary)", minWidth: 80 }}
                onFocus={e => { e.currentTarget.style.borderColor = "#3b6ea5"; }}
                onBlur={e => { e.currentTarget.style.borderColor = "var(--border)"; }}
              >
                {MESES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="section-title">Ano</label>
              <input
                type="number"
                value={ano}
                onChange={e => setAno(Number(e.target.value))}
                className="w-24 px-3 py-2 rounded-xl text-sm outline-none transition-all"
                style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                onFocus={e => { e.currentTarget.style.borderColor = "#3b6ea5"; }}
                onBlur={e => { e.currentTarget.style.borderColor = "var(--border)"; }}
              />
            </div>
          </div>
        </div>
      </header>

      <div className="p-6 space-y-6">

        {/* Empresa não selecionada */}
        {!empresaId && (
          <div className="flex flex-col items-center justify-center py-24 text-center card-premium">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5" style={{ background: "rgba(79,106,255,0.08)", border: "1px solid rgba(79,106,255,0.15)" }}>
              <svg className="w-8 h-8 opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="12" width="4" height="9" rx="1" />
                <rect x="10" y="7" width="4" height="14" rx="1" />
                <rect x="17" y="3" width="4" height="18" rx="1" />
              </svg>
            </div>
            <p className="text-base font-semibold" style={{ color: "var(--text-secondary)" }}>Selecione uma empresa para visualizar a DRE</p>
            <p className="text-sm mt-1.5" style={{ color: "var(--text-muted)" }}>Use o seletor no menu superior para escolher a empresa</p>
          </div>
        )}

        {/* Loading skeleton */}
        {carregando && <SkeletonDRE />}

        {erro && (
          <div className="p-4 rounded-2xl text-sm" style={{ background: "rgba(244,63,94,0.08)", border: "1px solid rgba(244,63,94,0.20)", color: "#fb7185" }}>
            {erro}
          </div>
        )}

        {dadosVisiveis && !carregando && (
          <div className="space-y-6 page-enter">

            {/* ── KPI Cards ── */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {kpis.map(kpi => (
                <div key={kpi.label} className={`card-premium ${kpi.border} ${kpi.bg} p-4 flex flex-col gap-2`}>
                  <div className="flex items-center justify-between">
                    <p className="section-title">{kpi.label}</p>
                    <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: "rgba(255,255,255,0.05)" }}>
                      <svg className={`w-3.5 h-3.5 ${kpi.color}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={kpi.icon} />
                      </svg>
                    </div>
                  </div>
                  <p className={`text-xl font-black font-mono tracking-tight ${kpi.color}`}>
                    {kpi.pct ? `${kpi.val.toFixed(1)}%` : formatBRL(kpi.val)}
                  </p>
                  <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{kpi.sub}</p>
                </div>
              ))}
            </div>

            {/* ── Insights + Benchmarks ── */}
            {dadosVisiveis.insights.length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* Insights — ocupa 2/3 */}
                <div className="lg:col-span-2 chart-container">
                  <div className="chart-header">
                    <p className="section-title">Insights Automáticos — {dadosVisiveis.periodo}</p>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-bold" style={{ background: "rgba(79,106,255,0.1)", color: "#9BB3FF" }}>
                      {dadosVisiveis.insights.length} alerta{dadosVisiveis.insights.length !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <div className="p-4 space-y-3">
                    {dadosVisiveis.insights.map(ins => {
                      const isAtencao = ins.severidade === "atencao";
                      const isCritico = ins.severidade === "critico";
                      return (
                        <div
                          key={ins.id}
                          className={`flex items-start gap-3 p-4 rounded-xl ${
                            isCritico ? "bg-rose-50 dark:bg-rose-500/8 border border-rose-200 dark:border-rose-500/25"
                            : isAtencao ? "bg-amber-50 dark:bg-amber-500/8 border border-amber-200 dark:border-amber-500/25"
                            : "bg-blue-50 dark:bg-blue-500/8 border border-blue-200 dark:border-blue-500/25"
                          }`}
                        >
                          {/* Accent bar */}
                          <div className={`w-0.5 self-stretch rounded-full flex-shrink-0 ${
                            isCritico ? "bg-[#B83030]" : isAtencao ? "bg-[#92400E]" : "bg-[#1E4976]"
                          }`} />

                          <div className="flex-1 min-w-0">
                            <div className="flex flex-wrap items-center gap-2 mb-1">
                              <p className={`text-sm font-bold ${
                                isCritico ? "text-rose-800 dark:text-rose-300"
                                : isAtencao ? "text-amber-800 dark:text-amber-300"
                                : "text-blue-800 dark:text-blue-300"
                              }`}>{ins.titulo}</p>
                              <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded-full border ${
                                isCritico ? "bg-rose-100 dark:bg-rose-500/15 border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-400"
                                : isAtencao ? "bg-amber-100 dark:bg-amber-500/15 border-amber-200 dark:border-amber-500/30 text-amber-700 dark:text-amber-400"
                                : "bg-blue-100 dark:bg-blue-500/15 border-blue-200 dark:border-blue-500/30 text-blue-700 dark:text-blue-400"
                              }`}>
                                {isCritico ? "Crítico" : isAtencao ? "Atenção" : "Info"}
                              </span>
                            </div>
                            <p className={`text-sm leading-relaxed ${
                              isCritico ? "text-rose-700 dark:text-rose-400"
                              : isAtencao ? "text-amber-700 dark:text-amber-400"
                              : "text-blue-700 dark:text-blue-400"
                            }`}>{ins.mensagem}</p>
                            {ins.valor_atual != null && ins.valor_referencia != null && (
                              <div className="flex items-center gap-6 mt-3 pt-3" style={{ borderTop: "1px solid currentColor", borderColor: "rgba(0,0,0,0.06)" }}>
                                <div>
                                  <p className="text-[9px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-0.5">Atual</p>
                                  <p className={`text-sm font-black font-mono tabular-nums ${
                                    isCritico ? "text-rose-700 dark:text-rose-300" : isAtencao ? "text-amber-700 dark:text-amber-300" : "text-blue-700 dark:text-blue-300"
                                  }`}>{ins.valor_atual.toFixed(1)}%</p>
                                </div>
                                <div className="text-[#94A3B8] dark:text-slate-600 text-sm">→</div>
                                <div>
                                  <p className="text-[9px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-0.5">Referência</p>
                                  <p className="text-sm font-mono font-semibold text-[#64748B] dark:text-slate-500">{ins.valor_referencia.toFixed(1)}%</p>
                                </div>
                                <div>
                                  <p className="text-[9px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-0.5">Desvio</p>
                                  <p className={`text-sm font-black font-mono tabular-nums ${
                                    (ins.valor_atual - ins.valor_referencia) >= 0 ? "text-[#1A6B3C] dark:text-emerald-400" : "text-[#B83030] dark:text-rose-400"
                                  }`}>
                                    {(ins.valor_atual - ins.valor_referencia) >= 0 ? "+" : ""}{(ins.valor_atual - ins.valor_referencia).toFixed(1)}pp
                                  </p>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Painel de benchmarks — 1/3 */}
                <div className="chart-container">
                  <div className="chart-header">
                    <p className="section-title">Benchmarks Setoriais</p>
                  </div>
                  <div className="p-4 space-y-1">
                    {[
                      {
                        label: "Margem Bruta",
                        atual: dadosVisiveis.metricas.margem_bruta ?? 0,
                        benchmark: 40,
                        unidade: "%",
                      },
                      {
                        label: "Margem Líquida",
                        atual: dadosVisiveis.metricas.margem_liquida ?? 0,
                        benchmark: 15,
                        unidade: "%",
                      },
                      {
                        label: "EBITDA",
                        atual: dadosVisiveis.metricas.ebitda ?? 0,
                        benchmark: null,
                        unidade: "R$",
                      },
                    ].map(({ label, atual, benchmark, unidade }) => {
                      const ok = benchmark !== null ? atual >= benchmark : atual > 0;
                      const cor = ok ? "#1A6B3C" : "#B83030";
                      const corClass = ok ? "text-[#1A6B3C] dark:text-emerald-400" : "text-[#B83030] dark:text-rose-400";
                      const fmtVal = unidade === "R$"
                        ? formatBRL(atual)
                        : `${atual.toFixed(1)}%`;
                      return (
                        <div key={label} className="py-3 border-b border-slate-100 dark:border-slate-700/60 last:border-0">
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-xs text-[#475569] dark:text-slate-400 font-medium">{label}</span>
                            <span className={`text-sm font-black font-mono tabular-nums ${corClass}`}>{fmtVal}</span>
                          </div>
                          {benchmark !== null && (
                            <>
                              <div className="relative h-1.5 rounded-full bg-slate-100 dark:bg-slate-700/40 overflow-hidden">
                                <div
                                  className="absolute top-0 left-0 h-full rounded-full transition-all"
                                  style={{
                                    width: `${Math.min(100, (atual / (benchmark * 1.8)) * 100)}%`,
                                    background: cor,
                                  }}
                                />
                                {/* Benchmark marker */}
                                <div
                                  className="absolute top-0 bottom-0 w-px bg-[#0F2D4A] dark:bg-white opacity-40"
                                  style={{ left: `${(benchmark / (benchmark * 1.8)) * 100}%` }}
                                />
                              </div>
                              <div className="flex items-center justify-between mt-1">
                                <span className="text-[9px] text-[#94A3B8] dark:text-slate-600">0{unidade}</span>
                                <span className="text-[9px] text-[#94A3B8] dark:text-slate-600 flex items-center gap-1">
                                  <span className="w-px h-2 bg-[#94A3B8] dark:bg-slate-600 inline-block" />
                                  ref. {benchmark}{unidade}
                                </span>
                              </div>
                            </>
                          )}
                        </div>
                      );
                    })}

                    {/* Score resumo */}
                    <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700/60">
                      <p className="text-[9px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-2">Score de Saúde Financeira</p>
                      {(() => {
                        const mb = dadosVisiveis.metricas.margem_bruta ?? 0;
                        const ml = dadosVisiveis.metricas.margem_liquida ?? 0;
                        const score = Math.round(
                          (Math.min(1, mb / 40) * 50) + (Math.min(1, ml / 15) * 50)
                        );
                        const scoreCor = score >= 70 ? "#1A6B3C" : score >= 40 ? "#92400E" : "#B83030";
                        const scoreLabel = score >= 70 ? "Saudável" : score >= 40 ? "Atenção" : "Crítico";
                        return (
                          <div className="flex items-center gap-3">
                            <div className="relative w-12 h-12 flex-shrink-0">
                              <svg viewBox="0 0 36 36" className="w-12 h-12 -rotate-90">
                                <circle cx="18" cy="18" r="15.9" fill="none" stroke="#E2E8F0" strokeWidth="3" className="dark:[stroke:#334155]" />
                                <circle
                                  cx="18" cy="18" r="15.9" fill="none"
                                  stroke={scoreCor} strokeWidth="3" strokeLinecap="round"
                                  strokeDasharray={`${score} 100`}
                                />
                              </svg>
                              <span className="absolute inset-0 flex items-center justify-center text-[10px] font-black font-mono" style={{ color: scoreCor }}>
                                {score}
                              </span>
                            </div>
                            <div>
                              <p className="text-sm font-bold" style={{ color: scoreCor }}>{scoreLabel}</p>
                              <p className="text-[10px] text-[#94A3B8] dark:text-slate-600 leading-snug">Baseado em margem bruta e líquida</p>
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  </div>
                </div>

              </div>
            )}

            {/* ── Charts + Table ── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

              {/* Gráfico Waterfall */}
              <GraficoComNome>
                <div className="chart-container">
                  <div className="chart-header">
                    <p className="section-title">Cascata DRE</p>
                    <div className="flex flex-wrap gap-3">
                      {Object.entries(colorMap).map(([tipo, cor]) => (
                        <span key={tipo} className="flex items-center gap-1.5 text-[10px]" style={{ color: "var(--text-muted)" }}>
                          <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: cor }} />
                          {tipo === "positivo" ? "Receita" : tipo === "negativo" ? "Custos" : tipo === "resultado" ? "Parcial" : "Lucro"}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="p-5">
                    <div className="h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 40, top: 4, bottom: 4 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} strokeOpacity={0.08} horizontal={false} />
                          <XAxis type="number" hide />
                          <YAxis
                            dataKey="nome"
                            type="category"
                            tick={{ fill: ct.tickFill, fontSize: 10, fontFamily: "inherit" }}
                            tickLine={false}
                            axisLine={false}
                            width={120}
                          />
                          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(79,106,255,0.05)" }} />
                          <Bar dataKey="abs" radius={[0, 6, 6, 0]} maxBarSize={16}>
                            {chartData.map((entry, i) => (
                              <Cell key={i} fill={colorMap[entry.tipo] || "#64748b"} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              </GraficoComNome>

              {/* Tabela DRE */}
              <div className="chart-container">
                <div className="chart-header">
                  <p className="section-title">Demonstrativo — {dadosVisiveis.periodo}</p>
                </div>
                <div className="overflow-y-auto max-h-80">
                  <table className="w-full table-premium">
                    <thead>
                      <tr>
                        <th>Linha</th>
                        <th className="text-right">Valor</th>
                        <th className="text-right">Var. %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dadosVisiveis.cascata.map((item, i) => (
                        <tr
                          key={i}
                          className={`border-l-2 ${
                            item.tipo === "positivo" ? "border-l-emerald-500/40"
                            : item.tipo === "negativo" ? "border-l-rose-500/40"
                            : item.tipo === "resultado_final" ? "border-l-indigo-500/40"
                            : item.tipo === "resultado" ? "border-l-blue-500/40"
                            : "border-l-transparent"
                          }`}
                          style={item.tipo.startsWith("resultado") ? { background: "rgba(79,106,255,0.06)" } : {}}
                        >
                          <td className={`px-4 py-2.5 text-sm ${item.tipo.startsWith("resultado") ? "font-bold" : ""}`} style={{ color: item.tipo.startsWith("resultado") ? "var(--text-primary)" : "var(--text-secondary)" }}>
                            {item.linha}
                          </td>
                          <td className={`px-4 py-2.5 text-right font-mono text-xs font-semibold ${
                            item.tipo === "negativo" ? "text-rose-400"
                            : item.tipo === "resultado_final" ? "text-[#0F2D4A] dark:text-blue-300"
                            : item.tipo === "resultado" ? "text-blue-600 dark:text-blue-400"
                            : "text-emerald-400"
                          }`}>
                            {item.tipo === "negativo" ? "(" : ""}{formatBRL(item.valor)}{item.tipo === "negativo" ? ")" : ""}
                          </td>
                          <td className="px-4 py-2.5 text-right text-xs">
                            {item.variacao_pct != null ? (
                              <span className={item.variacao_pct >= 0 ? "text-emerald-400" : "text-rose-400"}>
                                {item.variacao_pct >= 0 ? "▲" : "▼"} {Math.abs(item.variacao_pct).toFixed(1)}%
                              </span>
                            ) : <span style={{ color: "var(--text-muted)" }}>—</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Análise Narrativa */}
              {dadosVisiveis.narrativa && (
                <div className="chart-container">
                  <div className="chart-header">
                    <p className="section-title">Análise Financeira — {dadosVisiveis.periodo}</p>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-bold" style={{ background: "rgba(79,106,255,0.1)", color: "#9BB3FF" }}>
                      Relatório Automático
                    </span>
                  </div>
                  <div className="p-5 space-y-5">
                    {dadosVisiveis.narrativa.resumo_executivo && (
                      <div>
                        <h4 className="text-xs font-black uppercase tracking-widest mb-2" style={{ color: "var(--text-muted)" }}>Resumo Executivo</h4>
                        <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{dadosVisiveis.narrativa.resumo_executivo}</p>
                      </div>
                    )}
                    {dadosVisiveis.narrativa.analise_receita && (
                      <div>
                        <h4 className="text-xs font-black uppercase tracking-widest mb-2" style={{ color: "var(--text-muted)" }}>Receita</h4>
                        <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{dadosVisiveis.narrativa.analise_receita}</p>
                      </div>
                    )}
                    {dadosVisiveis.narrativa.analise_despesas && (
                      <div>
                        <h4 className="text-xs font-black uppercase tracking-widest mb-2" style={{ color: "var(--text-muted)" }}>Despesas</h4>
                        <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{dadosVisiveis.narrativa.analise_despesas}</p>
                      </div>
                    )}
                    {dadosVisiveis.narrativa.analise_margens && (
                      <div>
                        <h4 className="text-xs font-black uppercase tracking-widest mb-2" style={{ color: "var(--text-muted)" }}>Margens</h4>
                        <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{dadosVisiveis.narrativa.analise_margens}</p>
                      </div>
                    )}
                    {dadosVisiveis.narrativa.analise_caixa && (
                      <div>
                        <h4 className="text-xs font-black uppercase tracking-widest mb-2" style={{ color: "var(--text-muted)" }}>Fluxo de Caixa</h4>
                        <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{dadosVisiveis.narrativa.analise_caixa}</p>
                      </div>
                    )}
                    {dadosVisiveis.narrativa.analise_endividamento && (
                      <div>
                        <h4 className="text-xs font-black uppercase tracking-widest mb-2" style={{ color: "var(--text-muted)" }}>Endividamento</h4>
                        <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{dadosVisiveis.narrativa.analise_endividamento}</p>
                      </div>
                    )}
                    {dadosVisiveis.narrativa.conclusao && (
                      <div className="p-4 rounded-xl" style={{ background: "rgba(79,106,255,0.04)", border: "1px solid rgba(79,106,255,0.12)" }}>
                        <h4 className="text-xs font-black uppercase tracking-widest mb-2" style={{ color: "#4F6AFF" }}>Conclusão</h4>
                        <p className="text-sm leading-relaxed font-medium" style={{ color: "var(--text-primary)" }}>{dadosVisiveis.narrativa.conclusao}</p>
                      </div>
                    )}
                    {dadosVisiveis.narrativa.alertas && dadosVisiveis.narrativa.alertas.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-xs font-black uppercase tracking-widest" style={{ color: "#f59e0b" }}>Alertas</h4>
                        {dadosVisiveis.narrativa.alertas.map((a, i) => (
                          <div key={i} className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-500/8 border border-amber-200 dark:border-amber-500/20">
                            <svg className="w-4 h-4 mt-0.5 text-amber-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                            </svg>
                            <p className="text-xs text-amber-700 dark:text-amber-300">{a}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
