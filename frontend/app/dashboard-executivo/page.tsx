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

// Paleta de gráficos: lida via getComputedStyle dos tokens --chart-1..6
// definidos em globals.css. Ver hook useChartTokens() abaixo na página.
// Mapeamento semântico (§5.6): chart-1=accent (positivo principal),
// chart-2=success (lucro/positivo derivado), chart-3=danger (negativo),
// chart-4=warning (atenção), chart-5/6=extras quando 5+ séries.

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

  // Tokens de gráfico (--chart-1..6) lidos via getComputedStyle.
  // Recharts não resolve var() em props SVG (fill/stroke), então passamos hex literal.
  // Re-lê quando o tema muda (dark/light).
  const [chartTokens, setChartTokens] = useState({
    c1: "#4F8EFF", c2: "#34D399", c3: "#F87171",
    c4: "#FBBF24", c5: "#A78BFA", c6: "#94A3B8",
  });
  useEffect(() => {
    const update = () => {
      const cs = getComputedStyle(document.documentElement);
      setChartTokens({
        c1: cs.getPropertyValue("--chart-1").trim() || "#4F8EFF",
        c2: cs.getPropertyValue("--chart-2").trim() || "#34D399",
        c3: cs.getPropertyValue("--chart-3").trim() || "#F87171",
        c4: cs.getPropertyValue("--chart-4").trim() || "#FBBF24",
        c5: cs.getPropertyValue("--chart-5").trim() || "#A78BFA",
        c6: cs.getPropertyValue("--chart-6").trim() || "#94A3B8",
      });
    };
    update();
    const obs = new MutationObserver(update);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);

  // Paleta restrita do donut (Composição de Impostos): 6 cores semânticas.
  const CORES_PIE = [chartTokens.c1, chartTokens.c2, chartTokens.c3, chartTokens.c4, chartTokens.c5, chartTokens.c6];

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

  // Botão secondary §5.8 — bg-elevated + border-default + text-primary, hover bg-overlay.
  const SECONDARY_CLS = "flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border";
  const SECONDARY_STYLE: React.CSSProperties = {
    background: "var(--bg-elevated)",
    borderColor: "var(--border-default)",
    color: "var(--text-primary)",
    borderRadius: "var(--radius-md)",
  };
  const onSecondaryEnter = (e: React.MouseEvent<HTMLElement>) => { e.currentTarget.style.background = "var(--bg-overlay)"; };
  const onSecondaryLeave = (e: React.MouseEvent<HTMLElement>) => { e.currentTarget.style.background = "var(--bg-elevated)"; };

  return (
    <div className="min-h-full p-6" style={{ background: "var(--bg-canvas)" }}>

      {/* ── BARRA DE CONTROLES (segue o tema) ── */}
      <div className="flex items-center justify-between mb-6 no-export">
        <div>
          <p
            className="text-xs uppercase font-medium mb-1"
            style={{
              color: "var(--text-tertiary)",
              letterSpacing: "var(--tracking-widest)",
            }}
          >
            Executivo
          </p>
          {/* §4.2: hierarquia por peso, sem destaque cromático em palavra */}
          <h1 className="text-3xl tracking-tight" style={{ color: "var(--text-primary)" }}>
            <span className="font-semibold">Dashboard</span>{" "}
            <span className="font-normal" style={{ color: "var(--text-secondary)" }}>Executivo</span>
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-tertiary)" }}>
            Relatório premium para apresentação ao cliente
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {/* Baixar Planilha Modelo (secondary) */}
          <button
            onClick={baixarPlanilhaModelo}
            className={SECONDARY_CLS}
            style={SECONDARY_STYLE}
            onMouseEnter={onSecondaryEnter}
            onMouseLeave={onSecondaryLeave}
          >
            <Download className="w-4 h-4" />
            Planilha Modelo
          </button>

          {/* Importar planilha (secondary) */}
          <label
            className={`${SECONDARY_CLS} cursor-pointer`}
            style={SECONDARY_STYLE}
            onMouseEnter={onSecondaryEnter}
            onMouseLeave={onSecondaryLeave}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Importar Dados
            <input
              type="file" accept=".xlsx,.xls,.csv" className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) importarXlsx(f); e.target.value = ""; }}
            />
          </label>

          {/* Modo edição (toggle visual: ativo = accent-subtle border) */}
          <button
            onClick={() => setEditando(v => !v)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border"
            style={{
              background: editando ? "var(--accent-subtle)" : "var(--bg-elevated)",
              borderColor: editando ? "var(--accent-border)" : "var(--border-default)",
              color: editando ? "var(--accent-text)" : "var(--text-primary)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
            {editando ? "Editando..." : "Editar"}
          </button>

          {/* Apresentação (secondary) */}
          <button
            onClick={exportarApresentacao}
            disabled={exportandoApres}
            className={`${SECONDARY_CLS} disabled:opacity-60`}
            style={SECONDARY_STYLE}
            onMouseEnter={(e) => { if (!e.currentTarget.disabled) onSecondaryEnter(e); }}
            onMouseLeave={onSecondaryLeave}
          >
            {exportandoApres ? (
              <div className="w-4 h-4 border-2 rounded-full animate-spin" style={{ borderColor: "var(--text-tertiary)", borderTopColor: "transparent" }} />
            ) : (
              <FileImage className="w-4 h-4" />
            )}
            Apresentação
          </button>

          {/* Exportar PNG (PRIMARY — único da página) */}
          <button
            onClick={exportarImagem}
            disabled={exportando}
            className="flex items-center gap-2 px-4 py-2 disabled:opacity-60 text-sm font-semibold transition-colors"
            style={{
              background: "var(--accent)",
              color: "var(--text-inverse)",
              borderRadius: "var(--radius-md)",
            }}
            onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.background = "var(--accent-hover)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "var(--accent)"; }}
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
                className="text-2xl font-semibold text-white rounded-md px-2 py-0.5 cursor-text bg-navy-900/40 border border-dashed border-navy-500/70 focus:outline-none focus:ring-2 focus:ring-navy-400/50"
              />
            ) : (
              <h2 className="text-2xl font-semibold text-white tracking-tight">{dados.nomeEmpresa}</h2>
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
            <p className="text-xs uppercase font-medium" style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}>Relatório Financeiro</p>
            <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>Gerado por Controllo Analytics</p>
          </div>
        </div>

        {/* KPIs (§5.4) */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {dados.kpis.map((kpi, i) => (
            <div
              key={i}
              className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 hover:border-slate-700 transition-colors"
            >
              {/* Eyebrow */}
              <p
                className="text-xs uppercase font-medium mb-2"
                style={{
                  color: "var(--text-tertiary)",
                  letterSpacing: "var(--tracking-widest)",
                }}
              >
                {kpi.label}
              </p>
              {/* Valor — font-mono tabular-nums weight-semibold */}
              <div className="mb-1">
                <EditVal
                  valor={kpi.valor} onChange={v => atualizarKpi(i, v)}
                  editando={editando} prefixo={kpi.prefixo} sufixo={kpi.sufixo}
                  className="text-2xl font-semibold text-white font-mono tabular-nums"
                />
              </div>
              {/* Delta com cor semântica */}
              <div className="flex items-center gap-1 text-xs font-medium">
                <span style={{ color: kpi.variacao >= 0 ? chartTokens.c2 : chartTokens.c3 }}>
                  {kpi.variacao >= 0 ? "▲" : "▼"}
                </span>
                <span
                  className="font-mono tabular-nums"
                  style={{ color: kpi.variacao >= 0 ? chartTokens.c2 : chartTokens.c3 }}
                >
                  {Math.abs(kpi.variacao).toFixed(1)}{kpi.sufixo === "%" ? " p.p." : "%"}
                </span>
                <span className="font-normal" style={{ color: "var(--text-tertiary)" }}>vs ano ant.</span>
              </div>
            </div>
          ))}
        </div>

        {/* Gráficos 2×2 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">

          {/* DRE Simplificada — mapeamento semântico (§5.6):
                Receita / Rec. Líq. → chart-1 (azul, positivo principal)
                Deduções → chart-3 (vermelho, dedução)
                Lucro Bruto / EBITDA / Lucro Líq. → chart-2 (verde, lucro derivado) */}
          <GraficoComNome nome={dados.nomeEmpresa}>
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
              <p
                className="text-xs uppercase font-medium mb-4"
                style={{
                  color: "var(--text-tertiary)",
                  letterSpacing: "var(--tracking-widest)",
                }}
              >
                DRE Simplificada
              </p>
              <div className="h-52">
                {(() => {
                  const dreData = [
                    { nome: "Receita",     valor: totalReceita,                    cor: chartTokens.c1 },
                    { nome: "Deduções",    valor: -(totalReceita * 0.08),          cor: chartTokens.c3 },
                    { nome: "Rec. Líq.",   valor: totalReceita * 0.92,             cor: chartTokens.c1 },
                    { nome: "Lucro Bruto", valor: totalReceita * 0.45,             cor: chartTokens.c2 },
                    { nome: "EBITDA",      valor: totalLucro * 1.3,                cor: chartTokens.c2 },
                    { nome: "Lucro Líq.",  valor: totalLucro,                      cor: chartTokens.c2 },
                  ];
                  return (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={dreData} layout="vertical" margin={{ left: 20, right: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} horizontal={false} />
                        <XAxis type="number" hide />
                        <YAxis dataKey="nome" type="category" tick={{ fill: ct.tickFill, fontSize: 10 }} tickLine={false} axisLine={false} width={60} />
                        <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle} formatter={(v) => formatFull(Math.abs(Number(v)))} />
                        <Bar dataKey="valor" radius={[0, 4, 4, 0]} maxBarSize={20}>
                          {dreData.map((d, i) => <Cell key={i} fill={d.cor} />)}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  );
                })()}
              </div>
            </div>
          </GraficoComNome>

          {/* Fluxo de Caixa Mensal — receita=chart-2 (success), despesas=chart-3 (danger) */}
          <GraficoComNome nome={dados.nomeEmpresa}>
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
              <p
                className="text-xs uppercase font-medium mb-4"
                style={{
                  color: "var(--text-tertiary)",
                  letterSpacing: "var(--tracking-widest)",
                }}
              >
                Fluxo de Caixa Mensal
              </p>
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={dados.meses} margin={{ left: -10, right: 5 }}>
                    <defs>
                      <linearGradient id="gradRec" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor={chartTokens.c2} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={chartTokens.c2} stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="gradDesp" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor={chartTokens.c3} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={chartTokens.c3} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} vertical={false} />
                    <XAxis dataKey="mes" tick={{ fill: ct.tickFill, fontSize: 10 }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fill: ct.tickFill, fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                    <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle} formatter={(v) => formatFull(Number(v))} />
                    <Area type="monotone" dataKey="receita"  stroke={chartTokens.c2} fill="url(#gradRec)"  strokeWidth={2} name="Receita" />
                    <Area type="monotone" dataKey="despesas" stroke={chartTokens.c3} fill="url(#gradDesp)" strokeWidth={2} name="Despesas" />
                    <Area type="monotone" dataKey="saldo"    stroke={chartTokens.c1} fill="none"          strokeWidth={2} strokeDasharray="4 2" name="Saldo" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </GraficoComNome>

          {/* Composição de Impostos — paleta restrita de 6 cores via chart-* */}
          <GraficoComNome nome={dados.nomeEmpresa} className="self-start">
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
              <p
                className="text-xs uppercase font-medium mb-4"
                style={{
                  color: "var(--text-tertiary)",
                  letterSpacing: "var(--tracking-widest)",
                }}
              >
                Composição de Impostos
              </p>
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
                  <p className="text-xs font-medium mb-1" style={{ color: "var(--text-tertiary)" }}>
                    Total: <span className="font-mono tabular-nums" style={{ color: "#FFFFFF" }}>{formatBRL(totalImpostos)}</span>
                  </p>
                  {dados.impostos.map((imp, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: CORES_PIE[i % CORES_PIE.length] }} />
                      <span className="text-xs flex-1 truncate" style={{ color: "var(--text-tertiary)" }}>{imp.nome}</span>
                      <span className="text-xs font-mono tabular-nums" style={{ color: "var(--text-secondary)" }}>{((imp.valor / totalImpostos) * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </GraficoComNome>

          {/* Indicadores Financeiros (§5.4) */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
            <p
              className="text-xs uppercase font-medium mb-4"
              style={{
                color: "var(--text-tertiary)",
                letterSpacing: "var(--tracking-widest)",
              }}
            >
              Indicadores Financeiros
            </p>
            <div className="grid grid-cols-2 gap-3">
              {dados.indicadores.map((ind, i) => (
                <div key={i} className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                  <p
                    className="text-xs uppercase font-medium mb-1"
                    style={{
                      color: "var(--text-tertiary)",
                      letterSpacing: "var(--tracking-widest)",
                    }}
                  >
                    {ind.label}
                  </p>
                  <p className="text-base font-semibold font-mono tabular-nums" style={{ color: "#FFFFFF" }}>{ind.valor}</p>
                  <p className="text-xs font-medium font-mono tabular-nums mt-0.5" style={{ color: ind.variacao >= 0 ? chartTokens.c2 : chartTokens.c3 }}>
                    {ind.variacao >= 0 ? "▲" : "▼"} {Math.abs(ind.variacao).toFixed(1)}%
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Tabela Anual — cores das colunas via chart-* (semântico restrito) */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-800">
            <p
              className="text-xs uppercase font-medium"
              style={{
                color: "var(--text-tertiary)",
                letterSpacing: "var(--tracking-widest)",
              }}
            >
              Demonstrativo Anual Detalhado
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-800/60 border-b border-slate-800">
                  <th
                    className="px-4 py-3 text-left uppercase font-medium"
                    style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}
                  >Mês</th>
                  <th className="px-4 py-3 text-right uppercase font-medium" style={{ color: chartTokens.c2, letterSpacing: "var(--tracking-widest)" }}>Receita</th>
                  <th className="px-4 py-3 text-right uppercase font-medium" style={{ color: chartTokens.c3, letterSpacing: "var(--tracking-widest)" }}>Despesas</th>
                  <th className="px-4 py-3 text-right uppercase font-medium" style={{ color: chartTokens.c1, letterSpacing: "var(--tracking-widest)" }}>Lucro</th>
                  <th className="px-4 py-3 text-right uppercase font-medium" style={{ color: chartTokens.c4, letterSpacing: "var(--tracking-widest)" }}>Impostos</th>
                  <th className="px-4 py-3 text-right uppercase font-medium" style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}>Saldo</th>
                </tr>
              </thead>
              <tbody>
                {dados.meses.map((m, i) => {
                  const colorByCampo = (campo: keyof DadosMes) =>
                    campo === "receita"  ? chartTokens.c2 :
                    campo === "despesas" ? chartTokens.c3 :
                    campo === "lucro"    ? chartTokens.c1 :
                    campo === "impostos" ? chartTokens.c4 :
                                            "var(--text-secondary)";
                  return (
                    <tr key={i} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 font-medium text-slate-300">{m.mes}</td>
                      {(["receita","despesas","lucro","impostos","saldo"] as (keyof DadosMes)[]).map((campo) => (
                        <td key={campo} className="px-4 py-3 text-right font-mono tabular-nums font-medium" style={{ color: colorByCampo(campo) }}>
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
                  );
                })}
                <tr className="border-t-2 border-slate-700 bg-slate-800/60">
                  <td className="px-4 py-3 uppercase text-xs font-semibold tracking-widest" style={{ color: "#FFFFFF" }}>TOTAL</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums font-semibold" style={{ color: chartTokens.c2 }}>{formatBRL(totalReceita)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums font-semibold" style={{ color: chartTokens.c3 }}>{formatBRL(totalDespesas)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums font-semibold" style={{ color: chartTokens.c1 }}>{formatBRL(totalLucro)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums font-semibold" style={{ color: chartTokens.c4 }}>{formatBRL(dados.meses.reduce((s, m) => s + m.impostos, 0))}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums font-semibold" style={{ color: "var(--text-secondary)" }}>{formatBRL(dados.meses.reduce((s, m) => s + m.saldo, 0))}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Rodapé */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-800/50">
          <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>Controllo BPO Analytics — Plataforma de Inteligência Financeira</p>
          <p className="text-xs font-mono tabular-nums" style={{ color: "var(--text-tertiary)" }}>
            {new Date().toLocaleDateString("pt-BR", { day: "2-digit", month: "long", year: "numeric" })}
          </p>
        </div>
      </div>

      {editando && (
        <p className="text-center text-xs mt-3" style={{ color: "var(--text-tertiary)" }}>
          ✏️ Modo edição ativo — clique em qualquer valor numérico para editá-lo
        </p>
      )}
    </div>
  );
}
