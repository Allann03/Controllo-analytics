"use client";
import { useEffect, useState, useCallback, useMemo } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

const fmt = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v);

interface InsightItem {
  id: string;
  categoria: string;
  severidade: string;
  titulo: string;
  mensagem: string;
  valor_atual?: number;
  valor_referencia?: number;
}
interface InsightsData {
  empresa_id: number;
  periodo_referencia: string;
  total: number;
  criticos: number;
  atencao: number;
  info: number;
  insights: InsightItem[];
  sem_dados?: boolean;
}

type Filtro = "todos" | "critico" | "atencao" | "info" | "tributario" | "operacional" | "caixa" | "patrimonial";

const CATEGORIAS: { key: Filtro; label: string }[] = [
  { key: "todos",       label: "Todos" },
  { key: "critico",     label: "Crítico" },
  { key: "atencao",     label: "Atenção" },
  { key: "info",        label: "Informativo" },
  { key: "operacional", label: "Operacional" },
  { key: "caixa",       label: "Caixa" },
  { key: "patrimonial", label: "Patrimonial" },
  { key: "tributario",  label: "Tributário" },
];

const SEV_CFG = {
  critico: {
    label: "Crítico",
    accentBg: "#B83030",
    cardBg: "bg-rose-50 dark:bg-rose-500/8",
    cardBorder: "border-rose-200 dark:border-rose-500/25",
    titleColor: "text-rose-800 dark:text-rose-300",
    textColor: "text-rose-700 dark:text-rose-400",
    badgeBg: "bg-rose-100 dark:bg-rose-500/15 border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-400",
    icon: (
      <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
  },
  atencao: {
    label: "Atenção",
    accentBg: "#92400E",
    cardBg: "bg-amber-50 dark:bg-amber-500/8",
    cardBorder: "border-amber-200 dark:border-amber-500/25",
    titleColor: "text-amber-800 dark:text-amber-300",
    textColor: "text-amber-700 dark:text-amber-400",
    badgeBg: "bg-amber-100 dark:bg-amber-500/15 border-amber-200 dark:border-amber-500/30 text-amber-700 dark:text-amber-400",
    icon: (
      <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      </svg>
    ),
  },
  info: {
    label: "Informativo",
    accentBg: "#1E4976",
    cardBg: "bg-blue-50 dark:bg-blue-500/8",
    cardBorder: "border-blue-200 dark:border-blue-500/25",
    titleColor: "text-blue-800 dark:text-blue-300",
    textColor: "text-blue-700 dark:text-blue-400",
    badgeBg: "bg-blue-100 dark:bg-blue-500/15 border-blue-200 dark:border-blue-500/30 text-blue-700 dark:text-blue-400",
    icon: (
      <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
} as Record<string, { label: string; accentBg: string; cardBg: string; cardBorder: string; titleColor: string; textColor: string; badgeBg: string; icon: React.ReactNode }>;

const CAT_LABELS: Record<string, string> = {
  operacional: "Operacional",
  caixa: "Caixa",
  patrimonial: "Patrimonial",
  tributario: "Tributário",
};

function getRecommendation(ins: InsightItem): string {
  const cat = ins.categoria;
  const sev = ins.severidade;
  if (sev === "critico") {
    if (cat === "caixa") return "Revise imediatamente o fluxo de caixa e considere renegociar prazos com fornecedores. Priorize a cobrança de recebíveis em atraso.";
    if (cat === "operacional") return "Analise as despesas operacionais linha a linha. Identifique custos que cresceram acima da inflação e renegocie contratos.";
    if (cat === "patrimonial") return "Verifique a composição do endividamento e o prazo das obrigações. Considere reestruturar a dívida se necessário.";
    if (cat === "tributario") return "Consulte o planejamento tributário. Pode haver oportunidades de recuperação de créditos ou mudança de regime.";
    return "Este indicador requer atenção imediata. Reúna-se com a equipe para definir um plano de ação corretivo.";
  }
  if (sev === "atencao") {
    if (cat === "caixa") return "Monitore o capital de giro nas próximas semanas. Considere antecipar recebíveis se o fluxo apertar.";
    if (cat === "operacional") return "Acompanhe a evolução mensal das despesas. Defina alertas para desvios acima de 10% do orçado.";
    if (cat === "patrimonial") return "Avalie a necessidade de novos investimentos e o impacto no endividamento.";
    if (cat === "tributario") return "Verifique se há créditos tributários a compensar ou obrigações acessórias pendentes.";
    return "Acompanhe este indicador nos próximos meses. Se a tendência persistir, ação corretiva será necessária.";
  }
  return "Indicador dentro dos parâmetros esperados. Continue monitorando para manter a performance.";
}

function generateNarrative(dados: InsightsData): string {
  const { criticos, atencao, info } = dados;
  const parts: string[] = [];
  if (criticos > 0) {
    parts.push(`Foram identificados ${criticos} ponto${criticos > 1 ? "s" : ""} crítico${criticos > 1 ? "s" : ""} que requerem ação imediata.`);
  }
  if (atencao > 0) {
    parts.push(`${atencao} indicador${atencao > 1 ? "es" : ""} está${atencao > 1 ? "ão" : ""} em nível de atenção e deve${atencao > 1 ? "m" : ""} ser monitorado${atencao > 1 ? "s" : ""} de perto.`);
  }
  if (info > 0) {
    parts.push(`${info} insight${info > 1 ? "s" : ""} informativo${info > 1 ? "s" : ""} complementa${info > 1 ? "m" : ""} a análise.`);
  }
  if (criticos === 0 && atencao === 0) {
    parts.push("A empresa apresenta indicadores saudáveis neste período. Todos os pontos monitorados estão dentro dos parâmetros esperados.");
  } else if (criticos > 0 && atencao > 0) {
    parts.push("Recomenda-se priorizar os pontos críticos e estabelecer acompanhamento semanal para os indicadores em atenção.");
  }
  return parts.join(" ");
}

function InsightCard({ ins, periodo }: { ins: InsightItem; periodo?: string }) {
  const cfg = SEV_CFG[ins.severidade] ?? SEV_CFG.info;
  const catLabel = CAT_LABELS[ins.categoria] ?? ins.categoria;

  const fmtValor = (v: number) =>
    Math.abs(v) > 100
      ? v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 })
      : `${v.toFixed(2)}%`;

  const hasValues = ins.valor_atual != null && ins.valor_referencia != null;
  const desvio = hasValues
    ? ((ins.valor_atual! - ins.valor_referencia!) / Math.abs(ins.valor_referencia! || 1)) * 100
    : null;

  return (
    <div className={`rounded-2xl border overflow-hidden ${cfg.cardBg} ${cfg.cardBorder}`}>
      <div className="h-0.5 w-full" style={{ background: cfg.accentBg }} />
      <div className="p-5">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-0.5" style={{ color: cfg.accentBg }}>{cfg.icon}</div>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <p className={`text-sm font-bold leading-tight ${cfg.titleColor}`}>{ins.titulo}</p>
              <span className={`inline-flex items-center gap-1 text-[9px] font-black uppercase px-2 py-0.5 rounded-full border ${cfg.badgeBg}`}>
                {cfg.label}
              </span>
              <span className="text-[9px] font-semibold uppercase text-[#64748B] dark:text-slate-500 bg-slate-200 dark:bg-slate-700/50 px-2 py-0.5 rounded-full border border-slate-300 dark:border-slate-600/50">
                {catLabel}
              </span>
              {periodo && (
                <span className="text-[9px] font-semibold text-slate-400 dark:text-slate-500">
                  Ref: {periodo}
                </span>
              )}
            </div>
            <p className={`text-sm leading-relaxed ${cfg.textColor}`}>{ins.mensagem}</p>

            {/* Actionable recommendation */}
            <div className="mt-3 pt-3 border-t border-current/10">
              <div className="flex items-start gap-2">
                <svg className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" style={{ color: cfg.accentBg }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest mb-1" style={{ color: cfg.accentBg }}>
                    Recomendação
                  </p>
                  <p className={`text-xs leading-relaxed ${cfg.textColor} opacity-80`}>
                    {getRecommendation(ins)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
        {hasValues && (
          <div className="mt-4 pt-4 border-t border-current/10 grid grid-cols-3 gap-3">
            <div className="text-center">
              <p className="text-[9px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-1">Valor Atual</p>
              <p className={`text-base font-black font-mono tabular-nums ${cfg.titleColor}`}>{fmtValor(ins.valor_atual!)}</p>
            </div>
            <div className="text-center flex flex-col items-center justify-center">
              <p className="text-[9px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-1">Desvio</p>
              <p className={`text-sm font-black font-mono tabular-nums ${
                desvio !== null && Math.abs(desvio) < 5 ? "text-[#1A6B3C] dark:text-emerald-400" : cfg.textColor
              }`}>
                {desvio !== null ? `${desvio >= 0 ? "+" : ""}${desvio.toFixed(1)}%` : "—"}
              </p>
            </div>
            <div className="text-center">
              <p className="text-[9px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-1">Referência</p>
              <p className="text-base font-bold font-mono tabular-nums text-[#64748B] dark:text-slate-500">{fmtValor(ins.valor_referencia!)}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function SummaryKPI({ label, count, cfg }: { label: string; count: number; cfg: typeof SEV_CFG[string] }) {
  return (
    <div className={`rounded-2xl border overflow-hidden ${cfg.cardBg} ${cfg.cardBorder}`}>
      <div className="h-0.5 w-full" style={{ background: cfg.accentBg }} />
      <div className="px-4 py-3 flex items-center gap-3">
        <div style={{ color: cfg.accentBg }}>{cfg.icon}</div>
        <div>
          <p className={`text-[9px] font-black uppercase tracking-widest ${cfg.textColor}`}>{label}</p>
          <p className={`text-2xl font-black font-mono tabular-nums leading-none mt-0.5 ${cfg.titleColor}`}>{count}</p>
        </div>
      </div>
    </div>
  );
}

export default function InsightsPage() {
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const [dados, setDados] = useState<InsightsData | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [filtro, setFiltro] = useState<Filtro>("todos");

  // Simulação rápida
  const [simReceita, setSimReceita] = useState("100000");
  const [simCustos, setSimCustos] = useState("40000");
  const [simDespesas, setSimDespesas] = useState("20000");
  const [simRegime, setSimRegime] = useState<"simples" | "presumido" | "real">("simples");

  const h = () => ({ Authorization: `Bearer ${localStorage.getItem("controllo_token") || ""}` });

  const carregar = useCallback(async (signal?: AbortSignal) => {
    if (!empresaId) { setCarregando(false); return; }
    setCarregando(true); setErro(null); setDados(null);
    try {
      const r = await fetch(`${API}/api/financeiro/insights/${empresaId}`, { headers: h(), signal });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Erro ao carregar.");
      setDados(d);
    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") return;
      setErro(e instanceof Error ? e.message : "Erro desconhecido.");
    }
    finally { setCarregando(false); }
  }, [empresaId]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60_000);
    carregar(controller.signal);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [carregar]);

  const insightsFiltrados = (dados?.insights ?? []).filter(i => {
    if (filtro === "todos") return true;
    if (filtro === "critico" || filtro === "atencao" || filtro === "info") return i.severidade === filtro;
    return i.categoria === filtro;
  });

  const criticos = insightsFiltrados.filter(i => i.severidade === "critico");
  const atencao  = insightsFiltrados.filter(i => i.severidade === "atencao");
  const infoList = insightsFiltrados.filter(i => i.severidade === "info");

  const nomeSelecionado = empresaSelecionada?.nome;

  // Simulador de cenario — calculo local permitido APENAS porque os inputs
  // sao manipulados pelo usuario, nao vem da API. Formula deve espelhar
  // exatamente services/contabil/dre.py. Divergencia e bug.
  // Referencia: BLOCO 3B.2, mandato R3.
  const simResultado = useMemo(() => {
    const rb = parseFloat(simReceita) || 0;
    const custos = parseFloat(simCustos) || 0;
    const desp = parseFloat(simDespesas) || 0;  // despesas operacionais SEM financeiras
    const lucrobruto = rb - custos;
    // EBITDA = Lucro Bruto - Despesas Operacionais (sem financeiras, espelha dre.py)
    const ebitda = lucrobruto - desp;
    const margemBruta = rb > 0 ? (lucrobruto / rb) * 100 : 0;
    const margemLiquida = rb > 0 ? (ebitda / rb) * 100 : 0;
    let impostos = 0;
    if (simRegime === "simples") impostos = rb * 0.06;
    else if (simRegime === "presumido") impostos = rb * (0.15 + 0.09 + 0.0065 + 0.03 + 0.05);
    else impostos = Math.max(0, ebitda) * (0.15 + 0.09) + rb * (0.0165 + 0.076 + 0.05);
    const lucroLiquido = ebitda - impostos;
    const margemLiquPos = rb > 0 ? (lucroLiquido / rb) * 100 : 0;
    const cargaTrib = rb > 0 ? (impostos / rb) * 100 : 0;
    return { rb, custos, desp, lucrobruto, ebitda, impostos, lucroLiquido, margemBruta, margemLiquida, margemLiquPos, cargaTrib };
  }, [simReceita, simCustos, simDespesas, simRegime]);

  const simCor = {
    lucrobruto:   simResultado.lucrobruto   >= 0 ? "#1A6B3C" : "#B83030",
    ebitda:       simResultado.ebitda       >= 0 ? "#1E4976" : "#B83030",
    lucroLiquido: simResultado.lucroLiquido >= 0 ? "#1A6B3C" : "#B83030",
    margemBruta:  simResultado.margemBruta  >= 20 ? "#1A6B3C" : simResultado.margemBruta  >= 10 ? "#92400E" : "#B83030",
    cargaTrib:    simResultado.cargaTrib    <= 15 ? "#1A6B3C" : simResultado.cargaTrib    <= 25 ? "#92400E" : "#B83030",
  };

  // Cenário "E se?"
  const [cenarioPct, setCenarioPct] = useState(0);
  const cenarioReceita = (parseFloat(simReceita) || 0) * (1 + cenarioPct / 100);
  const cenarioLucroBruto = cenarioReceita - (parseFloat(simCustos) || 0);
  const cenarioEbitda = cenarioLucroBruto - (parseFloat(simDespesas) || 0);
  let cenarioImpostos = 0;
  if (simRegime === "simples") cenarioImpostos = cenarioReceita * 0.06;
  else if (simRegime === "presumido") cenarioImpostos = cenarioReceita * (0.15 + 0.09 + 0.0065 + 0.03 + 0.05);
  else cenarioImpostos = Math.max(0, cenarioEbitda) * (0.15 + 0.09) + cenarioReceita * (0.0165 + 0.076 + 0.05);
  const cenarioLucro = cenarioEbitda - cenarioImpostos;

  // KPI cards definition for the simulation dashboard
  const simKpis = [
    {
      label: "Receita Líquida",
      sub: "Após impostos",
      value: simResultado.rb > 0 ? simResultado.rb - simResultado.impostos : 0,
      pct: simResultado.rb > 0 ? ((simResultado.rb - simResultado.impostos) / simResultado.rb) * 100 : 0,
      cor: "#1E4976",
      barMax: 100,
    },
    {
      label: "Lucro Bruto",
      sub: `Margem ${simResultado.margemBruta.toFixed(1)}%`,
      value: simResultado.lucrobruto,
      pct: simResultado.margemBruta,
      cor: simCor.lucrobruto,
      barMax: 60,
    },
    {
      label: "EBITDA",
      sub: `Margem ${simResultado.margemLiquida.toFixed(1)}%`,
      value: simResultado.ebitda,
      pct: simResultado.margemLiquida,
      cor: simCor.ebitda,
      barMax: 40,
    },
    {
      label: "Lucro Líquido",
      sub: `Margem ${simResultado.margemLiquPos.toFixed(1)}%`,
      value: simResultado.lucroLiquido,
      pct: simResultado.margemLiquPos,
      cor: simCor.lucroLiquido,
      barMax: 30,
    },
    {
      label: "Carga Tributária",
      sub: simRegime === "simples" ? "Simples Nacional" : simRegime === "presumido" ? "Lucro Presumido" : "Lucro Real",
      value: simResultado.impostos,
      pct: simResultado.cargaTrib,
      cor: simCor.cargaTrib,
      barMax: 40,
    },
    {
      label: "Margem Bruta",
      sub: simResultado.margemBruta >= 20 ? "Saudável" : simResultado.margemBruta >= 10 ? "Atenção" : "Crítico",
      value: null,
      pct: simResultado.margemBruta,
      cor: simCor.margemBruta,
      barMax: 60,
    },
  ] as { label: string; sub: string; value: number | null; pct: number; cor: string; barMax: number }[];

  return (
    <div className="min-h-full p-6 md:p-8" style={{ background: "var(--bg-primary)" }}>

      {/* ── Header ── */}
      <header className="mb-6">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 mb-3">
              <div className="w-1 h-5 rounded-full bg-[#1E4976]" />
              <span className="text-[10px] font-black uppercase tracking-widest text-[#64748B] dark:text-slate-500">
                Inteligência Financeira
              </span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight" style={{ color: "var(--text-primary)" }}>
              Insights <span style={{ color: "#1E4976" }}>Financeiros</span>
            </h1>
            <p className="text-sm mt-1.5 text-[#64748B] dark:text-slate-400">
              Alertas automáticos baseados em regras de negócio e benchmarks setoriais
              {dados?.periodo_referencia && (
                <> · <span className="font-semibold text-[#0F172A] dark:text-slate-200">{dados.periodo_referencia}</span></>
              )}
            </p>
          </div>
          {dados && !dados.sem_dados && (
            <div className="grid grid-cols-3 gap-3 min-w-[280px]">
              <SummaryKPI label="Críticos" count={dados.criticos} cfg={SEV_CFG.critico} />
              <SummaryKPI label="Atenção"  count={dados.atencao}  cfg={SEV_CFG.atencao} />
              <SummaryKPI label="Info"     count={dados.info}     cfg={SEV_CFG.info} />
            </div>
          )}
        </div>
      </header>

      {/* ── Compact "no empresa" banner ── */}
      {!empresaId && (
        <div className="mb-6 flex items-center gap-3 px-4 py-3 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30 rounded-xl">
          <svg className="w-4 h-4 flex-shrink-0 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm text-amber-800 dark:text-amber-300">
            <span className="font-semibold">Selecione uma empresa</span> no menu superior para visualizar os insights e alertas automáticos.
          </p>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════
          CFO DASHBOARD — Análise Rápida (sempre visível)
      ══════════════════════════════════════════════════════════════ */}
      <div className="mb-8 bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">

        {/* Panel header */}
        <div className="px-6 pt-5 pb-4 border-b border-slate-100 dark:border-slate-700/60">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="w-0.5 h-5 rounded-full bg-[#1E4976]" />
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-black uppercase tracking-widest text-[#64748B] dark:text-slate-400">Análise Rápida</span>
                  <span className="text-[10px] text-[#64748B] dark:text-slate-500 bg-slate-100 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600/50 px-2 py-0.5 rounded-full font-medium">
                    DRE Simplificada
                  </span>
                </div>
                <p className="text-[10px] text-[#94A3B8] dark:text-slate-600 mt-0.5">Simulação em tempo real · Ajuste os valores abaixo</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-[10px] text-[#94A3B8] dark:text-slate-600">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse" />
              Cálculo automático
            </div>
          </div>
        </div>

        <div className="p-6 space-y-6">

          {/* ── Inputs ── */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Receita Bruta (R$)", value: simReceita, set: setSimReceita },
              { label: "Custos (R$)",         value: simCustos,  set: setSimCustos  },
              { label: "Despesas (R$)",       value: simDespesas,set: setSimDespesas },
            ].map(({ label, value, set }) => (
              <div key={label}>
                <label className="block text-[10px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-1.5">{label}</label>
                <input
                  type="number"
                  value={value}
                  onChange={e => set(e.target.value)}
                  className="w-full px-3 py-2.5 bg-[#F8FAFC] dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-[#0F172A] dark:text-slate-200 text-sm font-mono focus:outline-none focus:border-[#1E4976] transition-colors"
                />
              </div>
            ))}
            <div>
              <label className="block text-[10px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-1.5">Regime Tributário</label>
              <select
                value={simRegime}
                onChange={e => setSimRegime(e.target.value as "simples" | "presumido" | "real")}
                className="w-full px-3 py-2.5 bg-[#F8FAFC] dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-[#0F172A] dark:text-slate-200 text-sm focus:outline-none focus:border-[#1E4976] transition-colors"
              >
                <option value="simples">Simples Nacional</option>
                <option value="presumido">Lucro Presumido</option>
                <option value="real">Lucro Real</option>
              </select>
            </div>
          </div>

          {/* ── CFO KPI cards ── */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {simKpis.map(({ label, sub, value, pct, cor, barMax }) => {
              const barWidth = Math.min(100, Math.max(0, (Math.abs(pct) / barMax) * 100));
              const isLucroLiqNeg = label === "Lucro Líquido" && simResultado.lucroLiquido < 0;
              return (
                <div key={label} className="bg-[#F8FAFC] dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700/50 rounded-xl p-4 flex flex-col gap-1"
                  style={{
                    background: isLucroLiqNeg ? "rgba(184,48,48,0.08)" : undefined,
                    borderColor: isLucroLiqNeg ? "rgba(184,48,48,0.20)" : undefined,
                  }}>
                  <p className="text-[9px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600">{label}</p>
                  {value !== null && (
                    <p className="text-sm font-black font-mono tabular-nums leading-snug transition-all duration-300" style={{ color: cor }}>
                      {fmt(value)}
                    </p>
                  )}
                  <p className={`font-black font-mono tabular-nums leading-none transition-all duration-300 ${value !== null ? "text-xs" : "text-2xl"}`} style={{ color: cor }}>
                    {pct.toFixed(1)}%
                  </p>
                  {/* Health bar */}
                  <div className="mt-1.5 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-300"
                      style={{ width: `${barWidth}%`, background: cor }}
                    />
                  </div>
                  <p className="text-[9px] text-[#94A3B8] dark:text-slate-600 mt-0.5">{sub}</p>
                </div>
              );
            })}
          </div>

          {/* ── Barra de composição ── */}
          {simResultado.rb > 0 && (
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600 mb-2.5">Composição da Receita</p>
              <div className="flex h-7 rounded-xl overflow-hidden gap-px">
                {[
                  { pct: (simResultado.custos   / simResultado.rb) * 100, bg: "#B83030", label: "Custos" },
                  { pct: (simResultado.desp      / simResultado.rb) * 100, bg: "#92400E", label: "Despesas" },
                  { pct: (simResultado.impostos  / simResultado.rb) * 100, bg: "#1E4976", label: "Impostos" },
                  { pct: Math.max(0, (simResultado.lucroLiquido / simResultado.rb) * 100), bg: "#1A6B3C", label: "Lucro" },
                ].map(({ pct, bg, label }) => pct > 0 ? (
                  <div
                    key={label}
                    title={`${label}: ${pct.toFixed(1)}%`}
                    className="flex items-center justify-center"
                    style={{ width: `${pct}%`, background: bg }}
                  >
                    {pct > 8 && <span className="text-[9px] font-black text-white/90">{pct.toFixed(0)}%</span>}
                  </div>
                ) : null)}
              </div>
              <div className="flex flex-wrap gap-5 mt-3">
                {[
                  { label: "Custos",    cor: "#B83030", pct: (simResultado.custos   / simResultado.rb) * 100, val: simResultado.custos },
                  { label: "Despesas",  cor: "#92400E", pct: (simResultado.desp      / simResultado.rb) * 100, val: simResultado.desp },
                  { label: "Impostos",  cor: "#1E4976", pct: (simResultado.impostos  / simResultado.rb) * 100, val: simResultado.impostos },
                  { label: "Lucro",     cor: "#1A6B3C", pct: Math.max(0, (simResultado.lucroLiquido / simResultado.rb) * 100), val: simResultado.lucroLiquido },
                ].map(({ label, cor, pct, val }) => (
                  <div key={label} className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: cor }} />
                    <span className="text-[10px] text-[#64748B] dark:text-slate-500 font-medium">{label}</span>
                    <span className="text-[10px] font-black font-mono tabular-nums" style={{ color: cor }}>{pct.toFixed(1)}%</span>
                    <span className="text-[10px] text-[#94A3B8] dark:text-slate-600 font-mono">{fmt(val)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {/* ── Cenário "E se?" ── */}
          <div className="pt-4" style={{ borderTop: "1px solid var(--border)" }}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-0.5 h-4 rounded-full bg-[#1E4976]" />
                <p className="text-[10px] font-black uppercase tracking-widest text-[#64748B] dark:text-slate-400">Cenário &ldquo;E se?&rdquo;</p>
              </div>
              <span className="text-xs font-mono font-bold" style={{ color: cenarioPct >= 0 ? "#1A6B3C" : "#B83030" }}>
                {cenarioPct >= 0 ? "+" : ""}{cenarioPct}% receita
              </span>
            </div>
            <input
              type="range"
              min={-50}
              max={100}
              step={5}
              value={cenarioPct}
              onChange={e => setCenarioPct(Number(e.target.value))}
              className="w-full h-2 rounded-full appearance-none cursor-pointer"
              style={{ background: `linear-gradient(to right, #B83030, #92400E 33%, #1E4976 50%, #1A6B3C)` }}
            />
            <div className="flex justify-between text-[9px] text-[#94A3B8] dark:text-slate-600 mt-1 mb-3">
              <span>-50%</span><span>0%</span><span>+50%</span><span>+100%</span>
            </div>
            {cenarioPct !== 0 && (
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: "Receita Projetada", valor: cenarioReceita, cor: "#1E4976" },
                  { label: "Lucro Projetado", valor: cenarioLucro, cor: cenarioLucro >= 0 ? "#1A6B3C" : "#B83030" },
                  { label: "Variação Lucro", valor: cenarioLucro - simResultado.lucroLiquido, cor: cenarioLucro >= simResultado.lucroLiquido ? "#1A6B3C" : "#B83030" },
                ].map(item => (
                  <div key={item.label} className={`bg-[#F8FAFC] dark:bg-slate-900/60 border rounded-xl p-3 text-center ${
                    cenarioLucro < 0 ? "border-rose-500/20 bg-rose-500/5" : "border-slate-200 dark:border-slate-700/50"
                  }`}>
                    <p className="text-[9px] font-black uppercase tracking-widest text-[#94A3B8] dark:text-slate-600">{item.label}</p>
                    <p className="text-sm font-black font-mono tabular-nums mt-1 transition-all duration-300" style={{ color: item.cor }}>{fmt(item.valor)}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          DASHBOARD DE INSIGHTS — Score + Top Despesas + Anomalias
      ══════════════════════════════════════════════════════════════ */}
      {dados && !dados.sem_dados && !carregando && (() => {
        // Score de Saúde Financeira (0-100)
        const insights = dados.insights ?? [];
        const numCriticos = dados.criticos;
        const numAtencao  = dados.atencao;
        const numInfo     = dados.info;
        const score = Math.max(0, Math.min(100, 100 - (numCriticos * 20) - (numAtencao * 8) - (numInfo * 2)));
        const scoreLabel = score >= 80 ? "Excelente" : score >= 60 ? "Bom" : score >= 40 ? "Atenção" : "Risco";
        const scoreCor   = score >= 80 ? "#1A6B3C" : score >= 60 ? "#1E4976" : score >= 40 ? "#92400E" : "#B83030";
        const scoreBg    = score >= 80 ? "bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-500/20"
                         : score >= 60 ? "bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-500/20"
                         : score >= 40 ? "bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-500/20"
                         : "bg-rose-50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-500/20";

        // Insights de caixa e operacionais para destaque
        const caixaInsights = insights.filter(i => i.categoria === "caixa");
        const opInsights    = insights.filter(i => i.categoria === "operacional");
        const patrimoniais  = insights.filter(i => i.categoria === "patrimonial");

        return (
          <div className="mb-8 grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Score de Saúde */}
            <div className={`rounded-2xl border overflow-hidden ${scoreBg}`}>
              <div className="p-6 flex flex-col items-center gap-3">
                <p className="text-[10px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Score de Saúde Financeira</p>
                <div className="relative w-28 h-28">
                  <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
                    <circle cx="60" cy="60" r="50" fill="none" stroke="currentColor" className="text-slate-200 dark:text-slate-700" strokeWidth="10" />
                    <circle cx="60" cy="60" r="50" fill="none" stroke={scoreCor} strokeWidth="10" strokeLinecap="round"
                      strokeDasharray={`${(score / 100) * 314} 314`} />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-3xl font-black font-mono" style={{ color: scoreCor }}>{score}</span>
                    <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: scoreCor }}>{scoreLabel}</span>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-[10px]">
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-rose-500" />{numCriticos} críticos</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" />{numAtencao} atenção</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500" />{numInfo} info</span>
                </div>
              </div>
            </div>

            {/* Insights de Caixa */}
            <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-0.5 h-4 rounded-full bg-[#1E4976]" />
                <p className="text-[10px] font-black uppercase tracking-widest text-[#64748B] dark:text-slate-400">Insights de Caixa</p>
              </div>
              {caixaInsights.length > 0 ? (
                <div className="space-y-2.5">
                  {caixaInsights.slice(0, 4).map(ins => {
                    const cfg = SEV_CFG[ins.severidade] ?? SEV_CFG.info;
                    return (
                      <div key={ins.id} className={`flex items-start gap-2 px-3 py-2 rounded-lg border text-xs ${cfg.cardBg} ${cfg.cardBorder}`}>
                        <div className="flex-shrink-0 mt-0.5" style={{ color: cfg.accentBg }}>{cfg.icon}</div>
                        <div>
                          <p className={`font-semibold ${cfg.titleColor}`}>{ins.titulo}</p>
                          <p className={`text-[11px] mt-0.5 ${cfg.textColor}`}>{ins.mensagem}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-center py-6" style={{ color: "var(--text-muted)" }}>Sem alertas de caixa</p>
              )}
            </div>

            {/* Insights Operacionais + Patrimoniais */}
            <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-0.5 h-4 rounded-full bg-[#92400E]" />
                <p className="text-[10px] font-black uppercase tracking-widest text-[#64748B] dark:text-slate-400">Destaques Operacionais</p>
              </div>
              {[...opInsights, ...patrimoniais].length > 0 ? (
                <div className="space-y-2.5">
                  {[...opInsights, ...patrimoniais].slice(0, 4).map(ins => {
                    const cfg = SEV_CFG[ins.severidade] ?? SEV_CFG.info;
                    return (
                      <div key={ins.id} className={`flex items-start gap-2 px-3 py-2 rounded-lg border text-xs ${cfg.cardBg} ${cfg.cardBorder}`}>
                        <div className="flex-shrink-0 mt-0.5" style={{ color: cfg.accentBg }}>{cfg.icon}</div>
                        <div>
                          <p className={`font-semibold ${cfg.titleColor}`}>{ins.titulo}</p>
                          {ins.valor_atual != null && (
                            <p className={`text-[11px] font-mono mt-0.5 ${cfg.textColor}`}>
                              Atual: {Math.abs(ins.valor_atual) > 100 ? fmt(ins.valor_atual) : `${ins.valor_atual.toFixed(1)}%`}
                              {ins.valor_referencia != null && <span className="text-[#94A3B8]"> · Ref: {Math.abs(ins.valor_referencia) > 100 ? fmt(ins.valor_referencia) : `${ins.valor_referencia.toFixed(1)}%`}</span>}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-center py-6" style={{ color: "var(--text-muted)" }}>Sem alertas operacionais</p>
              )}
            </div>
          </div>
        );
      })()}

      {/* ── Loading ── */}
      {carregando && (
        <div className="py-16 flex flex-col items-center justify-center gap-4">
          <div className="w-10 h-10 border-2 border-[#1E4976]/20 border-t-[#1E4976] rounded-full animate-spin" />
          <p className="text-sm text-[#64748B] dark:text-slate-500">Analisando dados financeiros...</p>
        </div>
      )}

      {/* ── Error ── */}
      {erro && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl text-red-700 dark:text-red-300 text-sm">{erro}</div>
      )}

      {/* ── No data ── */}
      {dados?.sem_dados && (
        <div className="text-center py-12 bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl">
          <svg className="w-10 h-10 mx-auto mb-4 text-[#CBD5E1] dark:text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-base font-bold text-[#475569] dark:text-slate-400 mb-1">Sem dados para {nomeSelecionado}</p>
          <p className="text-sm text-[#94A3B8] dark:text-slate-600">Insira lançamentos em <strong>Lançamentos Financeiros</strong> para gerar insights.</p>
        </div>
      )}

      {/* ── Insights list ── */}
      {dados && !dados.sem_dados && !carregando && (
        <div className="space-y-6">

          {/* Filtros */}
          <div className="flex flex-wrap gap-2 p-4 bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl">
            {CATEGORIAS.map(c => {
              const count = c.key === "todos" ? dados.total
                : c.key === "critico" ? dados.criticos
                : c.key === "atencao" ? dados.atencao
                : c.key === "info" ? dados.info
                : (dados.insights ?? []).filter(i => i.categoria === c.key).length;
              const isActive = filtro === c.key;
              return (
                <button
                  key={c.key}
                  onClick={() => setFiltro(c.key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                    isActive
                      ? "text-white border-transparent"
                      : "bg-white dark:bg-slate-800/60 border-slate-200 dark:border-slate-700 text-[#475569] dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600"
                  }`}
                  style={isActive ? { background: "#1E4976", borderColor: "#1E4976" } : {}}
                >
                  {c.label}
                  {count > 0 && (
                    <span className={`ml-1.5 px-1.5 py-0.5 rounded-full text-[9px] font-black ${
                      isActive ? "bg-white/20 text-white" : "bg-slate-100 dark:bg-slate-700 text-[#64748B] dark:text-slate-400"
                    }`}>
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {insightsFiltrados.length === 0 && (
            <div className="text-center py-14 bg-white dark:bg-slate-800/40 border border-dashed border-slate-200 dark:border-slate-700 rounded-2xl">
              <svg className="w-10 h-10 mx-auto mb-3 text-[#CBD5E1] dark:text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-[#64748B] dark:text-slate-500 font-semibold">Nenhum alerta nesta categoria.</p>
            </div>
          )}

          {criticos.length > 0 && (
            <section>
              <div className="flex items-center gap-2.5 mb-3">
                <div className="w-0.5 h-5 rounded-full bg-[#B83030]" />
                <h2 className="text-xs font-black uppercase tracking-widest text-[#64748B] dark:text-slate-400">
                  Alertas Críticos — {criticos.length}
                </h2>
              </div>
              <div className="space-y-3">
                {criticos.map(ins => <InsightCard key={ins.id} ins={ins} periodo={dados?.periodo_referencia} />)}
              </div>
            </section>
          )}

          {atencao.length > 0 && (
            <section>
              <div className="flex items-center gap-2.5 mb-3">
                <div className="w-0.5 h-5 rounded-full bg-[#92400E]" />
                <h2 className="text-xs font-black uppercase tracking-widest text-[#64748B] dark:text-slate-400">
                  Pontos de Atenção — {atencao.length}
                </h2>
              </div>
              <div className="space-y-3">
                {atencao.map(ins => <InsightCard key={ins.id} ins={ins} periodo={dados?.periodo_referencia} />)}
              </div>
            </section>
          )}

          {infoList.length > 0 && (
            <section>
              <div className="flex items-center gap-2.5 mb-3">
                <div className="w-0.5 h-5 rounded-full bg-[#1E4976]" />
                <h2 className="text-xs font-black uppercase tracking-widest text-[#64748B] dark:text-slate-400">
                  Informativos — {infoList.length}
                </h2>
              </div>
              <div className="space-y-3">
                {infoList.map(ins => <InsightCard key={ins.id} ins={ins} periodo={dados?.periodo_referencia} />)}
              </div>
            </section>
          )}

          {/* Análise do Período — Narrative section */}
          {insightsFiltrados.length > 0 && (
            <div className="rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
              <div className="px-5 py-3.5 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-[#1E4976]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    Análise do Período
                  </h3>
                  {dados.periodo_referencia && (
                    <span className="text-xs font-normal text-slate-400 dark:text-slate-500">
                      {dados.periodo_referencia}
                    </span>
                  )}
                </div>
              </div>
              <div className="p-5">
                <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                  {generateNarrative(dados)}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
