"use client";
import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { Building2 } from "lucide-react";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

interface EmpresaGeral {
  id: number;
  nome: string;
  nome_fantasia: string;
  cnpj: string;
  ccm: string;
  observacoes: string;
  status: string;
  na_minha_carteira: boolean;
  carteira_observacoes: string;
  em_uso_por_id: number | null;
  em_uso_por: string | null;
  score_saude?: number | null;
  score_classificacao?: string | null;
  score_cor?: string | null;
}

type FiltroCarteira = "todas" | "minhas" | "livres" | "ocupadas";

const STATUS_LABEL: Record<string, string> = {
  iniciada: "Iniciada", em_andamento: "Em andamento", extratos_pendentes: "Extratos pendentes",
  pendencia_fiscal: "Pend. fiscal", pendencia_juridica: "Pend. jurídica", finalizada: "Finalizada",
  aguardando_documentos: "Ag. documentos", documentacao_pendente: "Doc. pendente", em_revisao: "Em revisão",
  entregue: "Entregue", suspenso: "Suspenso", concluida: "Concluída",
  defis_entregue: "DEFIS entregue", erro_integracao_fiscal: "Erro fiscal", erro_integracao_folha: "Erro folha",
};
const STATUS_COLOR: Record<string, { bg: string; color: string }> = {
  em_andamento: { bg: "rgba(79,106,255,0.12)", color: "#3b6ea5" },
  finalizada: { bg: "rgba(16,185,129,0.10)", color: "#34d399" },
  entregue: { bg: "rgba(16,185,129,0.10)", color: "#34d399" },
  concluida: { bg: "rgba(16,185,129,0.10)", color: "#34d399" },
  defis_entregue: { bg: "rgba(16,185,129,0.10)", color: "#34d399" },
  extratos_pendentes: { bg: "rgba(245,158,11,0.10)", color: "#f59e0b" },
  pendencia_fiscal: { bg: "rgba(245,158,11,0.10)", color: "#f59e0b" },
  pendencia_juridica: { bg: "rgba(245,158,11,0.10)", color: "#f59e0b" },
  aguardando_documentos: { bg: "rgba(245,158,11,0.10)", color: "#f59e0b" },
  documentacao_pendente: { bg: "rgba(245,158,11,0.10)", color: "#f59e0b" },
  em_revisao: { bg: "rgba(245,158,11,0.10)", color: "#f59e0b" },
  suspenso: { bg: "rgba(239,68,68,0.10)", color: "#f87171" },
  erro_integracao_fiscal: { bg: "rgba(239,68,68,0.10)", color: "#f87171" },
  erro_integracao_folha: { bg: "rgba(239,68,68,0.10)", color: "#f87171" },
};

function tk() { return localStorage.getItem("controllo_token") ?? ""; }

function StatusEmpresaBadge({ status }: { status: string }) {
  const label = STATUS_LABEL[status] ?? status;
  const style = STATUS_COLOR[status] ?? { bg: "rgba(100,116,139,0.10)", color: "var(--text-muted)" };
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold"
      style={{ background: style.bg, color: style.color }}
    >
      {label}
    </span>
  );
}

export default function CarteiraGeralPage() {
  const [empresas, setEmpresas]     = useState<EmpresaGeral[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [busca, setBusca]           = useState("");
  const [filtroCarteira, setFiltroCarteira] = useState<FiltroCarteira>("todas");
  const [filtroResponsavel, setFiltroResponsavel] = useState("");
  const [toggling, setToggling]     = useState<number | null>(null);
  const [toast, setToast]           = useState<{ msg: string; tipo: "ok" | "erro" } | null>(null);
  const [ordenacao, setOrdenacao]   = useState<"nome" | "score_asc" | "score_desc">("nome");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const mostrarToast = (msg: string, tipo: "ok" | "erro") => {
    setToast({ msg, tipo });
    setTimeout(() => setToast(null), 3500);
  };

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const res = await fetch(`${API}/api/carteira/disponiveis`, {
        headers: { Authorization: `Bearer ${tk()}` },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setEmpresas(await res.json());
    } catch {
      mostrarToast("Erro ao carregar empresas", "erro");
    } finally { setCarregando(false); }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  async function toggle(empresa: EmpresaGeral) {
    if (toggling !== null) return;
    if (!empresa.na_minha_carteira && empresa.em_uso_por) return;
    setToggling(empresa.id);
    try {
      const method = empresa.na_minha_carteira ? "DELETE" : "POST";
      const res = await fetch(`${API}/api/carteira/${empresa.id}`, {
        method,
        headers: { Authorization: `Bearer ${tk()}` },
      });
      if (!res.ok) throw new Error(((await res.json().catch(() => ({}))).detail) || "Erro ao atualizar.");
      setEmpresas(prev => prev.map(e =>
        e.id === empresa.id
          ? { ...e, na_minha_carteira: !empresa.na_minha_carteira, em_uso_por: !empresa.na_minha_carteira ? null : e.em_uso_por }
          : e
      ));
      mostrarToast(empresa.na_minha_carteira ? "Empresa removida da carteira." : "Empresa adicionada à carteira.", "ok");
    } catch (e: unknown) {
      mostrarToast(e instanceof Error ? e.message : "Erro ao atualizar", "erro");
    } finally { setToggling(null); }
  }

  const responsaveis = useMemo(() => {
    const set = new Set<string>();
    empresas.forEach(e => { if (e.em_uso_por) set.add(e.em_uso_por); });
    return Array.from(set).sort();
  }, [empresas]);

  const filtradas = useMemo(() => {
    let list = empresas;
    if (busca.trim()) {
      const q = busca.toLowerCase();
      list = list.filter(e =>
        e.nome.toLowerCase().includes(q) ||
        (e.nome_fantasia || "").toLowerCase().includes(q) ||
        e.cnpj.includes(q) ||
        e.ccm.toLowerCase().includes(q)
      );
    }
    if (filtroResponsavel) {
      list = list.filter(e => (e.em_uso_por ?? "") === filtroResponsavel);
    }
    if (filtroCarteira === "minhas")   list = list.filter(e => e.na_minha_carteira);
    if (filtroCarteira === "livres")   list = list.filter(e => !e.em_uso_por && !e.na_minha_carteira);
    if (filtroCarteira === "ocupadas") list = list.filter(e => !!e.em_uso_por && !e.na_minha_carteira);

    if (ordenacao === "score_desc") {
      list = [...list].sort((a, b) => (b.score_saude ?? -1) - (a.score_saude ?? -1));
    } else if (ordenacao === "score_asc") {
      list = [...list].sort((a, b) => (a.score_saude ?? 999) - (b.score_saude ?? 999));
    } else {
      list = [...list].sort((a, b) => a.nome.localeCompare(b.nome));
    }

    return list;
  }, [empresas, busca, filtroResponsavel, filtroCarteira, ordenacao]);

  const totalNaCarteira  = empresas.filter(e => e.na_minha_carteira).length;
  const totalOcupadas    = empresas.filter(e => e.em_uso_por && !e.na_minha_carteira).length;
  const totalDisponiveis = empresas.filter(e => !e.em_uso_por && !e.na_minha_carteira).length;
  const total            = empresas.length;
  const totalCriticos    = empresas.filter(e => e.score_saude != null && e.score_saude < 40).length;

  const FILTROS: { key: FiltroCarteira; label: string; count: number }[] = [
    { key: "todas",    label: "Todas",    count: total },
    { key: "minhas",   label: "Minhas",   count: totalNaCarteira },
    { key: "livres",   label: "Livres",   count: totalDisponiveis },
    { key: "ocupadas", label: "Ocupadas", count: totalOcupadas },
  ];

  return (
    <div className="min-h-full" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>

      {/* Toast */}
      {toast && (
        <div className="fixed top-6 right-6 z-50 px-5 py-3 rounded-2xl text-sm font-semibold shadow-2xl"
          style={{
            border: `1px solid ${toast.tipo === "ok" ? "rgba(16,185,129,0.35)" : "rgba(239,68,68,0.35)"}`,
            background: toast.tipo === "ok" ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.12)",
            color: toast.tipo === "ok" ? "#34d399" : "#f87171",
            backdropFilter: "blur(12px)",
          }}>
          {toast.msg}
        </div>
      )}

      {/* -- HEADER -- */}
      <header className="px-8 pt-8 pb-6 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5">

          {/* Title + description */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: "rgba(79,106,255,0.12)", border: "1px solid rgba(79,106,255,0.22)" }}>
              <svg className="w-5 h-5" style={{ color: "#3b6ea5" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight">Carteira Geral</h1>
              <p className="text-sm mt-0.5" style={{ color: "var(--text-muted)" }}>
                Selecione as empresas que você gerencia · empresas ocupadas por outro analista estão bloqueadas
              </p>
            </div>
          </div>

          {/* Stats pills */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex flex-col items-center px-4 py-2 rounded-xl cursor-pointer transition-all hover:scale-105 hover:shadow-lg"
              style={{ background: filtroCarteira === "minhas" ? "rgba(79,106,255,0.18)" : "rgba(79,106,255,0.10)", border: filtroCarteira === "minhas" ? "1px solid rgba(79,106,255,0.40)" : "1px solid rgba(79,106,255,0.20)" }}
              onClick={() => setFiltroCarteira(filtroCarteira === "minhas" ? "todas" : "minhas")}>
              <svg className="w-4 h-4 mb-0.5" style={{ color: "#3b6ea5" }} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
              <span className="text-xl font-black" style={{ color: "#3b6ea5" }}>{totalNaCarteira}</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "rgba(123,143,255,0.7)" }}>Minhas</span>
            </div>
            <div className="flex flex-col items-center px-4 py-2 rounded-xl cursor-pointer transition-all hover:scale-105 hover:shadow-lg"
              style={{ background: filtroCarteira === "livres" ? "rgba(16,185,129,0.16)" : "rgba(16,185,129,0.08)", border: filtroCarteira === "livres" ? "1px solid rgba(16,185,129,0.35)" : "1px solid rgba(16,185,129,0.18)" }}
              onClick={() => setFiltroCarteira(filtroCarteira === "livres" ? "todas" : "livres")}>
              <svg className="w-4 h-4 mb-0.5" style={{ color: "#34d399" }} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-xl font-black" style={{ color: "#34d399" }}>{totalDisponiveis}</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "rgba(52,211,153,0.6)" }}>Livres</span>
            </div>
            <div className="flex flex-col items-center px-4 py-2 rounded-xl cursor-pointer transition-all hover:scale-105 hover:shadow-lg"
              style={{ background: filtroCarteira === "ocupadas" ? "rgba(100,116,139,0.16)" : "rgba(100,116,139,0.08)", border: filtroCarteira === "ocupadas" ? "1px solid rgba(100,116,139,0.35)" : "1px solid rgba(100,116,139,0.18)" }}
              onClick={() => setFiltroCarteira(filtroCarteira === "ocupadas" ? "todas" : "ocupadas")}>
              <svg className="w-4 h-4 mb-0.5" style={{ color: "var(--text-secondary)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <span className="text-xl font-black" style={{ color: "var(--text-secondary)" }}>{totalOcupadas}</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Ocupadas</span>
            </div>
            {/* Critical score pill */}
            <div className="flex flex-col items-center px-4 py-2 rounded-xl transition-all hover:scale-105 hover:shadow-lg"
              style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.18)" }}>
              <svg className="w-4 h-4 mb-0.5" style={{ color: "#f87171" }} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.832c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <span className="text-xl font-black" style={{ color: "#f87171" }}>{totalCriticos}</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "rgba(248,113,113,0.7)" }}>Críticos</span>
            </div>
            <div className="flex flex-col items-center px-4 py-2 rounded-xl cursor-pointer transition-all hover:scale-105 hover:shadow-lg"
              style={{ background: filtroCarteira === "todas" ? "rgba(79,106,255,0.06)" : "var(--bg-card)", border: filtroCarteira === "todas" ? "1px solid rgba(79,106,255,0.20)" : "1px solid var(--border)" }}
              onClick={() => setFiltroCarteira("todas")}>
              <svg className="w-4 h-4 mb-0.5" style={{ color: "var(--text-primary)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
              <span className="text-xl font-black" style={{ color: "var(--text-primary)" }}>{total}</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Total</span>
            </div>
          </div>
        </div>
      </header>

      <div className="px-8 py-6 space-y-4">

        {/* -- TOOLBAR -- */}
        <div className="flex flex-col md:flex-row gap-3">

          {/* Search */}
          <div className="relative flex-1">
            <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none" style={{ color: "var(--text-muted)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              value={busca}
              onChange={e => {
                setBusca(e.target.value);
                if (debounceRef.current) clearTimeout(debounceRef.current);
              }}
              placeholder="Buscar por nome, fantasia, CNPJ ou CCM..."
              className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm outline-none transition-all"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
              onFocus={e => { e.currentTarget.style.borderColor = "rgba(79,106,255,0.5)"; e.currentTarget.style.boxShadow = "0 0 0 3px rgba(79,106,255,0.08)"; }}
              onBlur={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.boxShadow = "none"; }}
            />
          </div>

          {/* Filter: responsavel */}
          <div className="relative min-w-[200px]">
            <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none" style={{ color: "var(--text-muted)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            <select
              value={filtroResponsavel}
              onChange={e => setFiltroResponsavel(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm outline-none appearance-none"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
            >
              <option value="">Todos os analistas</option>
              {responsaveis.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>

          {/* Sorting select */}
          <select
            value={ordenacao}
            onChange={e => setOrdenacao(e.target.value as any)}
            className="min-w-[180px] pl-4 pr-4 py-2.5 rounded-xl text-sm outline-none"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
          >
            <option value="nome">Ordenar: Nome</option>
            <option value="score_desc">Score (maior primeiro)</option>
            <option value="score_asc">Score (menor primeiro)</option>
          </select>

          {/* Reload */}
          <button
            onClick={carregar}
            disabled={carregando}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all hover:opacity-80 disabled:opacity-40 flex-shrink-0"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}
          >
            <svg className={`w-4 h-4 ${carregando ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Atualizar
          </button>
        </div>

        {/* -- FILTRO TABS -- */}
        <div className="flex items-center gap-1 p-1 rounded-xl w-fit" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          {FILTROS.map(f => (
            <button
              key={f.key}
              onClick={() => setFiltroCarteira(f.key)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
              style={{
                background: filtroCarteira === f.key ? "rgba(79,106,255,0.18)" : "transparent",
                color: filtroCarteira === f.key ? "#3b6ea5" : "var(--text-muted)",
                border: filtroCarteira === f.key ? "1px solid rgba(79,106,255,0.28)" : "1px solid transparent",
              }}
            >
              {f.label}
              <span
                className="px-1.5 py-0.5 rounded-md text-[10px] font-bold"
                style={{
                  background: filtroCarteira === f.key ? "rgba(79,106,255,0.2)" : "rgba(100,116,139,0.12)",
                  color: filtroCarteira === f.key ? "#3b6ea5" : "var(--text-muted)",
                }}
              >
                {f.count}
              </span>
            </button>
          ))}
        </div>

        {/* -- TABLE / LIST -- */}
        {carregando ? (
          <div className="flex flex-col items-center justify-center py-24 gap-3">
            <div className="w-8 h-8 rounded-full animate-spin"
              style={{ border: "3px solid rgba(79,106,255,0.15)", borderTopColor: "#102a43" }} />
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Carregando empresas...</p>
          </div>
        ) : filtradas.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 rounded-2xl gap-3"
            style={{ border: "1px dashed rgba(79,106,255,0.18)", background: "rgba(79,106,255,0.02)" }}>
            <div className="w-12 h-12 rounded-2xl flex items-center justify-center"
              style={{ background: "rgba(79,106,255,0.08)", border: "1px solid rgba(79,106,255,0.15)" }}>
              <svg className="w-6 h-6" style={{ color: "rgba(79,106,255,0.5)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <p className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>Nenhuma empresa encontrada</p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>Tente ajustar os filtros de busca.</p>
            {(busca || filtroResponsavel || filtroCarteira !== "todas") && (
              <button
                onClick={() => { setBusca(""); setFiltroResponsavel(""); setFiltroCarteira("todas"); }}
                className="text-xs font-semibold px-4 py-1.5 rounded-lg mt-1 transition-all hover:opacity-80"
                style={{ background: "rgba(79,106,255,0.12)", color: "#3b6ea5", border: "1px solid rgba(79,106,255,0.2)" }}
              >
                Limpar filtros
              </button>
            )}
          </div>
        ) : (
          <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)", boxShadow: "0 4px 24px rgba(0,0,0,0.18)" }}>
            {/* Accent line */}
            <div style={{ height: 2, background: "linear-gradient(90deg, #102a43 0%, #3b6ea5 50%, transparent 100%)" }} />

            {/* Table header */}
            <div className="grid items-center gap-4 px-5 py-3 text-[10px] font-bold uppercase tracking-widest"
              style={{
                gridTemplateColumns: "28px 1fr 80px 140px 120px 100px",
                background: "rgba(79,106,255,0.04)",
                borderBottom: "1px solid var(--border)",
                color: "var(--text-muted)",
              }}>
              <span />
              <span>Empresa</span>
              <span className="hidden lg:block">Score</span>
              <span className="hidden md:block">Status</span>
              <span className="hidden sm:block">Responsável</span>
              <span className="text-right">Carteira</span>
            </div>

            {/* Rows */}
            {filtradas.map((e, idx) => {
              const bloqueada    = !e.na_minha_carteira && !!e.em_uso_por;
              const carregandoEsta = toggling === e.id;
              const clicavel     = !bloqueada && !carregandoEsta && !toggling;
              const nomeExibido  = e.nome_fantasia || e.nome;
              const nomeSecundario = e.nome_fantasia ? e.nome : null;

              return (
                <div
                  key={e.id}
                  onClick={() => clicavel && toggle(e)}
                  className={`grid items-center gap-4 px-5 py-3.5 transition-all select-none ${idx !== 0 ? "border-t" : ""}`}
                  style={{
                    gridTemplateColumns: "28px 1fr 80px 140px 120px 100px",
                    borderColor: "var(--border)",
                    cursor: bloqueada ? "not-allowed" : clicavel ? "pointer" : "default",
                    opacity: bloqueada ? 0.55 : 1,
                  }}
                  onMouseEnter={ev => { if (clicavel) (ev.currentTarget as HTMLElement).style.background = "rgba(79,106,255,0.04)"; }}
                  onMouseLeave={ev => { (ev.currentTarget as HTMLElement).style.background = "transparent"; }}
                >
                  {/* Checkbox */}
                  <div
                    className="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 transition-all"
                    style={{
                      border: carregandoEsta
                        ? "2px solid rgba(79,106,255,0.5)"
                        : e.na_minha_carteira
                        ? "2px solid #102a43"
                        : bloqueada
                        ? "2px solid rgba(100,116,139,0.3)"
                        : "2px solid rgba(100,116,139,0.45)",
                      background: carregandoEsta
                        ? "rgba(79,106,255,0.1)"
                        : e.na_minha_carteira
                        ? "linear-gradient(135deg, #102a43, #3b6ea5)"
                        : "transparent",
                    }}
                  >
                    {carregandoEsta ? (
                      <div className="w-2.5 h-2.5 rounded-full animate-spin" style={{ border: "2px solid rgba(79,106,255,0.3)", borderTopColor: "#102a43" }} />
                    ) : e.na_minha_carteira ? (
                      <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : bloqueada ? (
                      <svg className="w-2.5 h-2.5" style={{ color: "var(--text-muted)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                      </svg>
                    ) : null}
                  </div>

                  {/* Company */}
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-700/50 flex items-center justify-center flex-shrink-0">
                      <Building2 className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>{nomeExibido}</p>
                      {nomeSecundario && (
                        <p className="text-[11px] truncate" style={{ color: "var(--text-muted)" }}>{nomeSecundario}</p>
                      )}
                      <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                        {e.cnpj && <span className="text-[10px] font-mono" style={{ color: "var(--text-muted)" }}>{e.cnpj}</span>}
                        {e.ccm  && <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>CCM {e.ccm}</span>}
                        {/* Responsável — mobile only */}
                        {e.em_uso_por && (
                          <span className="sm:hidden flex items-center gap-1">
                            <span
                              className="w-5 h-5 rounded-full text-[9px] font-bold flex items-center justify-center flex-shrink-0"
                              style={{
                                background: "linear-gradient(135deg, rgba(79,106,255,0.22), rgba(123,143,255,0.12))",
                                border: "1px solid rgba(79,106,255,0.30)",
                                color: "#3b6ea5",
                              }}
                            >
                              {(e.em_uso_por || "?").slice(0, 2).toUpperCase()}
                            </span>
                            <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>{e.em_uso_por}</span>
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Score */}
                  <div className="hidden lg:flex items-center gap-1.5">
                    {e.score_saude != null ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold text-white"
                        style={{ background: e.score_cor || "#6b7280" }}>
                        {e.score_saude}
                      </span>
                    ) : (
                      <span className="text-xs" style={{ color: "var(--text-muted)" }}>—</span>
                    )}
                  </div>

                  {/* Status da empresa */}
                  <div className="hidden md:block">
                    {e.status ? <StatusEmpresaBadge status={e.status} /> : <span className="text-xs" style={{ color: "var(--text-muted)" }}>—</span>}
                  </div>

                  {/* Responsável — desktop */}
                  <div className="hidden sm:flex items-center gap-2 min-w-0">
                    {e.em_uso_por ? (
                      <>
                        <span
                          className="w-6 h-6 rounded-full text-[9px] font-bold flex items-center justify-center flex-shrink-0"
                          style={{
                            background: "linear-gradient(135deg, rgba(79,106,255,0.22), rgba(123,143,255,0.12))",
                            border: "1px solid rgba(79,106,255,0.30)",
                            color: "#3b6ea5",
                          }}
                        >
                          {(e.em_uso_por || "?").slice(0, 2).toUpperCase()}
                        </span>
                        <span className="text-xs font-medium truncate" style={{ color: "var(--text-secondary)" }}>{e.em_uso_por}</span>
                      </>
                    ) : (
                      <span className="text-xs" style={{ color: "var(--text-muted)" }}>—</span>
                    )}
                  </div>

                  {/* Carteira status */}
                  <div className="flex justify-end flex-shrink-0">
                    {e.na_minha_carteira ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold"
                        style={{ background: "rgba(79,106,255,0.14)", border: "1px solid rgba(79,106,255,0.28)", color: "#3b6ea5" }}>
                        <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#102a43", boxShadow: "0 0 6px #102a43" }} />
                        Minha
                      </span>
                    ) : bloqueada ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold"
                        style={{ background: "rgba(100,116,139,0.08)", border: "1px solid rgba(100,116,139,0.18)", color: "var(--text-muted)" }}>
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                        </svg>
                        Ocupada
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold"
                        style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.20)", color: "#34d399" }}>
                        <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#34d399", boxShadow: "0 0 5px #34d399" }} />
                        Livre
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Status summary footer */}
        {!carregando && filtradas.length > 0 && (() => {
          const statusCounts: Record<string, number> = {};
          filtradas.forEach(e => {
            const s = e.status || "sem_status";
            statusCounts[s] = (statusCounts[s] || 0) + 1;
          });
          const entries = Object.entries(statusCounts).sort((a, b) => b[1] - a[1]);
          return (
            <div className="flex items-center gap-3 flex-wrap px-5 py-3 rounded-xl"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <span className="text-[10px] font-bold uppercase tracking-widest mr-1" style={{ color: "var(--text-muted)" }}>Status:</span>
              {entries.map(([status, count]) => {
                const style = STATUS_COLOR[status] ?? { bg: "rgba(100,116,139,0.10)", color: "var(--text-muted)" };
                const label = STATUS_LABEL[status] ?? (status === "sem_status" ? "Sem status" : status);
                return (
                  <span key={status} className="inline-flex items-center gap-1.5 text-[11px] font-semibold">
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: style.color }} />
                    <span style={{ color: style.color }}>{count}</span>
                    <span style={{ color: "var(--text-muted)" }}>{label}</span>
                  </span>
                );
              })}
            </div>
          );
        })()}

        {/* Footer count */}
        {!carregando && filtradas.length > 0 && (
          <p className="text-xs text-center pb-4" style={{ color: "var(--text-muted)" }}>
            {filtradas.length} empresa{filtradas.length !== 1 ? "s" : ""} · Clique para adicionar ou remover da sua carteira
          </p>
        )}
      </div>
    </div>
  );
}
