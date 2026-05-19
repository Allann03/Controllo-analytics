"use client";

import GraficoComNome from "@/components/GraficoComNome";
import { useChartTheme } from "@/components/useChartTheme";
import { CheckCircle2, AlertTriangle, AlertCircle } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, ReferenceLine,
} from "recharts";

const fmt = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v);
const fmtPct = (v: number) => `${Number(v).toFixed(2)}%`;

export default function AbaCarga({ dados }: { dados: Record<string, unknown> | null }) {
  const ct = useChartTheme();

  // Chart tokens semanticos (§5.6)
  const chartC1 = ct.isLight ? "#3B82F6" : "#4F8EFF"; // azul — IR+CSLL / receita
  const chartC2 = ct.isLight ? "#059669" : "#34D399"; // verde — receita liquida
  const chartC3 = ct.isLight ? "#DC2626" : "#F87171"; // vermelho — impostos / despesa

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

  // Donut: Impostos s/ Receita = chart-3, IR+CSLL = chart-1, Receita Liquida = chart-2
  const pieData = [
    { name: "Impostos s/ Receita", value: Math.abs(kpis.deducoes_receita ?? 0), color: chartC3 },
    { name: "IR + CSLL",           value: Math.abs(kpis.ir_csll ?? 0),         color: chartC1 },
    { name: "Receita Líquida",     value: Math.abs(kpis.receita_liquida ?? 0), color: chartC2 },
  ].filter((d) => d.value > 0);

  const carga = kpis.carga_tributaria ?? 0;
  // Status semantico: usa tokens em vez de hex hardcoded
  const cargaStatus = carga <= 15 ? "ideal" : carga <= 25 ? "atencao" : "risco";
  const cargaSemantic = {
    ideal:    { borderLeft: "var(--success)", pillBg: "var(--success-subtle)", pillBorder: "var(--success-border)", pillText: "var(--success)", label: "Saudável" },
    atencao:  { borderLeft: "var(--warning)", pillBg: "var(--warning-subtle)", pillBorder: "var(--warning-border)", pillText: "var(--warning)", label: "Atenção" },
    risco:    { borderLeft: "var(--danger)",  pillBg: "var(--danger-subtle)",  pillBorder: "var(--danger-border)",  pillText: "var(--danger)",  label: "Alta" },
  }[cargaStatus];

  // Variação vs mês anterior (se houver histórico)
  const histArr = (dados.historico as Record<string, unknown>[]) ?? [];
  const prevCarga = histArr.length >= 2 ? (histArr[histArr.length - 2] as Record<string, number>).carga_tributaria : null;
  const varCarga = prevCarga != null ? carga - prevCarga : null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-0 divide-y lg:divide-y-0 lg:divide-x divide-slate-200 dark:divide-slate-700/40">

      {/* KPIs tributários */}
      <div className="lg:col-span-1 space-y-5 p-6">
        {/* Carga Tributária Total */}
        <div
          className="rounded-2xl p-5"
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderLeft: `3px solid ${cargaSemantic.borderLeft}`,
          }}
        >
          <div className="flex items-start justify-between mb-2 gap-2">
            <p
              className="text-xs uppercase font-medium"
              style={{
                color: "var(--text-tertiary)",
                letterSpacing: "var(--tracking-widest)",
              }}
            >
              Carga Tributária Total
            </p>
            <span
              className="text-xs font-semibold px-2 py-0.5 flex-shrink-0"
              style={{
                background: cargaSemantic.pillBg,
                border: `1px solid ${cargaSemantic.pillBorder}`,
                color: cargaSemantic.pillText,
                borderRadius: "var(--radius-md)",
              }}
            >
              {cargaSemantic.label}
            </span>
          </div>
          <p className="text-4xl font-mono font-semibold tabular-nums leading-none" style={{ color: "var(--text-primary)" }}>
            {fmtPct(carga)}
          </p>
          <div className="flex items-center justify-between mt-2.5">
            <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>sobre receita bruta</p>
            {varCarga !== null && (
              <span
                className="text-xs font-medium"
                style={{ color: varCarga > 0 ? "var(--danger)" : "var(--success)" }}
              >
                {varCarga > 0 ? "▲" : "▼"} {Math.abs(varCarga).toFixed(1)}pp vs anterior
              </span>
            )}
          </div>
          {/* Benchmark bar — gradiente sutil de cinza, marcador colorido apenas no ponto atual */}
          <div className="mt-4">
            <div
              className="h-1.5 rounded-full overflow-hidden relative"
              style={{ background: "var(--bg-inset)" }}
            >
              {/* Marker do valor atual */}
              <div
                className="absolute top-1/2 w-0.5 h-3"
                style={{
                  left: `${Math.min(100, (carga / 40) * 100)}%`,
                  transform: "translate(-50%, -50%)",
                  background: cargaSemantic.borderLeft,
                  borderRadius: 1,
                }}
              />
            </div>
            {/* Escala discreta */}
            <div className="flex justify-between mt-1">
              <span className="text-[10px] font-mono tabular-nums" style={{ color: "var(--text-tertiary)" }}>0%</span>
              <span className="text-[10px] font-mono tabular-nums" style={{ color: "var(--text-tertiary)" }}>≤15% Saudável</span>
              <span className="text-[10px] font-mono tabular-nums" style={{ color: "var(--text-tertiary)" }}>25% Atenção</span>
              <span className="text-[10px] font-mono tabular-nums" style={{ color: "var(--text-tertiary)" }}>40%</span>
            </div>
          </div>
        </div>

        {/* Resumo Tributário */}
        <div
          className="rounded-2xl p-5"
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <p
            className="text-xs uppercase font-medium mb-3"
            style={{
              color: "var(--text-tertiary)",
              letterSpacing: "var(--tracking-widest)",
            }}
          >
            Resumo Tributário
          </p>
          {[
            { label: "Receita Bruta",        value: fmt(kpis.receita_bruta ?? 0),    dest: true,  isTotal: false },
            { label: "Impostos s/ Receita",  value: fmt(kpis.deducoes_receita ?? 0), neg: true,   isTotal: false },
            { label: "Receita Líquida",      value: fmt(kpis.receita_liquida ?? 0),               isTotal: false },
            { label: "IR + CSLL",            value: fmt(kpis.ir_csll ?? 0),          neg: true,   isTotal: false },
            { label: "Total de Tributos",    value: fmt(kpis.total_tributos ?? 0),                isTotal: true  },
          ].map(({ label, value, neg, dest, isTotal }) => (
            <div
              key={label}
              className="flex justify-between items-center py-2.5"
              style={{
                borderBottom: "1px solid var(--border-subtle)",
                borderTop: isTotal ? "2px solid var(--border-default)" : undefined,
                marginTop: isTotal ? "0.25rem" : undefined,
                paddingTop: isTotal ? "0.75rem" : undefined,
              }}
            >
              <span
                className={`text-sm ${dest || isTotal ? "font-semibold" : ""}`}
                style={{ color: dest || isTotal ? "var(--text-primary)" : "var(--text-secondary)" }}
              >
                {label}
              </span>
              <span
                className={`text-sm font-mono tabular-nums text-right ${dest || isTotal ? "font-semibold" : ""}`}
                style={{
                  color: neg ? "var(--danger)" : dest || isTotal ? "var(--text-primary)" : "var(--text-secondary)",
                }}
              >
                {value}
              </span>
            </div>
          ))}
        </div>

        {/* Composição da Receita */}
        {pieData.length > 0 && (
          <GraficoComNome>
          <div
            className="rounded-2xl p-5"
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <p
              className="text-xs uppercase font-medium mb-3"
              style={{
                color: "var(--text-tertiary)",
                letterSpacing: "var(--tracking-widest)",
              }}
            >
              Composição da Receita
            </p>
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={60}>
                  {pieData.map((d, i) => <Cell key={i} fill={d.color} />)}
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
            <div
              className="rounded-2xl p-5"
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <p
                className="text-xs uppercase font-medium mb-4"
                style={{
                  color: "var(--text-tertiary)",
                  letterSpacing: "var(--tracking-widest)",
                }}
              >
                Evolução da Carga Tributária (%)
              </p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={hist.slice(-12)}>
                  <defs>
                    <linearGradient id="cargaGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%"   stopColor={chartC1} stopOpacity={1.0} />
                      <stop offset="100%" stopColor={chartC1} stopOpacity={0.55} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} strokeOpacity={0.08} />
                  <XAxis dataKey="mes_label" tick={{ fill: ct.tickFill, fontSize: 11 }} />
                  <YAxis tick={{ fill: ct.tickFill, fontSize: 11 }} tickFormatter={(v) => `${v.toFixed(0)}%`} />
                  <Tooltip
                    contentStyle={ct.tooltipStyle}
                    formatter={(v) => `${(v as number).toFixed(1)}%`}
                    labelStyle={ct.tooltipLabelStyle}
                    itemStyle={ct.tooltipItemStyle}
                  />
                  <ReferenceLine
                    y={15}
                    stroke={ct.tickFill}
                    strokeDasharray="4 4"
                    strokeWidth={1}
                    strokeOpacity={0.5}
                    label={{ value: "Benchmark 15%", position: "right", fill: ct.tickFill, fontSize: 10, fontWeight: 500 }}
                  />
                  <Bar dataKey="carga_tributaria" name="Carga Tributária %" fill="url(#cargaGrad)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            </GraficoComNome>

            <GraficoComNome>
            <div
              className="rounded-2xl p-5"
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <p
                className="text-xs uppercase font-medium mb-4"
                style={{
                  color: "var(--text-tertiary)",
                  letterSpacing: "var(--tracking-widest)",
                }}
              >
                Total de Tributos (R$)
              </p>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={hist.slice(-12)} barGap={3}>
                  <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} strokeOpacity={0.08} />
                  <XAxis dataKey="mes_label" tick={{ fill: ct.tickFill, fontSize: 11 }} />
                  <YAxis tick={{ fill: ct.tickFill, fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <Tooltip contentStyle={ct.tooltipStyle} formatter={(v) => fmt(v as number)} labelStyle={ct.tooltipLabelStyle} itemStyle={ct.tooltipItemStyle} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="deducoes_receita" name="Impostos s/ Receita" fill={chartC3} radius={[3, 3, 0, 0]} stackId="a" />
                  <Bar dataKey="ir_csll"          name="IR + CSLL"          fill={chartC1} radius={[3, 3, 0, 0]} stackId="a" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            </GraficoComNome>
          </>
        )}
        {hist.length <= 1 && (
          <div
            className="flex flex-col items-center justify-center h-40 gap-3 rounded-2xl"
            style={{
              border: "1px dashed var(--border-default)",
              background: "var(--bg-inset)",
            }}
          >
            <svg className="w-8 h-8 opacity-30" style={{ color: "var(--text-tertiary)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>Dados históricos insuficientes para gráficos.</p>
            <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>Importe dados de pelo menos 2 períodos para visualizar a evolução.</p>
          </div>
        )}

        {/* Alertas tributários */}
        <div
          className="rounded-2xl p-5"
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <p
            className="text-xs uppercase font-medium mb-3"
            style={{
              color: "var(--text-tertiary)",
              letterSpacing: "var(--tracking-widest)",
            }}
          >
            Alertas Tributários
          </p>
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

              return alertas.map((a, i) => {
                const cfg = {
                  ok:      { Icon: CheckCircle2, bg: "var(--success-subtle)", border: "var(--success-border)", color: "var(--success)" },
                  atencao: { Icon: AlertTriangle, bg: "var(--warning-subtle)", border: "var(--warning-border)", color: "var(--warning)" },
                  risco:   { Icon: AlertCircle,   bg: "var(--danger-subtle)",  border: "var(--danger-border)",  color: "var(--danger)"  },
                }[a.tipo];
                const { Icon } = cfg;
                return (
                  <div
                    key={i}
                    className="flex items-start gap-2 px-3 py-2 rounded-lg text-xs"
                    style={{
                      background: cfg.bg,
                      border: `1px solid ${cfg.border}`,
                      color: cfg.color,
                    }}
                  >
                    <Icon size={14} strokeWidth={2} style={{ flexShrink: 0, marginTop: 1 }} />
                    <span>{a.msg}</span>
                  </div>
                );
              });
            })()}
          </div>
        </div>
      </div>
    </div>
  );
}
