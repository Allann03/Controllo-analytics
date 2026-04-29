"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { Building2, CheckCircle2, XCircle, Clock } from "lucide-react";

/* -- types ------------------------------------------------ */
interface Escritorio {
  id: number;
  nome: string;
  slug: string;
  plano: string;
  max_empresas: number;
  max_usuarios: number;
  ativo: boolean;
  usuarios_count: number;
  usuarios_pendentes: number;
  empresas_count: number;
  criado_em: string;
}

interface Usuario {
  id: number;
  nome: string;
  login_completo: string;
  nome_exibicao: string;
  cargo: string;
  is_master: boolean;
  is_dono: boolean;
  is_admin: boolean;
  is_ceo: boolean;
  is_gestor: boolean;
  is_aprovado: boolean;
  escritorio_id: number;
  escritorio_nome: string;
  escritorio_slug: string;
}

interface Metricas {
  escritorios_total: number;
  escritorios_ativos: number;
  escritorios_inativos: number;
  usuarios_total: number;
  usuarios_pendentes_global: number;
  empresas_total: number;
  lancamentos_total: number;
  escritorios_por_plano: Record<string, number>;
}

interface EscritorioResumo {
  escritorio_id: number;
  nome: string;
  slug: string;
  plano: string;
  ativo: boolean;
  max_empresas: number;
  max_usuarios: number;
  total_usuarios: number;
  usuarios_pendentes: number;
  usuarios_ativos: number;
  total_empresas: number;
}

interface Toast {
  mensagem: string;
  tipo: "sucesso" | "erro";
}

type Tab = "escritorios" | "usuarios" | "metricas";
type StatusFiltro = "todos" | "pendentes" | "ativos";

const PLANOS: Record<string, { empresas: number; usuarios: number; cor: string; bg: string }> = {
  trial:         { empresas: 10,   usuarios: 2,   cor: "text-slate-600 dark:text-slate-400",   bg: "bg-slate-500/10 border-slate-500/20" },
  basico:        { empresas: 50,   usuarios: 5,   cor: "text-teal-600 dark:text-teal-400",     bg: "bg-teal-500/10 border-teal-500/20" },
  profissional:  { empresas: 500,  usuarios: 30,  cor: "text-blue-600 dark:text-blue-400",     bg: "bg-blue-500/10 border-blue-500/20" },
  enterprise:    { empresas: 1500, usuarios: 150, cor: "text-violet-600 dark:text-violet-400", bg: "bg-violet-500/10 border-violet-500/20" },
};

const PLANOS_CONFIG = [
  { id: "trial", nome: "Trial", empresas: 10, usuarios: 2, descricao: "Período de avaliação", badge: null },
  { id: "basico", nome: "Básico", empresas: 50, usuarios: 5, descricao: "Para escritórios iniciantes", badge: null },
  { id: "profissional", nome: "Profissional", empresas: 500, usuarios: 30, descricao: "Para escritórios em crescimento", badge: "Recomendado" },
  { id: "enterprise", nome: "Enterprise", empresas: 1500, usuarios: 150, descricao: "Para grandes escritórios", badge: null },
];

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

function getHeaders() {
  const t = typeof window !== "undefined" ? localStorage.getItem("controllo_token") : null;
  return { "Content-Type": "application/json", ...(t ? { Authorization: `Bearer ${t}` } : {}) };
}

function generateSlug(nome: string): string {
  return nome.toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]/g, "")
    .slice(0, 50);
}

/* -- small components ------------------------------------- */
function Badge({ children, className }: { children: React.ReactNode; className: string }) {
  return <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${className}`}>{children}</span>;
}

function KpiCard({ label, value, icon }: { label: string; value: number | string; icon?: React.ReactNode }) {
  return (
    <div
      className="rounded-2xl p-5 flex flex-col gap-2"
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
      }}
    >
      <div className="flex items-center justify-between">
        <span
          className="text-xs uppercase font-medium"
          style={{
            color: "var(--text-tertiary)",
            letterSpacing: "var(--tracking-widest)",
          }}
        >
          {label}
        </span>
        {icon && <span style={{ color: "var(--text-tertiary)" }}>{icon}</span>}
      </div>
      <span
        className="text-3xl font-mono font-semibold tabular-nums"
        style={{ color: "var(--text-primary)" }}
      >
        {value}
      </span>
    </div>
  );
}

function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80">
          <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">{title}</h3>
        </div>
        <div className="p-6 bg-white dark:bg-slate-800">{children}</div>
      </div>
    </div>
  );
}

function ToastBar({ toast, onDone }: { toast: Toast | null; onDone: () => void }) {
  useEffect(() => { if (toast) { const t = setTimeout(onDone, 3500); return () => clearTimeout(t); } }, [toast, onDone]);
  if (!toast) return null;
  const bg = toast.tipo === "sucesso"
    ? "bg-emerald-50 dark:bg-emerald-950/90 border border-emerald-200 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
    : "bg-rose-50 dark:bg-rose-950/90 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300";
  return (
    <div className={`fixed top-6 right-6 z-[60] px-5 py-3 rounded-xl text-sm font-semibold shadow-lg ${bg} animate-[fadeIn_0.2s]`}>
      {toast.mensagem}
    </div>
  );
}

/* -- main page -------------------------------------------- */
export default function MasterPage() {
  const router = useRouter();
  const [authed, setAuthed] = useState(false);

  /* data */
  const [tab, setTab] = useState<Tab>("escritorios");
  const [escritorios, setEscritorios] = useState<Escritorio[]>([]);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [metricas, setMetricas] = useState<Metricas | null>(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);

  /* filters */
  const [buscaEsc, setBuscaEsc] = useState("");
  const [selectedEscId, setSelectedEscId] = useState<number | null>(null);
  const [resumoEsc, setResumoEsc] = useState<EscritorioResumo | null>(null);
  const [statusUsuario, setStatusUsuario] = useState<StatusFiltro>("todos");
  const [buscaUser, setBuscaUser] = useState("");

  /* modals */
  const [showCriar, setShowCriar] = useState(false);
  const [editEsc, setEditEsc] = useState<Escritorio | null>(null);
  const [roleEdit, setRoleEdit] = useState<Record<number, { is_admin: boolean; is_ceo: boolean; is_gestor: boolean }>>({});

  /* create form */
  const [formNome, setFormNome] = useState("");
  const [formSlug, setFormSlug] = useState("");
  const [formPlano, setFormPlano] = useState("trial");
  const [formCnpj, setFormCnpj] = useState("");
  const [formTelefone, setFormTelefone] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formResponsavel, setFormResponsavel] = useState("");
  const [formMaxEmpresas, setFormMaxEmpresas] = useState(10);
  const [formMaxUsuarios, setFormMaxUsuarios] = useState(2);
  const [criadoSlug, setCriadoSlug] = useState("");
  const slugManuallyEdited = useRef(false);

  /* edit form */
  const [editNome, setEditNome] = useState("");
  const [editPlano, setEditPlano] = useState("trial");
  const [editMaxEmpresas, setEditMaxEmpresas] = useState(10);
  const [editMaxUsuarios, setEditMaxUsuarios] = useState(2);

  const show = useCallback((mensagem: string, tipo: "sucesso" | "erro") => setToast({ mensagem, tipo }), []);

  /* -- auth check ----------------------------------------- */
  useEffect(() => {
    const token = localStorage.getItem("controllo_token");
    if (!token) { router.replace("/"); return; }
    try {
      const u = JSON.parse(localStorage.getItem("controllo_user") || "{}");
      if (!u.is_master) { router.replace("/"); return; }
    } catch { router.replace("/"); return; }
    setAuthed(true);
  }, [router]);

  /* -- auto-slug from formNome ---------------------------- */
  useEffect(() => {
    if (!slugManuallyEdited.current) {
      setFormSlug(generateSlug(formNome));
    }
  }, [formNome]);

  /* -- auto-fill limits when plan changes ----------------- */
  useEffect(() => {
    const p = PLANOS_CONFIG.find(p => p.id === formPlano);
    if (p) { setFormMaxEmpresas(p.empresas); setFormMaxUsuarios(p.usuarios); }
  }, [formPlano]);

  /* -- data loaders --------------------------------------- */
  const loadEscritorios = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/master/escritorios`, { headers: getHeaders() });
      if (!r.ok) throw new Error();
      setEscritorios(await r.json());
    } catch { show("Erro ao carregar escritorios", "erro"); }
    setLoading(false);
  }, [show]);

  const loadResumo = useCallback(async (escId: number) => {
    try {
      const r = await fetch(`${API}/api/master/escritorios/${escId}/resumo`, { headers: getHeaders() });
      if (!r.ok) throw new Error();
      setResumoEsc(await r.json());
    } catch { /* silent — resumo is supplementary */ }
  }, []);

  const loadUsuarios = useCallback(async () => {
    if (!selectedEscId) { setUsuarios([]); return; }
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("escritorio_id", String(selectedEscId));
      if (statusUsuario !== "todos") params.set("status", statusUsuario);
      if (buscaUser.trim()) params.set("busca", buscaUser.trim());
      const r = await fetch(`${API}/api/master/usuarios?${params}`, { headers: getHeaders() });
      if (!r.ok) throw new Error();
      setUsuarios(await r.json());
    } catch { show("Erro ao carregar usuarios", "erro"); }
    setLoading(false);
  }, [selectedEscId, statusUsuario, buscaUser, show]);

  const loadMetricas = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/master/metricas`, { headers: getHeaders() });
      if (!r.ok) throw new Error();
      setMetricas(await r.json());
    } catch { show("Erro ao carregar metricas", "erro"); }
    setLoading(false);
  }, [show]);

  useEffect(() => {
    if (!authed) return;
    if (tab === "escritorios") loadEscritorios();
    else if (tab === "usuarios") { loadEscritorios(); if (selectedEscId) { loadUsuarios(); loadResumo(selectedEscId); } }
    else loadMetricas();
  }, [authed, tab, loadEscritorios, loadUsuarios, loadMetricas, selectedEscId, loadResumo]);

  /* -- actions -------------------------------------------- */
  async function criarEscritorio() {
    try {
      const r = await fetch(`${API}/api/master/escritorios`, {
        method: "POST", headers: getHeaders(),
        body: JSON.stringify({
          nome: formNome, slug: formSlug, plano: formPlano,
          max_empresas: formMaxEmpresas, max_usuarios: formMaxUsuarios
        }),
      });
      if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || "Erro"); }
      const data = await r.json();
      setCriadoSlug(data.escritorio?.slug || formSlug);
      show("Escritório criado com sucesso!", "sucesso");
      setShowCriar(false); resetForm();
      loadEscritorios();
    } catch (e: unknown) { show(e instanceof Error ? e.message : "Erro ao criar", "erro"); }
  }

  async function salvarEdicao() {
    if (!editEsc) return;
    try {
      const r = await fetch(`${API}/api/master/escritorios/${editEsc.id}`, {
        method: "PATCH", headers: getHeaders(),
        body: JSON.stringify({ nome: editNome, plano: editPlano, max_empresas: editMaxEmpresas, max_usuarios: editMaxUsuarios }),
      });
      if (!r.ok) throw new Error();
      show("Escritorio atualizado", "sucesso");
      setEditEsc(null); loadEscritorios();
    } catch { show("Erro ao atualizar", "erro"); }
  }

  async function toggleAtivo(e: Escritorio) {
    const action = e.ativo ? "desativar" : "ativar";
    try {
      const r = await fetch(`${API}/api/master/escritorios/${e.id}/${action}`, { method: "PATCH", headers: getHeaders() });
      if (!r.ok) throw new Error();
      show(`Escritorio ${action === "ativar" ? "ativado" : "desativado"}`, "sucesso");
      loadEscritorios();
    } catch { show("Erro ao alterar status", "erro"); }
  }

  async function excluirEscritorio(e: Escritorio) {
    if (e.empresas_count > 0) { show("Impossivel excluir: possui empresas", "erro"); return; }
    try {
      const r = await fetch(`${API}/api/master/escritorios/${e.id}`, { method: "DELETE", headers: getHeaders() });
      if (!r.ok) throw new Error();
      show("Escritorio excluido", "sucesso"); loadEscritorios();
    } catch { show("Erro ao excluir", "erro"); }
  }

  async function aprovarUsuario(id: number) {
    const eidParam = selectedEscId ? `?escritorio_id=${selectedEscId}` : "";
    try {
      const r = await fetch(`${API}/api/master/usuarios/${id}/aprovar${eidParam}`, { method: "PATCH", headers: getHeaders() });
      if (!r.ok) throw new Error();
      show("Usuario aprovado", "sucesso"); loadUsuarios(); if (selectedEscId) loadResumo(selectedEscId);
    } catch { show("Erro ao aprovar", "erro"); }
  }

  async function reprovarUsuario(id: number) {
    const eidParam = selectedEscId ? `?escritorio_id=${selectedEscId}` : "";
    try {
      const r = await fetch(`${API}/api/master/usuarios/${id}/reprovar${eidParam}`, { method: "PATCH", headers: getHeaders() });
      if (!r.ok) throw new Error();
      show("Usuario reprovado", "sucesso"); loadUsuarios(); if (selectedEscId) loadResumo(selectedEscId);
    } catch { show("Erro ao reprovar", "erro"); }
  }

  async function salvarRole(u: Usuario) {
    const r2 = roleEdit[u.id];
    if (!r2) return;
    const eidParam = selectedEscId ? `?escritorio_id=${selectedEscId}` : "";
    try {
      const r = await fetch(`${API}/api/master/usuarios/${u.id}/role${eidParam}`, {
        method: "PATCH", headers: getHeaders(),
        body: JSON.stringify(r2),
      });
      if (!r.ok) throw new Error();
      show("Perfil atualizado", "sucesso"); loadUsuarios();
    } catch { show("Erro ao atualizar perfil", "erro"); }
  }

  async function excluirUsuario(id: number) {
    const eidParam = selectedEscId ? `?escritorio_id=${selectedEscId}` : "";
    try {
      const r = await fetch(`${API}/api/master/usuarios/${id}${eidParam}`, { method: "DELETE", headers: getHeaders() });
      if (!r.ok) throw new Error();
      show("Usuario excluido", "sucesso"); loadUsuarios(); if (selectedEscId) loadResumo(selectedEscId);
    } catch { show("Erro ao excluir", "erro"); }
  }

  function resetForm() {
    setFormNome(""); setFormSlug(""); setFormPlano("trial");
    setFormCnpj(""); setFormTelefone(""); setFormEmail(""); setFormResponsavel("");
    setFormMaxEmpresas(10); setFormMaxUsuarios(2);
    slugManuallyEdited.current = false;
  }

  function openEdit(e: Escritorio) {
    setEditEsc(e); setEditNome(e.nome); setEditPlano(e.plano);
    setEditMaxEmpresas(e.max_empresas); setEditMaxUsuarios(e.max_usuarios);
  }

  function initRoleEdit(u: Usuario) {
    if (!roleEdit[u.id]) setRoleEdit(prev => ({ ...prev, [u.id]: { is_admin: u.is_admin, is_ceo: u.is_ceo, is_gestor: u.is_gestor } }));
  }

  function toggleRole(uid: number, key: "is_admin" | "is_ceo" | "is_gestor") {
    setRoleEdit(prev => ({ ...prev, [uid]: { ...prev[uid], [key]: !prev[uid][key] } }));
  }

  /* -- derived -------------------------------------------- */
  const escFiltrados = escritorios.filter(e => {
    const b = buscaEsc.toLowerCase();
    return !b || e.nome.toLowerCase().includes(b) || e.slug.toLowerCase().includes(b);
  });

  const pendentesGlobal = escritorios.reduce((a, e) => a + (e.usuarios_pendentes || 0), 0);

  /* slug auto gen */
  function handleNomeChange(v: string) {
    setFormNome(v);
    slugManuallyEdited.current = false;
  }

  function handleSlugManualChange(v: string) {
    setFormSlug(v);
    slugManuallyEdited.current = true;
  }

  /* plano change auto-sets limits */
  function handlePlanoChange(p: string, target: "create" | "edit") {
    const pl = PLANOS[p] || PLANOS.trial;
    if (target === "create") { setFormPlano(p); }
    else { setEditPlano(p); setEditMaxEmpresas(pl.empresas); setEditMaxUsuarios(pl.usuarios); }
  }

  if (!authed) return null;

  /* -- render --------------------------------------------- */
  const inputCls = "w-full px-4 py-2.5 rounded-xl text-sm border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 transition-all";

  // Tokens-based button styles (§5.8). Inline to manter o estilo original
  // dos modais e formularios (que ainda usam classes proprietarias).
  const btnPrimaryStyle: React.CSSProperties = {
    background: "var(--accent)",
    color: "var(--text-inverse)",
    borderRadius: "var(--radius-md)",
  };
  const btnSecondaryStyle: React.CSSProperties = {
    background: "var(--bg-elevated)",
    border: "1px solid var(--border-default)",
    color: "var(--text-primary)",
    borderRadius: "var(--radius-md)",
  };

  // Mantidos para os modais (form Criar Escritorio, Editar Escritorio, etc).
  const btnPrimary = "px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm transition-colors";
  const btnDanger = "px-3 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition-colors";
  const btnSecondary = "px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 text-sm font-semibold transition-colors";
  const btnGreen = "px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold transition-colors";

  const glassCard = "bg-white dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-700/50 rounded-2xl";

  return (
    <div className="min-h-screen font-[var(--font-body)]" style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      <ToastBar toast={toast} onDone={() => setToast(null)} />

      {/* Geometric background */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" style={{ zIndex: 0 }}>
        <div className="absolute inset-0 opacity-[var(--geo-dots-opacity,0.03)]"
          style={{ backgroundImage: 'radial-gradient(circle, currentColor 1px, transparent 1px)', backgroundSize: '32px 32px' }} />
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full border border-current opacity-[var(--geo-ring-opacity,0.04)]" />
        <div className="absolute -bottom-20 -left-20 w-64 h-64 rounded-full border border-current opacity-[var(--geo-ring-opacity,0.03)]" />
      </div>

      {/* header */}
      <header
        className="relative z-10 px-8 pt-8 pb-6"
        style={{ borderBottom: "1px solid var(--border-subtle)" }}
      >
        <div className="max-w-7xl mx-auto flex items-start justify-between gap-4">
          <div>
            <p
              className="text-xs uppercase font-medium mb-2"
              style={{
                color: "var(--text-tertiary)",
                letterSpacing: "var(--tracking-widest)",
              }}
            >
              Administrador
            </p>
            <h1 className="text-2xl font-extrabold tracking-tight" style={{ color: "var(--text-primary)" }}>
              Central de Controle
            </h1>
            <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
              Gestão centralizada de escritórios e usuários da plataforma
            </p>
          </div>
          <button
            onClick={() => router.push("/dashboard")}
            className="text-xs transition-colors"
            style={{ color: "var(--text-tertiary)" }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "var(--text-primary)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-tertiary)"; }}
          >
            Voltar ao Dashboard
          </button>
        </div>
      </header>

      {/* tabs — underline horizontal sobrio */}
      <nav className="relative z-10 max-w-7xl mx-auto px-6 pt-2">
        <div
          className="flex gap-0.5"
          style={{ borderBottom: "1px solid var(--border-subtle)" }}
        >
          {(["escritorios", "usuarios", "metricas"] as Tab[]).map(t => {
            const labels: Record<Tab, string> = { escritorios: "Escritórios", usuarios: "Usuários", metricas: "Métricas" };
            const active = tab === t;
            return (
              <button
                key={t}
                onClick={() => setTab(t)}
                className="relative px-5 py-3 text-sm font-semibold transition-colors"
                style={{
                  color: active ? "var(--text-primary)" : "var(--text-secondary)",
                }}
                onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = "var(--text-primary)"; }}
                onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = "var(--text-secondary)"; }}
              >
                {labels[t]}
                {active && (
                  <span
                    className="absolute left-0 right-0 -bottom-px h-0.5"
                    style={{ background: "var(--accent)" }}
                  />
                )}
              </button>
            );
          })}
        </div>
      </nav>

      <main className="relative z-10 max-w-7xl mx-auto px-6 pb-12 pt-6">
        <div className={`${glassCard} p-6 min-h-[60vh]`}>
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {/* ====== TAB: ESCRITORIOS ====== */}
          {tab === "escritorios" && !loading && (
            <div className="space-y-6">
              {/* summary */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard label="Total"            value={escritorios.length}                              icon={<Building2 size={20} strokeWidth={1.75} />} />
                <KpiCard label="Ativos"           value={escritorios.filter(e => e.ativo).length}         icon={<CheckCircle2 size={20} strokeWidth={1.75} />} />
                <KpiCard label="Inativos"         value={escritorios.filter(e => !e.ativo).length}        icon={<XCircle size={20} strokeWidth={1.75} />} />
                <KpiCard label="Pendentes Global" value={pendentesGlobal}                                  icon={<Clock size={20} strokeWidth={1.75} />} />
              </div>

              {/* toolbar */}
              <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
                <input placeholder="Buscar por nome ou código..." value={buscaEsc} onChange={e => setBuscaEsc(e.target.value)} className={`${inputCls} max-w-xs`} />
                <button
                  onClick={() => { resetForm(); setShowCriar(true); }}
                  className="px-4 py-2 text-sm font-semibold transition-colors"
                  style={btnPrimaryStyle}
                  onMouseEnter={(e) => { e.currentTarget.style.background = "var(--accent-hover)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "var(--accent)"; }}
                >
                  + Novo Escritório
                </button>
              </div>

              {/* list */}
              <div className="grid gap-4">
                {escFiltrados.map(e => {
                  return (
                    <div
                      key={e.id}
                      className="rounded-2xl p-5 flex flex-col md:flex-row md:items-start gap-4"
                      style={{
                        background: "var(--bg-surface)",
                        border: "1px solid var(--border-subtle)",
                      }}
                    >
                      <Building2 size={32} strokeWidth={1.5} style={{ color: "var(--text-tertiary)", flexShrink: 0 }} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-bold text-base" style={{ color: "var(--text-primary)" }}>{e.nome}</span>
                          <span className="text-sm" style={{ color: "var(--text-tertiary)" }}>@{e.slug}</span>
                          <span
                            className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide"
                            style={{
                              background: "var(--accent-subtle)",
                              border: "1px solid var(--accent-border)",
                              color: "var(--accent-text)",
                            }}
                          >
                            {e.plano}
                          </span>
                          <span
                            className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide"
                            style={{
                              background: e.ativo ? "var(--success-subtle)" : "var(--bg-inset)",
                              border: `1px solid ${e.ativo ? "var(--success-border)" : "var(--border-subtle)"}`,
                              color: e.ativo ? "var(--success)" : "var(--text-tertiary)",
                            }}
                          >
                            {e.ativo ? "Ativo" : "Inativo"}
                          </span>
                        </div>

                        {/* progress bars — 4px, bg-inset, fill accent */}
                        <div className="mt-3 space-y-2.5">
                          <div>
                            <div className="flex justify-between text-[11px] mb-1" style={{ color: "var(--text-tertiary)" }}>
                              <span>Empresas</span>
                              <span className="font-mono tabular-nums">{e.empresas_count}/{e.max_empresas}</span>
                            </div>
                            <div className="h-1 rounded-full overflow-hidden" style={{ background: "var(--bg-inset)" }}>
                              <div
                                className="h-full rounded-full transition-all"
                                style={{
                                  width: `${Math.min(100, (e.empresas_count / e.max_empresas) * 100)}%`,
                                  background: "var(--accent)",
                                }}
                              />
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-[11px] mb-1" style={{ color: "var(--text-tertiary)" }}>
                              <span>Usuários</span>
                              <span className="font-mono tabular-nums">{e.usuarios_count}/{e.max_usuarios}</span>
                            </div>
                            <div className="h-1 rounded-full overflow-hidden" style={{ background: "var(--bg-inset)" }}>
                              <div
                                className="h-full rounded-full transition-all"
                                style={{
                                  width: `${Math.min(100, (e.usuarios_count / e.max_usuarios) * 100)}%`,
                                  background: "var(--accent)",
                                }}
                              />
                            </div>
                          </div>
                        </div>

                        {e.usuarios_pendentes > 0 && (
                          <div className="mt-2.5">
                            <span
                              className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide"
                              style={{
                                background: "var(--warning-subtle)",
                                border: "1px solid var(--warning-border)",
                                color: "var(--warning)",
                              }}
                            >
                              {e.usuarios_pendentes} pendente{e.usuarios_pendentes > 1 ? "s" : ""}
                            </span>
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <button
                          onClick={() => openEdit(e)}
                          className="px-3 py-1.5 text-xs font-semibold transition-colors"
                          style={btnSecondaryStyle}
                          onMouseEnter={(ev) => { ev.currentTarget.style.background = "var(--bg-overlay)"; }}
                          onMouseLeave={(ev) => { ev.currentTarget.style.background = "var(--bg-elevated)"; }}
                        >
                          Gerenciar
                        </button>
                        <button
                          onClick={() => toggleAtivo(e)}
                          className="px-3 py-1.5 text-xs font-semibold transition-colors"
                          style={{
                            background: "transparent",
                            color: "var(--text-secondary)",
                            borderRadius: "var(--radius-md)",
                            border: "1px solid var(--border-subtle)",
                          }}
                          onMouseEnter={(ev) => {
                            ev.currentTarget.style.background = e.ativo ? "var(--warning-subtle)" : "var(--success-subtle)";
                            ev.currentTarget.style.color = e.ativo ? "var(--warning)" : "var(--success)";
                          }}
                          onMouseLeave={(ev) => {
                            ev.currentTarget.style.background = "transparent";
                            ev.currentTarget.style.color = "var(--text-secondary)";
                          }}
                        >
                          {e.ativo ? "Desativar" : "Ativar"}
                        </button>
                        {e.empresas_count === 0 && (
                          <button
                            onClick={() => excluirEscritorio(e)}
                            className="px-3 py-1.5 text-xs font-semibold transition-colors"
                            style={{
                              background: "transparent",
                              color: "var(--text-secondary)",
                              borderRadius: "var(--radius-md)",
                              border: "1px solid var(--border-subtle)",
                            }}
                            onMouseEnter={(ev) => {
                              ev.currentTarget.style.background = "var(--danger-subtle)";
                              ev.currentTarget.style.color = "var(--danger)";
                            }}
                            onMouseLeave={(ev) => {
                              ev.currentTarget.style.background = "transparent";
                              ev.currentTarget.style.color = "var(--text-secondary)";
                            }}
                          >
                            Excluir
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
                {escFiltrados.length === 0 && <p className="text-center py-8" style={{ color: "var(--text-tertiary)" }}>Nenhum escritório encontrado.</p>}
              </div>
            </div>
          )}

          {/* ====== TAB: USUARIOS ====== */}
          {tab === "usuarios" && !loading && (
            <div className="space-y-6">
              {/* Seletor de escritório */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Selecione um escritório</label>
                <select
                  value={selectedEscId ?? ""}
                  onChange={e => {
                    const v = e.target.value ? Number(e.target.value) : null;
                    setSelectedEscId(v);
                    setUsuarios([]);
                    setResumoEsc(null);
                    setStatusUsuario("todos");
                    setBuscaUser("");
                    setRoleEdit({});
                  }}
                  className={`${inputCls} max-w-md`}
                >
                  <option value="">-- Selecione um escritório --</option>
                  {escritorios.map(e => (
                    <option key={e.id} value={e.id}>
                      {e.nome} — {e.plano} — {e.usuarios_count} usuário{e.usuarios_count !== 1 ? "s" : ""}{e.usuarios_pendentes > 0 ? `, ${e.usuarios_pendentes} pendente${e.usuarios_pendentes > 1 ? "s" : ""}` : ""}
                    </option>
                  ))}
                </select>
              </div>

              {/* Sem seleção */}
              {!selectedEscId && (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-4">
                    <svg className="w-8 h-8 text-indigo-500/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                  </div>
                  <p className="text-lg font-semibold text-slate-600 dark:text-slate-300">Selecione um escritório para gerenciar seus usuários</p>
                  <p className="text-sm text-slate-400 dark:text-slate-500 mt-1">Cada escritório possui isolamento total de dados</p>
                </div>
              )}

              {/* Com escritório selecionado */}
              {selectedEscId && (
                <>
                  {/* Resumo do escritório */}
                  {resumoEsc && (
                    <div className={`${glassCard} p-5`}>
                      <div className="flex items-center gap-3 mb-3">
                        <svg className="w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                        <span className="text-lg font-bold text-slate-900 dark:text-slate-100">{resumoEsc.nome}</span>
                        <Badge className={`${(PLANOS[resumoEsc.plano] || PLANOS.trial).bg} ${(PLANOS[resumoEsc.plano] || PLANOS.trial).cor} border`}>{resumoEsc.plano}</Badge>
                        <Badge className={resumoEsc.ativo ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" : "bg-rose-500/10 text-rose-600 dark:text-rose-400"}>
                          {resumoEsc.ativo ? "Ativo" : "Inativo"}
                        </Badge>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="text-center p-3 rounded-xl bg-slate-50 dark:bg-slate-700/30">
                          <div className="text-2xl font-black font-mono text-slate-900 dark:text-slate-100">{resumoEsc.total_usuarios}</div>
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Usuários</div>
                        </div>
                        <div className="text-center p-3 rounded-xl bg-amber-50 dark:bg-amber-500/5">
                          <div className="text-2xl font-black font-mono text-amber-600 dark:text-amber-400">{resumoEsc.usuarios_pendentes}</div>
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Pendentes</div>
                        </div>
                        <div className="text-center p-3 rounded-xl bg-emerald-50 dark:bg-emerald-500/5">
                          <div className="text-2xl font-black font-mono text-emerald-600 dark:text-emerald-400">{resumoEsc.usuarios_ativos}</div>
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Ativos</div>
                        </div>
                        <div className="text-center p-3 rounded-xl bg-slate-50 dark:bg-slate-700/30">
                          <div className="text-2xl font-black font-mono text-slate-900 dark:text-slate-100">{resumoEsc.total_empresas}</div>
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Empresas</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Filtros de usuários */}
                  <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center flex-wrap">
                    <div className="flex gap-1">
                      {(["todos", "pendentes", "ativos"] as StatusFiltro[]).map(s => (
                        <button key={s} onClick={() => setStatusUsuario(s)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${statusUsuario === s ? "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20" : "bg-slate-100 dark:bg-slate-700/40 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"}`}>
                          {s.charAt(0).toUpperCase() + s.slice(1)}
                        </button>
                      ))}
                    </div>
                    <input placeholder="Buscar por nome..." value={buscaUser} onChange={e => setBuscaUser(e.target.value)} className={`${inputCls} max-w-xs`} />
                    <button onClick={loadUsuarios} className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-colors hover:bg-slate-200 dark:hover:bg-slate-600">Buscar</button>
                  </div>

                  {/* Lista de usuários */}
                  <div className="grid gap-3">
                    {usuarios.map(u => {
                      const isPending = !u.is_aprovado;
                      const re = roleEdit[u.id];
                      return (
                        <div key={u.id} className={`${glassCard} p-4 flex flex-col md:flex-row md:items-center gap-4 ${isPending ? "ring-2 ring-amber-500/20" : ""}`}>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-bold text-slate-900 dark:text-slate-100 text-sm">{u.login_completo}</span>
                              {u.nome_exibicao && <span className="text-slate-400 dark:text-slate-500 text-xs">({u.nome_exibicao})</span>}
                              {u.cargo && <span className="text-slate-500 text-xs">- {u.cargo}</span>}
                            </div>
                            <div className="flex gap-1.5 mt-1.5 flex-wrap">
                              {u.is_master && <Badge className="bg-violet-500/10 text-violet-600 dark:text-violet-400 border border-violet-500/20">Proprietario</Badge>}
                              {u.is_admin && <Badge className="bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">Admin</Badge>}
                              {u.is_ceo && <Badge className="bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20">CEO</Badge>}
                              {u.is_gestor && <Badge className="bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/20">Gestor</Badge>}
                              {u.is_dono && <Badge className="bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">Dono</Badge>}
                              {!u.is_master && !u.is_admin && !u.is_ceo && !u.is_gestor && !u.is_dono && <Badge className="bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20">Analista</Badge>}
                              <Badge className={
                                u.is_master
                                  ? "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400"
                                  : isPending
                                    ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                                    : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                              }>
                                {u.is_master ? "Protegido" : isPending ? "Pendente" : "Ativo"}
                              </Badge>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 flex-shrink-0 flex-wrap">
                            {u.is_master ? (
                              <span className="flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 font-semibold">
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                </svg>
                                Protegido
                              </span>
                            ) : isPending ? (
                              <>
                                <button onClick={() => aprovarUsuario(u.id)} className={btnGreen}>Aprovar</button>
                                <button onClick={() => reprovarUsuario(u.id)} className={btnDanger}>Reprovar</button>
                              </>
                            ) : (
                              <div className="flex items-center gap-2 flex-wrap">
                                <div className="flex items-center gap-3 bg-slate-100 dark:bg-slate-700/40 rounded-xl px-3 py-1.5">
                                  {(["is_admin", "is_ceo", "is_gestor"] as const).map(key => {
                                    const labels = { is_admin: "Admin", is_ceo: "CEO", is_gestor: "Gestor" };
                                    const checked = re ? re[key] : u[key];
                                    return (
                                      <label key={key} className="flex items-center gap-1 cursor-pointer">
                                        <input type="checkbox" checked={checked} onChange={() => { initRoleEdit(u); toggleRole(u.id, key); }}
                                          className="w-3.5 h-3.5 rounded border-slate-300 dark:border-slate-500 text-indigo-600 focus:ring-indigo-500/30 bg-white dark:bg-slate-600" />
                                        <span className="text-[11px] text-slate-600 dark:text-slate-300">{labels[key]}</span>
                                      </label>
                                    );
                                  })}
                                </div>
                                {re && <button onClick={() => salvarRole(u)} className={btnPrimary + " !py-1.5 !text-xs"}>Salvar</button>}
                                <button onClick={() => excluirUsuario(u.id)} className={btnDanger}>Excluir</button>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                    {usuarios.length === 0 && <p className="text-center text-slate-500 py-8">Nenhum usuario encontrado neste escritório.</p>}
                  </div>
                </>
              )}
            </div>
          )}

          {/* ====== TAB: METRICAS ====== */}
          {tab === "metricas" && !loading && metricas && (
            <div className="space-y-8">
              {/* KPIs */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <KpiCard label="Escritorios" value={metricas.escritorios_total} icon={
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
                } />
                <KpiCard label="Ativos" value={metricas.escritorios_ativos} icon={
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                } />
                <KpiCard label="Usuarios" value={metricas.usuarios_total} icon={
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                } />
                <KpiCard label="Empresas" value={metricas.empresas_total} icon={
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
                } />
                <KpiCard label="Pendentes" value={metricas.usuarios_pendentes_global} icon={
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                } />
              </div>

              {/* plano bars */}
              <div>
                <h3 className="text-sm font-bold text-indigo-600 dark:text-indigo-400 mb-3">Escritorios por Plano</h3>
                <div className="space-y-3">
                  {Object.entries(metricas.escritorios_por_plano || {}).map(([plano, count]) => {
                    const maxVal = Math.max(...Object.values(metricas.escritorios_por_plano || {}), 1);
                    const pct = (count / maxVal) * 100;
                    const pl = PLANOS[plano] || PLANOS.trial;
                    return (
                      <div key={plano}>
                        <div className="flex items-center justify-between mb-1">
                          <span className={`text-xs font-semibold capitalize ${pl.cor}`}>{plano}</span>
                          <span className="text-xs text-slate-400 dark:text-slate-500">{count}</span>
                        </div>
                        <div className="h-3 rounded-full bg-slate-200 dark:bg-slate-700/60 overflow-hidden">
                          <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-500" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* ranking */}
              <div>
                <h3 className="text-sm font-bold text-indigo-600 dark:text-indigo-400 mb-3">Ranking por Empresas</h3>
                <div className={`${glassCard} overflow-hidden`}>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700/50 bg-slate-50 dark:bg-slate-800/50">
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">#</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">Escritorio</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">Plano</th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">Empresas</th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">Usuarios</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...escritorios].sort((a, b) => b.empresas_count - a.empresas_count).slice(0, 10).map((e, i) => {
                        const pl = PLANOS[e.plano] || PLANOS.trial;
                        return (
                          <tr key={e.id} className="border-b border-slate-100 dark:border-slate-700/30 hover:bg-slate-50 dark:hover:bg-slate-700/20 transition-colors">
                            <td className="px-4 py-2.5 text-slate-400 dark:text-slate-500 font-bold">{i + 1}</td>
                            <td className="px-4 py-2.5">
                              <span className="font-semibold text-slate-900 dark:text-slate-100">{e.nome}</span>
                              <span className="text-slate-400 dark:text-slate-500 ml-1 text-xs">@{e.slug}</span>
                            </td>
                            <td className="px-4 py-2.5"><Badge className={`${pl.bg} ${pl.cor} border`}>{e.plano}</Badge></td>
                            <td className="px-4 py-2.5 text-right font-bold text-slate-900 dark:text-slate-100">{e.empresas_count}</td>
                            <td className="px-4 py-2.5 text-right text-slate-500 dark:text-slate-400">{e.usuarios_count}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* ====== MODAL: CRIAR ESCRITORIO ====== */}
      {showCriar && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" onClick={() => setShowCriar(false)}>
          <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl" onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Novo Escritório</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Configure um novo escritório de contabilidade na plataforma</p>
                </div>
                <button onClick={() => setShowCriar(false)} className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400 transition-colors">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
              </div>
            </div>

            <div className="p-6 space-y-5">
              {/* Section: Dados do Escritório */}
              <div className="flex items-center gap-3">
                <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700/50" />
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Dados do escritório</span>
                <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700/50" />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1.5">Nome do escritório *</label>
                <input value={formNome} onChange={e => { setFormNome(e.target.value); if (!slugManuallyEdited.current) setFormSlug(generateSlug(e.target.value)); }} placeholder="Ex: Contabilidade João Silva" className={inputCls} />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1.5">Código do escritório *</label>
                <input value={formSlug} onChange={e => handleSlugManualChange(e.target.value)} placeholder="Ex: joaosilva (sem espaços ou acentos)" className={`${inputCls} font-mono`} />
                {formSlug && (
                  <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-1">
                    Usuários farão login como <span className="font-mono text-indigo-600 dark:text-indigo-400">usuario@{formSlug}</span>
                  </p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1.5">CNPJ (opcional)</label>
                  <input value={formCnpj} onChange={e => setFormCnpj(e.target.value)} placeholder="00.000.000/0000-00" className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1.5">Telefone (opcional)</label>
                  <input value={formTelefone} onChange={e => setFormTelefone(e.target.value)} placeholder="(00) 00000-0000" className={inputCls} />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1.5">E-mail de contato (opcional)</label>
                  <input value={formEmail} onChange={e => setFormEmail(e.target.value)} placeholder="contato@escritorio.com" className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1.5">Responsável (opcional)</label>
                  <input value={formResponsavel} onChange={e => setFormResponsavel(e.target.value)} placeholder="João Silva" className={inputCls} />
                </div>
              </div>

              {/* Section: Plano de Acesso */}
              <div className="flex items-center gap-3 pt-2">
                <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700/50" />
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Plano de acesso</span>
                <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700/50" />
              </div>

              <div className="space-y-2">
                {PLANOS_CONFIG.map(p => (
                  <div key={p.id}
                    onClick={() => setFormPlano(p.id)}
                    className={`flex items-center justify-between p-4 rounded-xl cursor-pointer transition-all border ${
                      formPlano === p.id
                        ? "border-indigo-500 bg-indigo-500/5 dark:bg-indigo-500/10"
                        : "border-slate-200 dark:border-slate-700/50 hover:border-slate-300 dark:hover:border-slate-600"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                        formPlano === p.id ? "border-indigo-500" : "border-slate-300 dark:border-slate-600"
                      }`}>
                        {formPlano === p.id && <div className="w-2 h-2 rounded-full bg-indigo-500" />}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{p.nome}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {p.empresas.toLocaleString("pt-BR")} empresas · {p.usuarios} usuários · {p.descricao}
                        </p>
                      </div>
                    </div>
                    {p.badge && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-semibold">
                        {p.badge}
                      </span>
                    )}
                  </div>
                ))}
              </div>

              {/* Custom limits */}
              <div>
                <p className="text-xs text-slate-400 dark:text-slate-500 mb-2">Personalizar limites (preenchidos pelo plano selecionado)</p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1.5">Máx. empresas</label>
                    <input type="number" value={formMaxEmpresas} onChange={e => setFormMaxEmpresas(Number(e.target.value))} className={inputCls} />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1.5">Máx. usuários</label>
                    <input type="number" value={formMaxUsuarios} onChange={e => setFormMaxUsuarios(Number(e.target.value))} className={inputCls} />
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                <button onClick={() => setShowCriar(false)} className={btnSecondary + " flex-1"}>Cancelar</button>
                <button onClick={criarEscritorio} disabled={!formNome || !formSlug} className={`${btnPrimary} flex-1 disabled:opacity-40 disabled:cursor-not-allowed`}>Criar Escritório</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ====== MODAL: ESCRITORIO CRIADO ====== */}
      {criadoSlug && (
        <Modal open={true} onClose={() => setCriadoSlug("")} title="Escritório Criado">
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20">
              <svg className="w-5 h-5 text-emerald-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              <p className="text-sm text-emerald-700 dark:text-emerald-300 font-medium">Escritório criado com sucesso!</p>
            </div>
            <div className="space-y-2">
              <p className="text-sm text-slate-600 dark:text-slate-300">
                <span className="font-semibold">Código:</span> <code className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-sm font-mono">{criadoSlug}</code>
              </p>
              <div className="mt-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600">
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">Instruções para o responsável:</p>
                <ol className="text-sm text-slate-600 dark:text-slate-300 space-y-1 list-decimal list-inside">
                  <li>Acesse a tela de login do Controllo</li>
                  <li>Clique em &quot;Solicitar Acesso&quot;</li>
                  <li>Digite o código do escritório: <strong>{criadoSlug}</strong></li>
                  <li>Crie seu nome de usuário e senha</li>
                  <li>Aguarde aprovação</li>
                </ol>
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(`Acesse o Controllo e solicite acesso com o código: ${criadoSlug}\n\n1. Abra a tela de login\n2. Clique em "Solicitar Acesso"\n3. Digite o código: ${criadoSlug}\n4. Crie seu usuário e senha\n5. Aguarde aprovação`);
                  show("Instruções copiadas!", "sucesso");
                }}
                className="flex-1 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white transition-colors"
              >
                Copiar instruções
              </button>
              <button onClick={() => setCriadoSlug("")} className="flex-1 py-2.5 rounded-xl text-sm font-semibold border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                Fechar
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* ====== MODAL: EDITAR ESCRITORIO ====== */}
      <Modal open={!!editEsc} onClose={() => setEditEsc(null)} title={`Gerenciar: ${editEsc?.nome || ""}`}>
        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1 block">Nome</label>
            <input value={editNome} onChange={e => setEditNome(e.target.value)} className={inputCls} />
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1 block">Plano</label>
            <select value={editPlano} onChange={e => handlePlanoChange(e.target.value, "edit")} className={inputCls}>
              <option value="trial">Trial</option>
              <option value="basico">Basico</option>
              <option value="profissional">Profissional</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1 block">Max Empresas</label>
              <input type="number" value={editMaxEmpresas} onChange={e => setEditMaxEmpresas(Number(e.target.value))} className={inputCls} />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1 block">Max Usuarios</label>
              <input type="number" value={editMaxUsuarios} onChange={e => setEditMaxUsuarios(Number(e.target.value))} className={inputCls} />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => setEditEsc(null)} className="px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 text-sm font-semibold transition-colors">Cancelar</button>
            <button onClick={salvarEdicao} className={btnPrimary}>Salvar</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
