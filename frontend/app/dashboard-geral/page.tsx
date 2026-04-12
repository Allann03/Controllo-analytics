"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useEmpresa } from "@/contexts/EmpresaContext";

function useTheme() {
  const [isLight, setIsLight] = useState(false);
  useEffect(() => {
    const check = () => setIsLight(document.documentElement.classList.contains("light"));
    check();
    const obs = new MutationObserver(check);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);
  return isLight;
}
import GraficoComNome from "@/components/GraficoComNome";
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

interface KpiItem { valor: number; variacao_pct?: number | null; }

interface EvolucaoMes {
  mes: string;
  receita: number;
  lucro: number;
  despesas: number;
}

interface Insight {
  codigo: string;
  titulo: string;
  descricao: string;
  severidade: "critico" | "atencao" | "info";
}

// ──────────────────────────────────────────────────────────────────
const fmt = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v);
const fmtPct = (v: number) => `${v.toFixed(1)}%`;

function KPICard({ label, value, sub, accent, variacao }: {
  label: string; value: string; sub?: string;
  accent?: boolean; variacao?: number | null;
}) {
  return (
    <div
      className="rounded-2xl p-5 flex flex-col gap-2"
      style={{
        background: "var(--bg-card)",
        border: accent ? "1px solid rgba(79,106,255,0.25)" : "1px solid var(--border)",
      }}
    >
      <p className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{label}</p>
      <p className="text-2xl font-mono font-bold leading-tight" style={{ color: "var(--text-primary)" }}>{value}</p>
      <div className="flex items-center gap-2 mt-auto">
        {sub && <p className="text-xs" style={{ color: "var(--text-muted)" }}>{sub}</p>}
        {variacao != null && (
          <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${variacao >= 0 ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
            {variacao >= 0 ? "+" : ""}{variacao.toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  );
}

function InsightBadge({ sev }: { sev: string }) {
  const map: Record<string, string> = {
    critico: "bg-red-500/10 border-red-500/30 text-red-400",
    atencao: "bg-amber-500/10 border-amber-500/30 text-amber-400",
    info: "bg-blue-500/10 border-blue-500/30 text-blue-400",
  };
  const lbl: Record<string, string> = { critico: "Crítico", atencao: "Atenção", info: "Info" };
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${map[sev] ?? map.info}`}>
      {lbl[sev] ?? sev}
    </span>
  );
}

function CompletudeBar({ total, max = 12 }: { total: number; max?: number }) {
  const pct = Math.min((total / max) * 100, 100);
  const cor = pct >= 75 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${cor}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-400 w-16 text-right">{total}/{max} meses</span>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────
// Dados de exemplo para o estado sem dados (Tech Solutions Ltda)
// ──────────────────────────────────────────────────────────────────

const MESES_LABELS = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];

const EVOLUCAO_EXEMPLO: EvolucaoMes[] = [
  { mes: "Jan", receita: 82000, lucro: 14760, despesas: 54000 },
  { mes: "Fev", receita: 91000, lucro: 18200, despesas: 58000 },
  { mes: "Mar", receita: 87000, lucro: 15660, despesas: 57000 },
  { mes: "Abr", receita: 105000, lucro: 22050, despesas: 66000 },
  { mes: "Mai", receita: 98000, lucro: 19600, despesas: 62000 },
  { mes: "Jun", receita: 112000, lucro: 25760, despesas: 68000 },
  { mes: "Jul", receita: 108000, lucro: 23760, despesas: 67000 },
  { mes: "Ago", receita: 125000, lucro: 30000, despesas: 75000 },
  { mes: "Set", receita: 118000, lucro: 26260, despesas: 72000 },
  { mes: "Out", receita: 134000, lucro: 33500, despesas: 80000 },
  { mes: "Nov", receita: 142000, lucro: 35500, despesas: 84000 },
  { mes: "Dez", receita: 150000, lucro: 30000, despesas: 97000 },
];

const KPIS_EXEMPLO: Record<string, KpiItem> = {
  faturamento_liquido: { valor: 127500, variacao_pct: 6.2 },
  lucro_liquido: { valor: 28900, variacao_pct: -3.1 },
  margem_liquida: { valor: 22.7, variacao_pct: null },
  carga_tributaria: { valor: 19.4, variacao_pct: null },
};

const METRICAS_EXEMPLO: Record<string, number> = {
  receita_bruta: 142000,
  margem_bruta: 34.5,
  total_tributos: 27548,
};

const INSIGHTS_EXEMPLO: Insight[] = [
  { codigo: "ex1", titulo: "Despesas cresceram 8% em relação ao mês anterior", descricao: "Monitorar para evitar compressão adicional da margem.", severidade: "atencao" },
  { codigo: "ex2", titulo: "Margem dentro da média do setor", descricao: "22,7% está alinhado com empresas similares no segmento.", severidade: "info" },
  { codigo: "ex3", titulo: "Crescimento de receita consistente no semestre", descricao: "Alta de 6,2% em relação ao mês anterior mantém a tendência positiva.", severidade: "info" },
];

// ──────────────────────────────────────────────────────────────────

export default function DashboardGeralPage() {
  const router = useRouter();
  const isLight = useTheme();
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const [ano, setAno] = useState(new Date().getFullYear());
  const [mes, setMes] = useState(new Date().getMonth() + 1);

  // API data
  const [kpis, setKpis] = useState<Record<string, KpiItem> | null>(null);
  const [evolucao, setEvolucao] = useState<EvolucaoMes[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [totalLancamentos, setTotalLancamentos] = useState(0);
  const [metricas, setMetricas] = useState<Record<string, number> | null>(null);

  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  const token = () => localStorage.getItem("controllo_token") ?? "";

  useEffect(() => {
    const t = localStorage.getItem("controllo_token");
    const u = localStorage.getItem("controllo_user");
    if (!t || !u) { router.push("/"); return; }
    try { if (!JSON.parse(u).is_aprovado) { router.push("/"); return; } } catch { router.push("/"); return; }
  }, [router]);

  const [modoExemplo, setModoExemplo] = useState(false);

  const carregar = useCallback(async (signal?: AbortSignal) => {
    if (!empresaId) { setCarregando(false); return; }
    setCarregando(true);
    setErro("");
    setKpis(null);
    setModoExemplo(false);
    try {
      const h = { Authorization: `Bearer ${token()}` };
      const [dash, insRes] = await Promise.all([
        fetch(`${API}/api/financeiro/dashboard/${empresaId}?ano=${ano}&mes=${mes}`, { headers: h, signal }).then((r) => r.json()),
        fetch(`${API}/api/financeiro/insights/${empresaId}`, { headers: h, signal }).then((r) => r.json()),
      ]);

      if (dash.sem_dados) {
        // Sem dados reais: ativa modo exemplo
        setModoExemplo(true);
        setKpis(KPIS_EXEMPLO);
        setEvolucao(EVOLUCAO_EXEMPLO);
        setMetricas(METRICAS_EXEMPLO);
        setTotalLancamentos(12);
        setInsights(INSIGHTS_EXEMPLO);
        return;
      }
      if (dash.detail) throw new Error(dash.detail);

      setKpis(dash.kpis ?? {});
      setEvolucao(dash.evolucao_12m ?? []);
      setMetricas(dash.metricas ?? null);
      setTotalLancamentos((dash.evolucao_12m ?? []).length);
      setInsights(
        Array.isArray(insRes?.insights) ? insRes.insights.slice(0, 5) : []
      );
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") return;
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  }, [empresaId, ano, mes]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60_000);
    carregar(controller.signal);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [carregar]);

  const ANOS = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i);
  const MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];

  const tooltipStyle = {
    background: isLight ? "#FFFFFF" : "#1e293b",
    border: `1px solid ${isLight ? "#E2E8F0" : "#334155"}`,
    borderRadius: 8,
    color: isLight ? "#0F172A" : "#f8fafc",
    boxShadow: isLight ? "0 4px 12px rgba(0,0,0,0.08)" : "0 4px 20px rgba(0,0,0,0.40)",
    fontSize: 12,
    padding: "10px 14px",
  };
  const tooltipLabelStyle = { color: isLight ? "#64748b" : "#94a3b8", fontSize: 11, fontWeight: 500 as const };

  return (
    <div className="min-h-full" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>
      {/* HEADER */}
      <header className="px-8 pt-8 pb-6" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#102a43]/15 border border-[#102a43]/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-[#3b6ea5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight">Dashboard Geral</h1>
              <p className="text-slate-500 text-sm">Visão executiva consolidada — Controllo Analytics</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {[
              { val: String(mes), onChange: (v: string) => setMes(Number(v)), opts: MESES.map((m, i) => ({ v: String(i + 1), l: m })) },
              { val: String(ano), onChange: (v: string) => setAno(Number(v)), opts: ANOS.map(a => ({ v: String(a), l: String(a) })) },
            ].map((s, i) => (
              <select
                key={i}
                value={s.val}
                onChange={e => s.onChange(e.target.value)}
                className="rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#102a43]/30"
                style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
              >
                {s.opts.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
              </select>
            ))}
          </div>
        </div>
      </header>

      <div className="px-8 py-8 space-y-8">
        {!empresaId && !carregando && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <svg className="w-10 h-10 mb-4 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
            <p className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>Nenhuma empresa selecionada</p>
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Use o seletor no menu superior para escolher uma empresa</p>
          </div>
        )}

        {carregando && (
          <div className="flex flex-col items-center gap-3 py-20">
            <div className="w-8 h-8 border-2 border-[#102a43]/30 border-t-[#102a43] rounded-full animate-spin" />
            <p className="text-sm text-slate-400">Carregando dados...</p>
          </div>
        )}

        {erro && !carregando && (
          <div className="px-5 py-4 rounded-xl bg-amber-950/30 border border-amber-500/20 text-amber-300 text-sm flex items-start gap-2">
            <svg className="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
            <span>{erro}</span>
          </div>
        )}

        {/* Banner modo exemplo */}
        {modoExemplo && !carregando && (
          <div className="flex items-center justify-between gap-4 px-5 py-4 rounded-2xl bg-[#1e3a5f]/40 border border-[#102a43]/30">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-[#102a43]/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <svg className="w-4 h-4 text-[#3b6ea5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-semibold text-[#9BB3FF]">Este é um exemplo de como seu dashboard ficará</p>
                <p className="text-xs text-[#3b6ea5]/70 mt-0.5">
                  Dados fictícios de "Tech Solutions Ltda". Importe seus dados para ver suas informações reais.
                </p>
              </div>
            </div>
            <a href="/importar"
              className="flex-shrink-0 px-4 py-2 rounded-xl bg-[#1e3a5f] hover:bg-[#3D3A63] text-white text-xs font-semibold transition-colors whitespace-nowrap">
              Importar Dados
            </a>
          </div>
        )}

        {!carregando && !erro && kpis && metricas && (
          <>
            {/* KPIs */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <KPICard
                label="Faturamento Líquido"
                value={fmt(kpis.faturamento_liquido?.valor ?? 0)}
                sub={`Bruto: ${fmt(metricas.receita_bruta ?? 0)}`}
                variacao={kpis.faturamento_liquido?.variacao_pct}
              />
              <KPICard
                label="Lucro Líquido"
                value={fmt(kpis.lucro_liquido?.valor ?? 0)}
                sub={`Margem: ${fmtPct(kpis.margem_liquida?.valor ?? 0)}`}
                accent={(kpis.lucro_liquido?.valor ?? 0) >= 0}
                variacao={kpis.lucro_liquido?.variacao_pct}
              />
              <KPICard
                label="Margem Bruta"
                value={fmtPct(metricas.margem_bruta ?? 0)}
                sub="Lucro bruto / Rec. líquida"
              />
              <KPICard
                label="Carga Tributária"
                value={fmtPct(kpis.carga_tributaria?.valor ?? 0)}
                sub={`Total: ${fmt(metricas.total_tributos ?? 0)}`}
                accent={(kpis.carga_tributaria?.valor ?? 0) > 25}
              />
            </div>

            {/* Completude */}
            <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Completude dos dados ({ano})</p>
                <span className="text-[11px] text-slate-500">{totalLancamentos} períodos com dados</span>
              </div>
              <CompletudeBar total={totalLancamentos} />
            </div>

            {/* Gráficos */}
            {evolucao.length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Receita vs Lucro */}
                <GraficoComNome>
                <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                  <p className="text-sm font-bold mb-4" style={{ color: "var(--text-primary)" }}>Receita vs Lucro Líquido</p>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={evolucao} barGap={4}>
                      <CartesianGrid strokeDasharray="3 3" stroke={isLight ? "#e2e8f0" : "#334155"} />
                      <XAxis dataKey="mes" tick={{ fill: isLight ? "#555570" : "#64748b", fontSize: 11 }} />
                      <YAxis tick={{ fill: isLight ? "#555570" : "#64748b", fontSize: 11 }} tickFormatter={(v) => `${((v as number) / 1000).toFixed(0)}k`} />
                      <Tooltip contentStyle={tooltipStyle} formatter={(v) => fmt(v as number)} labelStyle={tooltipLabelStyle} />
                      <Legend wrapperStyle={{ fontSize: 11, color: isLight ? "#555570" : "#64748b" }} />
                      <Bar dataKey="receita" name="Receita" fill="#7c3aed" radius={[3, 3, 0, 0]} />
                      <Bar dataKey="lucro" name="Lucro Líquido" fill="#10b981" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                </GraficoComNome>

                {/* Despesas */}
                <GraficoComNome>
                <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                  <p className="text-sm font-bold mb-4" style={{ color: "var(--text-primary)" }}>Evolução das Despesas</p>
                  <ResponsiveContainer width="100%" height={220}>
                    <AreaChart data={evolucao}>
                      <defs>
                        <linearGradient id="gradDespesas" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                          <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke={isLight ? "#e2e8f0" : "#334155"} />
                      <XAxis dataKey="mes" tick={{ fill: isLight ? "#555570" : "#64748b", fontSize: 11 }} />
                      <YAxis tick={{ fill: isLight ? "#555570" : "#64748b", fontSize: 11 }} tickFormatter={(v) => `${((v as number) / 1000).toFixed(0)}k`} />
                      <Tooltip contentStyle={tooltipStyle} formatter={(v) => fmt(v as number)} labelStyle={tooltipLabelStyle} />
                      <Area type="monotone" dataKey="despesas" name="Despesas" stroke="#ef4444" fill="url(#gradDespesas)" strokeWidth={2} dot={{ fill: "#ef4444", r: 3 }} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                </GraficoComNome>
              </div>
            )}

            {/* Insights */}
            {insights.length > 0 && (
              <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                <div className="flex items-center gap-2 mb-4">
                  <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>Alertas Automáticos</p>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: "var(--bg-secondary)", color: "var(--text-muted)" }}>{insights.length}</span>
                </div>
                <div className="space-y-2">
                  {insights.map((ins) => (
                    <div key={ins.codigo} className={`flex items-start gap-3 px-4 py-3 rounded-xl border ${
                      ins.severidade === "critico" ? "border-red-500/20 bg-red-950/20"
                      : ins.severidade === "atencao" ? "border-amber-500/20 bg-amber-950/20"
                      : "border-blue-500/20 bg-blue-950/20"
                    }`}>
                      <div className="mt-0.5 flex-shrink-0"><InsightBadge sev={ins.severidade} /></div>
                      <div>
                        <p className="text-sm font-semibold text-slate-200">{ins.titulo}</p>
                        <p className="text-xs text-slate-400 mt-0.5">{ins.descricao}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {insights.length === 0 && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-emerald-950/20 border border-emerald-500/15 text-emerald-400 text-sm">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Nenhum alerta identificado para o período.
              </div>
            )}
          </>
        )}

        {/* Estado sem empresa: mostra exemplo */}
        {!carregando && !empresaId && !kpis && (
          <>
            <div className="flex items-center justify-between gap-4 px-5 py-4 rounded-2xl bg-[#1e3a5f]/40 border border-[#102a43]/30">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-[#102a43]/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg className="w-4 h-4 text-[#3b6ea5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-[#9BB3FF]">Prévia interativa — como seu dashboard ficará</p>
                  <p className="text-xs text-[#3b6ea5]/70 mt-0.5">Selecione uma empresa ou importe dados para visualizar suas informações reais.</p>
                </div>
              </div>
              <a href="/importar"
                className="flex-shrink-0 px-4 py-2 rounded-xl bg-[#1e3a5f] hover:bg-[#3D3A63] text-white text-xs font-semibold transition-colors whitespace-nowrap">
                Importar Dados
              </a>
            </div>
            <div className="pointer-events-none opacity-60">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <KPICard label="Faturamento Líquido" value={fmt(KPIS_EXEMPLO.faturamento_liquido?.valor ?? 0)} sub="Bruto: R$ 142.000" variacao={6.2} />
                <KPICard label="Lucro Líquido" value={fmt(KPIS_EXEMPLO.lucro_liquido?.valor ?? 0)} sub="Margem: 22,7%" accent variacao={-3.1} />
                <KPICard label="Margem Bruta" value="34,5%" sub="Lucro bruto / Rec. líquida" />
                <KPICard label="Carga Tributária" value="19,4%" sub="Total: R$ 27.548" />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
