"use client";

import { useState, useRef } from "react";
import GraficoComNome from "@/components/GraficoComNome";
import { useChartTheme } from "@/components/useChartTheme";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
} from "recharts";

// ──────────────────────────────────────────────────────────────── //
//  Tipos                                                           //
// ──────────────────────────────────────────────────────────────── //
type Transacao = {
  data: string;
  banco: string;
  categoria: string;
  descricao: string;
  tipo: "entrada" | "saida";
  valor: number;
};

type ResultadoApi = {
  transacoes: Transacao[];
  resumo: { entradas: number; saidas: number; saldo: number };
};

type MesSazonal = {
  mes: string;
  receita_bruta: number;
  custos: number;
  despesas_operacionais: number;
  lucro_liquido: number;
  entradas_caixa: number;
  saidas_caixa: number;
};

type ResultadoSazonal = {
  tipo: "sazonal";
  empresa: string;
  ano: number;
  meses: MesSazonal[];
  totais: Record<string, number>;
  medias: Record<string, number>;
  pico_receita: string;
  vale_receita: string;
  margem_media: number;
};

type Modo = "padrao" | "sazonal";

// ──────────────────────────────────────────────────────────────── //
//  Helpers                                                         //
// ──────────────────────────────────────────────────────────────── //
const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");
const authHeader = (): HeadersInit => {
  const tok = typeof window !== "undefined" ? localStorage.getItem("controllo_token") : null;
  return tok ? { Authorization: `Bearer ${tok}` } : {};
};

const fmt = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v);

const CORES_CATEGORIAS = [
  "#8b5cf6","#3b82f6","#10b981","#f59e0b","#ef4444",
  "#ec4899","#14b8a6","#f43f5e","#a78bfa","#34d399",
];

// ──────────────────────────────────────────────────────────────── //
//  Sub-componentes — Dashboard Sazonal                            //
// ──────────────────────────────────────────────────────────────── //
function DashboardSazonal({
  dados,
  onNovo,
}: {
  dados: ResultadoSazonal;
  onNovo: () => void;
}) {
  const ct = useChartTheme();
  const kpis = [
    {
      label: "Receita Bruta Anual",
      valor: fmt(dados.totais.receita_bruta),
      cor: "text-emerald-400",
      icon: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
    },
    {
      label: "Lucro Líquido Anual",
      valor: fmt(dados.totais.lucro_liquido),
      cor: dados.totais.lucro_liquido >= 0 ? "text-blue-400" : "text-red-400",
      icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
    },
    {
      label: "Margem Média",
      valor: `${dados.margem_media.toFixed(1)}%`,
      cor: dados.margem_media >= 15 ? "text-emerald-400" : dados.margem_media >= 5 ? "text-amber-400" : "text-red-400",
      icon: "M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z",
    },
    {
      label: "Mês de Pico",
      valor: dados.pico_receita,
      cor: "text-purple-400",
      icon: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6",
    },
  ];

  const chartBarras = dados.meses.map((m) => ({
    mes: m.mes.slice(0, 3),
    Receita: m.receita_bruta,
    Lucro: m.lucro_liquido,
    Custos: m.custos + m.despesas_operacionais,
  }));

  const chartCaixa = dados.meses.map((m) => ({
    mes: m.mes.slice(0, 3),
    Entradas: m.entradas_caixa,
    Saídas: m.saidas_caixa,
    Saldo: m.entradas_caixa - m.saidas_caixa,
  }));

  return (
    <div className="p-6 flex flex-col items-center w-full min-h-screen">
      {/* Header */}
      <div className="w-full max-w-7xl mb-8 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
            <svg className="w-8 h-8 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            Dashboard Sazonal — {dados.empresa}
          </h1>
          <p className="text-slate-400 mt-1">Análise anual {dados.ano} · {dados.meses.length} meses</p>
        </div>
        <button
          onClick={onNovo}
          className="border border-slate-700 hover:bg-slate-800 text-slate-300 px-5 py-2.5 rounded-lg font-medium transition-colors"
        >
          Novo Dashboard
        </button>
      </div>

      {/* KPIs */}
      <div className="w-full max-w-7xl grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {kpis.map((k, i) => (
          <div key={i} className="bg-slate-800/40 border border-slate-700/60 p-5 rounded-2xl shadow-xl">
            <div className="flex items-center gap-2 mb-2">
              <svg className={`w-4 h-4 ${k.cor}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={k.icon} />
              </svg>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{k.label}</p>
            </div>
            <p className={`text-2xl font-bold ${k.cor}`}>{k.valor}</p>
          </div>
        ))}
      </div>

      {/* Gráficos */}
      <div className="w-full max-w-7xl grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <GraficoComNome>
          <div className="bg-slate-800/40 border border-slate-700/60 rounded-2xl p-6 shadow-xl">
            <h2 className="text-lg font-semibold text-white mb-4">📊 Receita × Lucro × Custos</h2>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartBarras} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} vertical={false} />
                  <XAxis dataKey="mes" stroke={ct.tickFill} fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke={ct.tickFill} fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <Tooltip
                    contentStyle={ct.tooltipStyle} labelStyle={ct.tooltipLabelStyle} itemStyle={ct.tooltipItemStyle}
                    formatter={(v) => fmt(Number(v))}
                    cursor={{ fill: "#1e293b", opacity: 0.4 }}
                  />
                  <Legend iconType="circle" wrapperStyle={{ paddingTop: "12px" }} />
                  <Bar dataKey="Receita" fill="#10b981" radius={[3, 3, 0, 0]} maxBarSize={28} />
                  <Bar dataKey="Lucro"   fill="#3b82f6" radius={[3, 3, 0, 0]} maxBarSize={28} />
                  <Bar dataKey="Custos"  fill="#f43f5e" radius={[3, 3, 0, 0]} maxBarSize={28} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </GraficoComNome>

        <GraficoComNome>
          <div className="bg-slate-800/40 border border-slate-700/60 rounded-2xl p-6 shadow-xl">
            <h2 className="text-lg font-semibold text-white mb-4">💰 Fluxo de Caixa Mensal</h2>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartCaixa} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
                  <defs>
                    <linearGradient id="gradEntradas" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="gradSaidas" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#f43f5e" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} vertical={false} />
                  <XAxis dataKey="mes" stroke={ct.tickFill} fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke={ct.tickFill} fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <Tooltip
                    contentStyle={ct.tooltipStyle} labelStyle={ct.tooltipLabelStyle} itemStyle={ct.tooltipItemStyle}
                    formatter={(v) => fmt(Number(v))}
                    cursor={{ fill: "#1e293b", opacity: 0.4 }}
                  />
                  <Legend iconType="circle" wrapperStyle={{ paddingTop: "12px" }} />
                  <Area type="monotone" dataKey="Entradas" stroke="#10b981" fill="url(#gradEntradas)" strokeWidth={2} dot={false} />
                  <Area type="monotone" dataKey="Saídas"   stroke="#f43f5e" fill="url(#gradSaidas)"   strokeWidth={2} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </GraficoComNome>
      </div>

      {/* Tabela mensal */}
      <div className="w-full max-w-7xl bg-slate-800/40 border border-slate-700/60 rounded-2xl overflow-hidden shadow-xl mb-8">
        <div className="p-5 border-b border-slate-700/60 bg-slate-800/80">
          <h3 className="text-lg font-bold text-white">Detalhamento Mensal</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-900 sticky top-0 z-10">
              <tr className="text-slate-400 uppercase tracking-wider text-xs">
                <th className="text-left px-5 py-3 font-semibold">Mês</th>
                <th className="text-right px-5 py-3 font-semibold">Receita</th>
                <th className="text-right px-5 py-3 font-semibold">Custos</th>
                <th className="text-right px-5 py-3 font-semibold">Desp. Op.</th>
                <th className="text-right px-5 py-3 font-semibold">Lucro</th>
                <th className="text-right px-5 py-3 font-semibold">Margem</th>
                <th className="text-right px-5 py-3 font-semibold">Entradas Caixa</th>
                <th className="text-right px-5 py-3 font-semibold">Saídas Caixa</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {dados.meses.map((m, i) => {
                const margem = m.receita_bruta > 0 ? (m.lucro_liquido / m.receita_bruta) * 100 : 0;
                return (
                  <tr key={i} className="hover:bg-slate-700/30 transition-colors">
                    <td className="px-5 py-3 font-semibold text-slate-200">{m.mes}</td>
                    <td className="px-5 py-3 text-right text-emerald-400">{fmt(m.receita_bruta)}</td>
                    <td className="px-5 py-3 text-right text-red-400">{fmt(m.custos)}</td>
                    <td className="px-5 py-3 text-right text-amber-400">{fmt(m.despesas_operacionais)}</td>
                    <td className={`px-5 py-3 text-right font-medium ${m.lucro_liquido >= 0 ? "text-blue-400" : "text-red-400"}`}>{fmt(m.lucro_liquido)}</td>
                    <td className={`px-5 py-3 text-right text-xs font-semibold ${margem >= 15 ? "text-emerald-400" : margem >= 5 ? "text-amber-400" : "text-red-400"}`}>{margem.toFixed(1)}%</td>
                    <td className="px-5 py-3 text-right text-slate-300">{fmt(m.entradas_caixa)}</td>
                    <td className="px-5 py-3 text-right text-slate-400">{fmt(m.saidas_caixa)}</td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot className="bg-slate-900/60 border-t-2 border-slate-600">
              <tr className="text-xs font-bold text-slate-300 uppercase">
                <td className="px-5 py-3">TOTAL ANUAL</td>
                <td className="px-5 py-3 text-right text-emerald-400">{fmt(dados.totais.receita_bruta)}</td>
                <td className="px-5 py-3 text-right text-red-400">{fmt(dados.totais.custos)}</td>
                <td className="px-5 py-3 text-right text-amber-400">{fmt(dados.totais.despesas_operacionais)}</td>
                <td className={`px-5 py-3 text-right ${dados.totais.lucro_liquido >= 0 ? "text-blue-400" : "text-red-400"}`}>{fmt(dados.totais.lucro_liquido)}</td>
                <td className={`px-5 py-3 text-right ${dados.margem_media >= 15 ? "text-emerald-400" : dados.margem_media >= 5 ? "text-amber-400" : "text-red-400"}`}>{dados.margem_media.toFixed(1)}%</td>
                <td className="px-5 py-3 text-right text-slate-300">{fmt(dados.totais.entradas_caixa)}</td>
                <td className="px-5 py-3 text-right text-slate-400">{fmt(dados.totais.saidas_caixa)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────── //
//  Tela de upload — Modo Sazonal                                  //
// ──────────────────────────────────────────────────────────────── //
function UploadSazonal({ onVoltar }: { onVoltar: () => void }) {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");
  const [resultado, setResultado] = useState<ResultadoSazonal | null>(null);

  const baixarModelo = async (demo: boolean) => {
    try {
      const resp = await fetch(`${API}/api/dashboard/template?demo=${demo}`, {
        headers: authHeader(),
      });
      if (!resp.ok) throw new Error("Falha ao gerar modelo.");
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = demo ? "Controllo_Dashboard_Demo.xlsx" : "Controllo_Dashboard_Modelo.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setErro("Não foi possível baixar o modelo. Tente novamente.");
    }
  };

  const processar = async () => {
    if (!arquivo) return;
    setLoading(true);
    setErro("");
    try {
      const fd = new FormData();
      fd.append("arquivo", arquivo);
      const resp = await fetch(`${API}/api/dashboard/upload-template`, {
        method: "POST",
        headers: authHeader(),
        body: fd,
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Erro ao processar planilha.");
      setResultado(data as ResultadoSazonal);
    } catch (e: unknown) {
      setErro(e instanceof Error ? e.message : "Erro desconhecido.");
    } finally {
      setLoading(false);
    }
  };

  if (resultado) {
    return <DashboardSazonal dados={resultado} onNovo={() => setResultado(null)} />;
  }

  return (
    <div className="p-6 flex flex-col items-center w-full min-h-screen">
      <div className="w-full max-w-3xl mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">
            Dashboard <span className="text-purple-400">Sazonal</span>
          </h1>
          <p className="text-slate-400 mt-1">Baixe o modelo, preencha com seus dados e envie para gerar o dashboard.</p>
        </div>
        <button
          onClick={onVoltar}
          className="border border-slate-700 hover:bg-slate-800 text-slate-300 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          ← Voltar
        </button>
      </div>

      {/* Baixar modelos */}
      <div className="w-full max-w-3xl grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <button
          onClick={() => baixarModelo(false)}
          className="flex items-start gap-4 p-5 bg-slate-800/60 border border-slate-700 hover:border-blue-700/50 rounded-2xl transition-colors text-left"
        >
          <div className="p-2.5 bg-blue-900/20 rounded-xl flex-shrink-0">
            <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <p className="text-white font-semibold">Baixar Modelo em Branco</p>
            <p className="text-slate-400 text-xs mt-1">Planilha para preenchimento com os dados reais da sua empresa.</p>
          </div>
        </button>

        <button
          onClick={() => baixarModelo(true)}
          className="flex items-start gap-4 p-5 bg-slate-800/60 border border-slate-700 hover:border-emerald-500/50 rounded-2xl transition-colors text-left"
        >
          <div className="p-2.5 bg-emerald-500/10 rounded-xl flex-shrink-0">
            <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
            </svg>
          </div>
          <div>
            <p className="text-white font-semibold">Baixar Modelo com Demonstração</p>
            <p className="text-slate-400 text-xs mt-1">Pré-preenchido com dados fictícios para apresentação.</p>
          </div>
        </button>
      </div>

      {/* Upload */}
      <div className="w-full max-w-3xl bg-slate-800/40 border border-slate-700/60 rounded-2xl p-8">
        <h3 className="text-white font-semibold mb-4">Enviar Planilha Preenchida</h3>

        {erro && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/40 rounded-xl text-red-400 text-sm flex items-center gap-2">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {erro}
          </div>
        )}

        <label className="block w-full border-2 border-dashed border-slate-600 hover:border-blue-700/60 rounded-2xl p-10 text-center cursor-pointer transition-colors">
          <svg className="w-12 h-12 text-slate-500 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          {arquivo ? (
            <p className="text-white font-medium">{arquivo.name}</p>
          ) : (
            <p className="text-slate-400">Clique para selecionar a planilha preenchida (.xlsx)</p>
          )}
          <input
            type="file"
            accept=".xlsx"
            className="hidden"
            onChange={(e) => { if (e.target.files?.[0]) setArquivo(e.target.files[0]); }}
          />
        </label>

        <div className="mt-5 flex justify-end">
          <button
            onClick={processar}
            disabled={!arquivo || loading}
            className="bg-blue-900 hover:bg-blue-950 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-3 rounded-xl font-bold transition-colors flex items-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Processando...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Gerar Dashboard
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────── //
//  Página principal                                               //
// ──────────────────────────────────────────────────────────────── //
export default function DashboardPage() {
  const ct = useChartTheme();
  const [modo, setModo] = useState<Modo>("padrao");
  const dashboardRef = useRef<HTMLDivElement>(null);

  // Estado do dashboard padrão
  const [arquivos, setArquivos] = useState<File[]>([]);
  const [loading, setLoading]   = useState(false);
  const [resultado, setResultado] = useState<ResultadoApi | null>(null);
  const [erro, setErro]         = useState("");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) setArquivos((p) => [...p, ...Array.from(e.target.files!)]);
    e.target.value = "";
  };

  const removerArquivo = (idx: number) =>
    setArquivos((p) => p.filter((_, i) => i !== idx));

  const gerarBI = async () => {
    if (arquivos.length === 0) return;
    setLoading(true);
    setErro("");
    try {
      const excelFiles = arquivos.filter((f) => f.name.toLowerCase().endsWith(".xlsx"));
      const pdfFiles   = arquivos.filter((f) => f.name.toLowerCase().endsWith(".pdf"));
      let todasTransacoes: Transacao[] = [];

      if (excelFiles.length > 0) {
        const fd = new FormData();
        excelFiles.forEach((f) => fd.append("files", f));
        const resp = await fetch(`${API}/api/processar-excel`, { method: "POST", headers: authHeader(), body: fd });
        if (!resp.ok) throw new Error("Falha ao processar planilha Excel.");
        const dados = await resp.json();
        if (dados.erro) throw new Error(dados.erro);
        todasTransacoes = [...todasTransacoes, ...(dados.transacoes || [])];
      }

      for (const pdf of pdfFiles) {
        const fd = new FormData();
        fd.append("arquivo", pdf);
        fd.append("banco", "");
        const resp = await fetch(`${API}/api/processar-extrato`, { method: "POST", headers: authHeader(), body: fd });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(err.detail || `Falha ao processar ${pdf.name}.`);
        }
        const dados = await resp.json();
        if (dados.transacoes?.length) todasTransacoes = [...todasTransacoes, ...dados.transacoes];
      }

      const entradas = todasTransacoes.filter((t) => t.tipo === "entrada").reduce((s, t) => s + t.valor, 0);
      const saidas   = todasTransacoes.filter((t) => t.tipo === "saida").reduce((s, t) => s + t.valor, 0);
      setResultado({ transacoes: todasTransacoes, resumo: { entradas, saidas, saldo: entradas - saidas } });
    } catch (e: unknown) {
      setErro(e instanceof Error ? e.message : "Erro desconhecido.");
    } finally {
      setLoading(false);
    }
  };

  const novaAnalise = () => { setArquivos([]); setResultado(null); setErro(""); };

  const exportarPNG = async () => {
    if (!dashboardRef.current) return;
    const { toPng } = await import("html-to-image");
    // Força tema light para a captura (fundo branco + textos escuros)
    const root = document.documentElement;
    const temaOriginal = root.className;
    root.className = root.className.replace("dark", "").trim() + " light";
    // Pequeno delay para o browser recomputar estilos
    await new Promise(r => setTimeout(r, 50));
    try {
      const url = await toPng(dashboardRef.current, { backgroundColor: "#ffffff", pixelRatio: 2 });
      const a = document.createElement("a"); a.href = url; a.download = "dashboard_controllo.png"; a.click();
    } finally {
      root.className = temaOriginal;
    }
  };

  const baixarCSV = () => {
    if (!resultado) return;
    const header = "Data,Banco,Categoria,Descrição,Tipo,Valor\n";
    const rows = resultado.transacoes
      .map((t) => `"${t.data}","${t.banco}","${t.categoria || ""}","${t.descricao.replace(/"/g, '""')}","${t.tipo}","${t.valor.toFixed(2)}"`)
      .join("\n");
    const blob = new Blob(["\uFEFF" + header + rows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "dashboard_controllo.csv"; a.click();
    URL.revokeObjectURL(url);
  };

  const processarDadosGrafico = () => {
    if (!resultado) return [];
    const dias: Record<string, { data: string; Entradas: number; Saídas: number }> = {};
    resultado.transacoes.forEach((t) => {
      const d = t.data.substring(0, 5);
      if (!dias[d]) dias[d] = { data: d, Entradas: 0, Saídas: 0 };
      if (t.tipo === "entrada") dias[d].Entradas += t.valor;
      else dias[d].Saídas += t.valor;
    });
    return Object.values(dias);
  };

  const processarCategorias = () => {
    if (!resultado) return [];
    const cats: Record<string, number> = {};
    resultado.transacoes.forEach((t) => {
      if (t.tipo === "saida") {
        const c = t.categoria || "Outras Despesas";
        cats[c] = (cats[c] || 0) + t.valor;
      }
    });
    return Object.entries(cats).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);
  };

  // ── Modo Sazonal ───────────────────────────────────────────────
  if (modo as string === "sazonal") {
    return <UploadSazonal onVoltar={() => setModo("padrao")} />;
  }

  // ── Dashboard Padrão — tela de resultados ─────────────────────
  if (resultado) {
    const dadosBarras     = processarDadosGrafico();
    const dadosCategorias = processarCategorias();

    return (
      <div ref={dashboardRef} className="p-8 flex flex-col items-center w-full min-h-screen">
        <div className="w-full max-w-7xl mb-8 flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
              <svg className="w-8 h-8 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              Inteligência Consolidada
            </h1>
            <p className="text-slate-400 mt-1">
              Baseado em {arquivos.length} {arquivos.length === 1 ? "arquivo importado" : "arquivos importados"}.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={exportarPNG} className="border border-violet-700 hover:bg-violet-900/40 text-violet-400 px-5 py-2.5 rounded-lg font-medium transition-colors flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
              Exportar PNG
            </button>
            <button onClick={baixarCSV} className="border border-emerald-700 hover:bg-emerald-900/40 text-emerald-400 px-5 py-2.5 rounded-lg font-medium transition-colors flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
              Baixar CSV
            </button>
            <button onClick={novaAnalise} className="border border-slate-700 hover:bg-slate-800 text-slate-300 px-5 py-2.5 rounded-lg font-medium transition-colors">
              Nova Análise
            </button>
          </div>
        </div>

        <div className="w-full max-w-7xl grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {[
            { label: "Entradas Totais", valor: fmt(resultado.resumo.entradas), cor: "text-emerald-400" },
            { label: "Saídas Totais",   valor: fmt(resultado.resumo.saidas),   cor: "text-red-400" },
            { label: "Saldo do Período",valor: fmt(resultado.resumo.saldo),    cor: resultado.resumo.saldo >= 0 ? "text-blue-400" : "text-red-400" },
          ].map((c, i) => (
            <div key={i} className="bg-slate-800/40 border border-slate-700/60 p-6 rounded-2xl shadow-xl">
              <p className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">{c.label}</p>
              <p className={`text-3xl font-bold ${c.cor}`}>{c.valor}</p>
            </div>
          ))}
        </div>

        <div className="w-full max-w-7xl grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <GraficoComNome className="lg:col-span-2">
            <div className="bg-slate-800/40 border border-slate-700/60 rounded-2xl p-6 shadow-xl flex flex-col">
              <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">📊 Evolução de Fluxo de Caixa</h2>
              <div className="flex-1 min-h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dadosBarras} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} vertical={false} />
                    <XAxis dataKey="data" stroke={ct.tickFill} fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke={ct.tickFill} fontSize={12} tickLine={false} axisLine={false} tickFormatter={(v) => `R$${v}`} />
                    <Tooltip cursor={{ fill: "#1e293b", opacity: 0.4 }} contentStyle={ct.tooltipStyle} labelStyle={ct.tooltipLabelStyle} itemStyle={ct.tooltipItemStyle} formatter={(v) => fmt(Number(v))} />
                    <Legend iconType="circle" wrapperStyle={{ paddingTop: "20px" }} />
                    <Bar dataKey="Entradas" fill="#10b981" radius={[4, 4, 0, 0]} maxBarSize={40} />
                    <Bar dataKey="Saídas"   fill="#ef4444" radius={[4, 4, 0, 0]} maxBarSize={40} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </GraficoComNome>

          <GraficoComNome>
            <div className="bg-slate-800/40 border border-slate-700/60 rounded-2xl p-6 shadow-xl flex flex-col">
              <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">🎯 Despesas por Categoria</h2>
              <p className="text-xs text-slate-400 mb-4">Para onde o dinheiro está indo?</p>
              <div className="flex-1 min-h-[300px] w-full relative">
                {dadosCategorias.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={dadosCategorias} cx="50%" cy="45%" innerRadius={60} outerRadius={90} paddingAngle={5} dataKey="value" stroke="none">
                        {dadosCategorias.map((_e, idx) => (
                          <Cell key={idx} fill={CORES_CATEGORIAS[idx % CORES_CATEGORIAS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={ct.tooltipStyle} labelStyle={ct.tooltipLabelStyle} itemStyle={ct.tooltipItemStyle} formatter={(v) => fmt(Number(v))} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-full items-center justify-center text-slate-500 text-sm">Nenhuma despesa encontrada.</div>
                )}
              </div>
              <div className="mt-2 space-y-2">
                {dadosCategorias.slice(0, 4).map((cat, idx) => (
                  <div key={idx} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 truncate">
                      <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: CORES_CATEGORIAS[idx % CORES_CATEGORIAS.length] }} />
                      <span className="text-slate-300 truncate">{cat.name}</span>
                    </div>
                    <span className="text-slate-400 font-medium pl-2">{fmt(cat.value)}</span>
                  </div>
                ))}
                {dadosCategorias.length > 4 && (
                  <div className="text-xs text-slate-500 text-center pt-2 italic">+ {dadosCategorias.length - 4} outras categorias</div>
                )}
              </div>
            </div>
          </GraficoComNome>
        </div>

        <div className="w-full max-w-7xl bg-slate-800/40 border border-slate-700/60 rounded-2xl overflow-hidden shadow-xl flex flex-col">
          <div className="p-5 border-b border-slate-700/60 bg-slate-800/80">
            <h3 className="text-lg font-bold text-white">Todas as Transações ({resultado.transacoes.length})</h3>
          </div>
          <div className="overflow-x-auto max-h-[500px]">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-900 z-10 shadow-md">
                <tr className="text-slate-400 uppercase tracking-wider text-xs">
                  <th className="text-left px-6 py-4 font-semibold">Data</th>
                  <th className="text-left px-6 py-4 font-semibold">Banco</th>
                  <th className="text-left px-6 py-4 font-semibold">Categoria</th>
                  <th className="text-left px-6 py-4 font-semibold">Descrição</th>
                  <th className="text-right px-6 py-4 font-semibold">Valor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {resultado.transacoes.map((t, idx) => (
                  <tr key={idx} className="hover:bg-slate-700/30 transition-colors">
                    <td className="px-6 py-3 text-slate-300 whitespace-nowrap">{t.data}</td>
                    <td className="px-6 py-3 text-slate-400">{t.banco}</td>
                    <td className="px-6 py-3">
                      <span className="bg-slate-900 text-blue-300 text-[10px] uppercase font-bold px-2.5 py-1 rounded border border-blue-900/50">
                        {t.categoria}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-slate-300 max-w-xs truncate">{t.descricao}</td>
                    <td className={`px-6 py-3 text-right font-medium whitespace-nowrap ${t.tipo === "entrada" ? "text-emerald-400" : "text-red-400"}`}>
                      {t.tipo === "entrada" ? "+" : "-"}{fmt(t.valor)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // ── Dashboard Padrão — tela de upload ─────────────────────────
  return (
    <div className="p-8 flex flex-col items-center w-full min-h-screen">
      <div className="w-full max-w-5xl mb-8">
        {/* Tabs de modo */}
        <div className="flex items-center gap-2 mb-8">
          <button
            onClick={() => setModo("padrao")}
            className={`px-5 py-2.5 rounded-xl font-semibold text-sm transition-colors ${
              modo === "padrao"
                ? "bg-blue-600 text-white shadow-lg shadow-blue-900/30"
                : "border border-slate-700 text-slate-400 hover:bg-slate-800"
            }`}
          >
            📊 Dashboard Padrão
          </button>
          <button
            onClick={() => setModo("sazonal")}
            className={`px-5 py-2.5 rounded-xl font-semibold text-sm transition-colors ${
              modo === "sazonal"
                ? "bg-[#102a43] text-white shadow-lg shadow-navy-900/30"
                : "border border-slate-700 text-slate-400 hover:bg-slate-800"
            }`}
          >
            📅 Dashboard Sazonal
          </button>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight">
              Dashboard <span className="text-blue-400">Consolidado</span>
            </h1>
            <p className="text-slate-400 mt-2">
              Importe planilhas (.xlsx) ou extratos PDF para gerar o DRE e a previsão de caixa.
            </p>
          </div>
          <label className={`cursor-pointer bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 rounded-lg font-medium transition-colors shadow-lg flex items-center gap-2 ${loading ? "opacity-50 cursor-not-allowed" : ""}`}>
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
            Importar Arquivo
            <input type="file" accept=".xlsx,.pdf" multiple className="hidden" onChange={handleFileChange} disabled={loading} />
          </label>
        </div>
      </div>

      <div className="w-full max-w-5xl bg-slate-800/40 border border-slate-700/60 rounded-2xl p-8 min-h-[400px] flex flex-col relative">
        {erro && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            {erro}
          </div>
        )}

        {loading ? (
          <div className="flex-1 flex flex-col items-center justify-center">
            <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mb-4" />
            <p className="text-blue-400 font-medium animate-pulse">Cruzando dados e gerando inteligência...</p>
          </div>
        ) : arquivos.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center opacity-60 hover:opacity-100 transition-opacity">
            <div className="w-20 h-20 bg-slate-800 rounded-full flex items-center justify-center mb-4 border border-slate-700">
              <svg className="w-10 h-10 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Nenhum dado consolidado</h3>
            <p className="text-slate-400 max-w-md">Faça o upload de planilhas (.xlsx) ou extratos PDF. Você pode misturar tipos e importar vários arquivos de uma vez.</p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col">
            <h3 className="text-white font-medium mb-4 flex items-center gap-2">
              <span className="bg-blue-600 text-white text-xs px-2 py-0.5 rounded-full">{arquivos.length}</span>
              Arquivos na fila:
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {arquivos.map((arq, idx) => {
                const isPdf = arq.name.toLowerCase().endsWith(".pdf");
                return (
                  <div key={idx} className="bg-slate-900 border border-slate-700 p-3 rounded-xl flex items-center gap-3 group hover:border-slate-500">
                    <div className={`p-2 rounded-lg ${isPdf ? "bg-red-900/30" : "bg-emerald-900/30"}`}>
                      <svg className={`w-6 h-6 ${isPdf ? "text-red-400" : "text-emerald-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                    </div>
                    <div className="overflow-hidden flex-1">
                      <p className="text-sm font-medium text-slate-200 truncate">{arq.name}</p>
                      <p className="text-xs text-slate-500">{isPdf ? "Extrato PDF" : "Planilha Excel"}</p>
                    </div>
                    <button onClick={() => removerArquivo(idx)} className="text-slate-500 hover:text-red-400 p-1.5 rounded-lg transition-colors">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                  </div>
                );
              })}
            </div>
            <div className="mt-auto pt-8 flex justify-end">
              <button onClick={gerarBI} className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-3 rounded-xl font-bold shadow-lg shadow-emerald-900/20 transition-all flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                Gerar Business Intelligence
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
