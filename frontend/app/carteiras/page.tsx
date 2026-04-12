"use client";
import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { Building2 } from "lucide-react";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

// Paleta semântica — funciona em light e dark
const STATUS_MAP: Record<string, { label: string; color: string; bg: string; border: string; dot: string; accent: string }> = {
  iniciada:              { label: "Iniciada",              color: "text-slate-600 dark:text-slate-400",   bg: "bg-slate-100 dark:bg-slate-700/40",   border: "border-slate-200 dark:border-slate-600/30",   dot: "#829ab1", accent: "#829ab1" },
  em_andamento:          { label: "Em andamento",          color: "text-amber-800 dark:text-amber-300",   bg: "bg-amber-50 dark:bg-amber-500/10",    border: "border-amber-200 dark:border-amber-500/20",   dot: "#d97706", accent: "#d97706" },
  extratos_pendentes:    { label: "Extratos pendentes",    color: "text-rose-800 dark:text-rose-300",     bg: "bg-rose-50 dark:bg-rose-500/10",      border: "border-rose-200 dark:border-rose-500/20",     dot: "#dc2626", accent: "#dc2626" },
  pendencia_fiscal:      { label: "Pendência fiscal",      color: "text-rose-800 dark:text-rose-300",     bg: "bg-rose-50 dark:bg-rose-500/10",      border: "border-rose-200 dark:border-rose-500/20",     dot: "#dc2626", accent: "#dc2626" },
  pendencia_juridica:    { label: "Pendência jurídica",    color: "text-violet-800 dark:text-violet-300", bg: "bg-violet-50 dark:bg-violet-500/10",  border: "border-violet-200 dark:border-violet-500/20", dot: "#7c3aed", accent: "#7c3aed" },
  finalizada:            { label: "Finalizada",            color: "text-emerald-800 dark:text-emerald-300",bg: "bg-emerald-50 dark:bg-emerald-500/10",border: "border-emerald-200 dark:border-emerald-500/20",dot: "#065f46", accent: "#065f46" },
  aguardando_documentos: { label: "Ag. documentos",        color: "text-teal-800 dark:text-teal-300",     bg: "bg-teal-50 dark:bg-teal-500/10",      border: "border-teal-200 dark:border-teal-500/20",     dot: "#0f766e", accent: "#0f766e" },
  documentacao_pendente: { label: "Doc. pendente",         color: "text-orange-800 dark:text-orange-300", bg: "bg-orange-50 dark:bg-orange-500/10",  border: "border-orange-200 dark:border-orange-500/20", dot: "#c2410c", accent: "#c2410c" },
  em_revisao:            { label: "Em revisão",            color: "text-blue-800 dark:text-blue-300",     bg: "bg-blue-50 dark:bg-blue-500/10",      border: "border-blue-200 dark:border-blue-500/20",     dot: "#1d4ed8", accent: "#1d4ed8" },
  entregue:              { label: "Entregue",              color: "text-sky-800 dark:text-sky-300",       bg: "bg-sky-50 dark:bg-sky-500/10",        border: "border-sky-200 dark:border-sky-500/20",       dot: "#0369a1", accent: "#0369a1" },
  suspenso:              { label: "Suspenso",              color: "text-gray-700 dark:text-gray-400",     bg: "bg-gray-50 dark:bg-gray-700/20",      border: "border-gray-200 dark:border-gray-600/30",     dot: "#6b7280", accent: "#6b7280" },
  concluida:             { label: "Concluída",             color: "text-emerald-800 dark:text-emerald-300",bg: "bg-emerald-50 dark:bg-emerald-500/10",border: "border-emerald-200 dark:border-emerald-500/20",dot: "#065f46", accent: "#065f46" },
  defis_entregue:        { label: "DEFIS entregue",        color: "text-emerald-800 dark:text-emerald-300",bg: "bg-emerald-50 dark:bg-emerald-600/10",border: "border-emerald-200 dark:border-emerald-600/20",dot: "#065f46", accent: "#065f46" },
  erro_integracao_fiscal:{ label: "Erro fiscal",           color: "text-rose-800 dark:text-rose-300",     bg: "bg-rose-50 dark:bg-rose-500/10",      border: "border-rose-200 dark:border-rose-500/20",     dot: "#dc2626", accent: "#dc2626" },
  erro_integracao_folha: { label: "Erro folha",            color: "text-rose-800 dark:text-rose-300",     bg: "bg-rose-50 dark:bg-rose-500/10",      border: "border-rose-200 dark:border-rose-500/20",     dot: "#dc2626", accent: "#dc2626" },
};
const STATUS_KEYS = Object.keys(STATUS_MAP);

interface MinhaEmpresa {
  id: number;
  nome: string;
  nome_fantasia: string;
  cnpj: string;
  ccm: string;
  status: string;
  na_minha_carteira: boolean;
  carteira_observacoes: string;
  em_uso_por_id: number | null;
  em_uso_por: string | null;
  score_saude: number | null;
  score_classificacao: string | null;
  score_cor: string | null;
}

function StatusSelector({ status, onChange }: { status: string; onChange: (s: string) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const cfg = STATUS_MAP[status] ?? STATUS_MAP.iniciada;
  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all hover:opacity-90 ${cfg.bg} ${cfg.border} ${cfg.color}`}
        style={{ boxShadow: `0 0 0 1px ${cfg.accent}15` }}
      >
        <span className="w-1.5 h-1.5 rounded-full" style={{ background: cfg.dot }} />
        {cfg.label}
        <svg className="w-3 h-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-2 z-50 rounded-2xl shadow-2xl overflow-hidden min-w-[210px]"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)", boxShadow: "0 20px 50px rgba(0,0,0,0.15), 0 0 0 1px rgba(16,42,67,0.08)" }}>
          <div className="p-1.5">
            {STATUS_KEYS.map(s => {
              const c = STATUS_MAP[s];
              return (
                <button key={s} onClick={() => { onChange(s); setOpen(false); }}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 text-xs font-semibold text-left rounded-xl transition-all ${s === status ? "bg-[#102a43]/10" : "hover:bg-slate-800/40"}`}>
                  <span className="w-2 h-2 rounded-full" style={{ background: c.dot }} />
                  <span className={c.color}>{c.label}</span>
                  {s === status && (
                    <svg className="w-3.5 h-3.5 ml-auto" style={{ color: "#102a43" }} fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function tk() { return localStorage.getItem("controllo_token") ?? ""; }

function scoreBorderColor(score: number | null): string {
  if (score === null || score === undefined) return "border-l-slate-300 dark:border-l-slate-600";
  if (score >= 80) return "border-l-emerald-500";
  if (score >= 60) return "border-l-green-500";
  if (score >= 40) return "border-l-amber-500";
  if (score >= 20) return "border-l-orange-500";
  return "border-l-rose-500";
}

export default function CarteirasPage() {
  const [empresas, setEmpresas]       = useState<MinhaEmpresa[]>([]);
  const [carregando, setCarregando]   = useState(true);
  const [toast, setToast]             = useState<{ msg: string; tipo: "ok" | "erro" } | null>(null);
  const [removendo, setRemovendo]     = useState<number | null>(null);
  const [editandoObs, setEditandoObs] = useState<number | null>(null);
  const [obsTexto, setObsTexto]       = useState("");
  const [salvandoObs, setSalvandoObs] = useState(false);
  const [busca, setBusca]             = useState("");
  const [ordenacao, setOrdenacao]     = useState<"nome" | "score_asc" | "score_desc">("nome");

  const mostrarToast = (msg: string, tipo: "ok" | "erro") => {
    setToast({ msg, tipo });
    setTimeout(() => setToast(null), 3500);
  };

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const res = await fetch(`${API}/api/carteira/disponiveis`, { headers: { Authorization: `Bearer ${tk()}` } });
      if (!res.ok) throw new Error();
      const data: MinhaEmpresa[] = await res.json();
      setEmpresas(data.filter(e => e.na_minha_carteira));
    } catch { mostrarToast("Erro ao carregar carteira", "erro"); }
    finally { setCarregando(false); }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  async function remover(empresa: MinhaEmpresa) {
    if (!confirm(`Remover "${empresa.nome}" da sua carteira?`)) return;
    setRemovendo(empresa.id);
    try {
      const res = await fetch(`${API}/api/carteira/${empresa.id}`, {
        method: "DELETE", headers: { Authorization: `Bearer ${tk()}` },
      });
      if (!res.ok) throw new Error(((await res.json().catch(() => ({}))).detail) || "Erro");
      setEmpresas(prev => prev.filter(e => e.id !== empresa.id));
      mostrarToast(`"${empresa.nome}" removida.`, "ok");
    } catch (e: unknown) {
      mostrarToast(e instanceof Error ? e.message : "Erro ao remover", "erro");
    } finally { setRemovendo(null); }
  }

  async function alterarStatus(id: number, novoStatus: string) {
    try {
      const res = await fetch(`${API}/api/carteira/${id}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${tk()}` },
        body: JSON.stringify({ status: novoStatus }),
      });
      if (!res.ok) throw new Error();
      setEmpresas(prev => prev.map(e => e.id === id ? { ...e, status: novoStatus } : e));
      mostrarToast("Status atualizado.", "ok");
    } catch { mostrarToast("Erro ao atualizar status", "erro"); }
  }

  async function salvarObs(id: number) {
    setSalvandoObs(true);
    try {
      const res = await fetch(`${API}/api/carteira/${id}/notas`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${tk()}` },
        body: JSON.stringify({ observacoes: obsTexto }),
      });
      if (!res.ok) throw new Error();
      setEmpresas(prev => prev.map(e => e.id === id ? { ...e, carteira_observacoes: obsTexto } : e));
      setEditandoObs(null);
      mostrarToast("Observação salva.", "ok");
    } catch { mostrarToast("Erro ao salvar", "erro"); }
    finally { setSalvandoObs(false); }
  }

  const contadores = STATUS_KEYS.reduce((acc, s) => {
    acc[s] = empresas.filter(e => (e.status || "iniciada") === s).length;
    return acc;
  }, {} as Record<string, number>);

  const empresasComScore = empresas.filter(e => e.score_saude !== null && e.score_saude !== undefined);
  const empresasCriticas = empresas.filter(e => e.score_saude !== null && e.score_saude !== undefined && e.score_saude < 40);

  const empresasFiltradas = useMemo(() => {
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
    if (ordenacao === "score_desc") {
      list = [...list].sort((a, b) => (b.score_saude ?? -1) - (a.score_saude ?? -1));
    } else if (ordenacao === "score_asc") {
      list = [...list].sort((a, b) => (a.score_saude ?? 999) - (b.score_saude ?? 999));
    } else {
      list = [...list].sort((a, b) => a.nome.localeCompare(b.nome));
    }
    return list;
  }, [empresas, busca, ordenacao]);

  return (
    <div className="min-h-full" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>

      {/* ── TOAST ── */}
      {toast && (
        <div className={`fixed top-6 right-6 z-50 flex items-center gap-3 px-5 py-3.5 rounded-2xl border text-sm font-semibold shadow-2xl backdrop-blur-sm transition-all ${
          toast.tipo === "ok"
            ? "bg-emerald-600/15 border-emerald-500/25 text-emerald-300"
            : "bg-red-600/15 border-red-500/25 text-red-300"
        }`}>
          {toast.tipo === "ok"
            ? <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
            : <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" /></svg>
          }
          {toast.msg}
        </div>
      )}

      {/* ── HEADER ── */}
      <header className="relative px-8 pt-8 pb-6 overflow-hidden"
        style={{ borderBottom: "1px solid var(--border)" }}>
        {/* Subtle gradient accent */}
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: "linear-gradient(to right, rgba(16,42,67,0.04), transparent 60%)" }} />
        <div className="relative flex items-start justify-between gap-6 flex-wrap">
          {/* Title block */}
          <div>
            <h1 className="text-[22px] font-bold tracking-tight text-[#102a43] dark:text-slate-100 leading-none">
              Minha Carteira
            </h1>
            <p className="text-sm mt-2" style={{ color: "var(--text-secondary)" }}>
              Acompanhe suas empresas, status e observações privadas
            </p>

            {/* Metric pills row */}
            <div className="flex items-center gap-2 mt-4 flex-wrap">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold"
                style={{ background: "rgba(16,42,67,0.07)", border: "1px solid rgba(16,42,67,0.15)", color: "#102a43" }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#102a43" }} />
                {empresas.length} empresa{empresas.length !== 1 ? "s" : ""}
              </span>
              {empresasComScore.length > 0 && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border bg-blue-50 dark:bg-blue-500/10 border-blue-200 dark:border-blue-500/20 text-blue-800 dark:text-blue-300">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#1d4ed8" }} />
                  {empresasComScore.length} com score
                </span>
              )}
              {empresasCriticas.length > 0 && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/20 text-rose-800 dark:text-rose-300">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#dc2626" }} />
                  {empresasCriticas.length} {empresasCriticas.length === 1 ? "crítica" : "críticas"}
                </span>
              )}
              {STATUS_KEYS.filter(s => contadores[s] > 0).map(s => {
                const c = STATUS_MAP[s];
                return (
                  <span key={s} className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${c.bg} ${c.border} ${c.color}`}>
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: c.dot }} />
                    {contadores[s]} {c.label.toLowerCase()}
                  </span>
                );
              })}
            </div>
          </div>

          {/* Right CTA */}
          <a href="/admin/carteiras"
            className="flex items-center gap-2 text-sm font-semibold transition-all hover:opacity-80 self-start mt-1"
            style={{ color: "#486581" }}>
            Ver Carteira Geral
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </a>
        </div>
      </header>

      {/* ── CORPO ── */}
      <div className="px-8 py-7">
        {carregando ? (
          <div className="space-y-3 page-enter">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="rounded-3xl overflow-hidden"
                style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                <div className="h-px w-full skeleton" />
                <div className="p-5 pt-4 space-y-3">
                  <div className="flex items-center gap-4">
                    <div className="skeleton w-11 h-11 rounded-2xl flex-shrink-0" />
                    <div className="flex-1 space-y-2">
                      <div className="skeleton h-4 w-48 rounded" />
                      <div className="skeleton h-3 w-32 rounded" />
                    </div>
                    <div className="skeleton h-7 w-28 rounded-full flex-shrink-0" />
                  </div>
                  <div className="skeleton h-px w-full rounded mt-3" />
                  <div className="skeleton h-3 w-64 rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : empresas.length === 0 ? (
          /* ── Empty state ── */
          <div className="flex flex-col items-center justify-center py-28 rounded-3xl border border-dashed"
            style={{ borderColor: "var(--border)", background: "linear-gradient(135deg, rgba(79,106,255,0.02), transparent)" }}>
            <div className="relative mb-6">
              <div className="w-24 h-24 rounded-3xl flex items-center justify-center bg-navy-50 border border-navy-200 dark:bg-navy-900/30 dark:border-navy-700/40">
                <svg className="w-12 h-12" style={{ color: "#102a43", opacity: 0.7 }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.3} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              {/* Decorative glow */}
              <div className="absolute inset-0 rounded-3xl pointer-events-none"
                style={{ boxShadow: "0 0 40px rgba(79,106,255,0.12)" }} />
            </div>
            <p className="text-base font-bold mb-2" style={{ color: "var(--text-primary)" }}>Sua carteira está vazia</p>
            <p className="text-sm mb-6 text-center max-w-xs" style={{ color: "var(--text-muted)" }}>
              Acesse a Carteira Geral para vincular empresas à sua conta
            </p>
            <a href="/admin/carteiras"
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold text-white transition-all hover:brightness-110 active:scale-95 bg-navy-600 hover:bg-navy-700">
              Ir para Carteira Geral
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
            </a>
          </div>
        ) : (
          <>
            {/* ── Search bar ── */}
            <div className="flex items-center gap-3 mb-5">
              <div className="relative flex-1 max-w-md">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: "var(--text-muted)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  value={busca}
                  onChange={e => setBusca(e.target.value)}
                  placeholder="Buscar empresa por nome, CNPJ ou CCM..."
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm outline-none transition-all"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                />
              </div>
              <select
                value={ordenacao}
                onChange={e => setOrdenacao(e.target.value as "nome" | "score_asc" | "score_desc")}
                className="px-3 py-2.5 rounded-xl text-sm outline-none"
                style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
              >
                <option value="nome">Ordenar: Nome</option>
                <option value="score_desc">Score (maior)</option>
                <option value="score_asc">Score (menor)</option>
              </select>
            </div>

            {/* ── Empty search results ── */}
            {empresasFiltradas.length === 0 && busca.trim() ? (
              <div className="flex flex-col items-center justify-center py-20 rounded-2xl border border-dashed"
                style={{ borderColor: "var(--border)" }}>
                <svg className="w-10 h-10 mb-4" style={{ color: "var(--text-muted)", opacity: 0.5 }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <p className="text-sm font-semibold mb-1" style={{ color: "var(--text-primary)" }}>
                  Nenhuma empresa encontrada para &quot;{busca}&quot;
                </p>
                <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
                  Tente buscar por outro nome, CNPJ ou CCM
                </p>
                <button
                  onClick={() => setBusca("")}
                  className="px-4 py-2 rounded-xl text-xs font-bold transition-all hover:brightness-110"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                >
                  Limpar busca
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {empresasFiltradas.map(empresa => {
                  const cfg = STATUS_MAP[empresa.status || "iniciada"] ?? STATUS_MAP.iniciada;
                  return (
                    <div
                      key={empresa.id}
                      className={`group bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600/50 transition-colors duration-150 border-l-[3px] ${scoreBorderColor(empresa.score_saude)}`}
                    >

                      <div className="p-5 pt-4">
                        {/* Row 1: avatar | info | status + remove */}
                        <div className="flex items-center gap-4">
                          {/* Avatar */}
                          <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-700/50 flex items-center justify-center flex-shrink-0">
                            <Building2 className="w-5 h-5 text-slate-500 dark:text-slate-400" />
                          </div>

                          {/* Info */}
                          <div className="flex-1 min-w-0">
                            <p className="text-lg font-bold leading-snug truncate" style={{ color: "var(--text-primary)" }}>
                              {empresa.nome}
                            </p>
                            {empresa.nome_fantasia && empresa.nome_fantasia !== empresa.nome && (
                              <p className="text-xs truncate mt-0.5" style={{ color: "var(--text-secondary)" }}>
                                {empresa.nome_fantasia}
                              </p>
                            )}
                            <div className="flex items-center gap-2 mt-1 flex-wrap">
                              {empresa.cnpj && (
                                <span className="text-[11px] font-mono px-2 py-0.5 rounded-md"
                                  style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
                                  {empresa.cnpj}
                                </span>
                              )}
                              {empresa.ccm && (
                                <span className="text-[11px] font-mono px-2 py-0.5 rounded-md"
                                  style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
                                  CCM {empresa.ccm}
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <StatusSelector status={empresa.status || "iniciada"} onChange={s => alterarStatus(empresa.id, s)} />
                            <button
                              onClick={() => remover(empresa)}
                              disabled={removendo === empresa.id}
                              className="p-2 rounded-xl transition-all text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 disabled:opacity-40"
                            >
                              {removendo === empresa.id
                                ? <div className="w-4 h-4 border-2 border-rose-400/30 border-t-rose-400 rounded-full animate-spin" />
                                : <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                              }
                            </button>
                          </div>
                        </div>

                        {/* Row 2: Score de saúde */}
                        {empresa.score_saude !== null && empresa.score_saude !== undefined && (
                          <div className="mt-3 flex items-center gap-3">
                            <div className="flex items-center gap-2">
                              <div
                                className="w-9 h-9 rounded-xl flex items-center justify-center text-xs font-black text-white"
                                style={{ background: empresa.score_cor || "#6b7280" }}
                              >
                                {empresa.score_saude}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <div className="flex-1 h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden" style={{ maxWidth: "120px" }}>
                                    <div
                                      className="h-full rounded-full transition-all duration-500"
                                      style={{
                                        width: `${empresa.score_saude}%`,
                                        background: empresa.score_cor || "#6b7280",
                                      }}
                                    />
                                  </div>
                                  <span
                                    className="text-[11px] font-bold"
                                    style={{ color: empresa.score_cor || "#6b7280" }}
                                  >
                                    {empresa.score_classificacao}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Row 3: em_uso_por pill */}
                        {empresa.em_uso_por && (
                          <div className="mt-3">
                            <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full"
                              style={{ background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.2)", color: "#f59e0b" }}>
                              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                              </svg>
                              Em uso por: {empresa.em_uso_por}
                            </span>
                          </div>
                        )}

                        {/* Divider */}
                        <div className="mt-4 mb-3.5" style={{ height: "1px", background: "var(--border)" }} />

                        {/* Observation section */}
                        {editandoObs === empresa.id ? (
                          <div className="space-y-2.5">
                            <textarea
                              value={obsTexto}
                              onChange={e => setObsTexto(e.target.value)}
                              rows={3}
                              placeholder="Observações privadas sobre este cliente..."
                              autoFocus
                              className="w-full rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#102a43]/40 resize-none transition-all"
                              style={{
                                background: "var(--bg-secondary)",
                                border: "1px solid var(--border)",
                                color: "var(--text-primary)",
                              }}
                            />
                            <div className="flex gap-2">
                              <button onClick={() => salvarObs(empresa.id)} disabled={salvandoObs}
                                className="px-4 py-1.5 rounded-lg text-xs font-bold text-white disabled:opacity-50 transition-all hover:brightness-110"
                                style={{ background: "linear-gradient(135deg, #102a43, #1e3a5f)" }}>
                                {salvandoObs ? "Salvando..." : "Salvar"}
                              </button>
                              <button onClick={() => setEditandoObs(null)}
                                className="px-4 py-1.5 rounded-lg text-xs font-semibold transition-all hover:bg-white/5"
                                style={{ background: "var(--bg-secondary)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
                                Cancelar
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => { setEditandoObs(empresa.id); setObsTexto(empresa.carteira_observacoes ?? ""); }}
                            className="w-full text-left group/obs rounded-lg p-1 -m-1 transition-all hover:bg-white/2"
                          >
                            {empresa.carteira_observacoes ? (
                              <p className="text-xs leading-relaxed transition-opacity group-hover/obs:opacity-70"
                                style={{ color: "var(--text-secondary)" }}>
                                {empresa.carteira_observacoes}
                              </p>
                            ) : (
                              <p className="text-xs flex items-center gap-1.5 opacity-40 group-hover/obs:opacity-70 transition-opacity"
                                style={{ color: "var(--text-muted)" }}>
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                                Adicionar observação privada...
                              </p>
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}

        {!carregando && empresas.length > 0 && (
          <p className="text-xs text-center mt-10" style={{ color: "var(--text-muted)" }}>
            {empresas.length} empresa{empresas.length !== 1 ? "s" : ""} na sua carteira
            <span className="mx-2 opacity-30">·</span>
            <a href="/admin/carteiras" className="transition-colors hover:opacity-80" style={{ color: "#486581" }}>
              Carteira Geral
            </a>
            {" "}para adicionar ou transferir
          </p>
        )}
      </div>
    </div>
  );
}
