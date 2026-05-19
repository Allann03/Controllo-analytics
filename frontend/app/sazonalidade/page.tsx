"use client";

import { useEffect, useState, useCallback } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";
import GraficoComNome from "@/components/GraficoComNome";
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { useChartTheme } from "@/components/useChartTheme";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

// ─────────────────────────────────────────────────────────────────
//  Tipos
// ─────────────────────────────────────────────────────────────────

interface LancMensal {
  ano: number; mes: number;
  receita_bruta: number; lucro_liquido: number;
  entradas_caixa: number; saidas_caixa: number;
  folha_pagamento: number; despesas_adm: number;
  despesas_comerciais: number; outras_despesas: number;
  [key: string]: number | string;
}

// ─────────────────────────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────────────────────────

const MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
const ANOS  = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i);
const fmt   = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v);
const n = (v: unknown) => (typeof v === "number" ? v : 0);

/** Média simples */
function media(arr: number[]): number {
  if (!arr.length) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

/** Regressão linear simples — retorna { a (inclinação), b (intercepto) } */
function regressaoLinear(ys: number[]): { a: number; b: number } {
  const n_  = ys.length;
  if (n_ < 2) return { a: 0, b: ys[0] ?? 0 };
  const xs  = ys.map((_, i) => i + 1);
  const mx  = media(xs);
  const my  = media(ys);
  const num = xs.reduce((s, x, i) => s + (x - mx) * (ys[i] - my), 0);
  const den = xs.reduce((s, x) => s + (x - mx) ** 2, 0);
  const a   = den ? num / den : 0;
  const b   = my - a * mx;
  return { a, b };
}

/** Índice sazonal por mês: média do mês / média global */
function indicesSazonais(lancamentos: LancMensal[], campo: string): Record<number, number> {
  const mediaGlobal = media(lancamentos.map(l => n(l[campo])));
  if (!mediaGlobal) return {};
  const result: Record<number, number> = {};
  for (let m = 1; m <= 12; m++) {
    const vals = lancamentos.filter(l => l.mes === m).map(l => n(l[campo]));
    if (vals.length) result[m] = media(vals) / mediaGlobal;
  }
  return result;
}

/** Projeta os próximos N meses usando tendência + sazonalidade */
function projetar(
  lancamentos: LancMensal[],
  campo: string,
  nMeses: number,
): { mes: string; valor: number; tipo: "historico" | "projecao" }[] {
  const sorted = [...lancamentos].sort((a, b) => a.ano - b.ano || a.mes - b.mes);
  const ys = sorted.map(l => n(l[campo]));
  const { a, b } = regressaoLinear(ys);
  const sazonais = indicesSazonais(sorted, campo);

  // Histórico
  const hist = sorted.map((l, i) => ({
    mes: `${MESES[l.mes - 1]}/${String(l.ano).slice(-2)}`,
    valor: n(l[campo]),
    tipo: "historico" as const,
  }));

  // Projeção
  const ultimo = sorted[sorted.length - 1];
  let anoAtual = ultimo ? ultimo.ano : new Date().getFullYear();
  let mesAtual = ultimo ? ultimo.mes : new Date().getMonth() + 1;
  const nTotal = sorted.length;

  const proj = Array.from({ length: nMeses }, (_, i) => {
    mesAtual++;
    if (mesAtual > 12) { mesAtual = 1; anoAtual++; }
    const tendencia = a * (nTotal + i + 1) + b;
    const sazon = sazonais[mesAtual] ?? 1;
    return {
      mes: `${MESES[mesAtual - 1]}/${String(anoAtual).slice(-2)}`,
      valor: Math.max(0, tendencia * sazon),
      tipo: "projecao" as const,
    };
  });

  return [...hist, ...proj];
}

// ─────────────────────────────────────────────────────────────────
//  Componente: HeatMap de sazonalidade
// ─────────────────────────────────────────────────────────────────

function HeatmapSazonalidade({ dados }: { dados: { mes: number; indice: number }[] }) {
  const max = Math.max(...dados.map(d => d.indice), 0.01);
  const min = Math.min(...dados.map(d => d.indice));

  function corCelula(indice: number): string {
    const norm = (indice - min) / (max - min);
    if (norm > 0.75) return "bg-emerald-500 text-white";
    if (norm > 0.5)  return "bg-emerald-400/60 text-emerald-100";
    if (norm > 0.25) return "bg-amber-400/60 text-amber-100";
    return "bg-rose-500/60 text-rose-100";
  }

  return (
    <div className="grid grid-cols-12 gap-1.5">
      {dados.map(({ mes, indice }) => (
        <div key={mes} className={`rounded-xl p-2 text-center ${corCelula(indice)}`}>
          <p className="text-[10px] font-bold">{MESES[mes - 1]}</p>
          <p className="text-xs font-black font-mono">{indice.toFixed(2)}x</p>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
//  Página principal
// ─────────────────────────────────────────────────────────────────

type Campo = "receita_bruta" | "lucro_liquido" | "entradas_caixa";

// ─── Dados de demonstração ────────────────────────────────────────
const DEMO_LANCAMENTOS: LancMensal[] = [
  { ano: 2024, mes: 1,  receita_bruta: 120000, lucro_liquido: 22000, entradas_caixa: 115000, saidas_caixa: 90000, folha_pagamento: 35000, despesas_adm: 18000, despesas_comerciais: 12000, outras_despesas: 5000 },
  { ano: 2024, mes: 2,  receita_bruta: 115000, lucro_liquido: 20000, entradas_caixa: 110000, saidas_caixa: 88000, folha_pagamento: 35000, despesas_adm: 17000, despesas_comerciais: 11000, outras_despesas: 4500 },
  { ano: 2024, mes: 3,  receita_bruta: 130000, lucro_liquido: 26000, entradas_caixa: 125000, saidas_caixa: 95000, folha_pagamento: 35000, despesas_adm: 19000, despesas_comerciais: 13000, outras_despesas: 5000 },
  { ano: 2024, mes: 4,  receita_bruta: 145000, lucro_liquido: 30000, entradas_caixa: 140000, saidas_caixa: 100000, folha_pagamento: 36000, despesas_adm: 20000, despesas_comerciais: 14000, outras_despesas: 5500 },
  { ano: 2024, mes: 5,  receita_bruta: 160000, lucro_liquido: 35000, entradas_caixa: 155000, saidas_caixa: 108000, folha_pagamento: 37000, despesas_adm: 21000, despesas_comerciais: 15000, outras_despesas: 6000 },
  { ano: 2024, mes: 6,  receita_bruta: 175000, lucro_liquido: 42000, entradas_caixa: 170000, saidas_caixa: 115000, folha_pagamento: 37000, despesas_adm: 22000, despesas_comerciais: 16000, outras_despesas: 6000 },
  { ano: 2024, mes: 7,  receita_bruta: 180000, lucro_liquido: 44000, entradas_caixa: 175000, saidas_caixa: 118000, folha_pagamento: 38000, despesas_adm: 22000, despesas_comerciais: 16000, outras_despesas: 6500 },
  { ano: 2024, mes: 8,  receita_bruta: 190000, lucro_liquido: 48000, entradas_caixa: 185000, saidas_caixa: 125000, folha_pagamento: 38000, despesas_adm: 23000, despesas_comerciais: 17000, outras_despesas: 6500 },
  { ano: 2024, mes: 9,  receita_bruta: 185000, lucro_liquido: 46000, entradas_caixa: 180000, saidas_caixa: 122000, folha_pagamento: 38000, despesas_adm: 22000, despesas_comerciais: 17000, outras_despesas: 6000 },
  { ano: 2024, mes: 10, receita_bruta: 200000, lucro_liquido: 52000, entradas_caixa: 195000, saidas_caixa: 130000, folha_pagamento: 39000, despesas_adm: 24000, despesas_comerciais: 18000, outras_despesas: 7000 },
  { ano: 2024, mes: 11, receita_bruta: 210000, lucro_liquido: 55000, entradas_caixa: 205000, saidas_caixa: 135000, folha_pagamento: 39000, despesas_adm: 25000, despesas_comerciais: 18000, outras_despesas: 7000 },
  { ano: 2024, mes: 12, receita_bruta: 250000, lucro_liquido: 72000, entradas_caixa: 245000, saidas_caixa: 155000, folha_pagamento: 40000, despesas_adm: 27000, despesas_comerciais: 20000, outras_despesas: 8000 },
];

export default function SazonalidadePage() {
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const ct = useChartTheme();
  const [lancamentos, setLancs]   = useState<LancMensal[]>([]);
  const [campo, setCampo]         = useState<Campo>("receita_bruta");
  const [nProj, setNProj]         = useState(6);
  const [carregando, setCarregando] = useState(false);

  const carregar = useCallback(async (signal?: AbortSignal) => {
    if (!empresaId) { setCarregando(false); return; }
    setCarregando(true);
    try {
      const r = await fetch(`${API}/api/financeiro/lancamentos/${empresaId}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("controllo_token") ?? ""}` },
        signal,
      });
      if (!r.ok) { setLancs([]); return; }
      const data = await r.json();
      setLancs(Array.isArray(data) ? data : []);
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") return;
      setLancs([]);
    }
    finally { setCarregando(false); }
  }, [empresaId]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60_000);
    carregar(controller.signal);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [carregar]);

  // Usa dados reais se existirem, senão usa demonstração
  const isDemo = !empresaId || lancamentos.length === 0;
  const dadosBase = isDemo ? DEMO_LANCAMENTOS : lancamentos;

  // Dados computados
  const sorted = [...dadosBase].sort((a, b) => a.ano - b.ano || a.mes - b.mes);
  const sazonais = indicesSazonais(sorted, campo);
  const heatmapData = Array.from({ length: 12 }, (_, i) => ({
    mes: i + 1,
    indice: sazonais[i + 1] ?? 0,
  })).filter(d => d.indice > 0);

  const projecao = sorted.length >= 2 ? projetar(sorted, campo, nProj) : [];
  const histData = projecao.filter(d => d.tipo === "historico");
  const projData = projecao;

  // Estatísticas
  const vals = sorted.map(l => n(l[campo]));
  const mediaTot  = media(vals);
  const { a: tendencia } = regressaoLinear(vals);
  const melhorMes = heatmapData.sort((a,b) => b.indice - a.indice)[0];
  const piorMes   = [...heatmapData].sort((a,b) => a.indice - b.indice)[0];

  const CAMPOS: { key: Campo; label: string }[] = [
    { key: "receita_bruta",   label: "Receita Bruta" },
    { key: "lucro_liquido",   label: "Lucro Líquido" },
    { key: "entradas_caixa",  label: "Entradas de Caixa" },
  ];

  return (
    <div className="min-h-full" style={{ background: "var(--bg-canvas)", color: "var(--text-primary)" }}>
      {/* Header */}
      <header className="px-8 pt-8 pb-0 border-b border-slate-200 dark:border-slate-700">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-5">
          <div>
            <div className="inline-flex items-center gap-2 mb-3">
              <span className="px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-widest bg-amber-50 border border-amber-200 text-amber-700 dark:bg-amber-500/10 dark:border-amber-500/30 dark:text-amber-400">
                Análise Preditiva
              </span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight">
              Sazonalidade{" "}
              <span className="text-amber-600 dark:text-amber-400">e Projeção</span>
            </h1>
            <p className="text-sm mt-1.5 text-slate-500 dark:text-slate-400">
              Padrões sazonais históricos e projeção com tendência linear
            </p>
          </div>
          {empresaSelecionada && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl self-start mt-2 bg-amber-50 border border-amber-200 dark:bg-amber-500/8 dark:border-amber-500/20">
              <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
              <span className="text-sm font-medium text-amber-700 dark:text-amber-400">{empresaSelecionada.nome}</span>
            </div>
          )}
        </div>

        {/* Controles de análise */}
        <div className="flex gap-1 flex-wrap">
          {CAMPOS.map(c => (
            <button
              key={c.key}
              onClick={() => setCampo(c.key)}
              className={`px-5 py-2.5 text-sm font-semibold border-b-2 transition-all ${
                campo === c.key
                  ? "border-amber-500 text-amber-700 dark:text-amber-400"
                  : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
      </header>

      <div className="px-8 py-6 space-y-6">
        {isDemo && (
          <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-300 text-sm">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span><strong>Dados de Demonstração</strong> — Selecione uma empresa para visualizar seus dados reais.</span>
          </div>
        )}
        {carregando ? (
          <div className="space-y-6 page-enter">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="card-premium p-4 space-y-2">
                  <div className="skeleton h-3 w-20 rounded" />
                  <div className="skeleton h-6 w-28 rounded" />
                </div>
              ))}
            </div>
            <div className="card-premium p-5">
              <div className="skeleton h-4 w-40 rounded mb-4" />
              <div className="skeleton h-20 w-full rounded-xl" />
            </div>
            <div className="card-premium p-5">
              <div className="skeleton h-4 w-48 rounded mb-4" />
              <div className="skeleton h-72 w-full rounded-xl" />
            </div>
          </div>
        ) : (
          <>
            {/* Cards de estatísticas */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                {
                  label: "Média Mensal",
                  value: fmt(mediaTot),
                  sub: null,
                  accent: "#102a43",
                  bg: "rgba(79,106,255,0.08)",
                  border: "rgba(79,106,255,0.20)",
                  valColor: "var(--text-primary)",
                },
                {
                  label: "Tendência",
                  value: `${tendencia >= 0 ? "+" : ""}${fmt(Math.abs(tendencia))}/mês`,
                  sub: tendencia >= 0 ? "Crescimento" : "Queda",
                  accent: tendencia >= 0 ? "#10b981" : "#f43f5e",
                  bg: tendencia >= 0 ? "rgba(16,185,129,0.08)" : "rgba(244,63,94,0.08)",
                  border: tendencia >= 0 ? "rgba(16,185,129,0.20)" : "rgba(244,63,94,0.20)",
                  valColor: tendencia >= 0 ? "#34d399" : "#fb7185",
                },
                melhorMes ? {
                  label: "Melhor Mês",
                  value: MESES[melhorMes.mes - 1],
                  sub: `${melhorMes.indice.toFixed(2)}× da média`,
                  accent: "#10b981",
                  bg: "rgba(16,185,129,0.08)",
                  border: "rgba(16,185,129,0.20)",
                  valColor: "#34d399",
                } : null,
                piorMes ? {
                  label: "Menor Mês",
                  value: MESES[piorMes.mes - 1],
                  sub: `${piorMes.indice.toFixed(2)}× da média`,
                  accent: "#f43f5e",
                  bg: "rgba(244,63,94,0.08)",
                  border: "rgba(244,63,94,0.20)",
                  valColor: "#fb7185",
                } : null,
              ].filter(Boolean).map((card, i) => card && (
                <div
                  key={i}
                  className="card-premium p-4 relative overflow-hidden"
                >
                  <div className="absolute top-0 left-0 right-0 h-[1px]" style={{ background: `linear-gradient(90deg, ${card.accent} 0%, transparent 100%)` }} />
                  <p className="text-[11px] font-bold uppercase tracking-widest mb-1.5" style={{ color: "var(--text-muted)" }}>{card.label}</p>
                  <p className="text-xl font-black font-mono" style={{ color: card.valColor }}>{card.value}</p>
                  {card.sub && <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{card.sub}</p>}
                </div>
              ))}
            </div>

            {/* Heatmap de índices sazonais */}
            {heatmapData.length > 0 && (
              <div className="chart-container">
                <div className="chart-header">
                  <div>
                    <p className="section-title">Índice Sazonal por Mês</p>
                    <p className="text-xs text-slate-600 mt-0.5">1.0× = média histórica do período</p>
                  </div>
                  <span className="badge badge-amber">Análise Sazonal</span>
                </div>
                <HeatmapSazonalidade dados={heatmapData} />
              </div>
            )}

            {/* Gráfico histórico + projeção */}
            <GraficoComNome>
            <div className="chart-container">
              <div className="chart-header">
                <div>
                  <p className="section-title">Histórico + Projeção ({nProj} meses)</p>
                  <p className="text-xs text-slate-600 mt-0.5">Pontos amarelos = projeção futura</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">Projetar:</span>
                  {[3, 6, 12].map(n => (
                    <button key={n} onClick={() => setNProj(n)}
                      className={`text-xs px-2.5 py-1 rounded-lg font-bold transition-colors ${nProj === n ? "bg-[#102a43] text-white" : "bg-slate-700 text-slate-400 hover:bg-slate-600"}`}>
                      {n}m
                    </button>
                  ))}
                </div>
              </div>

              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={projData}>
                  <defs>
                    <linearGradient id="colorHist" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor={ct.lineStroke} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={ct.lineStroke} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorProj" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#fbbf24" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#fbbf24" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
                  <XAxis dataKey="mes" tick={{ fill: ct.tickFill, fontSize: 10 }} interval={Math.max(0, Math.floor(projData.length / 12) - 1)} />
                  <YAxis tick={{ fill: ct.tickFill, fontSize: 11 }} tickFormatter={v => `${((v as number) / 1000).toFixed(0)}k`} />
                  <Tooltip
                    contentStyle={ct.tooltipStyle} labelStyle={ct.tooltipLabelStyle} itemStyle={ct.tooltipItemStyle}
                    formatter={(v, name) => [fmt(v as number), name]}
                    labelFormatter={(label, payload) => {
                      const tipo = payload?.[0]?.payload?.tipo;
                      return `${label}${tipo === "projecao" ? " (projeção)" : ""}`;
                    }}
                  />
                  <ReferenceLine x={histData[histData.length - 1]?.mes} stroke={ct.axisStroke} strokeDasharray="4 4" label={{ value: "hoje", fill: ct.tickFill, fontSize: 10 }} />
                  <Area
                    type="monotone" dataKey="valor" name={CAMPOS.find(c => c.key === campo)?.label ?? campo}
                    stroke={ct.lineStroke} fill="url(#colorHist)" strokeWidth={2}
                    dot={(props) => {
                      const { cx, cy, payload } = props;
                      if (payload.tipo === "projecao") {
                        return <circle key={`dot-${cx}-${cy}`} cx={cx} cy={cy} r={3} fill="#fbbf24" stroke="#fbbf24" />;
                      }
                      return <circle key={`dot-${cx}-${cy}`} cx={cx} cy={cy} r={0} />;
                    }}
                  />
                </AreaChart>
              </ResponsiveContainer>

              <p className="text-[11px] text-slate-600 dark:text-slate-400 mt-2 flex items-center gap-1">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Projeção por regressão linear + índice sazonal histórico. Não constitui previsão contábil.
              </p>
            </div>
            </GraficoComNome>

            {/* Comparativo ano a ano por mês */}
            {(() => {
              const anos = [...new Set(sorted.map(l => l.ano))].sort();
              if (anos.length < 2) return null;
              const barData = MESES.map((mes, i) => {
                const row: Record<string, unknown> = { mes };
                anos.forEach(a => {
                  const l = sorted.find(l => l.ano === a && l.mes === i + 1);
                  row[String(a)] = l ? n(l[campo]) : null;
                });
                return row;
              });
              const CORES = ["#3b6ea5","#10b981","#f59e0b","#ef4444","#a78bfa"];

              return (
                <GraficoComNome>
                <div className="chart-container">
                  <div className="chart-header">
                    <div>
                      <p className="section-title">Comparativo Ano a Ano</p>
                    </div>
                  </div>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={barData}>
                      <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
                      <XAxis dataKey="mes" tick={{ fill: ct.tickFill, fontSize: 11 }} />
                      <YAxis tick={{ fill: ct.tickFill, fontSize: 11 }} tickFormatter={v => `${((v as number) / 1000).toFixed(0)}k`} />
                      <Tooltip contentStyle={ct.tooltipStyle} labelStyle={ct.tooltipLabelStyle} itemStyle={ct.tooltipItemStyle} formatter={v => fmt(v as number)} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      {anos.map((a, i) => (
                        <Bar key={a} dataKey={String(a)} fill={CORES[i % CORES.length]} radius={[3,3,0,0]} />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                </GraficoComNome>
              );
            })()}
          </>
        )}
      </div>
    </div>
  );
}
