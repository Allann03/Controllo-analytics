"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

// ─────────────────────────────────────────────────────────────────
//  Tipos
// ─────────────────────────────────────────────────────────────────

interface StepStatus {
  empresaCriada: boolean;
  dadosFiscais: boolean;
  lancamentoCriado: boolean;
  planoContas: boolean;
}

// ─────────────────────────────────────────────────────────────────
//  Definição dos passos
// ─────────────────────────────────────────────────────────────────

// ── Agrupamento visual dos steps ──────────────────────────────────
export const STEP_GRUPOS = [
  { label: "Configuração inicial", range: [0, 4] },
  { label: "Análise financeira",   range: [5, 9] },
  { label: "Tributário",           range: [10, 11] },
  { label: "Gestão operacional",   range: [12, 14] },
  { label: "Produtividade",        range: [15, 16] },
];

const STEPS = [
  // ── Configuração inicial ─────────────────────────────────────────
  {
    id: 1,
    titulo: "Selecione a empresa no menu superior",
    descricao: "O seletor de empresa fica no topo da tela. Ele filtra todos os módulos do sistema para exibir apenas os dados da empresa selecionada.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
      </svg>
    ),
    dica: "O seletor está no canto superior direito da topbar. Você pode buscar pelo nome ou CNPJ. A empresa fica salva entre sessões.",
    href: "/carteiras",
    acao: "Ir para Minha Carteira",
  },
  {
    id: 2,
    titulo: "Leitor de PDF — extratos bancários",
    descricao: "Faça o upload de extratos bancários em PDF (Itaú, Bradesco, Santander, BB, Nubank, C6, Caixa, Sicredi e outros). O sistema extrai todas as transações automaticamente.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    dica: "Após o upload, o sistema categoriza as transações e gera um Excel para download. Selecione o banco correto para melhor precisão.",
    href: "/",
    acao: "Ir para Leitor de PDF",
  },
  {
    id: 3,
    titulo: "Leitor em Lote — múltiplos PDFs",
    descricao: "Processe vários extratos de uma vez. Envie todos os PDFs do mês de uma empresa e o sistema consolida os dados automaticamente.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    ),
    dica: "Ideal para escritórios com muitos clientes. Processe 2-3 bancos de cada empresa em uma única operação e exporte tudo em lotes.",
    href: "/extrato-lote",
    acao: "Ir para Leitor em Lote",
  },
  {
    id: 4,
    titulo: "Importar Dados — planilhas financeiras",
    descricao: "Importe DRE, Balanço, Fluxo de Caixa, faturamento e folha de pagamento via Excel. O sistema detecta as colunas e faz o mapeamento automaticamente.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
      </svg>
    ),
    dica: "Use os modelos de planilha disponíveis na aba 'Modo Template' para garantir que os dados entrem sem erros. O modo avançado permite mapear colunas manualmente.",
    href: "/importar",
    acao: "Ir para Importar Dados",
  },
  {
    id: 5,
    titulo: "Plano de Contas — mapeamento contábil",
    descricao: "Configure o plano de contas da empresa, mapeando cada conta ao plano referencial do sistema. Isso garante que DRE, Balanço e Fluxo sejam calculados corretamente.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
      </svg>
    ),
    dica: "O sistema sugere mapeamentos automaticamente com base em palavras-chave. Confirme ou ajuste as sugestões e salve o template para reutilizar.",
    href: "/plano-contas",
    acao: "Ir para Plano de Contas",
  },

  // ── Análise financeira ───────────────────────────────────────────
  {
    id: 6,
    titulo: "Painel Financeiro — análise completa",
    descricao: "Visão integrada com DRE, Fluxo de Caixa, Balanço Patrimonial e Indicadores (EBITDA, ROE, ROA, Liquidez, Ciclo Financeiro) em abas. Selecione empresa e período.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    dica: "Navegue pelas abas DRE, Fluxo de Caixa, Balanço e Indicadores. Cada aba tem filtros por ano e mês com variação percentual mês a mês.",
    href: "/painel-financeiro",
    acao: "Ir para Análise Financeira",
  },
  {
    id: 7,
    titulo: "DRE — Demonstração do Resultado",
    descricao: "Visualize a DRE em cascata com Receita Bruta → Deduções → Receita Líquida → Lucro Bruto → EBIT → Lucro Líquido. Inclui variação % e insights automáticos.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
    dica: "A DRE compara automaticamente com benchmarks setoriais. Linhas em vermelho indicam desvios críticos que merecem atenção imediata.",
    href: "/dre",
    acao: "Ir para DRE",
  },
  {
    id: 8,
    titulo: "Fluxo de Caixa — histórico e projeção",
    descricao: "Acompanhe entradas, saídas e saldo mensal dos últimos 12 meses. O sistema projeta o saldo dos próximos 3 meses com base na tendência histórica.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
      </svg>
    ),
    dica: "Alertas são gerados automaticamente quando o saldo projetado fica negativo ou quando há queda abrupta de entradas.",
    href: "/fluxo-caixa",
    acao: "Ir para Fluxo de Caixa",
  },
  {
    id: 9,
    titulo: "Balanço Patrimonial",
    descricao: "Visualize o Ativo, Passivo e Patrimônio Líquido com grupos expansíveis. Indicadores de liquidez corrente, grau de imobilização e alavancagem são calculados automaticamente.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
      </svg>
    ),
    dica: "O balanço é montado a partir dos lançamentos mensais. O campo 'Patrimônio Líquido' deve equilibrar com a diferença entre Ativo e Passivo.",
    href: "/balanco",
    acao: "Ir para Balanço",
  },
  {
    id: 10,
    titulo: "Insights — alertas financeiros automáticos",
    descricao: "Painel consolidado de todos os alertas e insights detectados automaticamente: margem abaixo do benchmark, liquidez crítica, alta alavancagem, queda de receita e outros.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    dica: "Filtre por severidade (Crítico / Atenção / Info) ou por categoria (Margem, Liquidez, Alavancagem, Crescimento). Exporte para relatório em PDF.",
    href: "/insights",
    acao: "Ir para Insights",
  },

  // ── Tributário ───────────────────────────────────────────────────
  {
    id: 11,
    titulo: "Análise Tributária — carga e regime",
    descricao: "Compare a carga tributária real da empresa com benchmarks do setor. Visualize a evolução mensal de impostos sobre receita e identifique oportunidades de otimização.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z" />
      </svg>
    ),
    dica: "Informe o regime tributário (Simples Nacional, Lucro Presumido ou Lucro Real) no cadastro da empresa para que os cálculos sejam precisos.",
    href: "/painel-tributario",
    acao: "Ir para Análise Tributária",
  },
  {
    id: 12,
    titulo: "Simulação Tributária — Reforma 2026",
    descricao: "Simule o impacto da Reforma Tributária (IBS + CBS substituindo PIS/COFINS/ISS/ICMS) no regime atual da empresa. Veja lado a lado o cenário atual vs. reforma.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
      </svg>
    ),
    dica: "A simulação usa os parâmetros oficiais da reforma. Informe a atividade principal da empresa para calcular as alíquotas corretas do IBS e CBS.",
    href: "/simulacao-tributaria",
    acao: "Ir para Simulação Tributária",
  },

  // ── Gestão operacional ───────────────────────────────────────────
  {
    id: 13,
    titulo: "Conciliação Bancária",
    descricao: "Reconcilie os lançamentos do extrato bancário com os registros contábeis. Identifique lançamentos pendentes, duplicados ou com divergência de valor.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
    dica: "Importe o extrato via PDF ou planilha antes de iniciar a conciliação. O sistema sugerirá automaticamente os pares de lançamentos correspondentes.",
    href: "/conciliacao",
    acao: "Ir para Conciliação",
  },
  {
    id: 14,
    titulo: "Orçamento vs. Realizado",
    descricao: "Cadastre metas mensais (receita, despesas, lucro) e acompanhe automaticamente o desvio em relação ao realizado. Status OK / Atenção / Crítico por linha.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
    dica: "Defina o orçamento no início do ano ou mês a mês. O realizado é puxado automaticamente dos lançamentos importados.",
    href: "/orcamento",
    acao: "Ir para Orçamento",
  },
  {
    id: 15,
    titulo: "Relatórios — exportação profissional",
    descricao: "Gere relatórios financeiros completos em PDF ou Excel para enviar ao cliente. Inclui DRE, Balanço, Fluxo de Caixa, Indicadores e Análise de Sazonalidade.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    dica: "Os relatórios são gerados com o logo e nome da empresa. Use o módulo Sazonalidade para incluir análise histórica de 12 meses no pacote.",
    href: "/relatorios",
    acao: "Ir para Relatórios",
  },

  // ── Produtividade ────────────────────────────────────────────────
  {
    id: 16,
    titulo: "Agenda — lembretes e vencimentos",
    descricao: "Cadastre lembretes de vencimentos (impostos, obrigações acessórias, reuniões). Receba notificação visual quando um prazo estiver próximo ou atrasado.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
    dica: "O ícone de sino na sidebar mostra quantos lembretes estão atrasados. Vincule cada lembrete a uma empresa para manter o contexto organizado.",
    href: "/agenda",
    acao: "Ir para Agenda",
  },
  {
    id: 17,
    titulo: "Alertas por e-mail — notificações automáticas",
    descricao: "Configure alertas automáticos por e-mail para cada empresa: margem crítica, liquidez baixa, fluxo negativo, vencimentos próximos. Escolha a frequência e o horário.",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
    ),
    dica: "Configure um e-mail de destino por empresa ou use um e-mail central para toda a carteira. O resumo mensal é enviado automaticamente no dia configurado.",
    href: "/alertas",
    acao: "Configurar Alertas",
  },
];

// ─────────────────────────────────────────────────────────────────
//  SVG Icons reutilizáveis
// ─────────────────────────────────────────────────────────────────

const CheckIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
  </svg>
);

const BulbIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
  </svg>
);

// ─────────────────────────────────────────────────────────────────
//  Círculo de progresso SVG
// ─────────────────────────────────────────────────────────────────

function ProgressCircle({ value, total }: { value: number; total: number }) {
  const pct = total > 0 ? value / total : 0;
  const r = 26;
  const circ = 2 * Math.PI * r;
  const dash = circ * pct;
  return (
    <div className="relative w-16 h-16 flex-shrink-0">
      <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
        <circle cx="32" cy="32" r={r} fill="none" stroke="rgba(79,106,255,0.12)" strokeWidth="4" />
        <circle
          cx="32" cy="32" r={r} fill="none"
          stroke={pct === 1 ? "#10b981" : "#102a43"}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-sm font-extrabold" style={{ color: pct === 1 ? "#10b981" : "#3b6ea5" }}>{value}</span>
        <span className="text-[9px] font-bold" style={{ color: "var(--text-muted)" }}>/{total}</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
//  Página principal
// ─────────────────────────────────────────────────────────────────

const STORAGE_KEY = "controllo_onboarding_v2";

export default function OnboardingPage() {
  const router = useRouter();
  const [passo, setPasso]         = useState(0);
  const [concluidos, setConcluidos] = useState<Set<number>>(new Set());

  useEffect(() => {
    const t = localStorage.getItem("controllo_token");
    const u = localStorage.getItem("controllo_user");
    if (!t || !u) { router.push("/"); return; }
    try { if (!JSON.parse(u).is_aprovado) { router.push("/"); return; } } catch { router.push("/"); return; }

    // Restaura progresso do localStorage
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const arr: number[] = JSON.parse(saved);
        setConcluidos(new Set(arr));
        // Abre o primeiro passo não concluído
        const primeiro = STEPS.findIndex((_, i) => !arr.includes(i));
        setPasso(primeiro >= 0 ? primeiro : STEPS.length - 1);
      }
    } catch { /* ignora */ }
  }, [router]);

  function concluir(index: number) {
    const novo = new Set([...concluidos, index]);
    setConcluidos(novo);
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...novo]));
    // Avança para o próximo passo não concluído
    const proximo = STEPS.findIndex((_, i) => i > index && !novo.has(i));
    if (proximo >= 0) setPasso(proximo);
  }

  function resetar() {
    setConcluidos(new Set());
    setPasso(0);
    localStorage.removeItem(STORAGE_KEY);
  }

  const progresso = Math.round((concluidos.size / STEPS.length) * 100);
  const tudo = concluidos.size === STEPS.length;

  const stepAtivo = STEPS[passo];
  const isAtivoConcluido = concluidos.has(passo);

  return (
    <div className="min-h-full" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>

      {/* ── Header ── */}
      <header className="px-8 pt-8 pb-6" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-start justify-between gap-6">

          {/* Left: icon + title */}
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0 bg-navy-50 border border-navy-200 dark:bg-navy-900/30 dark:border-navy-700/50">
              <svg className="w-5 h-5 text-navy-600 dark:text-navy-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight" style={{ color: "var(--text-primary)" }}>
                Guia de Início
              </h1>
              <p className="text-sm mt-0.5" style={{ color: "var(--text-muted)" }}>
                Configure o Controllo passo a passo
              </p>
            </div>
          </div>

          {/* Right: progress circle + reset */}
          <div className="flex items-center gap-4">
            {tudo && (
              <button
                onClick={resetar}
                className="text-xs font-semibold transition-colors"
                style={{ color: "var(--text-muted)" }}
                onMouseEnter={e => (e.currentTarget.style.color = "var(--text-secondary)")}
                onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
              >
                Reiniciar guia
              </button>
            )}
            <ProgressCircle value={concluidos.size} total={STEPS.length} />
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
              Progresso geral
            </span>
            <span className="text-xs font-bold" style={{ color: tudo ? "#10b981" : "#3b6ea5" }}>
              {progresso}%
            </span>
          </div>
          <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "var(--bg-secondary)" }}>
            <div
              className="h-full rounded-full transition-all duration-700 ease-out"
              style={{
                width: `${progresso}%`,
                background: tudo
                  ? "linear-gradient(90deg, #10b981, #34d399)"
                  : "linear-gradient(90deg, #102a43, #3b6ea5)",
                boxShadow: tudo ? "0 0 8px rgba(16,185,129,0.4)" : "0 0 8px rgba(79,106,255,0.4)",
              }}
            />
          </div>
        </div>
      </header>

      {/* ── Body ── */}
      <div className="px-8 py-8">
        {tudo ? (
          /* ── Completion screen ── */
          <div className="max-w-xl mx-auto">
            <div
              className="rounded-3xl p-12 text-center"
              style={{
                background: "radial-gradient(ellipse at center top, rgba(16,185,129,0.10), rgba(79,106,255,0.05) 60%, transparent)",
                border: "1px solid rgba(16,185,129,0.2)",
                boxShadow: "0 0 60px rgba(16,185,129,0.06)",
              }}
            >
              {/* Animated check circle */}
              <div className="relative w-24 h-24 mx-auto mb-8">
                <div
                  className="w-24 h-24 rounded-full flex items-center justify-center"
                  style={{
                    background: "radial-gradient(circle, rgba(16,185,129,0.20), rgba(16,185,129,0.06))",
                    border: "2px solid rgba(16,185,129,0.35)",
                    boxShadow: "0 0 32px rgba(16,185,129,0.20)",
                  }}
                >
                  <CheckIcon className="w-12 h-12 text-emerald-400" />
                </div>
                <div
                  className="absolute inset-0 rounded-full animate-ping"
                  style={{ background: "rgba(16,185,129,0.06)", animationDuration: "2.5s" }}
                />
              </div>

              <span
                className="text-[10px] font-bold uppercase tracking-widest"
                style={{ color: "#10b981" }}
              >
                Configuração completa
              </span>
              <h2 className="text-3xl font-extrabold tracking-tight mt-2 mb-3" style={{ color: "var(--text-primary)" }}>
                Tudo configurado!
              </h2>
              <p className="text-sm leading-relaxed max-w-sm mx-auto" style={{ color: "var(--text-secondary)" }}>
                O Controllo está pronto para uso. Agora você pode importar dados de todas as suas empresas
                e acompanhar a saúde financeira de cada uma delas em tempo real.
              </p>

              <div className="grid grid-cols-2 gap-3 mt-8">
                <button
                  onClick={() => router.push("/dashboard-executivo")}
                  className="py-3.5 rounded-xl text-sm font-bold text-white transition-all duration-200 hover:-translate-y-0.5 active:scale-95"
                  style={{
                    background: "linear-gradient(135deg, #102a43, #1e3a5f)",
                    boxShadow: "0 4px 20px rgba(79,106,255,0.30)",
                  }}
                >
                  Ver Dashboard
                </button>
                <button
                  onClick={() => router.push("/painel-financeiro")}
                  className="py-3.5 rounded-xl text-sm font-semibold transition-all duration-200 hover:-translate-y-0.5 active:scale-95"
                  style={{
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border)",
                    color: "var(--text-secondary)",
                  }}
                >
                  Análise Financeira
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* ── Two-column stepper layout ── */
          <div className="flex flex-col lg:flex-row gap-6 lg:gap-8 items-start">

            {/* ── LEFT: Vertical stepper (fixed width) ── */}
            <div className="w-full lg:w-[300px] lg:flex-shrink-0 lg:sticky lg:top-8 lg:max-h-[calc(100vh-8rem)] lg:overflow-y-auto lg:pr-1">
              <div className="space-y-0">
                {STEPS.map((step, i) => {
                  const done = concluidos.has(i);
                  const active = passo === i;
                  const isLast = i === STEPS.length - 1;
                  const grupo = STEP_GRUPOS.find(g => g.range[0] === i);

                  return (
                    <div key={step.id}>
                      {/* Group header */}
                      {grupo && (
                        <p className="text-[9px] font-black uppercase tracking-[0.18em] px-1 pt-3 pb-1 first:pt-0"
                          style={{ color: "var(--text-muted)", opacity: 0.5 }}>
                          {grupo.label}
                        </p>
                      )}
                      {/* Step row */}
                      <div
                        onClick={() => setPasso(i)}
                        className="flex items-start gap-3 cursor-pointer group transition-all duration-150"
                        style={{ padding: "6px 0" }}
                      >
                        {/* Circle + connector column */}
                        <div className="flex flex-col items-center flex-shrink-0" style={{ width: 36 }}>
                          {/* Number circle */}
                          <div
                            className="w-9 h-9 rounded-full flex items-center justify-center transition-all duration-200 flex-shrink-0"
                            style={
                              done
                                ? {
                                    background: "linear-gradient(135deg, #10b981, #059669)",
                                    boxShadow: "0 0 12px rgba(16,185,129,0.30)",
                                  }
                                : active
                                ? {
                                    background: "linear-gradient(135deg, rgba(79,106,255,0.20), rgba(79,106,255,0.08))",
                                    border: "2px solid #102a43",
                                    boxShadow: "0 0 14px rgba(79,106,255,0.35)",
                                    color: "#3b6ea5",
                                  }
                                : {
                                    background: "var(--bg-secondary)",
                                    border: "1px solid var(--border)",
                                    opacity: 0.5,
                                    color: "var(--text-muted)",
                                  }
                            }
                          >
                            {done ? (
                              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                              </svg>
                            ) : (
                              <span className="w-5 h-5 flex items-center justify-center [&>svg]:w-5 [&>svg]:h-5"
                                style={{ color: active ? "#3b6ea5" : "var(--text-muted)" }}>
                                {step.icone}
                              </span>
                            )}
                          </div>

                          {/* Connector line */}
                          {!isLast && (
                            <div
                              className="mt-1"
                              style={{
                                width: 2,
                                height: 32,
                                borderRadius: 2,
                                background: done ? "#10b981" : "var(--border)",
                                opacity: done ? 0.6 : 0.4,
                                transition: "background 0.4s",
                              }}
                            />
                          )}
                        </div>

                        {/* Step label beside circle */}
                        <div className="pt-1 pb-1" style={{ minHeight: isLast ? 36 : 68 }}>
                          <span
                            className="text-[10px] font-bold uppercase tracking-widest block leading-none"
                            style={{
                              color: done ? "#10b981" : active ? "#3b6ea5" : "var(--text-muted)",
                            }}
                          >
                            Passo {i + 1}
                          </span>
                          <p
                            className="text-[13px] font-semibold mt-0.5 leading-snug transition-colors duration-150"
                            style={{
                              color: done
                                ? "var(--text-muted)"
                                : active
                                ? "var(--text-primary)"
                                : "var(--text-muted)",
                              opacity: done ? 0.55 : active ? 1 : 0.6,
                              textDecoration: done ? "line-through" : "none",
                            }}
                          >
                            {step.titulo}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ── RIGHT: Active step detail panel ── */}
            <div className="flex-1 min-w-0">
              <div
                className="rounded-2xl overflow-hidden"
                style={{
                  background: "var(--bg-card)",
                  borderTop: "4px solid transparent",
                  borderImage: "linear-gradient(90deg, #102a43, #3b6ea5) 1",
                  boxShadow: "0 8px 40px rgba(0,0,0,0.25), 0 0 0 1px var(--border)",
                }}
              >
                {/* Inner radial glow area */}
                <div
                  style={{
                    background: "radial-gradient(ellipse at top left, rgba(79,106,255,0.08), transparent 70%)",
                    padding: "32px",
                  }}
                >
                  {/* Step icon */}
                  <div
                    className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-5 ${
                      isAtivoConcluido
                        ? "bg-emerald-50 border border-emerald-200 text-emerald-600 dark:bg-emerald-900/20 dark:border-emerald-700/40 dark:text-emerald-400"
                        : "bg-navy-50 border border-navy-200 text-navy-600 dark:bg-navy-900/30 dark:border-navy-700/50 dark:text-navy-400"
                    }`}
                  >
                    {isAtivoConcluido ? (
                      <CheckIcon className="w-7 h-7 text-emerald-400" />
                    ) : (
                      stepAtivo.icone
                    )}
                  </div>

                  {/* Step meta label */}
                  <span
                    className="text-[10px] font-bold uppercase tracking-widest"
                    style={{ color: "#3b6ea5" }}
                  >
                    Passo {passo + 1} de {STEPS.length}
                  </span>

                  {/* Title */}
                  <h2 className="text-2xl font-extrabold tracking-tight mt-1" style={{ color: "var(--text-primary)" }}>
                    {stepAtivo.titulo}
                  </h2>

                  {/* Description */}
                  <p className="text-sm leading-relaxed mt-2" style={{ color: "var(--text-secondary)" }}>
                    {stepAtivo.descricao}
                  </p>

                  {/* Dica box */}
                  <div
                    className="mt-5 flex gap-3 items-start rounded-xl px-4 py-3"
                    style={{
                      borderLeft: "2px solid #3b6ea5",
                      background: "rgba(79,106,255,0.06)",
                    }}
                  >
                    <BulbIcon className="w-4 h-4 flex-shrink-0 mt-0.5 text-[#3b6ea5]" />
                    <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      {stepAtivo.dica}
                    </p>
                  </div>

                  {/* Action buttons */}
                  <div className="mt-6 flex flex-wrap gap-3">
                    {isAtivoConcluido ? (
                      /* Completed state */
                      <>
                        <div
                          className="flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-xl"
                          style={{
                            background: "rgba(16,185,129,0.10)",
                            border: "1px solid rgba(16,185,129,0.25)",
                            color: "#10b981",
                          }}
                        >
                          <CheckIcon className="w-4 h-4 text-emerald-400" />
                          Concluído
                        </div>

                        {/* Next step button if available */}
                        {passo < STEPS.length - 1 && (
                          <button
                            onClick={() => {
                              const proximo = STEPS.findIndex((_, i) => i > passo && !concluidos.has(i));
                              if (proximo >= 0) setPasso(proximo);
                              else setPasso(passo + 1);
                            }}
                            className="text-sm font-bold px-5 py-2 rounded-xl text-white transition-all duration-200 hover:-translate-y-0.5 active:scale-95"
                            style={{
                              background: "linear-gradient(135deg, #102a43, #1e3a5f)",
                              boxShadow: "0 4px 16px rgba(79,106,255,0.28)",
                            }}
                          >
                            Proximo passo →
                          </button>
                        )}
                      </>
                    ) : (
                      /* Active uncompleted state */
                      <>
                        <button
                          onClick={() => router.push(stepAtivo.href)}
                          className="text-sm font-bold px-5 py-2.5 rounded-xl text-white transition-all duration-200 hover:-translate-y-0.5 active:scale-95"
                          style={{
                            background: "linear-gradient(135deg, #102a43, #1e3a5f)",
                            boxShadow: "0 4px 18px rgba(79,106,255,0.30)",
                          }}
                        >
                          {stepAtivo.acao} →
                        </button>
                        <button
                          onClick={() => concluir(passo)}
                          className="text-sm font-bold px-5 py-2.5 rounded-xl transition-all duration-200 hover:-translate-y-0.5 active:scale-95"
                          style={{
                            border: "1px solid rgba(16,185,129,0.35)",
                            background: "rgba(16,185,129,0.08)",
                            color: "#10b981",
                          }}
                        >
                          Marcar como concluído
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
