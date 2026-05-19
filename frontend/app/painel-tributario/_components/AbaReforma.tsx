"use client";

import { useState } from "react";
import GraficoComNome from "@/components/GraficoComNome";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { useChartTheme } from "@/components/useChartTheme";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

const fmt = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v);
const fmtPct = (v: number) => `${Number(v).toFixed(2)}%`;

// ── Referência estática: alíquotas dos regimes ──────────────────────
const REGIME_ALIQUOTAS = [
  {
    regime: "Simples Nacional",
    cor: "#1A6B3C",
    tributos: [
      { nome: "Alíquota Efetiva (DAS)", atual: "~6%", obs: "varia por faixa" },
      { nome: "ISS/ICMS incluso", atual: "Sim", obs: "dentro do DAS" },
    ],
  },
  {
    regime: "Lucro Presumido",
    cor: "#1E4976",
    tributos: [
      { nome: "IRPJ", atual: "15% + 10% adicional", obs: "sobre lucro presumido" },
      { nome: "CSLL", atual: "9%", obs: "sobre lucro presumido" },
      { nome: "PIS", atual: "0,65%", obs: "sobre receita" },
      { nome: "COFINS", atual: "3,0%", obs: "sobre receita" },
    ],
  },
  {
    regime: "Lucro Real",
    cor: "#92400E",
    tributos: [
      { nome: "IRPJ", atual: "15% + 10% adicional", obs: "sobre lucro real" },
      { nome: "CSLL", atual: "9%", obs: "sobre lucro real" },
      { nome: "PIS (não-cumulativo)", atual: "1,65%", obs: "com créditos" },
      { nome: "COFINS (não-cumulativo)", atual: "7,6%", obs: "com créditos" },
    ],
  },
];

const CRONOGRAMA = [
  { ano: "2026", desc: "Início da cobrança de IBS e CBS com alíquotas reduzidas", status: "proximo" },
  { ano: "2027", desc: "PIS e COFINS extintos. CBS em vigência plena", status: "futuro" },
  { ano: "2029–2032", desc: "Redução gradual do ICMS e ISS estadual/municipal", status: "futuro" },
  { ano: "2033", desc: "Extinção do ICMS e ISS. IBS em vigência plena", status: "futuro" },
];

// ── Componente de referência de alíquota do IBS/CBS ─────────────────
function CardReforma() {
  return (
    <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">
      <div className="px-5 pt-5 pb-4 border-b border-slate-100 dark:border-slate-700/60">
        <div className="flex items-center gap-2.5 mb-1">
          <div className="w-0.5 h-5 rounded-full bg-[#1E4976] flex-shrink-0" />
          <h3 className="text-[11px] font-black uppercase tracking-widest text-[#64748B] dark:text-slate-400">
            Reforma Tributária — IBS + CBS
          </h3>
        </div>
        <p className="text-xs text-[#64748B] dark:text-slate-500 mt-2 leading-relaxed">
          A Reforma Tributária (PEC 45/2023) unifica PIS, COFINS, ISS e ICMS nos novos tributos <strong className="text-[#0F172A] dark:text-slate-200">IBS</strong> (Imposto sobre Bens e Serviços) e <strong className="text-[#0F172A] dark:text-slate-200">CBS</strong> (Contribuição sobre Bens e Serviços), com alíquota-padrão estimada em 26,5%.
        </p>
      </div>
      <div className="px-5 py-4 grid grid-cols-3 gap-4">
        {[
          { label: "Alíquota-padrão estimada", value: "26,5%", color: "#1E4976", sub: "CBS + IBS combinados" },
          { label: "Alíquota reduzida (saúde, educação)", value: "60%", color: "#1A6B3C", sub: "da alíquota-padrão" },
          { label: "Crédito sobre insumos", value: "Total", color: "#92400E", sub: "modelo não-cumulativo" },
        ].map(({ label, value, color, sub }) => (
          <div key={label} className="text-center">
            <p className="text-[9px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-1">{label}</p>
            <p className="text-xl font-black font-mono tabular-nums" style={{ color }}>{value}</p>
            <p className="text-[9px] text-[#94A3B8] dark:text-slate-600 mt-0.5">{sub}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Cronograma de transição ─────────────────────────────────────────
function Cronograma() {
  return (
    <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-5">
      <div className="flex items-center gap-2.5 mb-4 pb-2.5 border-b border-slate-100 dark:border-slate-700/60">
        <div className="w-0.5 h-5 rounded-full bg-[#92400E] flex-shrink-0" />
        <h3 className="text-[11px] font-black uppercase tracking-widest text-[#64748B] dark:text-slate-400">
          Cronograma de Transição
        </h3>
      </div>
      <div className="space-y-3">
        {CRONOGRAMA.map((item, i) => (
          <div key={i} className="flex items-start gap-3">
            <div className={`flex-shrink-0 px-2.5 py-1 rounded-lg text-[11px] font-black font-mono tabular-nums min-w-[68px] text-center ${
              item.status === "proximo"
                ? "bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/25 text-amber-700 dark:text-amber-400"
                : "bg-slate-100 dark:bg-slate-700/40 border border-slate-200 dark:border-slate-700 text-[#64748B] dark:text-slate-500"
            }`}>
              {item.ano}
            </div>
            <p className="text-xs text-[#475569] dark:text-slate-400 pt-1 leading-relaxed">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AbaReforma({
  empresaId,
  token,
}: {
  empresaId: number | null;
  token: () => string;
}) {
  const ct = useChartTheme();
  const [receitaBruta, setReceitaBruta] = useState("");
  const [custoServicos, setCustoServicos] = useState("");
  const [resultado, setResultado] = useState<Record<string, unknown> | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  const simular = async () => {
    if (!empresaId) return;
    setCarregando(true);
    setErro("");
    const params = new URLSearchParams();
    if (receitaBruta) params.set("receita_bruta", receitaBruta);
    if (custoServicos) params.set("custo_servicos", custoServicos);
    try {
      const res = await fetch(`${API}/api/financeiro/simulacao/${empresaId}?${params}`, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Erro na simulação");
      setResultado(data);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  };

  const fmtNum = (v: unknown) => typeof v === "number" ? fmt(v) : "—";
  const fmtPctNum = (v: unknown) => typeof v === "number" ? fmtPct(v) : "—";

  const impactoLiquido = typeof resultado?.impacto_liquido === "number" ? resultado.impacto_liquido : null;
  const economia = impactoLiquido !== null && impactoLiquido < 0;

  return (
    <div className="space-y-6">

      {/* ── Contexto: IBS/CBS + Cronograma ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <CardReforma />
        <Cronograma />
      </div>

      {/* ── Formulário de simulação ── */}
      <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">
        <div className="px-5 pt-5 pb-4 border-b border-slate-100 dark:border-slate-700/60 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-0.5 h-5 rounded-full bg-[#1E4976] flex-shrink-0" />
            <h3 className="text-[11px] font-black uppercase tracking-widest text-[#64748B] dark:text-slate-400">
              Simulação de Impacto
            </h3>
          </div>
          {!empresaId && (
            <span className="text-[10px] text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 px-2.5 py-1 rounded-full font-semibold">
              Selecione uma empresa
            </span>
          )}
        </div>

        <div className="p-5">
          <p className="text-xs text-[#64748B] dark:text-slate-500 mb-5 leading-relaxed">
            Informe os valores base para comparar a tributação atual com a Reforma (IBS + CBS).
            Se em branco, usará os dados do último lançamento disponível da empresa.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 block mb-1.5">
                Receita Bruta (R$)
              </label>
              <input
                type="number"
                value={receitaBruta}
                onChange={(e) => setReceitaBruta(e.target.value)}
                placeholder="Ex: 500000"
                className="w-full bg-[#F8FAFC] dark:bg-slate-900 border border-slate-200 dark:border-slate-600 rounded-xl px-4 py-2.5 text-sm text-[#0F172A] dark:text-slate-200 placeholder-[#CBD5E1] dark:placeholder-slate-600 focus:outline-none focus:border-[#1E4976] dark:focus:border-[#1E4976] transition-colors"
              />
            </div>
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 block mb-1.5">
                Custo dos Serviços (R$)
              </label>
              <input
                type="number"
                value={custoServicos}
                onChange={(e) => setCustoServicos(e.target.value)}
                placeholder="Ex: 150000"
                className="w-full bg-[#F8FAFC] dark:bg-slate-900 border border-slate-200 dark:border-slate-600 rounded-xl px-4 py-2.5 text-sm text-[#0F172A] dark:text-slate-200 placeholder-[#CBD5E1] dark:placeholder-slate-600 focus:outline-none focus:border-[#1E4976] dark:focus:border-[#1E4976] transition-colors"
              />
            </div>
          </div>

          {erro && (
            <div className="mb-4 px-4 py-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-500/20 text-red-700 dark:text-red-400 text-sm">
              {erro}
            </div>
          )}

          <button
            onClick={simular}
            disabled={carregando || !empresaId}
            className="w-full py-3 rounded-xl font-semibold text-sm text-white hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
            style={{ background: "#1E4976" }}
          >
            {carregando ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Simulando...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 11h.01M12 11h.01M15 11h.01M4 19h16a2 2 0 002-2V7a2 2 0 00-2-2H4a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                Simular Impacto da Reforma
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Resultado da simulação ── */}
      {resultado && (
        <div className="space-y-5">

          {/* KPI cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Regime Atual */}
            <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">
              <div className="h-1 w-full bg-[#B83030]" />
              <div className="p-5">
                <p className="text-[10px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-1">Regime Atual</p>
                <p className="text-xs text-[#64748B] dark:text-slate-500 mb-3 font-medium">{String(resultado.regime_atual ?? "—")}</p>
                <p className="text-3xl font-black font-mono tabular-nums text-[#B83030] dark:text-rose-400">
                  {fmtNum(resultado.tributo_atual_total)}
                </p>
                <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-between">
                  <span className="text-[10px] text-[#94A3B8] dark:text-slate-600">Carga tributária</span>
                  <span className="text-xs font-bold font-mono text-[#B83030] dark:text-rose-400">{fmtPctNum(resultado.carga_atual_pct)}</span>
                </div>
              </div>
            </div>

            {/* Reforma */}
            <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">
              <div className="h-1 w-full bg-[#1E4976]" />
              <div className="p-5">
                <p className="text-[10px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-1">Reforma Tributária</p>
                <p className="text-xs text-[#64748B] dark:text-slate-500 mb-3 font-medium">IBS + CBS estimado</p>
                <p className="text-3xl font-black font-mono tabular-nums text-[#1E4976] dark:text-blue-400">
                  {fmtNum(resultado.tributo_reforma_total)}
                </p>
                <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-between">
                  <span className="text-[10px] text-[#94A3B8] dark:text-slate-600">Carga estimada</span>
                  <span className="text-xs font-bold font-mono text-[#1E4976] dark:text-blue-400">{fmtPctNum(resultado.carga_reforma_pct)}</span>
                </div>
              </div>
            </div>

            {/* Impacto líquido */}
            <div className={`rounded-2xl overflow-hidden border ${
              economia
                ? "bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-500/25"
                : "bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-500/25"
            }`}>
              <div className={`h-1 w-full ${economia ? "bg-[#1A6B3C]" : "bg-[#92400E]"}`} />
              <div className="p-5">
                <p className="text-[10px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-1">Impacto Líquido</p>
                <p className={`text-xs font-medium mb-3 ${economia ? "text-emerald-700 dark:text-emerald-400" : "text-amber-700 dark:text-amber-400"}`}>
                  {economia ? "Economia estimada" : "Aumento estimado"}
                </p>
                <p className={`text-3xl font-black font-mono tabular-nums ${economia ? "text-[#1A6B3C] dark:text-emerald-400" : "text-[#92400E] dark:text-amber-400"}`}>
                  {impactoLiquido !== null
                    ? `${impactoLiquido >= 0 ? "+" : ""}${fmt(impactoLiquido)}`
                    : "—"}
                </p>
                {resultado.credito_ibs_cbs != null && (
                  <div className="mt-3 pt-3 border-t border-current/10 flex items-center justify-between">
                    <span className="text-[10px] text-[#94A3B8] dark:text-slate-600">Crédito IBS/CBS</span>
                    <span className={`text-xs font-bold font-mono ${economia ? "text-[#1A6B3C] dark:text-emerald-400" : "text-[#92400E] dark:text-amber-400"}`}>
                      {fmtNum(resultado.credito_ibs_cbs)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Comparativo visual + tabela de variação */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

            {/* Gráfico de barras */}
            <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-5">
              <div className="flex items-center gap-2.5 mb-4 pb-2.5 border-b border-slate-100 dark:border-slate-700/60">
                <div className="w-0.5 h-5 rounded-full bg-[#1E4976] flex-shrink-0" />
                <h3 className="text-[11px] font-black uppercase tracking-widest text-[#64748B] dark:text-slate-400">Comparativo Visual</h3>
              </div>
              <GraficoComNome>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart
                    data={[
                      { name: "Regime Atual", valor: resultado.tributo_atual_total as number ?? 0 },
                      { name: "IBS + CBS", valor: resultado.tributo_reforma_total as number ?? 0 },
                    ]}
                    margin={{ top: 10, right: 16, left: 8, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
                    <XAxis dataKey="name" tick={{ fill: ct.tickFill, fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: ct.tickFill, fontSize: 10 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={ct.tooltipStyle}
                      labelStyle={ct.tooltipLabelStyle}
                      itemStyle={ct.tooltipItemStyle}
                      formatter={(v) => fmt(v as number)}
                    />
                    <Bar dataKey="valor" name="Tributos" radius={[6, 6, 0, 0]} maxBarSize={72}>
                      <Cell fill="#B83030" />
                      <Cell fill="#1E4976" />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </GraficoComNome>
            </div>

            {/* Tabela de comparação de carga */}
            <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">
              <div className="px-5 pt-5 pb-4 border-b border-slate-100 dark:border-slate-700/60 flex items-center gap-2.5">
                <div className="w-0.5 h-5 rounded-full bg-[#92400E] flex-shrink-0" />
                <h3 className="text-[11px] font-black uppercase tracking-widest text-[#64748B] dark:text-slate-400">Análise de Carga</h3>
              </div>
              <div className="px-5 py-4 space-y-3">
                {[
                  { label: "Tributos atuais", value: resultado.tributo_atual_total, cor: "#B83030" },
                  { label: "Tributos na reforma", value: resultado.tributo_reforma_total, cor: "#1E4976" },
                  { label: "Crédito aproveitado (IBS/CBS)", value: resultado.credito_ibs_cbs, cor: "#1A6B3C" },
                ].map(({ label, value, cor }) => typeof value === "number" && (
                  <div key={label} className="flex items-center justify-between py-2.5 border-b border-slate-100 dark:border-slate-700/60 last:border-0">
                    <div className="flex items-center gap-2.5">
                      <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: cor }} />
                      <span className="text-sm text-[#475569] dark:text-slate-400">{label}</span>
                    </div>
                    <span className="text-sm font-mono font-bold tabular-nums" style={{ color: cor }}>{fmt(value)}</span>
                  </div>
                ))}

                {/* Carga percentual comparison */}
                <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-700">
                  <p className="text-[9px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-3">Variação da carga</p>
                  {(() => {
                    const atual = typeof resultado.carga_atual_pct === "number" ? resultado.carga_atual_pct : null;
                    const reform = typeof resultado.carga_reforma_pct === "number" ? resultado.carga_reforma_pct : null;
                    const diff = atual !== null && reform !== null ? reform - atual : null;
                    return (
                      <div className="flex items-center gap-4">
                        <div className="flex-1 text-center bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 rounded-xl p-3">
                          <p className="text-[9px] font-bold uppercase text-[#94A3B8] dark:text-slate-600 mb-1">Atual</p>
                          <p className="text-lg font-black font-mono text-[#B83030] dark:text-rose-400">{atual !== null ? `${atual.toFixed(2)}%` : "—"}</p>
                        </div>
                        <div className={`text-center font-black text-lg ${diff !== null && diff < 0 ? "text-[#1A6B3C] dark:text-emerald-400" : "text-[#92400E] dark:text-amber-400"}`}>
                          {diff !== null ? (diff >= 0 ? "▲" : "▼") : "→"}
                        </div>
                        <div className="flex-1 text-center bg-blue-50 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/20 rounded-xl p-3">
                          <p className="text-[9px] font-bold uppercase text-[#94A3B8] dark:text-slate-600 mb-1">Reforma</p>
                          <p className="text-lg font-black font-mono text-[#1E4976] dark:text-blue-400">{reform !== null ? `${reform.toFixed(2)}%` : "—"}</p>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            </div>
          </div>

          {/* Disclaimer */}
          <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-800/30 border border-slate-200 dark:border-slate-700/60">
            <svg className="w-4 h-4 text-[#94A3B8] dark:text-slate-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-[11px] text-[#64748B] dark:text-slate-500 leading-relaxed">
              Estimativa baseada nas alíquotas divulgadas até 2025. A reforma está em período de transição gradual até 2033. Os valores reais dependem das alíquotas definitivas fixadas por lei complementar e dos créditos específicos aplicáveis ao setor.
            </p>
          </div>
        </div>
      )}

      {/* ── Referência de alíquotas por regime ── */}
      <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">
        <div className="px-5 pt-5 pb-4 border-b border-slate-100 dark:border-slate-700/60 flex items-center gap-2.5">
          <div className="w-0.5 h-5 rounded-full bg-[#64748B] flex-shrink-0" />
          <h3 className="text-[11px] font-black uppercase tracking-widest text-[#64748B] dark:text-slate-400">
            Referência: Alíquotas por Regime
          </h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-slate-100 dark:divide-slate-700/60">
          {REGIME_ALIQUOTAS.map(({ regime, cor, tributos }) => (
            <div key={regime} className="p-5">
              <div className="flex items-center gap-2 mb-3">
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: cor }} />
                <p className="text-xs font-bold text-[#0F172A] dark:text-slate-200">{regime}</p>
              </div>
              <div className="space-y-2">
                {tributos.map(({ nome, atual, obs }) => (
                  <div key={nome} className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-[10px] font-semibold text-[#475569] dark:text-slate-400 truncate">{nome}</p>
                      <p className="text-[9px] text-[#94A3B8] dark:text-slate-600">{obs}</p>
                    </div>
                    <span className="text-[10px] font-black font-mono tabular-nums flex-shrink-0" style={{ color: cor }}>{atual}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
