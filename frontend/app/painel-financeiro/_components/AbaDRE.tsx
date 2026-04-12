"use client";

import GraficoComNome from "@/components/GraficoComNome";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell,
} from "recharts";
import { useChartTheme } from "@/components/useChartTheme";
import { fmt, fmtPct, n, SectionTitle, InsightsList, COR_POSITIVO, COR_NEGATIVO } from "./shared";
import type { DREResponse, HistoricoItem, MetricaFlat } from "./shared";

// Cores distintas para cada categoria de despesa
const DESP_COLORS = ["#1E4976", "#B83030", "#92400E", "#3b6ea5", "#64748B"];

// ── DRERow — inline MoM variation next to value ─────────────────────
function DRERow({ label, value, metricKey, m, ant }: { label: string; value: string; metricKey?: string; m: MetricaFlat; ant: MetricaFlat }) {
  const variacao = (() => {
    if (!metricKey) return null;
    const atual = n(m[metricKey]);
    const prev = n(ant[metricKey]);
    if (!prev || !atual) return null;
    const pct = ((atual - prev) / Math.abs(prev)) * 100;
    return pct;
  })();

  return (
    <div className="flex items-center justify-between py-2.5 last:border-0" style={{ borderBottom: "1px solid var(--border)" }}>
      <span className="text-sm" style={{ color: "var(--text-secondary)" }}>{label}</span>
      <div className="flex items-center gap-2">
        <span className="font-mono tabular-nums text-sm" style={{ color: "var(--text-secondary)" }}>{value}</span>
        {variacao !== null && (
          <span className={`text-[10px] font-semibold ${variacao > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
            {variacao > 0 ? "▲" : "▼"}{Math.abs(variacao).toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  );
}

// ── DRESubtotalRow — highlighted subtotal with inline variation ──────
function DRESubtotalRow({ label, value, metricKey, m, ant }: { label: string; value: string; metricKey?: string; m: MetricaFlat; ant: MetricaFlat }) {
  const variacao = (() => {
    if (!metricKey) return null;
    const atual = n(m[metricKey]);
    const prev = n(ant[metricKey]);
    if (!prev || !atual) return null;
    const pct = ((atual - prev) / Math.abs(prev)) * 100;
    return pct;
  })();

  return (
    <div className="flex items-center justify-between py-2.5 last:border-0 font-bold mt-1" style={{ borderBottom: "1px solid var(--border)" }}>
      <span className="text-sm font-semibold tracking-wide uppercase text-[10px]" style={{ color: "var(--text-primary)" }}>{label}</span>
      <div className="flex items-center gap-2">
        <span className="font-mono tabular-nums text-sm font-bold" style={{ color: "var(--text-primary)" }}>{value}</span>
        {variacao !== null && (
          <span className={`text-[10px] font-semibold ${variacao > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
            {variacao > 0 ? "▲" : "▼"}{Math.abs(variacao).toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  );
}

export default function AbaDRE({
  dre,
  historico,
}: {
  dre: DREResponse;
  historico: HistoricoItem[];
}) {
  const ct = useChartTheme();
  const m = dre.metricas;
  const ant = dre.anterior ?? {};

  const dispDesp = [
    { name: "Custo Serv.", value: n(m.custo_servicos) },
    { name: "Desp. Adm.", value: n(m.despesas_adm) },
    { name: "Desp. Comerciais", value: n(m.despesas_comerciais) },
    { name: "Desp. Financeiras", value: n(m.despesas_financeiras) },
    { name: "Outras", value: n(m.outras_despesas) },
  ].filter((d) => d.value > 0);

  const hist12 = historico.slice(-12);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Tabela */}
      <div className="lg:col-span-1 bg-slate-800/40 border border-slate-700 rounded-2xl p-5">
        <SectionTitle>DRE — {dre.periodo}</SectionTitle>

        {/* Receita section */}
        <div className="border-l-2 border-emerald-500/40 pl-3 mb-2">
          <DRERow label="Receita Bruta" value={fmt(n(m.receita_bruta))} metricKey="receita_bruta" m={m} ant={ant} />
          <DRERow label="(–) Deduções" value={`(${fmt(n(m.deducoes_receita))})`} metricKey="deducoes_receita" m={m} ant={ant} />
        </div>
        <div className="rounded-lg px-2 -mx-2" style={{ background: "rgba(30,73,118,0.12)" }}>
          <DRESubtotalRow label="= Receita Líquida" value={fmt(n(m.receita_liquida))} metricKey="receita_liquida" m={m} ant={ant} />
        </div>

        {/* Custos / Lucro Bruto section */}
        <div className="border-l-2 border-amber-500/40 pl-3 mb-2 mt-2">
          <DRERow label="(–) Custo dos Serv." value={`(${fmt(n(m.custo_servicos))})`} metricKey="custo_servicos" m={m} ant={ant} />
        </div>
        <div className="rounded-lg px-2 -mx-2" style={{ background: "rgba(26,107,60,0.12)" }}>
          <DRESubtotalRow label="= Lucro Bruto" value={fmt(n(m.lucro_bruto))} metricKey="lucro_bruto" m={m} ant={ant} />
        </div>

        {/* Despesas section */}
        <div className="border-l-2 border-rose-500/40 pl-3 mb-2 mt-2">
          <DRERow label="(–) Desp. Adm." value={`(${fmt(n(m.despesas_adm))})`} metricKey="despesas_adm" m={m} ant={ant} />
          <DRERow label="(–) Desp. Comerciais" value={`(${fmt(n(m.despesas_comerciais))})`} metricKey="despesas_comerciais" m={m} ant={ant} />
          <DRERow label="(–) Outras Despesas" value={`(${fmt(n(m.outras_despesas))})`} metricKey="outras_despesas" m={m} ant={ant} />
          <DRERow label="(–) Deprec./Amortiz." value={`(${fmt(n(m.depreciacao_amortizacao))})`} metricKey="depreciacao_amortizacao" m={m} ant={ant} />
        </div>

        {/* Resultado section */}
        <div className="border-l-2 border-blue-500/40 pl-3 mb-2 mt-2">
          <div className="rounded-lg px-2 -mx-2" style={{ background: "rgba(30,73,118,0.12)" }}>
            <DRESubtotalRow label="= EBIT" value={fmt(n(m.ebit))} metricKey="ebit" m={m} ant={ant} />
          </div>
          <DRERow label="(–) Desp. Financeiras" value={`(${fmt(n(m.despesas_financeiras))})`} metricKey="despesas_financeiras" m={m} ant={ant} />
          <div className="rounded-lg px-2 -mx-2" style={{ background: "rgba(30,73,118,0.08)" }}>
            <DRESubtotalRow label="= LAIR" value={fmt(n(m.lair ?? m.ebit))} metricKey="lair" m={m} ant={ant} />
          </div>
          <DRERow label="(–) IR + CSLL" value={`(${fmt(n(m.ir_csll))})`} metricKey="ir_csll" m={m} ant={ant} />
          <div className="rounded-lg px-2 -mx-2" style={{ background: n(m.lucro_liquido) >= 0 ? "rgba(26,107,60,0.12)" : "rgba(184,48,48,0.10)" }}>
            <DRESubtotalRow label="= Lucro Líquido" value={fmt(n(m.lucro_liquido))} metricKey="lucro_liquido" m={m} ant={ant} />
          </div>
        </div>

        {/* Cards de Margens */}
        <div className="grid grid-cols-3 gap-2 mt-4 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
          {[
            { label: "Margem Bruta", value: n(m.margem_bruta), cor: COR_POSITIVO },
            { label: "Margem Líquida", value: n(m.margem_liquida), cor: n(m.margem_liquida) >= 0 ? COR_POSITIVO : COR_NEGATIVO },
            { label: "Carga Tribut.", value: n(m.carga_tributaria), cor: "#92400E" },
          ].map(item => (
            <div key={item.label} className="rounded-lg p-2 text-center" style={{ background: `${item.cor}12`, border: `1px solid ${item.cor}30` }}>
              <p className="text-[9px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{item.label}</p>
              <p className="text-sm font-black font-mono mt-0.5" style={{ color: item.cor }}>{fmtPct(item.value)}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Gráficos */}
      <div className="lg:col-span-2 space-y-5">
        {dispDesp.length > 0 && (
          <GraficoComNome>
          <div className="bg-slate-800/40 border border-slate-700 rounded-2xl p-5">
            <SectionTitle>Composição das Despesas</SectionTitle>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart layout="vertical" data={dispDesp} margin={{ left: 80 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} strokeOpacity={0.08} horizontal={false} />
                <XAxis type="number" tick={{ fill: ct.tickFill, fontSize: 11 }} tickFormatter={(v) => `${((v as number) / 1000).toFixed(0)}k`} />
                <YAxis type="category" dataKey="name" tick={{ fill: ct.tickFill, fontSize: 11 }} width={90} />
                <Tooltip contentStyle={ct.tooltipStyle} labelStyle={ct.tooltipLabelStyle} itemStyle={ct.tooltipItemStyle} formatter={(v) => fmt(v as number)} />
                <Bar dataKey="value" name="Valor" radius={[0, 3, 3, 0]}>
                  {dispDesp.map((_, i) => (
                    <Cell key={i} fill={DESP_COLORS[i % DESP_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          </GraficoComNome>
        )}

        {hist12.length > 1 && (
          <GraficoComNome>
          <div className="bg-slate-800/40 border border-slate-700 rounded-2xl p-5">
            <SectionTitle>Evolução — Receita × Lucro (últimos 12 meses)</SectionTitle>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={hist12}>
                <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} strokeOpacity={0.08} />
                <XAxis dataKey="mes_label" tick={{ fill: ct.tickFill, fontSize: 11 }} />
                <YAxis tick={{ fill: ct.tickFill, fontSize: 11 }} tickFormatter={(v) => `${((v as number) / 1000).toFixed(0)}k`} />
                <Tooltip contentStyle={ct.tooltipStyle} labelStyle={ct.tooltipLabelStyle} itemStyle={ct.tooltipItemStyle} formatter={(v) => fmt(v as number)} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="receita_liquida" name="Receita Líquida" fill="#1E4976" radius={[3, 3, 0, 0]} />
                <Bar dataKey="lucro_liquido" name="Lucro Líquido" fill="#10b981" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          </GraficoComNome>
        )}

        <InsightsList insights={dre.insights?.filter((i) => ["R1","R2","R3","R4","R5"].includes(i.codigo)) ?? []} />
      </div>
    </div>
  );
}
