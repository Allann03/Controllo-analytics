"use client";
import { Fragment, useEffect, useState, useCallback } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");
const MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
const ANO_ATUAL = new Date().getFullYear();

interface InsightItem { id: string; categoria: string; severidade: string; titulo: string; mensagem: string; }
interface GrupoBalanco { total: number; itens: Record<string, number>; }
interface BalancoData {
  periodo: string;
  estrutura: {
    ativo: { circulante: GrupoBalanco; nao_circulante: GrupoBalanco; total: number; };
    passivo: { circulante: GrupoBalanco; nao_circulante: GrupoBalanco; total: number; };
    patrimonio_liquido: { total: number; itens: Record<string, number>; };
  };
  indicadores: {
    liquidez_corrente?: number | null;
    grau_imobilizacao?: number | null;
    passivo_pl?: number | null;
  };
  insights: InsightItem[];
  sem_dados?: boolean;
}

function formatBRL(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function SecaoBalanco({
  titulo,
  grupos,
  totalLabel,
  total,
  corTotal,
  accentColor,
  sectionTotal,
}: {
  titulo: string;
  grupos: { label: string; grupo: GrupoBalanco }[];
  totalLabel: string;
  total: number;
  corTotal: string;
  accentColor: string;
  sectionTotal?: number;
}) {
  const [aberta, setAberta] = useState(true);

  return (
    <div className="card-premium overflow-hidden">
      <button
        className="w-full px-5 py-4 flex items-center justify-between border-b border-slate-200 dark:border-slate-700/60 hover:bg-slate-50 dark:hover:bg-slate-700/10 transition-colors"
        onClick={() => setAberta(v => !v)}
      >
        <div className="flex items-center gap-2.5">
          <span className="w-1.5 h-5 rounded-full" style={{ background: accentColor }} />
          <p className="text-xs font-black text-slate-700 dark:text-slate-200 uppercase tracking-widest">{titulo}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-base font-black font-mono ${corTotal}`}>{formatBRL(total)}</span>
          <svg className={`w-4 h-4 text-slate-400 transition-transform ${aberta ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {aberta && (
        <table className="w-full">
          <tbody>
            {grupos.map(({ label, grupo }) => (
              <Fragment key={label}>
                <tr className="bg-slate-50 dark:bg-slate-800/40 border-b border-slate-200 dark:border-slate-700/40">
                  <td className="px-5 py-2.5 text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{label}</td>
                  <td className="px-5 py-2.5 text-right font-mono text-sm font-semibold text-slate-700 dark:text-slate-300">{formatBRL(grupo.total)}</td>
                </tr>
                {Object.entries(grupo.itens).map(([itemLabel, valor]) => (
                  <tr key={itemLabel} className={`border-b border-slate-100 dark:border-slate-700/20 hover:bg-slate-50 dark:hover:bg-slate-700/10 transition-colors ${valor === 0 ? "opacity-40" : ""}`}>
                    <td className="py-2 pl-10 pr-5 text-xs text-slate-500">{itemLabel}</td>
                    <td className="px-5 py-2 text-right">
                      <span className={`font-mono text-xs ${valor >= 0 ? "text-slate-600 dark:text-slate-400" : "text-rose-600 dark:text-rose-400"}`}>{formatBRL(valor)}</span>
                      {(sectionTotal ?? 0) > 0 && (
                        <span className="ml-2 text-[10px] text-slate-400 dark:text-slate-500 font-mono">
                          ({((Math.abs(valor) / (sectionTotal ?? 1)) * 100).toFixed(0)}%)
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </Fragment>
            ))}
            <tr className="border-t-2 border-slate-300 dark:border-slate-600">
              <td className="px-5 py-3 text-xs font-black text-slate-700 dark:text-slate-300 uppercase">{totalLabel}</td>
              <td className={`px-5 py-3 text-right font-mono font-black text-base ${corTotal}`}>{formatBRL(total)}</td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}

function SkeletonBalanco() {
  return (
    <div className="space-y-6 page-enter">
      <div className="grid grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="card-premium p-5 space-y-3">
            <div className="skeleton h-3 w-28 rounded" />
            <div className="skeleton h-8 w-20 rounded" />
            <div className="skeleton h-3 w-36 rounded" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[...Array(2)].map((_, i) => (
          <div key={i} className="card-premium overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-700/60 flex justify-between">
              <div className="skeleton h-4 w-20 rounded" />
              <div className="skeleton h-4 w-28 rounded" />
            </div>
            {[...Array(5)].map((_, j) => (
              <div key={j} className="px-5 py-3 border-b border-slate-700/20 flex justify-between">
                <div className="skeleton h-3 w-32 rounded" />
                <div className="skeleton h-3 w-24 rounded" />
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function BalancoPage() {
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const [ano, setAno] = useState(ANO_ATUAL);
  const [mes, setMes] = useState(new Date().getMonth() + 1);
  const [dados, setDados] = useState<BalancoData | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const h = () => ({ Authorization: `Bearer ${localStorage.getItem("controllo_token") || ""}` });

  const carregar = useCallback(async (signal?: AbortSignal) => {
    if (!empresaId) { setCarregando(false); return; }
    setCarregando(true); setErro(null); setDados(null);
    try {
      const r = await fetch(`${API}/api/financeiro/balanco/${empresaId}?ano=${ano}&mes=${mes}`, { headers: h(), signal });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Erro ao carregar.");
      setDados(d);
    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") return;
      setErro((e as Error).message);
    }
    finally { setCarregando(false); }
  }, [empresaId, ano, mes]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60_000);
    carregar(controller.signal);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [carregar]);

  const DEMO_BALANCO: BalancoData = {
    periodo: "Demonstração",
    estrutura: {
      ativo: {
        circulante: { total: 450000, itens: { "Caixa e Equivalentes": 180000, "Contas a Receber": 150000, "Estoques": 90000, "Outros Ativos Circulantes": 30000 } },
        nao_circulante: { total: 320000, itens: { "Imobilizado": 280000, "Depreciação Acumulada": -40000, "Intangível": 80000 } },
        total: 770000,
      },
      passivo: {
        circulante: { total: 210000, itens: { "Fornecedores": 80000, "Salários a Pagar": 45000, "Impostos a Recolher": 35000, "Empréstimos CP": 50000 } },
        nao_circulante: { total: 180000, itens: { "Empréstimos LP": 150000, "Provisões": 30000 } },
        total: 390000,
      },
      patrimonio_liquido: { total: 380000, itens: { "Capital Social": 200000, "Reservas": 100000, "Lucros Acumulados": 80000 } },
    },
    indicadores: { liquidez_corrente: 2.14, grau_imobilizacao: 41.6, passivo_pl: 1.03 },
    insights: [
      { id: "1", categoria: "liquidez", severidade: "info", titulo: "Liquidez saudável", mensagem: "Liquidez corrente de 2,14 — a empresa tem R$ 2,14 de ativo circulante para cada R$ 1,00 de passivo." },
      { id: "2", categoria: "endividamento", severidade: "atencao", titulo: "Endividamento moderado", mensagem: "Passivo/PL de 1,03 indica endividamento próximo ao patrimônio. Monitore." },
    ],
  };

  const isDemo = !empresaId || dados?.sem_dados || (!dados && !carregando);
  const dadosVisiveis = (dados && !dados.sem_dados) ? dados : (isDemo ? DEMO_BALANCO : null);

  const indicadores = dadosVisiveis ? [
    {
      label: "Liquidez Corrente",
      val: dadosVisiveis.indicadores.liquidez_corrente,
      fmtVal: (v: number) => v.toFixed(2),
      bom: (v: number) => v >= 1,
      desc: "≥ 1 é saudável",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
        </svg>
      ),
    },
    {
      label: "Grau de Imobilização",
      val: dadosVisiveis.indicadores.grau_imobilizacao,
      fmtVal: (v: number) => `${v.toFixed(1)}%`,
      bom: (v: number) => v <= 70,
      desc: "≤ 70% recomendado",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
        </svg>
      ),
    },
    {
      label: "Passivo / PL",
      val: dadosVisiveis.indicadores.passivo_pl,
      fmtVal: (v: number) => v.toFixed(2),
      bom: (v: number) => v <= 1,
      desc: "≤ 1 é saudável",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
    },
  ] : [];

  return (
    <div className="min-h-full bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">

      {/* HEADER */}
      <header className="page-header px-8 pt-8 pb-6 border-b border-slate-200 dark:border-slate-700">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-200 dark:bg-indigo-500/10 dark:border-indigo-500/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-indigo-700 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 11h.01M12 11h.01M15 11h.01M12 7h.01M15 7h.01M9 14h.01M12 14h.01M15 14h.01M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight">Balanço <span className="text-indigo-700 dark:text-indigo-400">Comentado</span></h1>
              <p className="text-slate-500 text-sm">Estrutura patrimonial com indicadores e alertas automáticos</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={mes}
              onChange={e => setMes(Number(e.target.value))}
              className="rounded-xl px-3 py-2 text-sm outline-none border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-200 focus:ring-2 focus:ring-navy-300 dark:focus:ring-navy-700"
            >
              {MESES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
            </select>
            <input
              type="number"
              value={ano}
              onChange={e => setAno(Number(e.target.value))}
              className="w-24 px-3 py-2 rounded-xl text-sm outline-none border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-200 focus:ring-2 focus:ring-navy-300 dark:focus:ring-navy-700"
            />
            {isDemo && !carregando && <span className="badge badge-amber">Demo</span>}
            {!isDemo && <span className="badge badge-violet">Ao vivo</span>}
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

        {/* Erro */}
        {erro && (
          <div className="p-4 bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 rounded-xl text-rose-600 dark:text-rose-300 text-sm flex items-center gap-3">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            {erro}
          </div>
        )}

        {/* Skeleton */}
        {carregando && <SkeletonBalanco />}

        {/* Conteúdo */}
        {dadosVisiveis && !carregando && (
          <div className="space-y-6 page-enter">

            {/* Disclaimer BP Gerencial — BLOCO 3C.3, mandato R3 */}
            <div className="flex items-start gap-3 px-5 py-4 bg-amber-50 dark:bg-amber-500/10 border border-amber-300 dark:border-amber-500/30 rounded-xl text-amber-800 dark:text-amber-200 text-sm" role="alert">
              <svg className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div>
                <p className="font-semibold mb-1">BP Gerencial</p>
                <p className="text-xs leading-relaxed opacity-90">
                  Este balanço reflete os saldos informados e não é derivado de escrituração com partida dobrada.
                  Não utilizar para fins legais ou fiscais.
                  A reconciliação contábil deve ser realizada no sistema contábil oficial com responsabilidade do contador CRC.
                </p>
              </div>
            </div>

            {/* Indicadores */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {indicadores.map(ind => {
                const bom = ind.val != null ? ind.bom(ind.val) : null;
                const statusLabel = bom === null ? "" : bom ? "Saudavel" : "Critico";
                const bgClass = bom === null
                  ? ""
                  : bom
                    ? "bg-emerald-500/[0.08] border-emerald-500/20"
                    : "bg-rose-500/[0.08] border-rose-500/20";
                return (
                  <div key={ind.label} className={`card-premium p-5 border ${bgClass} ${bom === null ? "" : bom ? "kpi-emerald" : "kpi-rose"}`}>
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{ind.label}</p>
                      <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${
                        bom === null ? "bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400"
                        : bom ? "bg-emerald-100 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                        : "bg-rose-100 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400"
                      }`}>
                        {ind.icon}
                      </div>
                    </div>
                    <div className="flex items-end gap-2">
                      <p className={`text-2xl font-black font-mono ${
                        bom === null ? "text-slate-500"
                        : bom ? "text-emerald-400"
                        : "text-rose-400"
                      }`}>
                        {ind.val != null ? ind.fmtVal(ind.val) : "—"}
                      </p>
                      {bom !== null && (
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full mb-1 ${
                          bom
                            ? "bg-emerald-500/10 text-emerald-500 dark:text-emerald-400"
                            : "bg-rose-500/10 text-rose-500 dark:text-rose-400"
                        }`}>
                          {statusLabel}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1">{ind.desc}</p>
                  </div>
                );
              })}
            </div>

            {/* Insights automáticos */}
            {dadosVisiveis.insights.length > 0 && (
              <div className="card-premium p-5">
                <p className="section-title mb-4">Comentários Automáticos</p>
                <div className="space-y-3">
                  {dadosVisiveis.insights.map(ins => (
                    <div key={ins.id} className={`flex items-start gap-3 p-3.5 rounded-xl border-l-4 ${
                      ins.severidade === "critico" ? "bg-rose-500/5 border-rose-500"
                      : ins.severidade === "atencao" ? "bg-amber-500/5 border-amber-400"
                      : "bg-blue-500/5 border-blue-400"
                    }`} style={{ borderLeftWidth: 3, borderTopWidth: 0, borderRightWidth: 0, borderBottomWidth: 0, borderStyle: "solid" }}>
                      <div className={`w-2 h-2 mt-1.5 rounded-full flex-shrink-0 ${
                        ins.severidade === "critico" ? "bg-rose-500"
                        : ins.severidade === "atencao" ? "bg-amber-400"
                        : "bg-blue-400"
                      }`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-0.5">
                          <p className="text-sm font-semibold text-slate-800 dark:text-white">{ins.titulo}</p>
                          <span className={`text-[9px] font-black uppercase px-1.5 py-0.5 rounded-full border ${
                            ins.severidade === "critico" ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                            : ins.severidade === "atencao" ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            : "bg-blue-500/10 text-blue-400 border-blue-500/20"
                          }`}>
                            {ins.severidade === "critico" ? "Critico" : ins.severidade === "atencao" ? "Atencao" : "Info"}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{ins.mensagem}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Estrutura do Balanço */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Ativo */}
              <SecaoBalanco
                titulo="ATIVO"
                grupos={[
                  { label: "Circulante", grupo: dadosVisiveis.estrutura.ativo.circulante },
                  { label: "Não Circulante", grupo: dadosVisiveis.estrutura.ativo.nao_circulante },
                ]}
                totalLabel="Total do Ativo"
                total={dadosVisiveis.estrutura.ativo.total}
                corTotal="text-emerald-600 dark:text-emerald-400"
                accentColor="#10b981"
                sectionTotal={dadosVisiveis.estrutura.ativo.total}
              />

              {/* Passivo + PL */}
              <div className="space-y-4">
                <SecaoBalanco
                  titulo="PASSIVO"
                  grupos={[
                    { label: "Circulante", grupo: dadosVisiveis.estrutura.passivo.circulante },
                    { label: "Não Circulante", grupo: dadosVisiveis.estrutura.passivo.nao_circulante },
                  ]}
                  totalLabel="Total do Passivo"
                  total={dadosVisiveis.estrutura.passivo.total}
                  corTotal="text-rose-600 dark:text-rose-400"
                  accentColor="#f43f5e"
                  sectionTotal={dadosVisiveis.estrutura.passivo.total}
                />

                {/* Patrimônio Líquido */}
                <div className="card-premium overflow-hidden">
                  <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700/60 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span className="w-1.5 h-5 rounded-full bg-[#1E4976]" />
                      <p className="text-xs font-black text-slate-700 dark:text-slate-200 uppercase tracking-widest">Patrimônio Líquido</p>
                    </div>
                    <span className="text-base font-black font-mono text-[#1E4976] dark:text-blue-400">
                      {formatBRL(dadosVisiveis.estrutura.patrimonio_liquido.total)}
                    </span>
                  </div>
                  <table className="w-full">
                    <tbody>
                      {Object.entries(dadosVisiveis.estrutura.patrimonio_liquido.itens).map(([k, v]) => (
                        <tr key={k} className={`border-b border-slate-100 dark:border-slate-700/20 hover:bg-slate-50 dark:hover:bg-slate-700/10 transition-colors ${v === 0 ? "opacity-40" : ""}`}>
                          <td className="px-5 py-2 text-xs text-slate-500 pl-10">{k}</td>
                          <td className="px-5 py-2 text-right">
                            <span className={`font-mono text-xs ${v >= 0 ? "text-slate-600 dark:text-slate-400" : "text-rose-600 dark:text-rose-400"}`}>{formatBRL(v)}</span>
                            {dadosVisiveis.estrutura.patrimonio_liquido.total > 0 && (
                              <span className="ml-2 text-[10px] text-slate-400 dark:text-slate-500 font-mono">
                                ({((Math.abs(v) / dadosVisiveis.estrutura.patrimonio_liquido.total) * 100).toFixed(0)}%)
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                      <tr className="border-t-2 border-slate-300 dark:border-slate-600">
                        <td className="px-5 py-3 text-xs font-black text-slate-700 dark:text-slate-300 uppercase">Total PL</td>
                        <td className="px-5 py-3 text-right font-mono font-black text-base text-[#1E4976] dark:text-blue-400">
                          {formatBRL(dadosVisiveis.estrutura.patrimonio_liquido.total)}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                {/* Equação contábil */}
                <div className="px-5 py-3 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 rounded-xl flex items-center justify-between text-xs">
                  <span className="text-slate-500 font-medium">Ativo = Passivo + PL</span>
                  <span className={`font-mono font-semibold ${
                    Math.abs(dadosVisiveis.estrutura.ativo.total - dadosVisiveis.estrutura.passivo.total - dadosVisiveis.estrutura.patrimonio_liquido.total) < 0.01
                      ? "text-emerald-400" : "text-amber-400"
                  }`}>
                    {formatBRL(dadosVisiveis.estrutura.ativo.total)} = {formatBRL(dadosVisiveis.estrutura.passivo.total + dadosVisiveis.estrutura.patrimonio_liquido.total)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
