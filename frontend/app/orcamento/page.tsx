"use client";

import { useEffect, useState, useCallback } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";
import GraficoComNome from "@/components/GraficoComNome";
import { useChartTheme } from "@/components/useChartTheme";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

// ─────────────────────────────────────────────────────────────────
//  Tipos
// ─────────────────────────────────────────────────────────────────

interface ParComparativo {
  orcado: number;
  realizado: number;
  variacao: number | null;
  status: "ok" | "atencao" | "critico" | "sem_orcamento";
}

interface Comparativo {
  sem_orcamento?: boolean;
  sem_lancamento?: boolean;
  periodo: { ano: number; mes: number };
  receita_bruta: ParComparativo;
  deducoes_receita: ParComparativo;
  receita_liquida: ParComparativo;
  custo_servicos: ParComparativo;
  lucro_bruto: ParComparativo;
  despesas_adm: ParComparativo;
  despesas_comerciais: ParComparativo;
  despesas_financeiras: ParComparativo;
  outras_despesas: ParComparativo;
  ir_csll: ParComparativo;
  lucro_liquido: ParComparativo;
  entradas_caixa: ParComparativo;
  saidas_caixa: ParComparativo;
  folha_pagamento: ParComparativo;
}

interface MesAnual {
  mes: number;
  receita_bruta_orc: number;
  receita_bruta_real: number;
  lucro_liquido_orc: number;
  lucro_liquido_real: number;
  desvio_receita: number | null;
  desvio_lucro: number | null;
}

interface OrcamentoForm {
  receita_bruta: string;
  deducoes_receita: string;
  custo_servicos: string;
  despesas_adm: string;
  despesas_comerciais: string;
  despesas_financeiras: string;
  outras_despesas: string;
  ir_csll: string;
  entradas_caixa: string;
  saidas_caixa: string;
  folha_pagamento: string;
}

// ─────────────────────────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────────────────────────

const fmt = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v);
const fmtPct = (v: number | null) => v === null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;

const MESES_LABEL = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
const ANOS = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i);

function statusCor(s: ParComparativo["status"]) {
  return s === "ok" ? "text-emerald-600 dark:text-emerald-400" : s === "atencao" ? "text-amber-600 dark:text-amber-400" : s === "critico" ? "text-rose-600 dark:text-rose-400" : "text-slate-500";
}

function statusBg(s: ParComparativo["status"]) {
  return s === "ok" ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20" : s === "atencao" ? "bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/20" : s === "critico" ? "bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/20" : "bg-slate-100 dark:bg-slate-800/20 border-slate-200 dark:border-slate-700/30";
}

// ─────────────────────────────────────────────────────────────────
//  Linha da tabela comparativa (UNCHANGED)
// ─────────────────────────────────────────────────────────────────

function LinhaComparativa({
  label, par, destaque = false, invertido = false,
}: {
  label: string;
  par: ParComparativo;
  destaque?: boolean;
  invertido?: boolean;
}) {
  if (par.status === "sem_orcamento" && par.orcado === 0 && par.realizado === 0) return null;

  const varOk = invertido
    ? (par.variacao ?? 0) <= 5
    : (par.variacao ?? 0) >= -5;

  return (
    <tr className={`border-b border-slate-100 dark:border-slate-800/50 ${destaque ? "bg-slate-50 dark:bg-slate-800/30" : "hover:bg-slate-50 dark:hover:bg-slate-800/20"}`}>
      <td className={`px-4 py-2.5 text-sm ${destaque ? "font-bold text-slate-800 dark:text-slate-100" : "text-slate-500 dark:text-slate-400"}`}>
        {label}
      </td>
      <td className="px-4 py-2.5 text-right font-mono text-sm text-slate-500 dark:text-slate-400">
        {fmt(par.orcado)}
      </td>
      <td className="px-4 py-2.5 text-right font-mono text-sm text-slate-800 dark:text-slate-200">
        {fmt(par.realizado)}
      </td>
      <td className="px-4 py-2.5 text-right">
        <span className={`text-xs font-bold font-mono ${statusCor(par.status)}`}>
          {fmtPct(par.variacao)}
        </span>
      </td>
      <td className="px-4 py-2.5 text-center">
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${statusBg(par.status)} ${statusCor(par.status)}`}>
          {par.status === "sem_orcamento" ? "—"
            : par.status === "ok" ? varOk ? "✓ Ok" : "Ok"
            : par.status === "atencao" ? "Atenção"
            : "Crítico"}
        </span>
      </td>
    </tr>
  );
}

// ─────────────────────────────────────────────────────────────────
//  Modal de cadastro de orçamento (UNCHANGED logic, upgraded shell)
// ─────────────────────────────────────────────────────────────────

interface ModalOrcamentoProps {
  token: string;
  empresaId: number;
  ano: number;
  mes: number;
  inicial?: Partial<OrcamentoForm>;
  onClose: () => void;
  onSaved: () => void;
}

function ModalOrcamento({ token, empresaId, ano, mes, inicial, onClose, onSaved }: ModalOrcamentoProps) {
  const vazio: OrcamentoForm = {
    receita_bruta: "0", deducoes_receita: "0", custo_servicos: "0",
    despesas_adm: "0", despesas_comerciais: "0", despesas_financeiras: "0",
    outras_despesas: "0", ir_csll: "0", entradas_caixa: "0",
    saidas_caixa: "0", folha_pagamento: "0",
  };
  const [form, setForm] = useState<OrcamentoForm>({ ...vazio, ...inicial });
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  function set(campo: keyof OrcamentoForm) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm(prev => ({ ...prev, [campo]: e.target.value }));
  }

  async function salvar() {
    setSalvando(true);
    setErro("");
    try {
      const payload: Record<string, number | string> = { ano, mes };
      for (const [k, v] of Object.entries(form)) {
        payload[k] = parseFloat(v) || 0;
      }
      const r = await fetch(`${API}/api/orcamento/empresas/${empresaId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      });
      if (!r.ok) { const d = await r.json(); setErro(d.detail || "Erro ao salvar."); return; }
      onSaved();
    } finally { setSalvando(false); }
  }

  const campo = (label: string, key: keyof OrcamentoForm) => (
    <div>
      <label className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{label}</label>
      <input type="number" min="0" step="0.01" value={form[key]} onChange={set(key)}
        className="mt-1.5 w-full rounded-xl px-3 py-2.5 text-sm font-mono outline-none transition-all"
        style={{
          background: "var(--bg-secondary)",
          border: "1px solid var(--border)",
          color: "var(--text-primary)",
        }}
        onFocus={e => { e.currentTarget.style.borderColor = "rgba(79,106,255,0.5)"; e.currentTarget.style.boxShadow = "0 0 0 3px rgba(79,106,255,0.08)"; }}
        onBlur={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.boxShadow = "none"; }}
      />
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.75)", backdropFilter: "blur(4px)" }}>
      <div
        className="w-full max-w-2xl rounded-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto"
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          boxShadow: "0 0 0 1px rgba(79,106,255,0.08), 0 32px 64px rgba(0,0,0,0.5)",
        }}
      >
        {/* Top accent */}
        <div className="rounded-t-2xl -mx-6 -mt-6 mb-5 px-6 pt-6 pb-4 bg-navy-50 dark:bg-navy-900/40 border-b border-navy-100 dark:border-navy-700/50">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Orçamento —{" "}
              <span className="text-navy-600 dark:text-navy-400">{MESES_LABEL[mes - 1]}/{ano}</span>
            </h2>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-xl flex items-center justify-center text-lg font-bold transition-colors"
              style={{ color: "var(--text-muted)", background: "var(--bg-secondary)", border: "1px solid var(--border)" }}
            >
              ×
            </button>
          </div>
        </div>

        {erro && (
          <p className="text-xs mb-4 px-3 py-2 rounded-xl" style={{ color: "#f87171", background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.20)" }}>{erro}</p>
        )}

        <div className="space-y-5">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest mb-3 text-navy-600 dark:text-navy-400">DRE</p>
            <div className="grid grid-cols-2 gap-3">
              {campo("Receita Bruta", "receita_bruta")}
              {campo("(–) Deduções", "deducoes_receita")}
              {campo("(–) Custo dos Serviços", "custo_servicos")}
              {campo("(–) Despesas Adm.", "despesas_adm")}
              {campo("(–) Despesas Comerciais", "despesas_comerciais")}
              {campo("(–) Despesas Financeiras", "despesas_financeiras")}
              {campo("(–) Outras Despesas", "outras_despesas")}
              {campo("(–) IR + CSLL", "ir_csll")}
            </div>
          </div>

          <div>
            <p className="text-[11px] font-bold text-emerald-400 uppercase tracking-widest mb-3">Fluxo de Caixa</p>
            <div className="grid grid-cols-2 gap-3">
              {campo("Entradas", "entradas_caixa")}
              {campo("Saídas", "saidas_caixa")}
            </div>
          </div>

          <div>
            <p className="text-[11px] font-bold text-amber-400 uppercase tracking-widest mb-3">RH</p>
            <div className="grid grid-cols-2 gap-3">
              {campo("Folha de Pagamento", "folha_pagamento")}
            </div>
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={salvar}
            disabled={salvando}
            data-notheme className="flex-1 text-white text-sm font-bold py-2.5 rounded-xl transition-all disabled:opacity-50 bg-[#102a43] hover:bg-[#0a1f33]"
          >
            {salvando ? "Salvando..." : "Salvar Orçamento"}
          </button>
          <button
            onClick={onClose}
            className="flex-1 text-sm font-semibold py-2.5 rounded-xl transition-colors"
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              color: "var(--text-secondary)",
            }}
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
//  Página principal
// ─────────────────────────────────────────────────────────────────

export default function OrcamentoPage() {
  const ct = useChartTheme();
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const [ano, setAno]                 = useState(new Date().getFullYear());
  const [mes, setMes]                 = useState(new Date().getMonth() + 1);
  const [comparativo, setComparativo] = useState<Comparativo | null>(null);
  const [anual, setAnual]             = useState<MesAnual[]>([]);
  const [carregando, setCarregando]   = useState(false);
  const [showModal, setShowModal]     = useState(false);
  const [aba, setAba]                 = useState<"mensal" | "anual">("mensal");

  const carregar = useCallback(async (signal?: AbortSignal) => {
    if (!empresaId) { setCarregando(false); return; }
    setCarregando(true);
    try {
      const token = localStorage.getItem("controllo_token") ?? "";
      const h = { Authorization: `Bearer ${token}` };
      const [cRes, aRes] = await Promise.all([
        fetch(`${API}/api/orcamento/comparativo/${empresaId}?ano=${ano}&mes=${mes}`, { headers: h, signal }).then(r => r.json()),
        fetch(`${API}/api/orcamento/comparativo/${empresaId}/anual?ano=${ano}`,      { headers: h, signal }).then(r => r.json()),
      ]);
      setComparativo(cRes);
      setAnual(aRes.meses ?? []);
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") return;
      /* erro de rede — não quebra a página */
    } finally { setCarregando(false); }
  }, [empresaId, ano, mes]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60_000);
    carregar(controller.signal);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [carregar]);

  function mkPar(orcado: number, realizado: number): ParComparativo {
    const variacao = orcado > 0 ? ((realizado - orcado) / orcado) * 100 : null;
    const status: ParComparativo["status"] = !orcado ? "sem_orcamento"
      : variacao !== null && variacao < -20 ? "critico"
      : variacao !== null && variacao < -5  ? "atencao"
      : "ok";
    return { orcado, realizado, variacao, status };
  }

  const DEMO_COMP: Comparativo = {
    periodo: { ano: 2025, mes: 6 },
    receita_bruta:         mkPar(180000, 195000),
    deducoes_receita:      mkPar(15000,  16000),
    receita_liquida:       mkPar(165000, 179000),
    custo_servicos:        mkPar(70000,  72000),
    lucro_bruto:           mkPar(95000,  107000),
    despesas_adm:          mkPar(22000,  24000),
    despesas_comerciais:   mkPar(18000,  17000),
    despesas_financeiras:  mkPar(8000,   9500),
    outras_despesas:       mkPar(5000,   4000),
    ir_csll:               mkPar(9000,   10000),
    lucro_liquido:         mkPar(33000,  42500),
    entradas_caixa:        mkPar(175000, 190000),
    saidas_caixa:          mkPar(140000, 145000),
    folha_pagamento:       mkPar(38000,  39000),
  };

  const DEMO_ANUAL: MesAnual[] = [
    { mes: 1,  receita_bruta_orc: 150000, receita_bruta_real: 120000, lucro_liquido_orc: 25000, lucro_liquido_real: 22000, desvio_receita: -20, desvio_lucro: -12 },
    { mes: 2,  receita_bruta_orc: 155000, receita_bruta_real: 115000, lucro_liquido_orc: 26000, lucro_liquido_real: 20000, desvio_receita: -26, desvio_lucro: -23 },
    { mes: 3,  receita_bruta_orc: 160000, receita_bruta_real: 130000, lucro_liquido_orc: 28000, lucro_liquido_real: 26000, desvio_receita: -19, desvio_lucro: -7 },
    { mes: 4,  receita_bruta_orc: 165000, receita_bruta_real: 145000, lucro_liquido_orc: 29000, lucro_liquido_real: 30000, desvio_receita: -12, desvio_lucro: 3 },
    { mes: 5,  receita_bruta_orc: 170000, receita_bruta_real: 160000, lucro_liquido_orc: 30000, lucro_liquido_real: 35000, desvio_receita: -6,  desvio_lucro: 17 },
    { mes: 6,  receita_bruta_orc: 180000, receita_bruta_real: 195000, lucro_liquido_orc: 33000, lucro_liquido_real: 42500, desvio_receita: 8,   desvio_lucro: 29 },
    { mes: 7,  receita_bruta_orc: 185000, receita_bruta_real: 0, lucro_liquido_orc: 34000, lucro_liquido_real: 0, desvio_receita: null, desvio_lucro: null },
    { mes: 8,  receita_bruta_orc: 190000, receita_bruta_real: 0, lucro_liquido_orc: 35000, lucro_liquido_real: 0, desvio_receita: null, desvio_lucro: null },
    { mes: 9,  receita_bruta_orc: 195000, receita_bruta_real: 0, lucro_liquido_orc: 36000, lucro_liquido_real: 0, desvio_receita: null, desvio_lucro: null },
    { mes: 10, receita_bruta_orc: 200000, receita_bruta_real: 0, lucro_liquido_orc: 38000, lucro_liquido_real: 0, desvio_receita: null, desvio_lucro: null },
    { mes: 11, receita_bruta_orc: 210000, receita_bruta_real: 0, lucro_liquido_orc: 40000, lucro_liquido_real: 0, desvio_receita: null, desvio_lucro: null },
    { mes: 12, receita_bruta_orc: 240000, receita_bruta_real: 0, lucro_liquido_orc: 55000, lucro_liquido_real: 0, desvio_receita: null, desvio_lucro: null },
  ];

  const isDemo = !empresaId || (!comparativo && !carregando);
  const compVisiveis: Comparativo | null  = comparativo  ?? (isDemo ? DEMO_COMP  : null);
  const anualVisiveis: MesAnual[] = anual.length > 0 ? anual : (isDemo ? DEMO_ANUAL : []);

  const inicialModal: Partial<OrcamentoForm> | undefined = compVisiveis && !compVisiveis.sem_orcamento
    ? {
        receita_bruta:        String(compVisiveis.receita_bruta.orcado),
        deducoes_receita:     String(compVisiveis.deducoes_receita.orcado),
        custo_servicos:       String(compVisiveis.custo_servicos.orcado),
        despesas_adm:         String(compVisiveis.despesas_adm.orcado),
        despesas_comerciais:  String(compVisiveis.despesas_comerciais.orcado),
        despesas_financeiras: String(compVisiveis.despesas_financeiras.orcado),
        outras_despesas:      String(compVisiveis.outras_despesas.orcado),
        ir_csll:              String(compVisiveis.ir_csll.orcado),
        entradas_caixa:       String(compVisiveis.entradas_caixa.orcado),
        saidas_caixa:         String(compVisiveis.saidas_caixa.orcado),
        folha_pagamento:      String(compVisiveis.folha_pagamento.orcado),
      }
    : undefined;

  const dadosGrafico = anualVisiveis.map(m => ({
    name: MESES_LABEL[m.mes - 1],
    "Receita Orçada": m.receita_bruta_orc,
    "Receita Realizada": m.receita_bruta_real,
    "Lucro Orç.": m.lucro_liquido_orc,
    "Lucro Real.": m.lucro_liquido_real,
  }));

  const semDados = false;

  return (
    <div className="min-h-full" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>

      {/* ── Header ── */}
      <header
        className="px-8 pt-8 pb-0 bg-white dark:bg-slate-900/95 border-b border-[#E2E8F0] dark:border-slate-700"
      >
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-5">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-navy-50 border border-navy-200 dark:bg-navy-900/30 dark:border-navy-700/50">
                <svg className="w-5 h-5 text-navy-600 dark:text-navy-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100">
                Orçamento{" "}
                <span className="text-navy-600 dark:text-navy-400">vs. Realizado</span>
              </h1>
            </div>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Acompanhe o desempenho financeiro frente às metas</p>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={mes}
              onChange={e => setMes(Number(e.target.value))}
              className="rounded-xl px-3 py-2 text-sm outline-none"
              style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
            >
              {MESES_LABEL.map((m, i) => <option key={i + 1} value={i + 1}>{m}</option>)}
            </select>
            <select
              value={ano}
              onChange={e => setAno(Number(e.target.value))}
              className="rounded-xl px-3 py-2 text-sm outline-none"
              style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
            >
              {ANOS.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
            {empresaId && (
              <button
                onClick={() => setShowModal(true)}
                data-notheme className="flex items-center gap-1.5 text-white text-sm font-bold px-4 py-2 rounded-xl transition-all bg-[#102a43] hover:bg-[#0a1f33]"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                {compVisiveis && !compVisiveis.sem_orcamento ? "Editar orçamento" : "Cadastrar orçamento"}
              </button>
            )}
          </div>
        </div>

        {/* Tab navigation */}
        <div className="flex gap-1">
          {(["mensal", "anual"] as const).map(t => (
            <button
              key={t}
              onClick={() => setAba(t)}
              className={`px-5 py-2.5 text-sm font-semibold border-b-2 transition-all ${
                aba === t
                  ? "border-navy-500 text-navy-600 dark:text-navy-400"
                  : "border-transparent text-slate-500 dark:text-slate-400"
              }`}
            >
              {t === "mensal" ? "Mensal" : "Visão Anual"}
            </button>
          ))}
        </div>
      </header>

      <div className="px-8 py-8">
        {isDemo && !carregando && (
          <div className="mb-6 flex items-center gap-2 px-4 py-2.5 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30 rounded-xl text-amber-700 dark:text-amber-300 text-sm">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span><strong>Dados de Demonstração</strong> — Selecione uma empresa para visualizar seus dados reais.</span>
          </div>
        )}
        {carregando ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <div className="w-10 h-10 rounded-full animate-spin" style={{ border: "3px solid rgba(79,106,255,0.15)", borderTopColor: "#102a43" }} />
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Carregando dados...</p>
          </div>
        ) : aba === "mensal" ? (
          // ── ABA MENSAL ────────────────────────────────────────────────
          compVisiveis?.sem_orcamento ? (
            <div
              className="flex flex-col items-center gap-4 py-20 rounded-2xl"
              style={{
                border: "1px dashed rgba(79,106,255,0.2)",
                background: "rgba(79,106,255,0.02)",
              }}
            >
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center"
                style={{
                  background: "rgba(79,106,255,0.08)",
                  border: "1px solid rgba(79,106,255,0.15)",
                }}
              >
                <svg className="w-7 h-7" style={{ color: "rgba(79,106,255,0.5)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <p className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>
                Nenhum orçamento cadastrado para {MESES_LABEL[mes - 1]}/{ano}.
              </p>
              <p className="text-xs max-w-md text-center" style={{ color: "var(--text-muted)" }}>
                Defina metas mensais de receita, custos e despesas para acompanhar o desempenho real da empresa vs. o planejado.
              </p>
              <div className="flex flex-wrap gap-2 justify-center mt-2">
                {["Receita Bruta", "Custos", "Despesas Adm.", "Folha", "IR+CSLL"].map(cat => (
                  <span key={cat} className="text-[10px] font-medium px-2.5 py-1 rounded-full" style={{ background: "rgba(59,110,165,0.08)", border: "1px solid rgba(59,110,165,0.2)", color: "#3b6ea5" }}>
                    {cat}
                  </span>
                ))}
              </div>
              <button
                onClick={() => setShowModal(true)}
                data-notheme className="text-white text-sm font-bold px-6 py-2.5 rounded-xl transition-all bg-[#102a43] hover:bg-[#0a1f33] mt-2"
              >
                Cadastrar orçamento
              </button>
            </div>
          ) : compVisiveis ? (
            <div className="space-y-6">
              {/* Aderência + Totais */}
              {(() => {
                const totalOrc = compVisiveis.receita_bruta.orcado;
                const totalReal = compVisiveis.receita_bruta.realizado;
                const economia = totalReal - totalOrc;
                const aderencia = totalOrc > 0 ? Math.min(100, Math.max(0, 100 - Math.abs(((totalReal - totalOrc) / totalOrc) * 100))) : 0;
                const aderCor = aderencia >= 90 ? "#1A6B3C" : aderencia >= 70 ? "#92400E" : "#B83030";
                return (
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="rounded-2xl p-4 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                      <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Total Orçado</p>
                      <p className="text-lg font-black font-mono mt-1" style={{ color: "#3b6ea5" }}>{fmt(totalOrc)}</p>
                    </div>
                    <div className="rounded-2xl p-4 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                      <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Total Realizado</p>
                      <p className="text-lg font-black font-mono mt-1" style={{ color: "var(--text-primary)" }}>{fmt(totalReal)}</p>
                    </div>
                    <div className="rounded-2xl p-4 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                      <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{economia >= 0 ? "Superávit" : "Déficit"}</p>
                      <p className="text-lg font-black font-mono mt-1" style={{ color: economia >= 0 ? "#1A6B3C" : "#B83030" }}>{fmt(economia)}</p>
                    </div>
                    <div className="rounded-2xl p-4 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                      <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Aderência</p>
                      <p className="text-lg font-black font-mono mt-1" style={{ color: aderCor }}>{aderencia.toFixed(0)}%</p>
                      <div className="w-full h-1.5 rounded-full mt-2 overflow-hidden" style={{ background: "var(--border)" }}>
                        <div className="h-full rounded-full" style={{ width: `${aderencia}%`, background: aderCor }} />
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* Summary metric cards */}
              <div className="grid grid-cols-3 gap-4">
                {[
                  {
                    label: "Receita Bruta",
                    par: compVisiveis.receita_bruta,
                    icon: (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    ),
                  },
                  {
                    label: "Receita Líquida",
                    par: compVisiveis.receita_liquida,
                    icon: (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z" />
                      </svg>
                    ),
                  },
                  {
                    label: "Lucro Líquido",
                    par: compVisiveis.lucro_liquido,
                    icon: (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                      </svg>
                    ),
                  },
                ].map(({ label, par, icon }) => (
                  <div
                    key={label}
                    className="rounded-2xl p-5 relative overflow-hidden"
                    style={{
                      background: "var(--bg-card)",
                      border: "1px solid var(--border)",
                      boxShadow: "0 4px 24px rgba(0,0,0,0.25)",
                    }}
                  >
                    {/* Top accent gradient line */}
                    <div
                      className="absolute top-0 left-0 right-0 h-[1px]"
                      style={{
                        background: par.status === "ok"
                          ? "linear-gradient(90deg, #10b981 0%, transparent 100%)"
                          : par.status === "atencao"
                          ? "linear-gradient(90deg, #f59e0b 0%, transparent 100%)"
                          : par.status === "critico"
                          ? "linear-gradient(90deg, #ef4444 0%, transparent 100%)"
                          : "linear-gradient(90deg, #102a43 0%, transparent 100%)",
                      }}
                    />
                    <div className="flex items-start justify-between mb-3">
                      <p className="text-[11px] font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>{label}</p>
                      <div
                        className="w-8 h-8 rounded-xl flex items-center justify-center"
                        style={{
                          background: "rgba(79,106,255,0.10)",
                          border: "1px solid rgba(79,106,255,0.20)",
                          color: "#3b6ea5",
                        }}
                      >
                        {icon}
                      </div>
                    </div>
                    <p className="text-2xl font-black font-mono" style={{ color: "var(--text-primary)" }}>{fmt(par.realizado)}</p>
                    <div className="flex items-center justify-between mt-2">
                      <p className="text-xs" style={{ color: "var(--text-muted)" }}>Meta: {fmt(par.orcado)}</p>
                      <span className={`text-xs font-bold ${statusCor(par.status)}`}>{fmtPct(par.variacao)}</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Warning: no entries */}
              {compVisiveis.sem_lancamento && (
                <div
                  className="px-4 py-3 rounded-xl text-sm"
                  style={{
                    background: "rgba(245,158,11,0.08)",
                    border: "1px solid rgba(245,158,11,0.20)",
                    color: "#fbbf24",
                  }}
                >
                  Nenhum dado real lançado para este período. Os valores de "Realizado" estão zerados.
                </div>
              )}

              {/* Comparative table */}
              <div
                className="rounded-2xl overflow-hidden"
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  boxShadow: "0 4px 24px rgba(0,0,0,0.25)",
                }}
              >
                {/* Top accent */}
                <div style={{ height: "1px", background: "linear-gradient(90deg, #102a43 0%, #3b6ea5 60%, transparent 100%)" }} />
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
                    <tr>
                      {["Linha", "Orçado", "Realizado", "Desvio", "Status"].map((h, i) => (
                        <th
                          key={h}
                          className={`px-4 py-3 text-[11px] font-bold uppercase tracking-widest ${i === 0 ? "text-left" : i < 4 ? "text-right" : "text-center"}`}
                          style={{ color: "var(--text-muted)" }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <LinhaComparativa label="Receita Bruta"          par={compVisiveis.receita_bruta} />
                    <LinhaComparativa label="(–) Deduções"           par={compVisiveis.deducoes_receita} invertido />
                    <LinhaComparativa label="= Receita Líquida"      par={compVisiveis.receita_liquida} destaque />
                    <LinhaComparativa label="(–) Custo dos Serviços" par={compVisiveis.custo_servicos} invertido />
                    <LinhaComparativa label="= Lucro Bruto"          par={compVisiveis.lucro_bruto} destaque />
                    <LinhaComparativa label="(–) Despesas Adm."      par={compVisiveis.despesas_adm} invertido />
                    <LinhaComparativa label="(–) Desp. Comerciais"   par={compVisiveis.despesas_comerciais} invertido />
                    <LinhaComparativa label="(–) Desp. Financeiras"  par={compVisiveis.despesas_financeiras} invertido />
                    <LinhaComparativa label="(–) Outras Despesas"    par={compVisiveis.outras_despesas} invertido />
                    <LinhaComparativa label="(–) IR + CSLL"          par={compVisiveis.ir_csll} invertido />
                    <LinhaComparativa label="= Lucro Líquido"        par={compVisiveis.lucro_liquido} destaque />
                    <tr><td colSpan={5} className="py-2" /></tr>
                    <LinhaComparativa label="Entradas de Caixa"      par={compVisiveis.entradas_caixa} />
                    <LinhaComparativa label="Saídas de Caixa"        par={compVisiveis.saidas_caixa} invertido />
                    <LinhaComparativa label="Folha de Pagamento"      par={compVisiveis.folha_pagamento} invertido />
                  </tbody>
                </table>
              </div>
            </div>
          ) : null
        ) : (
          // ── ABA ANUAL ─────────────────────────────────────────────────
          <div className="space-y-6">
            {anualVisiveis.length === 0 ? (
              <div
                className="flex flex-col items-center justify-center py-20 rounded-2xl gap-3"
                style={{
                  border: "1px dashed rgba(79,106,255,0.2)",
                  background: "rgba(79,106,255,0.02)",
                }}
              >
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center"
                  style={{ background: "rgba(79,106,255,0.08)", border: "1px solid rgba(79,106,255,0.15)" }}
                >
                  <svg className="w-7 h-7" style={{ color: "rgba(79,106,255,0.5)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <p className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>
                  Nenhum orçamento cadastrado para {ano}.
                </p>
                <p className="text-xs text-center" style={{ color: "var(--text-muted)" }}>
                  Selecione um mês e cadastre orçamentos mês a mês.
                </p>
              </div>
            ) : (
              <>
                {/* Chart: Revenue */}
                <GraficoComNome>
                <div
                  className="rounded-2xl p-5 relative overflow-hidden"
                  style={{
                    background: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    boxShadow: "0 4px 24px rgba(0,0,0,0.25)",
                  }}
                >
                  <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: "1px", background: "linear-gradient(90deg, #102a43 0%, #3b6ea5 60%, transparent 100%)" }} />
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-1 h-4 rounded-full" style={{ background: "#102a43", boxShadow: "0 0 8px rgba(79,106,255,0.6)" }} />
                    <h3 className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Receita — Orçado × Realizado {ano}</h3>
                  </div>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={dadosGrafico}>
                      <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
                      <XAxis dataKey="name" tick={{ fill: ct.tickFill, fontSize: 11 }} />
                      <YAxis tick={{ fill: ct.tickFill, fontSize: 11 }} tickFormatter={v => `${((v as number) / 1000).toFixed(0)}k`} />
                      <Tooltip contentStyle={ct.tooltipStyle} labelStyle={ct.tooltipLabelStyle} itemStyle={ct.tooltipItemStyle} formatter={v => fmt(v as number)} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Bar dataKey="Receita Orçada"   fill="#1E4976" radius={[3,3,0,0]} />
                      <Bar dataKey="Receita Realizada" fill="#3b6ea5" radius={[3,3,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                </GraficoComNome>

                {/* Chart: Profit */}
                <GraficoComNome>
                <div
                  className="rounded-2xl p-5 relative overflow-hidden"
                  style={{
                    background: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    boxShadow: "0 4px 24px rgba(0,0,0,0.25)",
                  }}
                >
                  <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: "1px", background: "linear-gradient(90deg, #10b981 0%, transparent 100%)" }} />
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-1 h-4 rounded-full" style={{ background: "#10b981", boxShadow: "0 0 8px rgba(16,185,129,0.6)" }} />
                    <h3 className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Lucro Líquido — Orçado × Realizado {ano}</h3>
                  </div>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={dadosGrafico}>
                      <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
                      <XAxis dataKey="name" tick={{ fill: ct.tickFill, fontSize: 11 }} />
                      <YAxis tick={{ fill: ct.tickFill, fontSize: 11 }} tickFormatter={v => `${((v as number) / 1000).toFixed(0)}k`} />
                      <Tooltip contentStyle={ct.tooltipStyle} labelStyle={ct.tooltipLabelStyle} itemStyle={ct.tooltipItemStyle} formatter={v => fmt(v as number)} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Bar dataKey="Lucro Orç."   fill="#065f46" radius={[3,3,0,0]} />
                      <Bar dataKey="Lucro Real."  fill="#10b981" radius={[3,3,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                </GraficoComNome>

                {/* Annual table */}
                <div
                  className="rounded-2xl overflow-hidden"
                  style={{
                    background: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    boxShadow: "0 4px 24px rgba(0,0,0,0.25)",
                  }}
                >
                  <div style={{ height: "1px", background: "linear-gradient(90deg, #102a43 0%, #3b6ea5 60%, transparent 100%)" }} />
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
                      <tr>
                        {["Mês","Rec. Orçada","Rec. Realizada","Desvio Rec.","Lucro Orçado","Lucro Real.","Desvio Lucro"].map((h, i) => (
                          <th
                            key={h}
                            className={`px-4 py-3 text-[11px] font-bold uppercase tracking-widest ${i === 0 ? "text-left" : "text-right"}`}
                            style={{ color: "var(--text-muted)" }}
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {anualVisiveis.map(m => (
                        <tr key={m.mes} className="border-b border-slate-100 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/30">
                          <td className="px-4 py-2.5 font-semibold text-slate-700 dark:text-slate-300">{MESES_LABEL[m.mes - 1]}</td>
                          <td className="px-4 py-2.5 text-right font-mono text-slate-500 dark:text-slate-400 text-xs">{fmt(m.receita_bruta_orc)}</td>
                          <td className="px-4 py-2.5 text-right font-mono text-slate-800 dark:text-slate-200 text-xs">{fmt(m.receita_bruta_real)}</td>
                          <td className={`px-4 py-2.5 text-right font-mono text-xs font-bold ${(m.desvio_receita ?? 0) >= -5 ? "text-emerald-600 dark:text-emerald-400" : (m.desvio_receita ?? 0) >= -20 ? "text-amber-600 dark:text-amber-400" : "text-rose-600 dark:text-rose-400"}`}>
                            {fmtPct(m.desvio_receita)}
                          </td>
                          <td className="px-4 py-2.5 text-right font-mono text-slate-500 dark:text-slate-400 text-xs">{fmt(m.lucro_liquido_orc)}</td>
                          <td className="px-4 py-2.5 text-right font-mono text-slate-800 dark:text-slate-200 text-xs">{fmt(m.lucro_liquido_real)}</td>
                          <td className={`px-4 py-2.5 text-right font-mono text-xs font-bold ${(m.desvio_lucro ?? 0) >= -5 ? "text-emerald-600 dark:text-emerald-400" : (m.desvio_lucro ?? 0) >= -20 ? "text-amber-600 dark:text-amber-400" : "text-rose-600 dark:text-rose-400"}`}>
                            {fmtPct(m.desvio_lucro)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && empresaId && (
        <ModalOrcamento
          token={localStorage.getItem("controllo_token") ?? ""}
          empresaId={empresaId}
          ano={ano}
          mes={mes}
          inicial={inicialModal}
          onClose={() => setShowModal(false)}
          onSaved={() => { setShowModal(false); carregar(); }}
        />
      )}
    </div>
  );
}
