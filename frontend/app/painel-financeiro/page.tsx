"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useEmpresa } from "@/contexts/EmpresaContext";
import AbaDRE from "./_components/AbaDRE";
import AbaFluxo from "./_components/AbaFluxo";
import AbaBalanco from "./_components/AbaBalanco";
import AbaIndicadores from "./_components/AbaIndicadores";
import type {
  DREResponse, FluxoResponse, BalancoResponse, IndicadoresResponse, HistoricoItem,
} from "./_components/shared";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

type Aba = "dre" | "fluxo" | "balanco" | "indicadores";

const DEMO_DRE: DREResponse = {
  periodo: "Demonstração",
  cascata: [],
  insights: [],
  metricas: {
    receita_bruta: 200000, deducoes_receita: 18000, receita_liquida: 182000,
    custo_servicos: 60000, lucro_bruto: 122000, despesas_adm: 25000,
    despesas_comerciais: 15000, despesas_financeiras: 5000, outras_despesas: 2000,
    ebit: 75000, ir_csll: 9000, lucro_liquido: 51000,
    margem_bruta: 61.0, margem_liquida: 25.5, carga_tributaria: 13.5,
  },
};

const DEMO_HISTORICO: HistoricoItem[] = [
  { mes_label: "Jan/24", receita_bruta: 120000, receita_liquida: 102000, lucro_liquido: 30600, margem_liquida: 25.5, carga_tributaria: 13.5 },
  { mes_label: "Fev/24", receita_bruta: 115000, receita_liquida: 97750, lucro_liquido: 29321, margem_liquida: 25.5, carga_tributaria: 13.5 },
  { mes_label: "Mar/24", receita_bruta: 130000, receita_liquida: 110500, lucro_liquido: 33150, margem_liquida: 25.5, carga_tributaria: 13.5 },
  { mes_label: "Abr/24", receita_bruta: 145000, receita_liquida: 123250, lucro_liquido: 36975, margem_liquida: 25.5, carga_tributaria: 13.5 },
  { mes_label: "Mai/24", receita_bruta: 160000, receita_liquida: 136000, lucro_liquido: 40800, margem_liquida: 25.5, carga_tributaria: 13.5 },
  { mes_label: "Jun/24", receita_bruta: 175000, receita_liquida: 148750, lucro_liquido: 44625, margem_liquida: 25.5, carga_tributaria: 13.5 },
];

const DEMO_FLUXO: FluxoResponse = {
  historico: [
    { mes: "Jan/24", entradas: 115000, saidas: 90000, saldo: 25000 },
    { mes: "Fev/24", entradas: 110000, saidas: 88000, saldo: 22000 },
    { mes: "Mar/24", entradas: 125000, saidas: 95000, saldo: 30000 },
    { mes: "Abr/24", entradas: 140000, saidas: 100000, saldo: 40000 },
    { mes: "Mai/24", entradas: 155000, saidas: 108000, saldo: 47000 },
    { mes: "Jun/24", entradas: 170000, saidas: 115000, saldo: 55000 },
  ],
  saldo_atual: 55000, saldo_proj_3m: 70000,
  media_entradas: 135833, media_saidas: 99333, alertas: [],
};

const DEMO_BALANCO: BalancoResponse = {
  periodo: "Demonstração",
  metricas: {
    caixa_equivalentes: 180000, contas_receber: 150000, estoques: 90000,
    outros_ativo_circ: 30000, ativo_nao_circulante: 320000, ativo_total: 770000,
    passivo_circulante: 210000, passivo_nao_circulante: 180000, passivo_total: 390000,
    patrimonio_liquido: 380000,
  },
  indicadores: { liquidez_corrente: 2.14, grau_imobilizacao: 41.6, passivo_pl: 1.03 },
  insights: [],
};

const DEMO_IND: IndicadoresResponse = {
  ebitda: { valor: 77000, variacao_pct: 8.2, tooltip: "Lucro antes de juros, impostos, depreciação e amortização" },
  margem_ebitda: { valor: 38.5, variacao_pct: 1.2, tooltip: "EBITDA / Receita Líquida", faixas: { ok: 20, atencao: 10 } },
  capital_giro_liquido: { valor: 240000, variacao_pct: 5.1, tooltip: "Ativo Circulante – Passivo Circulante" },
  liquidez_corrente: { valor: 2.14, variacao_pct: 0.3, tooltip: "Ativo Circulante / Passivo Circulante", faixas: { ok: 1.5, atencao: 1 } },
  liquidez_seca: { valor: 1.52, variacao_pct: 0.1, tooltip: "(Ativo Circulante – Estoques) / Passivo Circulante", faixas: { ok: 1, atencao: 0.8 } },
  roe: { valor: 13.4, variacao_pct: 0.8, tooltip: "Lucro Líquido / Patrimônio Líquido", faixas: { ok: 15, atencao: 8 } },
  roa: { valor: 6.6, variacao_pct: 0.4, tooltip: "Lucro Líquido / Ativo Total", faixas: { ok: 5, atencao: 2 } },
  endividamento_geral: { valor: 50.6, variacao_pct: -0.5, tooltip: "Passivo Total / Ativo Total", faixas: { ok: 40, atencao: 60 }, invertido: true },
};

export default function PainelFinanceiroPage() {
  const router = useRouter();
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const [aba, setAba] = useState<Aba>("dre");
  const [ano, setAno] = useState(new Date().getFullYear());
  const [mes, setMes] = useState(new Date().getMonth() + 1);

  const [dreDados, setDreDados] = useState<DREResponse | null>(null);
  const [fluxoDados, setFluxoDados] = useState<FluxoResponse | null>(null);
  const [balancoDados, setBalancoDados] = useState<BalancoResponse | null>(null);
  const [indicadoresDados, setIndicadoresDados] = useState<IndicadoresResponse | null>(null);
  const [historico, setHistorico] = useState<HistoricoItem[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  const token = () => localStorage.getItem("controllo_token") ?? "";

  useEffect(() => {
    const t = localStorage.getItem("controllo_token");
    const u = localStorage.getItem("controllo_user");
    if (!t || !u) { router.push("/"); return; }
    try { if (!JSON.parse(u).is_aprovado) { router.push("/"); return; } } catch { router.push("/"); return; }
  }, [router]);

  const carregar = useCallback(async (signal?: AbortSignal) => {
    if (!empresaId) { setCarregando(false); return; }
    setCarregando(true);
    setErro("");
    try {
      const h = { Authorization: `Bearer ${token()}` };
      const [dre, fluxo, balanco, lanc, ind] = await Promise.all([
        fetch(`${API}/api/financeiro/dre/${empresaId}?ano=${ano}&mes=${mes}`, { headers: h, signal }).then((r) => r.json()),
        fetch(`${API}/api/financeiro/fluxo-caixa/${empresaId}`, { headers: h, signal }).then((r) => r.json()),
        fetch(`${API}/api/financeiro/balanco/${empresaId}?ano=${ano}&mes=${mes}`, { headers: h, signal }).then((r) => r.json()),
        fetch(`${API}/api/financeiro/lancamentos/${empresaId}`, { headers: h, signal }).then((r) => r.json()),
        fetch(`${API}/api/financeiro/indicadores/${empresaId}?ano=${ano}&mes=${mes}`, { headers: h, signal }).then((r) => r.json()),
      ]);

      if (dre.detail) throw new Error(dre.detail);
      if (dre.sem_dados) {
        setDreDados(DEMO_DRE);
        setFluxoDados(DEMO_FLUXO);
        setBalancoDados(DEMO_BALANCO);
        setIndicadoresDados(DEMO_IND);
        setHistorico(DEMO_HISTORICO);
        return;
      }

      setDreDados(dre);
      setFluxoDados(fluxo.sem_dados ? null : fluxo);
      setBalancoDados(balanco.sem_dados ? null : balanco);
      setIndicadoresDados(ind.sem_dados ? null : ind);
      setHistorico(Array.isArray(lanc) ? lanc : []);
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
  const MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
  const ABAS: { key: Aba; label: string }[] = [
    { key: "dre", label: "DRE" },
    { key: "fluxo", label: "Fluxo de Caixa" },
    { key: "balanco", label: "Balanço Patrimonial" },
    { key: "indicadores", label: "Indicadores" },
  ];

  return (
    <div className="min-h-full" style={{ background: "var(--bg-canvas)", color: "var(--text-primary)" }}>
      <header className="px-8 pt-8 pb-0 border-b border-slate-200 dark:border-slate-700">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-navy-50 border border-navy-200 dark:bg-navy-500/10 dark:border-navy-500/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-navy-600 dark:text-navy-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight">Painel Financeiro</h1>
              <p className="text-slate-500 text-sm">DRE · Fluxo de Caixa · Balanço Patrimonial</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap pb-1">
            <select value={mes} onChange={(e) => setMes(Number(e.target.value))}
              className="border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-navy-300 dark:focus:ring-navy-700">
              {MESES.map((m, i) => <option key={i + 1} value={i + 1}>{m}</option>)}
            </select>
            <select value={ano} onChange={(e) => setAno(Number(e.target.value))}
              className="border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-navy-300 dark:focus:ring-navy-700">
              {ANOS.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
        </div>
        <div className="flex gap-1">
          {ABAS.map((a) => (
            <button key={a.key} onClick={() => setAba(a.key)}
              className={`px-5 py-2.5 text-sm font-semibold border-b-2 transition-colors ${aba === a.key ? "border-[#102a43] text-[#3b6ea5]" : "border-transparent text-slate-500 hover:text-slate-300"}`}>
              {a.label}
            </button>
          ))}
        </div>
      </header>

      <div className="px-8 py-8 space-y-6">
        {/* Demo banner */}
        {!empresaId && !carregando && (
          <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-300 text-sm">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span><strong>Dados de Demonstração</strong> — Selecione uma empresa para visualizar seus dados reais.</span>
          </div>
        )}

        {carregando && (
          <div className="space-y-6 page-enter">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="card-premium p-5 space-y-3">
                  <div className="skeleton h-3 w-20 rounded" />
                  <div className="skeleton h-7 w-32 rounded" />
                  <div className="skeleton h-3 w-16 rounded" />
                </div>
              ))}
            </div>
            <div className="card-premium p-5">
              <div className="skeleton h-4 w-48 rounded mb-5" />
              <div className="skeleton h-64 w-full rounded-xl" />
            </div>
          </div>
        )}

        {erro && !carregando && (
          <div className="px-5 py-4 rounded-xl bg-amber-950/30 border border-amber-500/20 text-amber-300 text-sm">
            {erro}
          </div>
        )}

        {!carregando && !erro && (() => {
          const isDemo = !empresaId;
          const dreVis = dreDados ?? (isDemo ? DEMO_DRE : null);
          const fluxoVis = fluxoDados ?? (isDemo ? DEMO_FLUXO : null);
          const balancoVis = balancoDados ?? (isDemo ? DEMO_BALANCO : null);
          const indVis = indicadoresDados ?? (isDemo ? DEMO_IND : null);
          const histVis = historico.length > 0 ? historico : isDemo ? DEMO_HISTORICO : [];

          if (!dreVis && empresaId) return (
            <div className="flex flex-col items-center gap-3 py-20 text-slate-600">
              <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-sm">Importe dados financeiros para visualizar este painel.</p>
            </div>
          );

          return (
            <>
              {aba === "dre" && dreVis && <AbaDRE dre={dreVis} historico={histVis} />}
              {aba === "fluxo" && (fluxoVis ? <AbaFluxo fluxo={fluxoVis} /> : <div className="py-16 text-center text-slate-600 text-sm">Sem dados de fluxo de caixa disponíveis.</div>)}
              {aba === "balanco" && (balancoVis ? <AbaBalanco balanco={balancoVis} /> : <div className="py-16 text-center text-slate-600 text-sm">Sem dados de balanço para este período.</div>)}
              {aba === "indicadores" && (indVis && dreVis ? <AbaIndicadores ind={indVis} metricas={dreVis.metricas} /> : <div className="py-16 text-center text-slate-600 text-sm">Sem dados de indicadores para este período.</div>)}
            </>
          );
        })()}
      </div>
    </div>
  );
}
