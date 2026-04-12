"use client";
import { useEffect, useState } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_BASE = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

interface Importacao {
  id: number;
  nome_arquivo: string;
  tipo_dado: string;
  status: "processando" | "concluido" | "erro";
  linhas_processadas: number;
  linhas_com_erro: number;
  resumo: Record<string, unknown>;
  mensagem_erro: string;
  criado_em: string;
}

const TIPO_LABELS: Record<string, string> = {
  faturamento: "Faturamento",
  folha: "Folha de Pagamento",
  impostos: "Impostos",
  dre: "DRE",
  fluxo: "Fluxo de Caixa",
  balanco: "Balanço",
  generico: "Genérico",
};

const TIPO_CORES: Record<string, string> = {
  faturamento: "bg-emerald-50 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20",
  folha: "bg-indigo-50 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-400 border-indigo-200 dark:border-indigo-500/20",
  impostos: "bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-500/20",
  dre: "bg-blue-50 dark:bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-500/20",
  fluxo: "bg-teal-50 dark:bg-teal-500/15 text-teal-700 dark:text-teal-400 border-teal-200 dark:border-teal-500/20",
  balanco: "bg-indigo-50 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-400 border-indigo-200 dark:border-indigo-500/20",
  generico: "bg-slate-100 dark:bg-slate-500/15 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-500/20",
};

function StatusBadge({ status }: { status: Importacao["status"] }) {
  if (status === "concluido")
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-500/15 border border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-400 text-xs font-semibold">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 dark:bg-emerald-400" />
        Concluído
      </span>
    );
  if (status === "erro")
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-50 dark:bg-rose-500/15 border border-rose-200 dark:border-rose-500/20 text-rose-700 dark:text-rose-400 text-xs font-semibold">
        <span className="w-1.5 h-1.5 rounded-full bg-rose-500 dark:bg-rose-400" />
        Erro
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-500/15 border border-amber-200 dark:border-amber-500/20 text-amber-700 dark:text-amber-400 text-xs font-semibold">
      <span className="w-1.5 h-1.5 rounded-full bg-amber-500 dark:bg-amber-400 animate-pulse" />
      Processando
    </span>
  );
}

function TipoBadge({ tipo }: { tipo: string }) {
  const cor = TIPO_CORES[tipo] ?? TIPO_CORES.generico;
  const label = TIPO_LABELS[tipo] ?? tipo;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs font-semibold ${cor}`}>
      {label}
    </span>
  );
}

function formatarData(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function DetalheResumo({ resumo }: { resumo: Record<string, unknown> }) {
  const entradas = Object.entries(resumo);
  if (entradas.length === 0) return <p className="text-xs text-slate-500 italic">Sem resumo disponível.</p>;
  return (
    <div className="grid grid-cols-2 gap-x-8 gap-y-1">
      {entradas.map(([k, v]) => (
        <div key={k} className="flex items-center gap-2 text-xs">
          <span className="text-[#64748B] dark:text-slate-500 capitalize">{k.replace(/_/g, " ")}:</span>
          <span className="text-[#0F172A] dark:text-slate-300 font-medium">{String(v)}</span>
        </div>
      ))}
    </div>
  );
}

function LinhaImportacao({ imp }: { imp: Importacao }) {
  const [expandido, setExpandido] = useState(false);
  const temResumo = Object.keys(imp.resumo).length > 0;
  const temErro = !!imp.mensagem_erro;

  return (
    <div className="border border-[#e2e8f0] dark:border-slate-700 rounded-xl overflow-hidden transition-all bg-white dark:bg-slate-800/40">
      <button
        onClick={() => setExpandido(!expandido)}
        className="w-full flex items-center gap-4 px-5 py-4 hover:bg-[#f8f9fb] dark:hover:bg-slate-700/30 transition-colors text-left"
      >
        {/* ícone arquivo */}
        <div className="w-9 h-9 rounded-lg bg-[#f0f4f8] dark:bg-slate-700 flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 text-[#829ab1] dark:text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>

        {/* nome do arquivo */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-[#102a43] dark:text-white truncate">{imp.nome_arquivo}</p>
          <p className="text-xs text-[#829ab1] mt-0.5">{formatarData(imp.criado_em)}</p>
        </div>

        {/* badges */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <TipoBadge tipo={imp.tipo_dado} />
          <StatusBadge status={imp.status} />
        </div>

        {/* stats */}
        <div className="hidden md:flex items-center gap-6 flex-shrink-0 text-xs">
          <div className="text-center">
            <p className="text-emerald-700 dark:text-emerald-400 font-bold">{imp.linhas_processadas}</p>
            <p className="text-slate-500">processadas</p>
          </div>
          {imp.linhas_com_erro > 0 && (
            <div className="text-center">
              <p className="text-rose-700 dark:text-rose-400 font-bold">{imp.linhas_com_erro}</p>
              <p className="text-slate-500">com erro</p>
            </div>
          )}
        </div>

        {/* chevron */}
        <svg
          className={`w-4 h-4 text-slate-500 flex-shrink-0 transition-transform ${expandido ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expandido && (
        <div className="border-t border-[#f1f5f9] dark:border-slate-700 px-5 py-4 bg-[#f8f9fb] dark:bg-slate-900/40 space-y-4">
          {/* stats mobile */}
          <div className="flex md:hidden gap-6 text-xs">
            <div>
              <span className="text-emerald-700 dark:text-emerald-400 font-bold">{imp.linhas_processadas}</span>
              <span className="text-slate-500 ml-1">linhas processadas</span>
            </div>
            {imp.linhas_com_erro > 0 && (
              <div>
                <span className="text-rose-700 dark:text-rose-400 font-bold">{imp.linhas_com_erro}</span>
                <span className="text-slate-500 ml-1">com erro</span>
              </div>
            )}
          </div>

          {temResumo && (
            <div>
              <p className="text-xs font-semibold text-[#64748B] dark:text-slate-400 uppercase tracking-widest mb-2">Resumo</p>
              <DetalheResumo resumo={imp.resumo} />
            </div>
          )}

          {temErro && (
            <div className="bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 rounded-lg px-4 py-3">
              <p className="text-xs font-semibold text-rose-700 dark:text-rose-400 mb-1">Mensagem de Erro</p>
              <p className="text-xs text-rose-600 dark:text-rose-300 font-mono whitespace-pre-wrap">{imp.mensagem_erro}</p>
            </div>
          )}

          {!temResumo && !temErro && (
            <p className="text-xs text-slate-500 italic">Nenhum detalhe adicional disponível.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function HistoricoImportacoesPage() {
  const { empresaSelecionada } = useEmpresa();
  const [importacoes, setImportacoes] = useState<Importacao[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [filtroTipo, setFiltroTipo] = useState("todos");
  const [filtroStatus, setFiltroStatus] = useState("todos");

  useEffect(() => {
    if (!empresaSelecionada) return;
    const token = localStorage.getItem("controllo_token");
    if (!token) return;

    setCarregando(true);
    fetch(`${API_BASE}/api/importacao/historico/${empresaSelecionada.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setImportacoes(Array.isArray(data) ? data : []))
      .catch(() => setImportacoes([]))
      .finally(() => setCarregando(false));
  }, [empresaSelecionada]);

  const filtradas = importacoes.filter((i) => {
    if (filtroTipo !== "todos" && i.tipo_dado !== filtroTipo) return false;
    if (filtroStatus !== "todos" && i.status !== filtroStatus) return false;
    return true;
  });

  const totalLinhas = importacoes.reduce((s, i) => s + i.linhas_processadas, 0);
  const totalErros = importacoes.reduce((s, i) => s + i.linhas_com_erro, 0);
  const totalFalhas = importacoes.filter((i) => i.status === "erro").length;

  return (
    <div className="min-h-full p-6 md:p-8" style={{ background: "var(--bg-primary)" }}>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-start gap-4 mb-5">
          <div className="w-11 h-11 rounded-xl bg-[#102a43] flex items-center justify-center shadow-sm flex-shrink-0">
            <svg className="w-5 h-5 text-[#9fb3c8]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </div>
          <div>
            <span className="text-[10px] font-semibold uppercase tracking-widest text-[#486581] bg-[#f0f4f8] dark:bg-navy-900/40 px-2 py-0.5 rounded">Central de Dados</span>
            <h1 className="text-[22px] font-bold text-[#102a43] dark:text-slate-100 tracking-tight mt-1">Importações e Dados</h1>
            <p className="text-sm text-[#627d98] dark:text-slate-400 mt-0.5">
              Gerencie a entrada de dados para cada módulo do sistema
            </p>
          </div>
        </div>

        {/* Bloco explicativo */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/40 rounded-xl p-4 mb-5 flex items-start gap-3">
          <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="text-sm font-semibold text-[#102a43] dark:text-blue-300">Como alimentar o sistema</p>
            <p className="text-xs text-[#486581] dark:text-slate-400 mt-1 leading-relaxed">
              Cada seção possui sua própria planilha modelo com as colunas específicas necessárias.
              Baixe o modelo da seção desejada, preencha com os dados da empresa selecionada e faça o upload.
              Os gráficos e relatórios são gerados automaticamente a partir dos dados importados.
              Selecione a empresa no seletor superior antes de importar.
            </p>
          </div>
        </div>

        {/* Hub de seções */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
          {[
            { name: "Dashboard Executivo", icon: "📊", href: "/dashboard-executivo" },
            { name: "Balanço Patrimonial", icon: "⚖️", href: "/balanco" },
            { name: "Insights Financeiros", icon: "💡", href: "/insights" },
            { name: "Orçamento vs Realizado", icon: "🎯", href: "/orcamento" },
            { name: "Sazonalidade", icon: "📅", href: "/sazonalidade" },
            { name: "Análise Tributária", icon: "🧾", href: "/painel-tributario" },
            { name: "Relatórios",  icon: "📄", href: "/relatorios" },
          ].map(section => (
            <div
              key={section.name}
              className="bg-white dark:bg-slate-800 rounded-xl border border-[#e2e8f0] dark:border-slate-700 p-4 flex items-center justify-between"
              style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}
            >
              <div className="flex items-center gap-3">
                <span className="text-xl leading-none">{section.icon}</span>
                <div>
                  <p className="text-sm font-semibold text-[#102a43] dark:text-slate-100">{section.name}</p>
                  <p className="text-xs text-[#829ab1] dark:text-slate-500 mt-0.5">
                    {empresaSelecionada ? empresaSelecionada.nome : "Selecione uma empresa"}
                  </p>
                </div>
              </div>
              <a
                href={section.href}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
                style={{ background: "#1E4976", color: "white" }}
                onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.background = "#0F2D4A"; }}
                onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.background = "#1E4976"; }}
              >
                Acessar
              </a>
            </div>
          ))}
        </div>
      </div>

      {/* Histórico */}
      <div className="mb-4">
        <h2 className="text-base font-bold text-[#102a43] dark:text-slate-100 mb-1">Histórico de Importações</h2>
        <p className="text-sm text-[#627d98] dark:text-slate-400">
          Registro de todos os arquivos importados e seu status de processamento.
        </p>
      </div>

      {!empresaSelecionada ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="w-14 h-14 rounded-2xl bg-[#f0f4f8] dark:bg-slate-800 border border-[#e2e8f0] dark:border-slate-700 flex items-center justify-center mb-4">
            <svg className="w-7 h-7 text-[#829ab1] dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M20 7H4a1 1 0 00-1 1v3a1 1 0 001 1h16a1 1 0 001-1V8a1 1 0 00-1-1z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 12v3a1 1 0 001 1h16a1 1 0 001-1v-3" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16v3a1 1 0 001 1h16a1 1 0 001-1v-3" />
              <circle cx="17" cy="9.5" r="0.75" fill="currentColor" stroke="none" />
              <circle cx="17" cy="14.5" r="0.75" fill="currentColor" stroke="none" />
            </svg>
          </div>
          <p className="text-[#486581] dark:text-slate-400 font-semibold">Selecione uma empresa</p>
          <p className="text-[#829ab1] dark:text-slate-500 text-sm mt-1">Use o seletor na barra superior para escolher uma empresa.</p>
        </div>
      ) : carregando ? (
        <div className="flex items-center justify-center py-24">
          <div className="w-8 h-8 border-2 border-[#102a43] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          {/* Resumo cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {[
              { label: "Total de Importações", value: importacoes.length, color: "text-[#1E4976] dark:text-blue-400" },
              { label: "Linhas Processadas", value: totalLinhas.toLocaleString("pt-BR"), color: "text-[#1A6B3C] dark:text-emerald-400" },
              { label: "Linhas com Erro", value: totalErros.toLocaleString("pt-BR"), color: totalErros > 0 ? "text-[#92400E] dark:text-amber-400" : "text-[#64748B] dark:text-slate-500" },
              { label: "Importações com Falha", value: totalFalhas, color: totalFalhas > 0 ? "text-[#B83030] dark:text-rose-400" : "text-[#64748B] dark:text-slate-500" },
            ].map((c) => (
              <div key={c.label} className="bg-white dark:bg-slate-800/50 border border-[#e2e8f0] dark:border-slate-700/50 rounded-xl p-4" style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}>
                <p className="text-xs text-[#829ab1] mb-1">{c.label}</p>
                <p className={`text-2xl font-black ${c.color}`}>{c.value}</p>
              </div>
            ))}
          </div>

          {/* Filtros */}
          <div className="flex flex-wrap gap-3 mb-5">
            <div className="flex items-center gap-2">
              <label className="text-xs text-[#829ab1] dark:text-slate-400">Tipo:</label>
              <select
                value={filtroTipo}
                onChange={(e) => setFiltroTipo(e.target.value)}
                className="bg-white dark:bg-slate-800 border border-[#e2e8f0] dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-[#334e68] dark:text-white focus:outline-none focus:ring-2 focus:ring-[#102a43]/10"
              >
                <option value="todos">Todos</option>
                {Object.entries(TIPO_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-[#829ab1] dark:text-slate-400">Status:</label>
              <select
                value={filtroStatus}
                onChange={(e) => setFiltroStatus(e.target.value)}
                className="bg-white dark:bg-slate-800 border border-[#e2e8f0] dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-[#334e68] dark:text-white focus:outline-none focus:ring-2 focus:ring-[#102a43]/10"
              >
                <option value="todos">Todos</option>
                <option value="concluido">Concluído</option>
                <option value="processando">Processando</option>
                <option value="erro">Erro</option>
              </select>
            </div>
            {(filtroTipo !== "todos" || filtroStatus !== "todos") && (
              <button
                onClick={() => { setFiltroTipo("todos"); setFiltroStatus("todos"); }}
                className="text-xs text-[#829ab1] dark:text-slate-400 hover:text-[#102a43] dark:hover:text-white underline"
              >
                Limpar filtros
              </button>
            )}
          </div>

          {/* Lista */}
          {filtradas.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center border border-dashed border-[#e2e8f0] dark:border-slate-700 rounded-2xl">
              <svg className="w-10 h-10 text-[#829ab1] dark:text-slate-600 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="text-[#486581] dark:text-slate-400 font-semibold">Nenhuma importação encontrada</p>
              <p className="text-[#829ab1] dark:text-slate-500 text-sm mt-1">
                {importacoes.length === 0
                  ? "Ainda não há importações para esta empresa."
                  : "Nenhuma importação corresponde aos filtros aplicados."}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {filtradas.map((imp) => (
                <LinhaImportacao key={imp.id} imp={imp} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
