"use client";
import { useEffect, useState, useMemo, useRef, useCallback } from "react";

const API = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  .replace(/\/api\/?$/, "").replace(/\/$/, "");

interface TarefaEquipe {
  id: number;
  titulo: string;
  descricao: string;
  prioridade: string;
  categoria: string;
  data_entrega: string;
  hora: string;
  concluida: boolean;
  criador_id: number;
}

type Prioridade = "baixa" | "media" | "alta" | "urgente";
type Categoria  = "geral" | "financeiro" | "cliente" | "reuniao" | "prazo";

interface Subtarefa {
  id: string;
  titulo: string;
  concluida: boolean;
}

interface Tarefa {
  id: string;
  titulo: string;
  descricao: string;
  responsavel: string;
  prioridade: Prioridade;
  categoria: Categoria;
  hora: string;
  concluida: boolean;
  criadaEm: number;
  subtarefas?: Subtarefa[];
}

const PRIO: Record<Prioridade, { label: string; dot: string; bg: string; border: string; color: string; accent: string; glow: string }> = {
  urgente: { label: "Urgente", dot: "#f43f5e", bg: "bg-rose-500/10",  border: "border-rose-500/25",  color: "text-rose-400",  accent: "#f43f5e", glow: "rgba(244,63,94,0.12)"  },
  alta:    { label: "Alta",    dot: "#f59e0b", bg: "bg-amber-500/10", border: "border-amber-500/25", color: "text-amber-400", accent: "#f59e0b", glow: "rgba(245,158,11,0.12)" },
  media:   { label: "Média",   dot: "#3b82f6", bg: "bg-blue-500/10",  border: "border-blue-500/25",  color: "text-blue-400",  accent: "#3b82f6", glow: "rgba(59,130,246,0.12)"  },
  baixa:   { label: "Baixa",   dot: "#64748b", bg: "bg-slate-500/10", border: "border-slate-500/25", color: "text-slate-400", accent: "#64748b", glow: "rgba(100,116,139,0.06)" },
};

const PRIO_SECTION_LABELS: Record<Prioridade, string> = {
  urgente: "URGENTE",
  alta: "ALTA",
  media: "NORMAL",
  baixa: "BAIXA",
};

const CAT: Record<Categoria, { label: string; color: string }> = {
  geral:       { label: "Geral",       color: "#3b6ea5" },
  financeiro:  { label: "Financeiro",  color: "#10b981" },
  cliente:     { label: "Cliente",     color: "#f59e0b" },
  reuniao:     { label: "Reuniao",     color: "#8b5cf6" },
  prazo:       { label: "Prazo",       color: "#f43f5e" },
};

const STORAGE_KEY = "controllo_tarefas_v2";

function load(): Tarefa[] {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]"); } catch { return []; }
}
function save(t: Tarefa[]) { localStorage.setItem(STORAGE_KEY, JSON.stringify(t)); }

function dataHoje() {
  return new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

// -- CAT ICON (SVG, no emojis) --
function CatIcon({ cat, size = 14 }: { cat: Categoria; size?: number }) {
  const s = size;
  switch (cat) {
    case "financeiro": return (
      <svg width={s} height={s} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    );
    case "cliente": return (
      <svg width={s} height={s} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    );
    case "reuniao": return (
      <svg width={s} height={s} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    );
    case "prazo": return (
      <svg width={s} height={s} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    );
    default: return (
      <svg width={s} height={s} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
    );
  }
}

export default function TarefasPage() {
  const [tarefas,     setTarefas]     = useState<Tarefa[]>([]);
  const [filtro,      setFiltro]      = useState<"todas" | "pendentes" | "concluidas">("pendentes");
  const [filtroCat,   setFiltroCat]   = useState<Categoria | "todas">("todas");
  const [modalAberto, setModalAberto] = useState(false);
  const [editando,    setEditando]    = useState<Tarefa | null>(null);
  const [quickAdd,    setQuickAdd]    = useState("");
  const [confirmarExclusao, setConfirmarExclusao] = useState<string | null>(null);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const [novaSubtarefa, setNovaSubtarefa] = useState("");
  const quickRef = useRef<HTMLInputElement>(null);

  // Tarefas designadas pela equipe (backend)
  const [tarefasEquipe, setTarefasEquipe] = useState<TarefaEquipe[]>([]);

  // Form
  const [titulo,      setTitulo]      = useState("");
  const [descricao,   setDescricao]   = useState("");
  const [responsavel, setResponsavel] = useState("");
  const [prioridade,  setPrioridade]  = useState<Prioridade>("media");
  const [categoria,   setCategoria]   = useState<Categoria>("geral");
  const [hora,        setHora]        = useState("");

  useEffect(() => { setTarefas(load()); }, []);

  const carregarTarefasEquipe = useCallback(async () => {
    const t = localStorage.getItem("controllo_token");
    if (!t) return;
    try {
      const res = await fetch(`${API}/api/equipe/minhas-tarefas`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (res.ok) setTarefasEquipe(await res.json());
    } catch { /* silencioso */ }
  }, []);

  useEffect(() => { carregarTarefasEquipe(); }, [carregarTarefasEquipe]);

  const concluirTarefaEquipe = async (tarefa: TarefaEquipe) => {
    const t = localStorage.getItem("controllo_token");
    if (!t) return;
    try {
      await fetch(`${API}/api/equipe/minhas-tarefas/${tarefa.id}/concluir`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${t}` },
      });
      await carregarTarefasEquipe();
    } catch { /* silencioso */ }
  };

  function persist(nova: Tarefa[]) { setTarefas(nova); save(nova); }

  function abrirNova() {
    setEditando(null); setTitulo(""); setDescricao(""); setResponsavel("");
    setPrioridade("media"); setCategoria("geral"); setHora("");
    setModalAberto(true);
  }

  function abrirEditar(t: Tarefa) {
    setEditando(t); setTitulo(t.titulo); setDescricao(t.descricao ?? "");
    setResponsavel(t.responsavel); setPrioridade(t.prioridade);
    setCategoria(t.categoria ?? "geral"); setHora(t.hora);
    setModalAberto(true);
  }

  function salvar(e: React.SyntheticEvent) {
    e.preventDefault();
    if (!titulo.trim()) return;
    if (editando) {
      persist(tarefas.map(t => t.id === editando.id
        ? { ...t, titulo, descricao, responsavel, prioridade, categoria, hora }
        : t
      ));
    } else {
      persist([{ id: crypto.randomUUID(), titulo, descricao, responsavel, prioridade, categoria, hora, concluida: false, criadaEm: Date.now() }, ...tarefas]);
    }
    setModalAberto(false);
  }

  function handleQuickAdd(e: React.KeyboardEvent) {
    if (e.key !== "Enter" || !quickAdd.trim()) return;
    persist([{ id: crypto.randomUUID(), titulo: quickAdd.trim(), descricao: "", responsavel: "", prioridade: "media", categoria: "geral", hora: "", concluida: false, criadaEm: Date.now() }, ...tarefas]);
    setQuickAdd("");
  }

  function doQuickAdd() {
    if (!quickAdd.trim()) return;
    persist([{ id: crypto.randomUUID(), titulo: quickAdd.trim(), descricao: "", responsavel: "", prioridade: "media", categoria: "geral", hora: "", concluida: false, criadaEm: Date.now() }, ...tarefas]);
    setQuickAdd("");
  }

  const [alertaSubtarefas, setAlertaSubtarefas] = useState<string | null>(null);

  function toggleConcluida(id: string) {
    const tarefa = tarefas.find(t => t.id === id);
    if (!tarefa) return;
    // Se tentando marcar como concluida e tem subtarefas pendentes, pedir confirmacao
    if (!tarefa.concluida && (tarefa.subtarefas ?? []).length > 0) {
      const pendentes = (tarefa.subtarefas ?? []).filter(s => !s.concluida).length;
      if (pendentes > 0) {
        setAlertaSubtarefas(id);
        return;
      }
    }
    persist(tarefas.map(t => t.id === id ? { ...t, concluida: !t.concluida } : t));
  }

  function forcarConclusao(id: string) {
    // Marca todas as subtarefas como concluidas + a tarefa principal
    persist(tarefas.map(t => t.id === id
      ? { ...t, concluida: true, subtarefas: (t.subtarefas ?? []).map(s => ({ ...s, concluida: true })) }
      : t
    ));
    setAlertaSubtarefas(null);
  }

  function remover(id: string) {
    setConfirmarExclusao(id);
  }

  function removerConfirmado() {
    persist(tarefas.filter(t => t.id !== confirmarExclusao));
    setConfirmarExclusao(null);
  }

  function limparConcluidas() {
    persist(tarefas.filter(t => !t.concluida));
  }

  function adicionarSubtarefa(tarefaId: string, titulo: string) {
    if (!titulo.trim()) return;
    persist(tarefas.map(t => t.id === tarefaId
      ? { ...t, subtarefas: [...(t.subtarefas ?? []), { id: crypto.randomUUID(), titulo: titulo.trim(), concluida: false }] }
      : t
    ));
  }

  function toggleSubtarefa(tarefaId: string, subId: string) {
    persist(tarefas.map(t => t.id === tarefaId
      ? { ...t, subtarefas: (t.subtarefas ?? []).map(s => s.id === subId ? { ...s, concluida: !s.concluida } : s) }
      : t
    ));
  }

  function removerSubtarefa(tarefaId: string, subId: string) {
    persist(tarefas.map(t => t.id === tarefaId
      ? { ...t, subtarefas: (t.subtarefas ?? []).filter(s => s.id !== subId) }
      : t
    ));
  }

  function moverSubtarefa(tarefaId: string, subId: string, direcao: "up" | "down") {
    persist(tarefas.map(t => {
      if (t.id !== tarefaId) return t;
      const subs = [...(t.subtarefas ?? [])];
      const idx = subs.findIndex(s => s.id === subId);
      if (idx < 0) return t;
      const novoIdx = direcao === "up" ? idx - 1 : idx + 1;
      if (novoIdx < 0 || novoIdx >= subs.length) return t;
      [subs[idx], subs[novoIdx]] = [subs[novoIdx], subs[idx]];
      return { ...t, subtarefas: subs };
    }));
  }

  const pendentes  = tarefas.filter(t => !t.concluida).length;
  const concluidas = tarefas.filter(t =>  t.concluida).length;
  const urgentes   = tarefas.filter(t => !t.concluida && t.prioridade === "urgente").length;
  const total      = tarefas.length;
  const progresso  = total > 0 ? Math.round((concluidas / total) * 100) : 0;

  const visiveis = useMemo(() => {
    let lista = tarefas;
    if (filtro === "pendentes")  lista = lista.filter(t => !t.concluida);
    if (filtro === "concluidas") lista = lista.filter(t =>  t.concluida);
    if (filtroCat !== "todas")   lista = lista.filter(t => t.categoria === filtroCat);
    const ordem: Record<Prioridade, number> = { urgente: 0, alta: 1, media: 2, baixa: 3 };
    return [...lista].sort((a, b) => {
      if (a.concluida !== b.concluida) return a.concluida ? 1 : -1;
      const pd = ordem[a.prioridade] - ordem[b.prioridade];
      if (pd !== 0) return pd;
      if (a.hora && b.hora) return a.hora.localeCompare(b.hora);
      return a.criadaEm - b.criadaEm;
    });
  }, [tarefas, filtro, filtroCat]);

  // Group tasks by priority
  const grupos = useMemo(() => {
    const order: Prioridade[] = ["urgente", "alta", "media", "baixa"];
    return order.map(prio => ({
      prioridade: prio,
      tarefas: visiveis.filter(t => t.prioridade === prio),
    })).filter(g => g.tarefas.length > 0);
  }, [visiveis]);

  const catsAtivas = useMemo(
    () => [...new Set(tarefas.map(t => t.categoria ?? "geral"))] as Categoria[],
    [tarefas]
  );

  // -- LABEL STYLES --
  const labelStyle: React.CSSProperties = {
    display: "block",
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    color: "var(--text-muted)",
    marginBottom: 6,
  };

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "10px 14px",
    borderRadius: 12,
    background: "var(--bg-secondary)",
    border: "1px solid var(--border)",
    color: "var(--text-primary)",
    fontSize: 13,
    outline: "none",
    transition: "border-color 0.2s, box-shadow 0.2s",
  };

  return (
    <div className="min-h-full" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>

      {/* -- HEADER STRIP -- */}
      <div className="relative overflow-hidden border-b border-slate-200 dark:border-slate-700/60">
        {/* Radial glow */}
        <div className="absolute inset-0 pointer-events-none" style={{
          background: "radial-gradient(ellipse 60% 80% at 0% 0%, rgba(16,42,67,0.06), transparent 70%)",
        }} />

        <div className="relative px-6 pt-7 pb-6">
          {/* Title row */}
          <div className="flex items-start justify-between mb-5">
            <div className="flex items-center gap-4">
              <div className="w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0" style={{
                background: "linear-gradient(135deg, #102a43, #1e3a5f)",
                border: "1px solid rgba(16,42,67,0.20)",
                boxShadow: "0 4px 16px rgba(16,42,67,0.20)",
              }}>
                <svg className="w-5 h-5" style={{ color: "#3b6ea5" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-extrabold tracking-tight leading-tight">
                  Tarefas <span style={{ color: "#3b6ea5" }}>do Dia</span>
                </h1>
                <p className="text-sm mt-0.5 capitalize" style={{ color: "var(--text-secondary)" }}>
                  {dataHoje()}
                </p>
              </div>
            </div>

            <button
              onClick={abrirNova}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-white text-sm font-semibold transition-all active:scale-95"
              style={{
                background: "linear-gradient(135deg, #102a43, #1e3a5f)",
                boxShadow: "0 4px 16px rgba(16,42,67,0.25)",
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 6px 24px rgba(16,42,67,0.40)"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 4px 16px rgba(16,42,67,0.25)"; }}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
              </svg>
              Nova Tarefa
            </button>
          </div>

          {/* Stats pills + progress */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Metric pills */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl" style={{
              background: "rgba(16,42,67,0.06)",
              border: "1px solid rgba(16,42,67,0.12)",
            }}>
              <span className="text-xs font-bold tabular-nums" style={{ color: "#486581" }}>{total}</span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>total</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl" style={{
              background: pendentes > 0 ? "rgba(16,42,67,0.06)" : "rgba(16,185,129,0.08)",
              border: pendentes > 0 ? "1px solid rgba(16,42,67,0.12)" : "1px solid rgba(16,185,129,0.18)",
            }}>
              <span className="text-xs font-bold tabular-nums" style={{ color: pendentes > 0 ? "#486581" : "#10b981" }}>{pendentes}</span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>pendentes</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl" style={{
              background: "rgba(16,185,129,0.08)",
              border: "1px solid rgba(16,185,129,0.15)",
            }}>
              <span className="text-xs font-bold tabular-nums" style={{ color: "#10b981" }}>{concluidas}</span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>concluidas</span>
            </div>
            {urgentes > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl" style={{
                background: "rgba(244,63,94,0.10)",
                border: "1px solid rgba(244,63,94,0.22)",
              }}>
                <svg className="w-3 h-3" style={{ color: "#f43f5e" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <span className="text-xs font-bold tabular-nums" style={{ color: "#f43f5e" }}>{urgentes}</span>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>urgente{urgentes !== 1 ? "s" : ""}</span>
              </div>
            )}

            {/* Progress bar */}
            <div className="flex items-center gap-2.5 ml-1">
              <div className="h-1.5 w-36 rounded-full overflow-hidden" style={{ background: "rgba(16,42,67,0.10)" }}>
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${progresso}%`,
                    background: progresso === 100
                      ? "linear-gradient(90deg, #10b981, #059669)"
                      : "linear-gradient(90deg, #102a43, #486581)",
                    boxShadow: progresso > 0 ? `0 0 8px ${progresso === 100 ? "rgba(16,185,129,0.5)" : "rgba(16,42,67,0.3)"}` : "none",
                  }}
                />
              </div>
              <span className="text-xs font-bold tabular-nums" style={{ color: progresso === 100 ? "#10b981" : "#486581" }}>
                {progresso}%
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="px-6 py-5 space-y-4">

        {/* -- QUICK ADD -- */}
        <div
          className="flex items-center gap-3 px-4 py-3 rounded-2xl transition-all group"
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
          }}
        >
          <div className="w-5 h-5 rounded-md border-2 flex-shrink-0 transition-colors" style={{ borderColor: "rgba(16,42,67,0.25)" }} />
          <input
            ref={quickRef}
            value={quickAdd}
            onChange={e => setQuickAdd(e.target.value)}
            onKeyDown={handleQuickAdd}
            placeholder="Adicionar tarefa rapida... (Enter para salvar)"
            className="flex-1 bg-transparent text-sm focus:outline-none"
            style={{ color: "var(--text-primary)" }}
          />
          {quickAdd ? (
            <button
              onClick={doQuickAdd}
              className="flex-shrink-0 text-xs font-bold px-3 py-1.5 rounded-lg transition-all active:scale-95"
              style={{
                background: "linear-gradient(135deg, #102a43, #1e3a5f)",
                color: "white",
                boxShadow: "0 2px 8px rgba(16,42,67,0.25)",
              }}
            >
              Adicionar
            </button>
          ) : (
            <kbd className="text-[10px] px-2 py-0.5 rounded-md font-mono flex-shrink-0" style={{
              background: "rgba(16,42,67,0.07)",
              color: "#486581",
              border: "1px solid rgba(16,42,67,0.12)",
            }}>
              Enter
            </kbd>
          )}
        </div>

        {/* -- FILTROS -- */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2 flex-wrap">
            {/* Status pills */}
            <div className="flex gap-1 p-1 rounded-xl" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              {([
                { key: "pendentes",  label: "Pendentes"  },
                { key: "todas",      label: "Todas"       },
                { key: "concluidas", label: "Concluidas" },
              ] as const).map(f => (
                <button
                  key={f.key}
                  onClick={() => setFiltro(f.key)}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all active:scale-95"
                  style={filtro === f.key
                    ? { background: "linear-gradient(135deg, #102a43, #1e3a5f)", color: "white", boxShadow: "0 2px 8px rgba(16,42,67,0.20)" }
                    : { color: "var(--text-muted)" }
                  }
                >
                  {f.label}
                </button>
              ))}
            </div>

            {/* Category pills */}
            {catsAtivas.length > 1 && (
              <div className="flex gap-1.5 flex-wrap">
                <button
                  onClick={() => setFiltroCat("todas")}
                  className="px-3 py-1.5 rounded-xl text-xs font-semibold transition-all active:scale-95"
                  style={filtroCat === "todas"
                    ? { background: "rgba(16,42,67,0.08)", color: "#486581", border: "1px solid rgba(16,42,67,0.15)" }
                    : { background: "var(--bg-card)", color: "var(--text-muted)", border: "1px solid var(--border)" }
                  }
                >
                  Todas
                </button>
                {catsAtivas.map(cat => (
                  <button
                    key={cat}
                    onClick={() => setFiltroCat(cat)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all active:scale-95"
                    style={filtroCat === cat
                      ? { background: `${CAT[cat].color}18`, color: CAT[cat].color, border: `1px solid ${CAT[cat].color}35`, boxShadow: `0 0 10px ${CAT[cat].color}18` }
                      : { background: "var(--bg-card)", color: "var(--text-muted)", border: "1px solid var(--border)" }
                    }
                  >
                    <span style={{ color: filtroCat === cat ? CAT[cat].color : "var(--text-muted)" }}>
                      <CatIcon cat={cat} size={12} />
                    </span>
                    {CAT[cat].label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {concluidas > 0 && (
            <button
              onClick={limparConcluidas}
              className="text-xs font-semibold px-3 py-1.5 rounded-xl transition-all hover:bg-rose-500/10 hover:text-rose-400 active:scale-95"
              style={{ color: "var(--text-muted)", border: "1px solid var(--border)" }}
            >
              Limpar concluidas
            </button>
          )}
        </div>

        {/* -- TAREFAS DESIGNADAS PELA EQUIPE -- */}
        {tarefasEquipe.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "#a78bfa" }}>
                Designadas pelo gestor
              </span>
              <div className="flex-1 h-px" style={{ background: "rgba(167,139,250,0.2)" }} />
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                style={{ background: "rgba(167,139,250,0.12)", color: "#a78bfa" }}>
                {tarefasEquipe.filter(t => !t.concluida).length} pendentes
              </span>
            </div>
            <div className="space-y-2">
              {tarefasEquipe.map(t => (
                <div key={t.id}
                  className="flex items-start gap-3 px-4 py-3 rounded-xl transition-all"
                  style={{
                    background: t.concluida ? "rgba(167,139,250,0.04)" : "rgba(167,139,250,0.08)",
                    border: `1px solid ${t.concluida ? "rgba(167,139,250,0.15)" : "rgba(167,139,250,0.25)"}`,
                    opacity: t.concluida ? 0.65 : 1,
                  }}>
                  <button
                    onClick={() => concluirTarefaEquipe(t)}
                    className="flex-shrink-0 mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all"
                    style={{ borderColor: t.concluida ? "#a78bfa" : "rgba(167,139,250,0.5)", background: t.concluida ? "#a78bfa" : "transparent" }}>
                    {t.concluida && (
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </button>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-semibold ${t.concluida ? "line-through" : ""}`}
                      style={{ color: t.concluida ? "var(--text-muted)" : "var(--text-primary)" }}>
                      {t.titulo}
                    </p>
                    {t.descricao && (
                      <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{t.descricao}</p>
                    )}
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      {t.categoria && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: "rgba(167,139,250,0.15)", color: "#a78bfa" }}>
                          {t.categoria}
                        </span>
                      )}
                      {t.data_entrega && (
                        <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                          {t.data_entrega} {t.hora}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* -- LISTA -- */}
        {visiveis.length === 0 ? (
          /* Empty state */
          filtro === "pendentes" ? (
            <div className="flex flex-col items-center justify-center py-24 rounded-2xl border border-dashed" style={{ borderColor: "var(--border)" }}>
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
                style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.18)" }}>
                <svg className="w-7 h-7 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-sm font-bold mb-1.5" style={{ color: "var(--text-secondary)" }}>
                Dia livre de pendências!
              </p>
              <p className="text-xs mb-6 text-center max-w-xs" style={{ color: "var(--text-muted)" }}>
                Todas as tarefas foram concluídas. Aproveite para revisar as empresas com alertas pendentes.
              </p>
              <a href="/carteiras"
                className="flex items-center gap-2 text-xs font-semibold px-4 py-2.5 rounded-xl transition-all"
                style={{ background: "rgba(16,42,67,0.08)", color: "#486581", border: "1px solid rgba(16,42,67,0.15)" }}>
                Ver empresas na carteira
              </a>
            </div>
          ) : (
            <div
              className="flex flex-col items-center justify-center py-24 rounded-2xl border border-dashed border-slate-300 dark:border-slate-700"
            >
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
                style={{
                  background: "rgba(16,42,67,0.06)",
                  border: "1px solid rgba(16,42,67,0.12)",
                }}
              >
                <svg className="w-7 h-7" style={{ color: "#3b6ea5", opacity: 0.6 }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
              </div>
              <p className="text-sm font-bold mb-1.5" style={{ color: "var(--text-secondary)" }}>
                {filtro === "concluidas" ? "Nenhuma tarefa concluida ainda" : "Nenhuma tarefa encontrada"}
              </p>
              <p className="text-xs mb-6" style={{ color: "var(--text-muted)" }}>
                {filtro === "concluidas" ? "Conclua tarefas para ve-las aqui" : "Use o campo acima ou crie uma tarefa detalhada"}
              </p>
              {filtro !== "concluidas" && (
                <button
                  onClick={abrirNova}
                  className="flex items-center gap-1.5 text-xs font-semibold px-4 py-2.5 rounded-xl transition-all active:scale-95"
                  style={{
                    background: "linear-gradient(135deg, #102a43, #1e3a5f)",
                    color: "white",
                    boxShadow: "0 4px 16px rgba(16,42,67,0.25)",
                  }}
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
                  </svg>
                  Criar primeira tarefa
                </button>
              )}
            </div>
          )
        ) : (
          <div>
            {grupos.map(grupo => {
              const p = PRIO[grupo.prioridade];
              return (
                <div key={grupo.prioridade}>
                  {/* Priority section header */}
                  <div className="flex items-center gap-2 mt-6 mb-3 first:mt-0">
                    <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: p.dot }}>
                      {PRIO_SECTION_LABELS[grupo.prioridade]}
                    </span>
                    <div className="flex-1 h-px" style={{ background: `${p.dot}25` }} />
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                      style={{ background: `${p.dot}12`, color: p.dot }}>
                      {grupo.tarefas.length}
                    </span>
                  </div>

                  {/* Tasks in this group */}
                  <div className="space-y-2.5">
                    {grupo.tarefas.map(t => {
                      const tp = PRIO[t.prioridade];
                      const cat = CAT[t.categoria ?? "geral"];
                      return (
                        <div
                          key={t.id}
                          className="group rounded-2xl overflow-hidden transition-all duration-200"
                          style={{
                            background: "var(--bg-card)",
                            border: `1px solid var(--border)`,
                            boxShadow: t.concluida ? "none" : `0 2px 16px ${tp.glow}`,
                            opacity: t.concluida ? 0.55 : 1,
                            transform: "translateY(0)",
                            transition: "all 0.2s ease",
                          }}
                          onMouseEnter={e => {
                            if (!t.concluida) {
                              (e.currentTarget as HTMLDivElement).style.transform = "translateY(-1px)";
                              (e.currentTarget as HTMLDivElement).style.boxShadow = `0 6px 24px ${tp.glow.replace("0.12", "0.20").replace("0.10", "0.18").replace("0.06", "0.10")}`;
                            }
                          }}
                          onMouseLeave={e => {
                            (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
                            (e.currentTarget as HTMLDivElement).style.boxShadow = t.concluida ? "none" : `0 2px 16px ${tp.glow}`;
                          }}
                        >
                          {/* Priority accent bar */}
                          <div
                            className="h-px"
                            style={{
                              background: t.concluida
                                ? "transparent"
                                : `linear-gradient(90deg, ${tp.accent}, transparent 70%)`,
                            }}
                          />

                          <div className="flex items-start gap-4 px-4 py-4">
                            {/* Left priority accent bar */}
                            <div
                              className="absolute left-0 top-0 bottom-0 w-0.5 rounded-full"
                              style={{ background: t.concluida ? "transparent" : tp.accent }}
                            />

                            {/* Checkbox */}
                            <button
                              onClick={() => toggleConcluida(t.id)}
                              className="mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all duration-200 active:scale-90"
                              style={t.concluida
                                ? { borderColor: "#10b981", background: "#10b981" }
                                : {
                                    borderColor: "rgba(16,42,67,0.25)",
                                    background: "transparent",
                                  }
                              }
                            >
                              {t.concluida && (
                                <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3.5} d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                            </button>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-start justify-between gap-2">
                                <p
                                  className={`text-sm font-semibold leading-snug cursor-pointer select-none ${t.concluida ? "line-through" : ""}`}
                                  style={{ color: t.concluida ? "var(--text-muted)" : "var(--text-primary)" }}
                                  onClick={() => abrirEditar(t)}
                                >
                                  {t.titulo}
                                </p>
                                <div className="flex items-center gap-1 flex-shrink-0">
                                  {/* [+] Subtask button - always visible */}
                                  <button
                                    onClick={(e) => { e.stopPropagation(); setExpandedTask(expandedTask === t.id ? null : t.id); }}
                                    className="p-1.5 rounded-lg transition-all hover:bg-slate-700/30 flex-shrink-0"
                                    style={{ color: "var(--text-muted)" }}
                                    title="Subtarefas"
                                  >
                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                                    </svg>
                                  </button>
                                  {/* Hover actions */}
                                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button
                                      onClick={() => abrirEditar(t)}
                                      className="p-1.5 rounded-lg transition-all"
                                      style={{ color: "var(--text-muted)" }}
                                      onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(59,130,246,0.10)"; (e.currentTarget as HTMLButtonElement).style.color = "#3b82f6"; }}
                                      onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = "transparent"; (e.currentTarget as HTMLButtonElement).style.color = "var(--text-muted)"; }}
                                    >
                                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                      </svg>
                                    </button>
                                    <button
                                      onClick={() => remover(t.id)}
                                      className="p-1.5 rounded-lg transition-all"
                                      style={{ color: "var(--text-muted)" }}
                                      onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(244,63,94,0.10)"; (e.currentTarget as HTMLButtonElement).style.color = "#f43f5e"; }}
                                      onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = "transparent"; (e.currentTarget as HTMLButtonElement).style.color = "var(--text-muted)"; }}
                                    >
                                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                      </svg>
                                    </button>
                                  </div>
                                </div>
                              </div>

                              {/* Description */}
                              {t.descricao && (
                                <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                                  {t.descricao}
                                </p>
                              )}

                              {/* Meta badges */}
                              <div className="flex items-center gap-2 mt-2.5 flex-wrap">
                                {/* Priority dot + label */}
                                <span
                                  className={`flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded-full border ${tp.bg} ${tp.border} ${tp.color}`}
                                >
                                  <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: tp.dot }} />
                                  {tp.label}
                                </span>

                                {/* Category */}
                                <span
                                  className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full"
                                  style={{ background: `${cat.color}12`, color: cat.color, border: `1px solid ${cat.color}28` }}
                                >
                                  <span style={{ color: cat.color }}><CatIcon cat={t.categoria ?? "geral"} size={10} /></span>
                                  {cat.label}
                                </span>

                                {t.responsavel && (
                                  <span className="flex items-center gap-1 text-[11px]" style={{ color: "var(--text-muted)" }}>
                                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                      <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                    </svg>
                                    {t.responsavel}
                                  </span>
                                )}

                                {t.hora && (
                                  <span className="flex items-center gap-1 text-[11px] font-mono" style={{ color: "var(--text-muted)" }}>
                                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    {t.hora}
                                  </span>
                                )}

                                {/* Subtask count indicator */}
                                {(t.subtarefas ?? []).length > 0 && (() => {
                                  const subs = t.subtarefas!;
                                  const done = subs.filter(s => s.concluida).length;
                                  const stotal = subs.length;
                                  const pct = Math.round((done / stotal) * 100);
                                  return (
                                    <span
                                      className="flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded-full cursor-pointer"
                                      style={{
                                        background: done === stotal ? "rgba(16,185,129,0.10)" : "rgba(16,42,67,0.06)",
                                        color: done === stotal ? "#10b981" : "#486581",
                                        border: `1px solid ${done === stotal ? "rgba(16,185,129,0.20)" : "rgba(16,42,67,0.12)"}`,
                                      }}
                                      onClick={(e) => { e.stopPropagation(); setExpandedTask(expandedTask === t.id ? null : t.id); }}
                                    >
                                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                                      </svg>
                                      {done}/{stotal} subtarefas
                                      {/* Mini progress bar */}
                                      <span className="inline-block w-10 h-1 rounded-full overflow-hidden ml-0.5" style={{ background: "rgba(16,42,67,0.10)" }}>
                                        <span className="block h-full rounded-full" style={{
                                          width: `${pct}%`,
                                          background: done === stotal ? "#10b981" : "#486581",
                                          transition: "width 0.3s ease",
                                        }} />
                                      </span>
                                    </span>
                                  );
                                })()}
                              </div>

                              {/* -- INLINE SUBTASKS (always visible) -- */}
                              {(t.subtarefas ?? []).length > 0 && (
                                <div className="mt-2 ml-7 space-y-1">
                                  {(t.subtarefas ?? []).map(sub => (
                                    <div key={sub.id} className="flex items-center gap-2">
                                      <span className="text-slate-600 dark:text-slate-500 text-xs select-none">{"\u2514\u2500"}</span>
                                      <button onClick={() => toggleSubtarefa(t.id, sub.id)}
                                        className="w-3.5 h-3.5 rounded border flex items-center justify-center flex-shrink-0 transition-all"
                                        style={sub.concluida ? { borderColor: "#10b981", background: "#10b981" } : { borderColor: "rgba(16,42,67,0.25)" }}>
                                        {sub.concluida && <svg className="w-2 h-2 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3.5} d="M5 13l4 4L19 7" /></svg>}
                                      </button>
                                      <span className={`text-xs ${sub.concluida ? "line-through text-slate-500" : "text-slate-300"}`}>
                                        {sub.titulo}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              )}

                              {/* -- EXPANDED SUBTASKS SECTION (add/reorder/remove) -- */}
                              {expandedTask === t.id && (
                                <div className="mt-3 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
                                  {/* Subtask list with management controls */}
                                  {(t.subtarefas ?? []).length > 0 && (
                                    <div className="space-y-1.5 mb-2.5">
                                      {(t.subtarefas ?? []).map(sub => (
                                        <div key={sub.id} className="flex items-center gap-2.5 group/sub px-1 py-1 rounded-lg transition-all hover:bg-white/5">
                                          <button
                                            onClick={() => toggleSubtarefa(t.id, sub.id)}
                                            className="w-4 h-4 rounded border-[1.5px] flex items-center justify-center flex-shrink-0 transition-all active:scale-90"
                                            style={sub.concluida
                                              ? { borderColor: "#10b981", background: "#10b981" }
                                              : { borderColor: "rgba(16,42,67,0.25)", background: "transparent" }
                                            }
                                          >
                                            {sub.concluida && (
                                              <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3.5} d="M5 13l4 4L19 7" />
                                              </svg>
                                            )}
                                          </button>
                                          <span
                                            className={`text-xs flex-1 ${sub.concluida ? "line-through" : ""}`}
                                            style={{ color: sub.concluida ? "var(--text-muted)" : "var(--text-secondary)" }}
                                          >
                                            {sub.titulo}
                                          </span>
                                          <div className="flex items-center gap-0.5 opacity-0 group-hover/sub:opacity-100 transition-opacity">
                                            <button onClick={() => moverSubtarefa(t.id, sub.id, "up")} title="Mover para cima"
                                              className="p-0.5 rounded transition-colors" style={{ color: "var(--text-muted)" }}
                                              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = "#3b6ea5"; }}
                                              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = "var(--text-muted)"; }}>
                                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
                                              </svg>
                                            </button>
                                            <button onClick={() => moverSubtarefa(t.id, sub.id, "down")} title="Mover para baixo"
                                              className="p-0.5 rounded transition-colors" style={{ color: "var(--text-muted)" }}
                                              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = "#3b6ea5"; }}
                                              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = "var(--text-muted)"; }}>
                                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                                              </svg>
                                            </button>
                                            <button onClick={() => removerSubtarefa(t.id, sub.id)} title="Remover subtarefa"
                                              className="p-0.5 rounded transition-colors" style={{ color: "var(--text-muted)" }}
                                              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = "#f43f5e"; }}
                                              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = "var(--text-muted)"; }}>
                                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                              </svg>
                                            </button>
                                          </div>
                                        </div>
                                      ))}

                                      {/* Subtask progress bar */}
                                      {(() => {
                                        const subs = t.subtarefas!;
                                        const done = subs.filter(s => s.concluida).length;
                                        const pct = Math.round((done / subs.length) * 100);
                                        return (
                                          <div className="flex items-center gap-2 mt-2 px-1">
                                            <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(16,42,67,0.10)" }}>
                                              <div className="h-full rounded-full transition-all duration-500" style={{
                                                width: `${pct}%`,
                                                background: done === subs.length
                                                  ? "linear-gradient(90deg, #10b981, #059669)"
                                                  : "linear-gradient(90deg, #102a43, #486581)",
                                              }} />
                                            </div>
                                            <span className="text-[10px] font-bold tabular-nums" style={{ color: done === subs.length ? "#10b981" : "#486581" }}>
                                              {done}/{subs.length}
                                            </span>
                                          </div>
                                        );
                                      })()}
                                    </div>
                                  )}

                                  {/* Add subtask input */}
                                  <div className="flex items-center gap-2 px-1">
                                    <input
                                      value={expandedTask === t.id ? novaSubtarefa : ""}
                                      onChange={e => setNovaSubtarefa(e.target.value)}
                                      onKeyDown={e => {
                                        if (e.key === "Enter" && novaSubtarefa.trim()) {
                                          adicionarSubtarefa(t.id, novaSubtarefa);
                                          setNovaSubtarefa("");
                                        }
                                      }}
                                      placeholder="Adicionar subtarefa..."
                                      className="flex-1 text-xs bg-transparent focus:outline-none py-1.5 px-2 rounded-lg"
                                      style={{
                                        color: "var(--text-primary)",
                                        background: "var(--bg-secondary)",
                                        border: "1px solid var(--border)",
                                      }}
                                    />
                                    <button
                                      onClick={() => { adicionarSubtarefa(t.id, novaSubtarefa); setNovaSubtarefa(""); }}
                                      className="text-[10px] font-bold px-2.5 py-1.5 rounded-lg transition-all active:scale-95 flex-shrink-0"
                                      style={{
                                        background: novaSubtarefa.trim() ? "linear-gradient(135deg, #102a43, #1e3a5f)" : "var(--bg-secondary)",
                                        color: novaSubtarefa.trim() ? "white" : "var(--text-muted)",
                                        border: novaSubtarefa.trim() ? "none" : "1px solid var(--border)",
                                      }}
                                    >
                                      + Adicionar
                                    </button>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* -- CONFIRM DELETE DIALOG -- */}
      {confirmarExclusao && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.70)", backdropFilter: "blur(8px)" }}>
          <div
            className="w-full max-w-sm rounded-3xl overflow-hidden shadow-2xl"
            style={{
              background: "var(--bg-card)",
              border: "1px solid rgba(244,63,94,0.20)",
              boxShadow: "0 30px 70px rgba(0,0,0,0.60), 0 0 0 1px rgba(244,63,94,0.08)",
            }}
          >
            {/* Dialog header */}
            <div className="px-6 pt-6 pb-4">
              <div
                className="w-11 h-11 rounded-2xl flex items-center justify-center mb-4"
                style={{ background: "rgba(244,63,94,0.10)", border: "1px solid rgba(244,63,94,0.22)" }}
              >
                <svg className="w-5 h-5 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </div>
              <h3 className="font-bold text-base mb-1" style={{ color: "var(--text-primary)" }}>Remover tarefa?</h3>
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                Esta tarefa sera removida permanentemente. Esta acao nao pode ser desfeita.
              </p>
            </div>
            <div className="flex gap-2 px-6 pb-6">
              <button
                onClick={() => setConfirmarExclusao(null)}
                className="flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all hover:bg-white/5 active:scale-95"
                style={{ border: "1px solid var(--border)", color: "var(--text-secondary)" }}
              >
                Cancelar
              </button>
              <button
                onClick={removerConfirmado}
                className="flex-1 py-2.5 rounded-xl text-white text-sm font-bold transition-all active:scale-95"
                style={{
                  background: "linear-gradient(135deg, #f43f5e, #be123c)",
                  boxShadow: "0 4px 14px rgba(244,63,94,0.35)",
                }}
              >
                Remover
              </button>
            </div>
          </div>
        </div>
      )}

      {/* -- ALERTA SUBTAREFAS PENDENTES -- */}
      {alertaSubtarefas && (() => {
        const tarefa = tarefas.find(t => t.id === alertaSubtarefas);
        const pendentesCount = (tarefa?.subtarefas ?? []).filter(s => !s.concluida).length;
        return (
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.70)", backdropFilter: "blur(8px)" }}>
            <div className="w-full max-w-sm rounded-3xl overflow-hidden shadow-2xl"
              style={{ background: "var(--bg-card)", border: "1px solid rgba(245,158,11,0.20)", boxShadow: "0 30px 70px rgba(0,0,0,0.60)" }}>
              <div className="px-6 pt-6 pb-4">
                <div className="w-11 h-11 rounded-2xl flex items-center justify-center mb-4"
                  style={{ background: "rgba(245,158,11,0.10)", border: "1px solid rgba(245,158,11,0.22)" }}>
                  <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <h3 className="font-bold text-base mb-1" style={{ color: "var(--text-primary)" }}>Subtarefas pendentes</h3>
                <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                  Esta tarefa tem <strong>{pendentesCount} subtarefa{pendentesCount > 1 ? "s" : ""} pendente{pendentesCount > 1 ? "s" : ""}</strong>. Deseja concluir mesmo assim?
                </p>
              </div>
              <div className="flex gap-2 px-6 pb-6">
                <button onClick={() => setAlertaSubtarefas(null)}
                  className="flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all"
                  style={{ border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                  Cancelar
                </button>
                <button onClick={() => forcarConclusao(alertaSubtarefas)}
                  className="flex-1 py-2.5 rounded-xl text-white text-sm font-bold transition-all"
                  style={{ background: "linear-gradient(135deg, #f59e0b, #d97706)", boxShadow: "0 4px 14px rgba(245,158,11,0.35)" }}>
                  Concluir tudo
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      {/* -- MODAL -- */}
      {modalAberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.75)", backdropFilter: "blur(12px)" }}>
          <div
            className="w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden"
            style={{
              background: "var(--bg-card)",
              border: "1px solid rgba(16,42,67,0.15)",
              boxShadow: "0 30px 80px rgba(0,0,0,0.40)",
            }}
          >
            {/* Modal header */}
            <div className="relative px-6 py-5 overflow-hidden bg-navy-50 dark:bg-navy-900/30 border-b border-navy-100 dark:border-navy-700/40">
              <div className="absolute inset-0 pointer-events-none" style={{
                background: "radial-gradient(ellipse at top left, rgba(16,42,67,0.06), transparent 60%)",
              }} />
              <div className="relative flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="w-9 h-9 rounded-xl flex items-center justify-center"
                    style={{ background: "rgba(16,42,67,0.10)", border: "1px solid rgba(16,42,67,0.18)" }}
                  >
                    <svg className="w-5 h-5" style={{ color: "#3b6ea5" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                  </div>
                  <div>
                    <h2 className="font-bold text-base" style={{ color: "var(--text-primary)" }}>
                      {editando ? "Editar Tarefa" : "Nova Tarefa"}
                    </h2>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {editando ? "Atualize os detalhes" : "Adicione detalhes da tarefa"}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setModalAberto(false)}
                  className="w-8 h-8 flex items-center justify-center rounded-xl transition-all hover:bg-white/5 active:scale-90"
                  style={{ color: "var(--text-muted)", border: "1px solid var(--border)" }}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <form onSubmit={salvar} className="p-6 space-y-4">
              {/* Titulo */}
              <div>
                <label style={labelStyle}>Titulo *</label>
                <input
                  value={titulo}
                  onChange={e => setTitulo(e.target.value)}
                  required
                  placeholder="O que precisa ser feito?"
                  style={inputStyle}
                  onFocus={e => { (e.target as HTMLInputElement).style.borderColor = "rgba(16,42,67,0.40)"; (e.target as HTMLInputElement).style.boxShadow = "0 0 0 3px rgba(16,42,67,0.06)"; }}
                  onBlur={e => { (e.target as HTMLInputElement).style.borderColor = "var(--border)"; (e.target as HTMLInputElement).style.boxShadow = "none"; }}
                />
              </div>

              {/* Descricao */}
              <div>
                <label style={labelStyle}>Descricao</label>
                <textarea
                  value={descricao}
                  onChange={e => setDescricao(e.target.value)}
                  rows={2}
                  placeholder="Detalhes, contexto ou instrucoes..."
                  style={{ ...inputStyle, resize: "none" }}
                  onFocus={e => { (e.target as HTMLTextAreaElement).style.borderColor = "rgba(16,42,67,0.40)"; (e.target as HTMLTextAreaElement).style.boxShadow = "0 0 0 3px rgba(16,42,67,0.06)"; }}
                  onBlur={e => { (e.target as HTMLTextAreaElement).style.borderColor = "var(--border)"; (e.target as HTMLTextAreaElement).style.boxShadow = "none"; }}
                />
              </div>

              {/* Categoria */}
              <div>
                <label style={labelStyle}>Categoria</label>
                <div className="grid grid-cols-5 gap-1.5">
                  {(Object.entries(CAT) as [Categoria, typeof CAT[Categoria]][]).map(([key, c]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setCategoria(key)}
                      className="py-2.5 rounded-xl text-[11px] font-semibold border transition-all active:scale-95 flex flex-col items-center gap-1"
                      style={categoria === key
                        ? { background: `${c.color}15`, borderColor: `${c.color}38`, color: c.color, boxShadow: `0 0 12px ${c.color}18` }
                        : { background: "var(--bg-secondary)", borderColor: "var(--border)", color: "var(--text-muted)" }
                      }
                    >
                      <span style={{ color: categoria === key ? c.color : "var(--text-muted)" }}>
                        <CatIcon cat={key} size={14} />
                      </span>
                      <span>{c.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Responsavel + Hora */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label style={labelStyle}>Atribuido a</label>
                  <input
                    value={responsavel}
                    onChange={e => setResponsavel(e.target.value)}
                    placeholder="Nome ou equipe"
                    style={inputStyle}
                    onFocus={e => { (e.target as HTMLInputElement).style.borderColor = "rgba(16,42,67,0.40)"; (e.target as HTMLInputElement).style.boxShadow = "0 0 0 3px rgba(16,42,67,0.06)"; }}
                    onBlur={e => { (e.target as HTMLInputElement).style.borderColor = "var(--border)"; (e.target as HTMLInputElement).style.boxShadow = "none"; }}
                  />
                </div>
                <div>
                  <label style={labelStyle}>Hora</label>
                  <input
                    type="time"
                    value={hora}
                    onChange={e => setHora(e.target.value)}
                    style={inputStyle}
                    onFocus={e => { (e.target as HTMLInputElement).style.borderColor = "rgba(16,42,67,0.40)"; (e.target as HTMLInputElement).style.boxShadow = "0 0 0 3px rgba(16,42,67,0.06)"; }}
                    onBlur={e => { (e.target as HTMLInputElement).style.borderColor = "var(--border)"; (e.target as HTMLInputElement).style.boxShadow = "none"; }}
                  />
                </div>
              </div>

              {/* Prioridade */}
              <div>
                <label style={labelStyle}>Prioridade</label>
                <div className="grid grid-cols-4 gap-2">
                  {(["baixa", "media", "alta", "urgente"] as Prioridade[]).map(p => {
                    const c = PRIO[p];
                    const sel = prioridade === p;
                    return (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setPrioridade(p)}
                        className={`py-2.5 rounded-xl text-xs font-bold border transition-all active:scale-95 ${sel ? `${c.bg} ${c.border} ${c.color}` : "hover:bg-white/5"}`}
                        style={!sel
                          ? { background: "var(--bg-secondary)", borderColor: "var(--border)", color: "var(--text-muted)" }
                          : sel ? { boxShadow: `0 0 12px ${c.glow}` } : undefined
                        }
                      >
                        <span className="flex items-center justify-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full" style={{ background: c.dot }} />
                          {c.label}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Buttons */}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setModalAberto(false)}
                  className="flex-1 py-3 rounded-xl text-sm font-semibold transition-all hover:bg-white/5 active:scale-95"
                  style={{ border: "1px solid var(--border)", color: "var(--text-secondary)" }}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 py-3 rounded-xl text-white text-sm font-bold transition-all active:scale-95"
                  style={{
                    background: "linear-gradient(135deg, #102a43, #1e3a5f)",
                    boxShadow: "0 4px 18px rgba(16,42,67,0.30)",
                  }}
                  onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 6px 24px rgba(16,42,67,0.40)"; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 4px 18px rgba(16,42,67,0.30)"; }}
                >
                  {editando ? "Salvar alteracoes" : "Criar Tarefa"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
