"use client";
import { useEffect, useState, useCallback, useMemo } from "react";
import { Avatar, Input, Select, EmptyState } from "@/components/ui";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_BASE = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

interface LogEntry {
  id: number;
  usuario_id: number | null;
  usuario_nome: string;
  acao: string;
  recurso: string;
  recurso_id: number | null;
  detalhes: Record<string, unknown>;
  ip: string;
  criado_em: string;
}

interface Paginacao {
  items: LogEntry[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// ─── Ação config — label + cores semantic light/dark + ícone SVG ──────────────
const ACAO_CONFIG: Record<string, {
  label: string;
  bg: string; border: string; text: string;
  icon: React.ReactNode;
}> = {
  login: {
    label: "Login",
    bg: "bg-blue-50 dark:bg-blue-500/10",
    border: "border-blue-200 dark:border-blue-500/25",
    text: "text-blue-700 dark:text-blue-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" /></svg>,
  },
  criar_empresa: {
    label: "Criar Empresa",
    bg: "bg-emerald-50 dark:bg-emerald-500/10",
    border: "border-emerald-200 dark:border-emerald-500/25",
    text: "text-emerald-700 dark:text-emerald-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  },
  atualizar_empresa: {
    label: "Atualizar Empresa",
    bg: "bg-amber-50 dark:bg-amber-500/10",
    border: "border-amber-200 dark:border-amber-500/25",
    text: "text-amber-700 dark:text-amber-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536M9 11l6.5-6.5a2.121 2.121 0 113 3L12 14H9v-3z" /></svg>,
  },
  inativar_empresa: {
    label: "Inativar Empresa",
    bg: "bg-red-50 dark:bg-red-500/10",
    border: "border-red-200 dark:border-red-500/25",
    text: "text-red-700 dark:text-red-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" /></svg>,
  },
  aprovar_usuario: {
    label: "Aprovar Usuário",
    bg: "bg-emerald-50 dark:bg-emerald-500/10",
    border: "border-emerald-200 dark:border-emerald-500/25",
    text: "text-emerald-700 dark:text-emerald-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>,
  },
  bloquear_usuario: {
    label: "Bloquear Usuário",
    bg: "bg-red-50 dark:bg-red-500/10",
    border: "border-red-200 dark:border-red-500/25",
    text: "text-red-700 dark:text-red-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" /></svg>,
  },
  promover_admin: {
    label: "Promover Admin",
    bg: "bg-emerald-50 dark:bg-emerald-500/10",
    border: "border-emerald-200 dark:border-emerald-500/25",
    text: "text-emerald-700 dark:text-emerald-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>,
  },
  revogar_admin: {
    label: "Revogar Admin",
    bg: "bg-orange-50 dark:bg-orange-500/10",
    border: "border-orange-200 dark:border-orange-500/25",
    text: "text-orange-700 dark:text-orange-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M20.618 5.984A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016zM12 9v4m0 4h.01" /></svg>,
  },
  excluir_usuario: {
    label: "Excluir Usuário",
    bg: "bg-red-100 dark:bg-red-500/15",
    border: "border-red-300 dark:border-red-500/30",
    text: "text-red-800 dark:text-red-300",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>,
  },
  promover_ceo: {
    label: "Promover CEO",
    bg: "bg-amber-50 dark:bg-amber-500/10",
    border: "border-amber-200 dark:border-amber-500/25",
    text: "text-amber-700 dark:text-amber-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 3l14 9-14 9V3z" /></svg>,
  },
  revogar_ceo: {
    label: "Revogar CEO",
    bg: "bg-slate-100 dark:bg-slate-500/10",
    border: "border-slate-200 dark:border-slate-500/25",
    text: "text-slate-700 dark:text-slate-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>,
  },
  promover_gestor: {
    label: "Promover Gestor",
    bg: "bg-emerald-50 dark:bg-emerald-500/10",
    border: "border-emerald-200 dark:border-emerald-500/25",
    text: "text-emerald-700 dark:text-emerald-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>,
  },
  revogar_gestor: {
    label: "Revogar Gestor",
    bg: "bg-orange-50 dark:bg-orange-500/10",
    border: "border-orange-200 dark:border-orange-500/25",
    text: "text-orange-700 dark:text-orange-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M20.618 5.984A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016zM12 9v4m0 4h.01" /></svg>,
  },
  criar_tarefa: {
    label: "Criar Tarefa",
    bg: "bg-emerald-50 dark:bg-emerald-500/10",
    border: "border-emerald-200 dark:border-emerald-500/25",
    text: "text-emerald-700 dark:text-emerald-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>,
  },
  concluir_tarefa: {
    label: "Concluir Tarefa",
    bg: "bg-emerald-50 dark:bg-emerald-500/10",
    border: "border-emerald-200 dark:border-emerald-500/25",
    text: "text-emerald-700 dark:text-emerald-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>,
  },
  importar_dados: {
    label: "Importar Dados",
    bg: "bg-amber-50 dark:bg-amber-500/10",
    border: "border-amber-200 dark:border-amber-500/25",
    text: "text-amber-700 dark:text-amber-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>,
  },
  exportar_dados: {
    label: "Exportar Dados",
    bg: "bg-purple-50 dark:bg-purple-500/10",
    border: "border-purple-200 dark:border-purple-500/25",
    text: "text-purple-700 dark:text-purple-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>,
  },
  exportar: {
    label: "Exportar",
    bg: "bg-purple-50 dark:bg-purple-500/10",
    border: "border-purple-200 dark:border-purple-500/25",
    text: "text-purple-700 dark:text-purple-400",
    icon: <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>,
  },
};

// Infer color category for unknown actions based on keyword patterns
function inferAcaoStyle(acao: string): { bg: string; border: string; text: string } {
  const a = acao.toLowerCase();
  if (a.includes("login") || a.includes("logout") || a.includes("auth"))
    return { bg: "bg-blue-50 dark:bg-blue-500/10", border: "border-blue-200 dark:border-blue-500/25", text: "text-blue-700 dark:text-blue-400" };
  if (a.includes("criar") || a.includes("cadastr") || a.includes("aprovar") || a.includes("promov"))
    return { bg: "bg-emerald-50 dark:bg-emerald-500/10", border: "border-emerald-200 dark:border-emerald-500/25", text: "text-emerald-700 dark:text-emerald-400" };
  if (a.includes("editar") || a.includes("atualiz") || a.includes("importar"))
    return { bg: "bg-amber-50 dark:bg-amber-500/10", border: "border-amber-200 dark:border-amber-500/25", text: "text-amber-700 dark:text-amber-400" };
  if (a.includes("exclu") || a.includes("remov") || a.includes("inativ") || a.includes("bloque"))
    return { bg: "bg-red-50 dark:bg-red-500/10", border: "border-red-200 dark:border-red-500/25", text: "text-red-700 dark:text-red-400" };
  if (a.includes("export"))
    return { bg: "bg-purple-50 dark:bg-purple-500/10", border: "border-purple-200 dark:border-purple-500/25", text: "text-purple-700 dark:text-purple-400" };
  return { bg: "bg-slate-100 dark:bg-slate-700/40", border: "border-slate-200 dark:border-slate-600/30", text: "text-slate-600 dark:text-slate-400" };
}

function AcaoBadge({ acao }: { acao: string }) {
  const cfg = ACAO_CONFIG[acao];
  if (!cfg) {
    const inferred = inferAcaoStyle(acao);
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border ${inferred.bg} ${inferred.border} ${inferred.text}`}>
        {acao}
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border ${cfg.bg} ${cfg.border} ${cfg.text}`}>
      {cfg.icon}
      {cfg.label}
    </span>
  );
}

function formatarData(iso: string) {
  try {
    return new Date(iso).toLocaleString("pt-BR", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  } catch { return iso; }
}

function IpCell({ ip }: { ip: string }) {
  if (!ip) return (
    <span className="flex items-center gap-1 text-xs text-slate-400 dark:text-slate-500">
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      Desconhecido
    </span>
  );
  if (ip === "127.0.0.1" || ip === "::1") return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 dark:bg-slate-700/40 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-600/30">
      Local
    </span>
  );
  return <span className="text-xs font-mono text-slate-500 dark:text-slate-400 whitespace-nowrap">{ip}</span>;
}

function DetalhesPill({ detalhes }: { detalhes: Record<string, unknown> }) {
  const entries = Object.entries(detalhes);
  if (entries.length === 0) return <span className="text-slate-400 dark:text-slate-500 text-xs">—</span>;
  return (
    <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
      {entries.map(([k, v]) => `${k}: ${v}`).join("  ·  ")}
    </span>
  );
}

export default function AuditoriaPage() {
  const [dados, setDados] = useState<Paginacao | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [filtroAcao, setFiltroAcao] = useState("");
  const [filtroUsuario, setFiltroUsuario] = useState("");
  const [filtroDataInicio, setFiltroDataInicio] = useState("");
  const [filtroDataFim, setFiltroDataFim] = useState("");
  const [page, setPage] = useState(1);
  const [acoesDisponiveis, setAcoesDisponiveis] = useState<string[]>([]);

  const carregar = useCallback(async (pg = page) => {
    const token = localStorage.getItem("controllo_token");
    if (!token) return;
    setCarregando(true);
    setErro("");
    try {
      const params = new URLSearchParams({ page: String(pg), per_page: "50" });
      if (filtroAcao) params.set("acao", filtroAcao);
      if (filtroUsuario) params.set("usuario", filtroUsuario);
      if (filtroDataInicio) params.set("data_inicio", filtroDataInicio);
      if (filtroDataFim) params.set("data_fim", filtroDataFim);
      const res = await fetch(`${API_BASE}/api/auditoria?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) { setErro("Acesso restrito a administradores."); return; }
      if (!res.ok) throw new Error();
      setDados(await res.json());
    } catch { setErro("Erro ao carregar o log de auditoria."); }
    finally { setCarregando(false); }
  }, [filtroAcao, filtroUsuario, filtroDataInicio, filtroDataFim, page]);

  useEffect(() => {
    const token = localStorage.getItem("controllo_token");
    if (!token) return;
    fetch(`${API_BASE}/api/auditoria/acoes`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : [])
      .then(setAcoesDisponiveis)
      .catch(() => {});
  }, []);

  useEffect(() => { setPage(1); }, [filtroAcao, filtroUsuario, filtroDataInicio, filtroDataFim]);
  useEffect(() => { carregar(page); }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  const limparFiltros = () => {
    setFiltroAcao(""); setFiltroUsuario("");
    setFiltroDataInicio(""); setFiltroDataFim(""); setPage(1);
  };

  const temFiltro = filtroAcao || filtroUsuario || filtroDataInicio || filtroDataFim;

  // ─── Métricas derivadas dos itens carregados ───────────────────────────────
  const metricas = useMemo(() => {
    if (!dados) return null;
    const items = dados.items;
    const hoje = new Date().toDateString();
    const acoesHoje = items.filter(i => new Date(i.criado_em).toDateString() === hoje).length;
    const usuariosDistintos = new Set(items.map(i => i.usuario_nome).filter(Boolean)).size;
    const freq: Record<string, number> = {};
    items.forEach(i => { freq[i.acao] = (freq[i.acao] ?? 0) + 1; });
    const acaoFrequente = Object.entries(freq).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—";
    return { acoesHoje, usuariosDistintos, acaoFrequente };
  }, [dados]);

  return (
    <div className="min-h-full" style={{ background: "var(--bg-canvas)", color: "var(--text-primary)" }}>

      {/* ── Header ── */}
      <div className="px-6 pt-6 pb-5 bg-white dark:bg-slate-900 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 bg-gradient-to-br from-[#102a43] to-[#1e3a5f] dark:from-slate-700 dark:to-slate-600">
              <svg className="w-5 h-5 text-[#9fb3c8]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-[#829ab1] dark:text-slate-500 mb-0.5">Administração</p>
              <h1 className="text-2xl font-bold text-[#102a43] dark:text-slate-100 leading-tight">Log de Auditoria</h1>
              <p className="text-sm text-[#627d98] dark:text-slate-400 mt-0.5">Registro completo de todas as ações realizadas</p>
            </div>
          </div>
          {dados && (
            <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#f0f4f8] dark:bg-navy-900/30 border border-[#e2e8f0] dark:border-navy-800/60">
              <svg className="w-4 h-4 text-[#486581] dark:text-navy-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <span className="text-xl font-black text-[#102a43] dark:text-navy-200">{dados.total.toLocaleString("pt-BR")}</span>
              <span className="text-xs font-semibold text-[#627d98] dark:text-slate-400">
                registro{dados.total !== 1 ? "s" : ""}{temFiltro ? " (filtrado)" : ""}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="px-6 py-5 space-y-4">

        {erro ? (
          <div className="px-5 py-4 rounded-xl text-sm font-medium bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800/40">
            {erro}
          </div>
        ) : (
          <>
            {/* ── Metric cards ── */}
            {dados && metricas && (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {[
                  {
                    label: "Total de Ações",
                    value: dados.total.toLocaleString("pt-BR"),
                    iconBg: "bg-[#102a43] dark:bg-slate-700",
                    icon: <svg className="w-5 h-5 text-[#9fb3c8] dark:text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>,
                    sub: "no sistema",
                  },
                  {
                    label: "Usuários Ativos",
                    value: metricas.usuariosDistintos,
                    iconBg: "bg-emerald-700 dark:bg-emerald-900/80",
                    icon: <svg className="w-5 h-5 text-emerald-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>,
                    sub: "nesta página",
                  },
                  {
                    label: "Ações Hoje",
                    value: metricas.acoesHoje,
                    iconBg: "bg-amber-700 dark:bg-amber-900/80",
                    icon: <svg className="w-5 h-5 text-amber-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>,
                    sub: "registradas",
                  },
                  {
                    label: "Mais Frequente",
                    value: ACAO_CONFIG[metricas.acaoFrequente]?.label ?? metricas.acaoFrequente,
                    iconBg: "bg-[#1e3a5f] dark:bg-blue-900/80",
                    icon: <svg className="w-5 h-5 text-blue-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>,
                    sub: "ação",
                    small: true,
                  },
                ].map(m => (
                  <div key={m.label} className="bg-white dark:bg-slate-800/60 rounded-xl border border-[#e2e8f0] dark:border-slate-700/50 p-4" style={{ boxShadow: "0 1px 4px rgba(0,0,0,0.04)" }}>
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-3 ${m.iconBg}`}>
                      {m.icon}
                    </div>
                    <p className={`font-black text-[#102a43] dark:text-slate-100 leading-tight ${m.small ? "text-base" : "text-2xl"}`}>{m.value}</p>
                    <p className="text-[11px] text-[#829ab1] dark:text-slate-500 mt-0.5">{m.label}</p>
                  </div>
                ))}
              </div>
            )}

            {/* ── Filter bar ── */}
            <div className="flex flex-wrap gap-3 items-end p-4 rounded-xl bg-white dark:bg-slate-800 border border-[#e2e8f0] dark:border-slate-700" style={{ boxShadow: "0 1px 4px rgba(0,0,0,0.04)" }}>
              <Select
                label="Ação"
                value={filtroAcao}
                onChange={e => setFiltroAcao(e.target.value)}
                className="min-w-[160px]"
              >
                <option value="">Todas</option>
                {acoesDisponiveis.map(a => (
                  <option key={a} value={a}>{ACAO_CONFIG[a]?.label ?? a}</option>
                ))}
              </Select>

              <Input
                label="Usuário"
                value={filtroUsuario}
                onChange={e => setFiltroUsuario(e.target.value)}
                placeholder="Buscar por nome..."
                className="min-w-[180px]"
              />

              <Input label="De" type="date" value={filtroDataInicio} onChange={e => setFiltroDataInicio(e.target.value)} />
              <Input label="Até" type="date" value={filtroDataFim} onChange={e => setFiltroDataFim(e.target.value)} />

              <div className="flex flex-col gap-1">
                <span className="text-[10px] invisible select-none">x</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => { carregar(1); setPage(1); }}
                    data-notheme
                    className="flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-xl text-white bg-[#102a43] dark:bg-blue-600 hover:bg-[#1e3a5f] dark:hover:bg-blue-500 transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z" />
                    </svg>
                    Filtrar
                  </button>
                  <button
                    onClick={limparFiltros}
                    disabled={!temFiltro}
                    className="flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-xl
                               text-[#486581] dark:text-slate-400 hover:text-[#102a43] dark:hover:text-slate-200
                               border border-[#e2e8f0] dark:border-slate-700
                               bg-[#f8f9fb] dark:bg-slate-800 hover:bg-[#f0f4f8] dark:hover:bg-slate-700
                               disabled:opacity-40 disabled:cursor-not-allowed
                               transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    Limpar
                  </button>
                </div>
              </div>

              {dados && dados.pages > 1 && (
                <span className="ml-auto text-xs self-end pb-2 text-[#829ab1] dark:text-slate-500">
                  Página {dados.page} de {dados.pages}
                </span>
              )}
            </div>

            {/* ── Table ── */}
            {carregando ? (
              <div className="space-y-2 py-2">
                {[...Array(8)].map((_, i) => (
                  <div key={i} className="flex items-center gap-4 px-5 py-3.5 rounded-xl bg-white dark:bg-slate-800 border border-[#e2e8f0] dark:border-slate-700">
                    <div className="skeleton w-8 h-8 rounded-lg flex-shrink-0" />
                    <div className="flex-1 space-y-1.5">
                      <div className="skeleton h-3 rounded" style={{ width: `${50 + (i % 4) * 12}%` }} />
                      <div className="skeleton h-2.5 w-32 rounded" />
                    </div>
                    <div className="skeleton h-5 w-24 rounded-full flex-shrink-0" />
                  </div>
                ))}
              </div>
            ) : dados && dados.items.length === 0 ? (
              <EmptyState
                icon={
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                }
                title="Nenhum registro encontrado"
                description={temFiltro ? "Tente remover os filtros." : "As ações serão registradas conforme o uso do sistema."}
              />
            ) : dados ? (
              <>
                <div className="bg-white dark:bg-slate-800 border border-[#e2e8f0] dark:border-slate-700 rounded-xl overflow-hidden" style={{ boxShadow: "0 1px 4px rgba(0,0,0,0.04)" }}>
                  <div className="h-[2px] bg-gradient-to-r from-[#102a43] via-[#486581] to-transparent" />
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-[#f8f9fb] dark:bg-slate-700/50 border-b border-[#e2e8f0] dark:border-slate-700">
                        <tr>
                          {["Data / Hora", "Usuário", "Ação", "Recurso", "Detalhes", "IP"].map((h, i) => (
                            <th
                              key={h}
                              className={`px-4 py-3 text-left text-[10px] font-bold uppercase tracking-widest text-[#829ab1] dark:text-slate-400 ${i === 0 ? "whitespace-nowrap" : ""}`}
                            >
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#f1f5f9] dark:divide-slate-700">
                        {dados.items.map(log => (
                          <tr
                            key={log.id}
                            className="hover:bg-[#f8f9fb] dark:hover:bg-slate-700/30 transition-colors"
                          >
                            <td className="px-4 py-3.5 text-xs font-mono text-[#627d98] dark:text-slate-400 whitespace-nowrap">
                              {formatarData(log.criado_em)}
                            </td>
                            <td className="px-4 py-3.5">
                              {log.usuario_nome ? (
                                <div className="flex items-center gap-2">
                                  <Avatar name={log.usuario_nome} size="sm" />
                                  <span className="text-xs font-medium text-[#334e68] dark:text-slate-200">
                                    {log.usuario_nome}
                                  </span>
                                </div>
                              ) : (
                                <span className="text-xs text-[#829ab1] dark:text-slate-500">Sistema</span>
                              )}
                            </td>
                            <td className="px-4 py-3.5">
                              <AcaoBadge acao={log.acao} />
                            </td>
                            <td className="px-4 py-3.5">
                              {log.recurso ? (
                                <span className="text-xs text-[#334e68] dark:text-slate-300">
                                  {log.recurso}
                                  {log.recurso_id && (
                                    <span className="ml-1 text-[#829ab1] dark:text-slate-500">#{log.recurso_id}</span>
                                  )}
                                </span>
                              ) : (
                                <span className="text-xs text-[#829ab1] dark:text-slate-500">—</span>
                              )}
                            </td>
                            <td className="px-4 py-3.5 max-w-xs">
                              <DetalhesPill detalhes={log.detalhes} />
                            </td>
                            <td className="px-4 py-3.5">
                              <IpCell ip={log.ip} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Paginação */}
                {dados.pages > 1 && (
                  <div className="flex items-center justify-center gap-2 mt-1">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold
                                 border border-[#e2e8f0] dark:border-slate-700
                                 bg-white dark:bg-slate-800
                                 text-[#486581] dark:text-slate-300
                                 hover:border-[#9fb3c8] dark:hover:border-navy-600
                                 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                      </svg>
                      Anterior
                    </button>
                    <span className="px-4 py-2 rounded-xl text-xs font-bold bg-[#f0f4f8] dark:bg-navy-900/30 border border-[#e2e8f0] dark:border-navy-800/60 text-[#102a43] dark:text-navy-300">
                      {page} / {dados.pages}
                    </span>
                    <button
                      onClick={() => setPage(p => Math.min(dados.pages, p + 1))}
                      disabled={page === dados.pages}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold
                                 border border-[#e2e8f0] dark:border-slate-700
                                 bg-white dark:bg-slate-800
                                 text-[#486581] dark:text-slate-300
                                 hover:border-[#9fb3c8] dark:hover:border-navy-600
                                 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                    >
                      Próxima
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  </div>
                )}
              </>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
