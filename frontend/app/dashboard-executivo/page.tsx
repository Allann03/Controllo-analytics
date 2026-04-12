"use client";
import { useState, useCallback, useRef, useEffect } from "react";
import GraficoComNome from "@/components/GraficoComNome";
import { useChartTheme } from "@/components/useChartTheme";
import { useToast } from "@/contexts/ToastContext";
import { Download, FileImage } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell,
} from "recharts";

// ── Tipos ──────────────────────────────────────────────────────────
const MESES_ABREV = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];

interface DadosMes {
  mes: string;
  receita: number;
  despesas: number;
  lucro: number;
  impostos: number;
  saldo: number;
}

interface KPI {
  label: string;
  valor: number;
  variacao: number;
  prefixo?: string;
  sufixo?: string;
}

interface DadosDashboard {
  nomeEmpresa: string;
  periodo: string;
  kpis: KPI[];
  meses: DadosMes[];
  impostos: { nome: string; valor: number }[];
  indicadores: { label: string; valor: string; variacao: number }[];
}

const DADOS_PADRAO: DadosDashboard = {
  nomeEmpresa: "Empresa Exemplo Ltda",
  periodo: "Janeiro — Dezembro 2025",
  kpis: [
    { label: "RECEITA BRUTA",   valor: 2400000, variacao: 12.3, prefixo: "R$" },
    { label: "DESPESAS TOTAIS", valor: 1800000, variacao: -3.1, prefixo: "R$" },
    { label: "LUCRO LÍQUIDO",   valor:  420000, variacao: 28.7, prefixo: "R$" },
    { label: "MARGEM LÍQUIDA",  valor:    17.5, variacao:  2.1, sufixo: "%" },
    { label: "IMPOSTOS PAGOS",  valor:  180000, variacao: -8.4, prefixo: "R$" },
  ],
  meses: MESES_ABREV.map((mes, i) => ({
    mes,
    receita:  150000 + Math.round(Math.sin(i * 0.8) * 40000 + Math.random() * 20000),
    despesas: 110000 + Math.round(Math.cos(i * 0.7) * 20000 + Math.random() * 15000),
    lucro:     40000 + Math.round(Math.sin(i * 0.5) * 15000 + Math.random() * 10000),
    impostos:  15000 + Math.round(Math.random() * 5000),
    saldo:     30000 + Math.round(Math.sin(i * 0.6) * 12000),
  })),
  impostos: [
    { nome: "Simples Nacional", valor: 80000 },
    { nome: "ISS",              valor: 35000 },
    { nome: "IRPJ",             valor: 28000 },
    { nome: "CSLL",             valor: 18000 },
    { nome: "PIS/COFINS",       valor: 12000 },
    { nome: "Outros",           valor:  7000 },
  ],
  indicadores: [
    { label: "Ticket Médio",          valor: "R$ 12.400", variacao:  8.2 },
    { label: "Prazo Méd. Receb.",     valor: "28 dias",   variacao: -3.5 },
    { label: "Prazo Méd. Pgto.",      valor: "35 dias",   variacao:  1.2 },
    { label: "Índice de Liquidez",    valor: "1,42",      variacao:  0.8 },
    { label: "Break-even Mensal",     valor: "R$ 95.000", variacao: -2.1 },
    { label: "Taxa Efetiva Impostos", valor: "7,5%",      variacao: -0.9 },
  ],
};

// Cores para gráficos — array de hex aceito por Recharts Cell/linearGradient
const CORES_PIE = ["#102a43","#3b82f6","#06b6d4","#10b981","#f59e0b","#f43f5e","#3b6ea5","#ec4899"];

function formatBRL(v: number): string {
  if (v >= 1_000_000) return `R$ ${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000)     return `R$ ${(v / 1_000).toFixed(0)}k`;
  return `R$ ${v.toLocaleString("pt-BR")}`;
}

function formatFull(v: number): string {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

// ── Valor editável ────────────────────────────────────────────────
function EditVal({
  valor, onChange, editando, prefixo, sufixo, className,
}: {
  valor: number; onChange: (v: number) => void; editando: boolean;
  prefixo?: string; sufixo?: string; className?: string;
}) {
  const [inputVal, setInputVal] = useState(String(valor));

  useEffect(() => {
    if (!editando) setInputVal(String(valor));
  }, [editando, valor]);

  const commit = () => {
    const parsed = parseFloat(inputVal.replace(",", ".").replace(/[^0-9.]/g, ""));
    if (!isNaN(parsed)) onChange(parsed);
  };

  if (!editando) {
    return (
      <span className={className}>
        {prefixo && <span className="opacity-70 text-sm mr-0.5">{prefixo}</span>}
        {sufixo
          ? valor.toFixed(1)
          : valor >= 1_000
          ? valor.toLocaleString("pt-BR")
          : valor.toFixed(2).replace(".", ",")}
        {sufixo && <span className="opacity-70 text-sm ml-0.5">{sufixo}</span>}
      </span>
    );
  }

  return (
    <input
      value={inputVal}
      onChange={e => setInputVal(e.target.value)}
      onBlur={commit}
      onKeyDown={e => e.key === "Enter" && commit()}
      className={`${className} rounded-md px-2 py-0.5 text-center w-full cursor-text bg-navy-900/40 border border-dashed border-navy-500/70 focus:outline-none focus:ring-2 focus:ring-navy-400/50`}
      style={{ minWidth: 80 }}
    />
  );
}

// ── Página principal ──────────────────────────────────────────────
export default function DashboardExecutivoPage() {
  const ct = useChartTheme();
  const STORAGE_KEY = "controllo_dashboard_executivo";

  const [dados, setDados] = useState<DadosDashboard>(() => {
    if (typeof window === "undefined") return DADOS_PADRAO;
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return { ...DADOS_PADRAO, ...JSON.parse(saved) };
    } catch { /* ignore */ }
    return DADOS_PADRAO;
  });

  const [editando, setEditando]       = useState(false);
  const [exportando, setExportando]   = useState(false);
  const [exportandoApres, setExportandoApres] = useState(false);
  const [isLight, setIsLight]         = useState(false);
  const dashRef = useRef<HTMLDivElement>(null);
  const { error: showError, success: showSuccess, warning: showWarning } = useToast();

  // Detecta tema claro/escuro para estilos reativos
  useEffect(() => {
    const check = () => setIsLight(document.documentElement.classList.contains("light"));
    check();
    const obs = new MutationObserver(check);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(dados)); } catch { /* ignore */ }
  }, [dados]);

  const atualizarKpi = useCallback((idx: number, novoValor: number) => {
    setDados(prev => {
      const kpis = [...prev.kpis];
      kpis[idx] = { ...kpis[idx], valor: novoValor };
      return { ...prev, kpis };
    });
  }, []);

  const atualizarMes = useCallback((mesIdx: number, campo: keyof DadosMes, valor: number) => {
    setDados(prev => {
      const meses = prev.meses.map((m, i) =>
        i === mesIdx ? { ...m, [campo]: valor } : m
      );
      return { ...prev, meses };
    });
  }, []);

  const importarXlsx = useCallback(async (file: File) => {
    try {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      const XLSX = await import("xlsx");
      const buffer = await file.arrayBuffer();
      const wb = XLSX.read(buffer, { type: "array" });
      const ws = wb.Sheets[wb.SheetNames[0]];
      const rows: Record<string, unknown>[] = XLSX.utils.sheet_to_json(ws, { defval: 0 });

      if (rows.length === 0) { showWarning("Dados insuficientes", "Planilha vazia ou sem dados."); return; }

      const norm = (s: string) => String(s).toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      const headers = Object.keys(rows[0]);
      const find = (...keys: string[]) => headers.find(h => keys.some(k => norm(h).includes(norm(k))));

      const colMes   = find("mes","month","periodo");
      const colRec   = find("receita","revenue","faturamento","entrada");
      const colDesp  = find("despesa","custo","saida","expense");
      const colLucro = find("lucro","profit","resultado");
      const colImp   = find("imposto","tax","tributo");
      const colSaldo = find("saldo","balance","caixa");

      const parseNum = (v: unknown) => {
        if (typeof v === "number") return v;
        const s = String(v).replace(/[R$\s.]/g, "").replace(",", ".");
        return parseFloat(s) || 0;
      };

      const mesesParsed: typeof DADOS_PADRAO.meses = rows.slice(0, 12).map((r, i) => ({
        mes:      colMes   ? String(r[colMes]).slice(0, 3) : MESES_ABREV[i] || `M${i+1}`,
        receita:  colRec   ? parseNum(r[colRec])   : 0,
        despesas: colDesp  ? parseNum(r[colDesp])  : 0,
        lucro:    colLucro ? parseNum(r[colLucro]) : 0,
        impostos: colImp   ? parseNum(r[colImp])   : 0,
        saldo:    colSaldo ? parseNum(r[colSaldo]) : 0,
      }));

      const nomeArq = file.name.replace(/\.[^.]+$/, "").replace(/[_-]/g, " ");
      setDados(prev => ({ ...prev, nomeEmpresa: nomeArq, meses: mesesParsed }));
      showSuccess("Planilha importada!", `${mesesParsed.length} meses carregados.`);
    } catch (e) {
      console.error(e);
      showError("Erro ao ler planilha", "Verifique o formato do arquivo (.xlsx, .xls ou .csv).");
    }
  }, [showError, showSuccess]);

  const exportarImagem = useCallback(async () => {
    if (!dashRef.current) return;
    setExportando(true);
    try {
      const { toPng } = await import("html-to-image");
      const dataUrl = await toPng(dashRef.current, {
        backgroundColor: "#ffffff",
        pixelRatio: 2,
      });
      const link = document.createElement("a");
      link.download = `dashboard_${dados.nomeEmpresa.replace(/\s+/g, "_")}_${Date.now()}.png`;
      link.href = dataUrl;
      link.click();
      showSuccess("Exportação concluída", "Dashboard exportado como PNG (fundo branco).");
    } catch (e) {
      console.error("Erro ao exportar:", e);
      showError("Erro ao exportar", "Não foi possível gerar a imagem. Tente novamente.");
    } finally {
      setExportando(false);
    }
  }, [dados.nomeEmpresa, showError, showSuccess]);

  const totalImpostos = dados.impostos.reduce((s, i) => s + i.valor, 0);
  const totalReceita  = dados.meses.reduce((s, m) => s + m.receita, 0);
  const totalDespesas = dados.meses.reduce((s, m) => s + m.despesas, 0);
  const totalLucro    = dados.meses.reduce((s, m) => s + m.lucro, 0);

  // Recharts tooltip — a área exportável é sempre escura, mas a UI segue o tema
  // Nota: a área de dados (dashRef) usa fundo escuro intencional para o relatório exportado
  const tooltipStyle      = ct.tooltipStyle;
  const tooltipLabelStyle = ct.tooltipLabelStyle;
  const tooltipItemStyle  = ct.tooltipItemStyle;

  // ── Baixar Planilha Modelo ────────────────────────────────────────
  const baixarPlanilhaModelo = useCallback(async () => {
    try {
      // @ts-ignore
      const XLSX = await import("xlsx");
      const wb = XLSX.utils.book_new();

      // ── Aba "Instruções" ──────────────────────────────────────────
      const wsInstrData = [
        { "": "MODELO — DASHBOARD EXECUTIVO (Controllo BPO)" },
        { "": "" },
        { "": "COMO USAR" },
        { "": "1. Preencha a aba 'Meses' com os dados mensais da empresa (até 12 linhas)." },
        { "": "2. Preencha a aba 'KPIs' com os totais anuais (ou do período desejado)." },
        { "": "3. Preencha a aba 'Impostos' com os tributos pagos no período." },
        { "": "4. Salve o arquivo e importe via botão 'Importar Dados' no dashboard." },
        { "": "" },
        { "": "DESCRIÇÃO DAS COLUNAS — Aba 'Meses'" },
        { "": "  mes      (texto, obrigatório) — Abreviação do mês: Jan, Fev, Mar ... Dez" },
        { "": "  receita  (número, obrigatório) — Receita total do mês em R$ (sem símbolo)" },
        { "": "  despesas (número, obrigatório) — Total de despesas do mês em R$" },
        { "": "  lucro    (número, obrigatório) — Lucro líquido do mês em R$  (pode ser negativo)" },
        { "": "  impostos (número, opcional)   — Total de impostos pagos no mês em R$" },
        { "": "  saldo    (número, opcional)   — Saldo disponível em caixa/banco ao fim do mês em R$" },
        { "": "" },
        { "": "DESCRIÇÃO DAS COLUNAS — Aba 'KPIs'" },
        { "": "  label (texto)  — Nome do indicador (não altere os nomes)" },
        { "": "  valor (número) — Valor do indicador no período (MARGEM LÍQUIDA em %, demais em R$)" },
        { "": "" },
        { "": "DESCRIÇÃO DAS COLUNAS — Aba 'Impostos'" },
        { "": "  nome  (texto)  — Nome do tributo (ex: Simples Nacional, IRPJ, ISS, CSLL, PIS, COFINS)" },
        { "": "  valor (número) — Valor total pago no período em R$" },
        { "": "" },
        { "": "OBSERVAÇÕES" },
        { "": "  - Valores monetários são numéricos sem R$ ou pontuação (use . como decimal)." },
        { "": "  - O dashboard detecta automaticamente as colunas pelo nome (insensível a maiúsculas)." },
        { "": "  - Você pode importar dados de qualquer período (mensal, trimestral, anual)." },
        { "": "  - Use até 12 linhas na aba 'Meses' para cobrir o ano completo." },
      ];
      const wsInstr = XLSX.utils.json_to_sheet(wsInstrData);
      wsInstr["!cols"] = [{ wch: 90 }];
      XLSX.utils.book_append_sheet(wb, wsInstr, "Instruções");

      // ── Aba "Meses" ───────────────────────────────────────────────
      // Colunas exatas consumidas pelo parser do dashboard
      const wsMeses = XLSX.utils.json_to_sheet([
        { mes: "Jan", receita: 150000, despesas: 112000, lucro:  38000, impostos: 14500, saldo:  32000 },
        { mes: "Fev", receita: 162000, despesas: 115500, lucro:  46500, impostos: 16000, saldo:  41000 },
        { mes: "Mar", receita: 178000, despesas: 121000, lucro:  57000, impostos: 18000, saldo:  55000 },
        { mes: "Abr", receita: 195000, despesas: 130000, lucro:  65000, impostos: 20000, saldo:  68000 },
        { mes: "Mai", receita: 188000, despesas: 125000, lucro:  63000, impostos: 19500, saldo:  74000 },
        { mes: "Jun", receita: 201000, despesas: 135000, lucro:  66000, impostos: 21000, saldo:  82000 },
        { mes: "Jul", receita: 215000, despesas: 142000, lucro:  73000, impostos: 22500, saldo:  92000 },
        { mes: "Ago", receita: 220000, despesas: 148000, lucro:  72000, impostos: 23000, saldo:  98000 },
        { mes: "Set", receita: 198000, despesas: 138000, lucro:  60000, impostos: 20000, saldo:  89000 },
        { mes: "Out", receita: 210000, despesas: 140000, lucro:  70000, impostos: 21500, saldo:  95000 },
        { mes: "Nov", receita: 225000, despesas: 152000, lucro:  73000, impostos: 23500, saldo: 103000 },
        { mes: "Dez", receita: 240000, despesas: 160000, lucro:  80000, impostos: 25000, saldo: 115000 },
      ]);
      wsMeses["!cols"] = [{ wch: 8 }, { wch: 14 }, { wch: 14 }, { wch: 14 }, { wch: 14 }, { wch: 14 }];
      XLSX.utils.book_append_sheet(wb, wsMeses, "Meses");

      // ── Aba "KPIs" ────────────────────────────────────────────────
      const wsKpis = XLSX.utils.json_to_sheet([
        { label: "RECEITA BRUTA",   valor: 2382000 },
        { label: "DESPESAS TOTAIS", valor: 1618500 },
        { label: "LUCRO LÍQUIDO",   valor:  763500 },
        { label: "MARGEM LÍQUIDA",  valor:    32.1 },
        { label: "IMPOSTOS PAGOS",  valor:  244500 },
      ]);
      wsKpis["!cols"] = [{ wch: 22 }, { wch: 14 }];
      XLSX.utils.book_append_sheet(wb, wsKpis, "KPIs");

      // ── Aba "Impostos" ────────────────────────────────────────────
      const wsImpostos = XLSX.utils.json_to_sheet([
        { nome: "Simples Nacional", valor:  98000 },
        { nome: "ISS",              valor:  42000 },
        { nome: "IRPJ",             valor:  38500 },
        { nome: "CSLL",             valor:  28000 },
        { nome: "PIS/COFINS",       valor:  38000 },
      ]);
      wsImpostos["!cols"] = [{ wch: 22 }, { wch: 14 }];
      XLSX.utils.book_append_sheet(wb, wsImpostos, "Impostos");

      XLSX.writeFile(wb, "modelo_dashboard_executivo.xlsx");
      showSuccess("Planilha modelo baixada!", "Preencha com os dados reais e importe no dashboard.");
    } catch (e) {
      console.error(e);
      showError("Erro ao gerar planilha", "Tente novamente.");
    }
  }, [showError, showSuccess]);

  // ── Exportar para Apresentação (fundo branco/limpo) ───────────────
  const exportarApresentacao = useCallback(async () => {
    if (!dashRef.current) return;
    setExportandoApres(true);
    try {
      const { toPng } = await import("html-to-image");
      const dataUrl = await toPng(dashRef.current, {
        backgroundColor: "#ffffff",
        pixelRatio: 2,
        style: { padding: "32px" },
      });
      const link = document.createElement("a");
      link.download = `apresentacao_${dados.nomeEmpresa.replace(/\s+/g, "_")}_${Date.now()}.png`;
      link.href = dataUrl;
      link.click();
      showSuccess("Exportação concluída", "Dashboard exportado para apresentação (fundo claro).");
    } catch (e) {
      console.error("Erro ao exportar apresentação:", e);
      showError("Erro ao exportar", "Não foi possível gerar a imagem.");
    } finally {
      setExportandoApres(false);
    }
  }, [dados.nomeEmpresa, showError, showSuccess]);

  return (
    <div className="min-h-full bg-white dark:bg-slate-900 p-6">

      {/* ── BARRA DE CONTROLES (segue o tema) ── */}
      <div className="flex items-center justify-between mb-6 no-export">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest mb-1 text-navy-600 dark:text-navy-400">
            Executivo
          </p>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            Dashboard <span className="text-navy-600 dark:text-navy-400">Executivo</span>
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            Relatório premium para apresentação ao cliente
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {/* Baixar Planilha Modelo */}
          <button
            onClick={baixarPlanilhaModelo}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
          >
            <Download className="w-4 h-4" />
            Planilha Modelo
          </button>

          {/* Importar planilha */}
          <label className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors border cursor-pointer border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Importar Dados
            <input
              type="file" accept=".xlsx,.xls,.csv" className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) importarXlsx(f); e.target.value = ""; }}
            />
          </label>

          {/* Modo edição */}
          <button
            onClick={() => setEditando(v => !v)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors border ${
              editando
                ? "bg-blue-900 border-blue-800 text-white"
                : "border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
            }`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
            {editando ? "Editando..." : "Editar"}
          </button>

          {/* Exportar para Apresentação (fundo branco) */}
          <button
            onClick={exportarApresentacao}
            disabled={exportandoApres}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-60"
          >
            {exportandoApres ? (
              <div className="w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <FileImage className="w-4 h-4" />
            )}
            Apresentação
          </button>

          {/* Exportar PNG (fundo escuro, relatório executivo) */}
          <button
            onClick={exportarImagem}
            disabled={exportando}
            className="flex items-center gap-2 px-4 py-2 bg-blue-900 hover:bg-blue-950 disabled:opacity-60 rounded-lg text-white text-sm font-semibold transition-colors"
          >
            {exportando ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            )}
            {exportando ? "Gerando..." : "Exportar PNG"}
          </button>
        </div>
      </div>

      {/*
        ── ÁREA EXPORTÁVEL (superfície escura intencional) ──
        Esta área é o "relatório executivo" capturado como PNG para o cliente.
        Permanece sempre escura para manter o visual premium da apresentação,
        independentemente do tema da interface.
      */}
      <div
        ref={dashRef}
        id="dashboard-exportavel"
        className={`space-y-6 p-6 rounded-2xl bg-slate-950 border border-slate-800 ${editando ? "ring-2 ring-navy-500/30" : ""}`}
      >
        {/* Cabeçalho do relatório */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-5">
          <div>
            {editando ? (
              <input
                value={dados.nomeEmpresa}
                onChange={e => setDados(p => ({ ...p, nomeEmpresa: e.target.value }))}
                className="text-2xl font-black text-white rounded-md px-2 py-0.5 cursor-text bg-navy-900/40 border border-dashed border-navy-500/70 focus:outline-none focus:ring-2 focus:ring-navy-400/50"
              />
            ) : (
              <h2 className="text-2xl font-black text-white">{dados.nomeEmpresa}</h2>
            )}
            {editando ? (
              <input
                value={dados.periodo}
                onChange={e => setDados(p => ({ ...p, periodo: e.target.value }))}
                className="text-sm text-slate-400 rounded-md px-2 py-0.5 mt-1 w-64 cursor-text bg-navy-900/30 border border-dashed border-navy-600/50 focus:outline-none"
              />
            ) : (
              <p className="text-sm text-slate-400 mt-1">{dados.periodo}</p>
            )}
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-600 uppercase font-bold tracking-widest">Relatório Financeiro</p>
            <p className="text-xs text-slate-600">Gerado por Controllo Analytics</p>
          </div>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {dados.kpis.map((kpi, i) => (
            <div key={i} className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 hover:border-slate-700 transition-all">
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">{kpi.label}</p>
              <div className="text-xl font-black text-white font-mono mb-1">
                <EditVal
                  valor={kpi.valor} onChange={v => atualizarKpi(i, v)}
                  editando={editando} prefixo={kpi.prefixo} sufixo={kpi.sufixo}
                  className="text-xl font-black text-white font-mono"
                />
              </div>
              <div className={`flex items-center gap-1 text-xs font-semibold ${kpi.variacao >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                <span>{kpi.variacao >= 0 ? "▲" : "▼"}</span>
                <span>{Math.abs(kpi.variacao).toFixed(1)}{kpi.sufixo === "%" ? " p.p." : "%"}</span>
                <span className="text-slate-600 font-normal">vs ano ant.</span>
              </div>
            </div>
          ))}
        </div>

        {/* Gráficos 2×2 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">

          {/* DRE Simplificada */}
          <GraficoComNome nome={dados.nomeEmpresa}>
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
              <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">DRE Simplificada</p>
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={[
                      { nome: "Receita",    valor: totalReceita },
                      { nome: "Deduções",   valor: -(totalReceita * 0.08) },
                      { nome: "Rec. Líq.",  valor: totalReceita * 0.92 },
                      { nome: "Lucro Bruto",valor: totalReceita * 0.45 },
                      { nome: "EBITDA",     valor: totalLucro * 1.3 },
                      { nome: "Lucro Líq.", valor: totalLucro },
                    ]}
                    layout="vertical"
                    margin={{ left: 20, right: 10 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} horizontal={false} />
                    <XAxis type="number" hide />
                    <YAxis dataKey="nome" type="category" tick={{ fill: ct.tickFill, fontSize: 10 }} tickLine={false} axisLine={false} width={60} />
                    <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle} formatter={(v) => formatFull(Math.abs(Number(v)))} />
                    <Bar dataKey="valor" radius={[0, 4, 4, 0]} maxBarSize={20}>
                      {[totalReceita, -(totalReceita * 0.08), totalReceita * 0.92, totalReceita * 0.45, totalLucro * 1.3, totalLucro].map((v, i) => (
                        <Cell key={i} fill={v < 0 ? "#f43f5e" : `hsl(${220 + i * 15}, 80%, ${55 + i * 3}%)`} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </GraficoComNome>

          {/* Fluxo de Caixa */}
          <GraficoComNome nome={dados.nomeEmpresa}>
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
              <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Fluxo de Caixa Mensal</p>
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={dados.meses} margin={{ left: -10, right: 5 }}>
                    <defs>
                      <linearGradient id="gradRec" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="gradDesp" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#f43f5e" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} vertical={false} />
                    <XAxis dataKey="mes" tick={{ fill: ct.tickFill, fontSize: 10 }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fill: ct.tickFill, fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                    <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle} formatter={(v) => formatFull(Number(v))} />
                    <Area type="monotone" dataKey="receita"  stroke="#10b981" fill="url(#gradRec)"  strokeWidth={2} name="Receita" />
                    <Area type="monotone" dataKey="despesas" stroke="#f43f5e" fill="url(#gradDesp)" strokeWidth={2} name="Despesas" />
                    <Area type="monotone" dataKey="saldo"    stroke={ct.lineStroke} fill="none"           strokeWidth={2} strokeDasharray="4 2" name="Saldo" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </GraficoComNome>

          {/* Composição de Impostos */}
          <GraficoComNome nome={dados.nomeEmpresa} className="self-start">
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
              <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Composição de Impostos</p>
              <div className="flex items-center gap-4">
                <div className="h-44 w-44 flex-shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={dados.impostos} cx="50%" cy="50%" innerRadius={40} outerRadius={68} dataKey="valor" paddingAngle={2}>
                        {dados.impostos.map((_, i) => (
                          <Cell key={i} fill={CORES_PIE[i % CORES_PIE.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle} formatter={(v) => formatFull(Number(v))} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex-1 space-y-2">
                  <p className="text-xs text-slate-500 font-bold mb-1">
                    Total: <span className="text-white">{formatBRL(totalImpostos)}</span>
                  </p>
                  {dados.impostos.map((imp, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: CORES_PIE[i % CORES_PIE.length] }} />
                      <span className="text-xs text-slate-400 flex-1 truncate">{imp.nome}</span>
                      <span className="text-xs font-mono text-slate-300">{((imp.valor / totalImpostos) * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </GraficoComNome>

          {/* Indicadores */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
            <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Indicadores Financeiros</p>
            <div className="grid grid-cols-2 gap-3">
              {dados.indicadores.map((ind, i) => (
                <div key={i} className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                  <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">{ind.label}</p>
                  <p className="text-sm font-black text-white font-mono">{ind.valor}</p>
                  <p className={`text-[10px] font-semibold mt-0.5 ${ind.variacao >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                    {ind.variacao >= 0 ? "▲" : "▼"} {Math.abs(ind.variacao).toFixed(1)}%
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Tabela Anual */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-800">
            <p className="text-xs font-black text-slate-400 uppercase tracking-widest">Demonstrativo Anual Detalhado</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-800/60 border-b border-slate-800">
                  <th className="px-4 py-3 text-left text-slate-500 font-bold uppercase tracking-wider">Mês</th>
                  <th className="px-4 py-3 text-right text-emerald-500 font-bold uppercase tracking-wider">Receita</th>
                  <th className="px-4 py-3 text-right text-rose-500 font-bold uppercase tracking-wider">Despesas</th>
                  <th className="px-4 py-3 text-right text-blue-400 font-bold uppercase tracking-wider">Lucro</th>
                  <th className="px-4 py-3 text-right text-amber-500 font-bold uppercase tracking-wider">Impostos</th>
                  <th className="px-4 py-3 text-right text-navy-400 font-bold uppercase tracking-wider">Saldo</th>
                </tr>
              </thead>
              <tbody>
                {dados.meses.map((m, i) => (
                  <tr key={i} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-2.5 font-semibold text-slate-300">{m.mes}</td>
                    {(["receita","despesas","lucro","impostos","saldo"] as (keyof DadosMes)[]).map((campo) => (
                      <td key={campo} className={`px-4 py-2.5 text-right font-mono font-medium ${
                        campo === "receita"  ? "text-emerald-400" :
                        campo === "despesas" ? "text-rose-400" :
                        campo === "lucro"    ? "text-blue-400" :
                        campo === "impostos" ? "text-amber-400" :
                        "text-navy-400"
                      }`}>
                        {editando ? (
                          <input
                            type="number"
                            defaultValue={m[campo] as number}
                            onBlur={e => atualizarMes(i, campo, Number(e.target.value))}
                            className="bg-transparent border-b border-dashed border-navy-500/50 focus:outline-none text-right w-24"
                          />
                        ) : (
                          formatBRL(m[campo] as number)
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
                <tr className="border-t-2 border-slate-700 bg-slate-800/60 font-black">
                  <td className="px-4 py-3 text-white uppercase text-xs tracking-wider">TOTAL</td>
                  <td className="px-4 py-3 text-right font-mono text-emerald-300">{formatBRL(totalReceita)}</td>
                  <td className="px-4 py-3 text-right font-mono text-rose-300">{formatBRL(totalDespesas)}</td>
                  <td className="px-4 py-3 text-right font-mono text-blue-300">{formatBRL(totalLucro)}</td>
                  <td className="px-4 py-3 text-right font-mono text-amber-300">{formatBRL(dados.meses.reduce((s, m) => s + m.impostos, 0))}</td>
                  <td className="px-4 py-3 text-right font-mono text-navy-300">{formatBRL(dados.meses.reduce((s, m) => s + m.saldo, 0))}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Rodapé */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-800/50">
          <p className="text-[10px] text-slate-700">Controllo BPO Analytics — Plataforma de Inteligência Financeira</p>
          <p className="text-[10px] text-slate-700">
            {new Date().toLocaleDateString("pt-BR", { day: "2-digit", month: "long", year: "numeric" })}
          </p>
        </div>
      </div>

      {editando && (
        <p className="text-center text-xs text-navy-400/60 mt-3">
          ✏️ Modo edição ativo — clique em qualquer valor numérico para editá-lo
        </p>
      )}
    </div>
  );
}
