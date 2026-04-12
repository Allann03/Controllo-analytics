"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Badge, type BadgeVariant } from "@/components/ui";

const API = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  .replace(/\/api\/?$/, "").replace(/\/$/, "");

interface Colaborador {
  id: number;
  nome: string;
  nome_exibicao: string;
  cargo: string;
  is_admin: boolean;
  is_gestor: boolean;
  tarefas_pendentes: number;
}

interface TarefaEquipe {
  id: number;
  destinatario_id: number;
  criador_id: number;
  titulo: string;
  descricao: string;
  prioridade: "baixa" | "media" | "alta" | "urgente";
  categoria: string;
  data_entrega: string;
  hora: string;
  concluida: boolean;
  criado_em: string;
}

type FiltroTask = "todas" | "pendentes" | "urgentes" | "concluidas";

const PRIORIDADE_LABEL: Record<string, string> = {
  baixa: "Baixa", media: "Média", alta: "Alta", urgente: "Urgente",
};

const PRIORIDADE_VARIANT: Record<string, BadgeVariant> = {
  baixa: "muted", media: "warning", alta: "warning", urgente: "danger",
};

const PRIORIDADE_BORDER: Record<string, string> = {
  baixa:   "border-l-slate-300 dark:border-l-slate-600",
  media:   "border-l-amber-400 dark:border-l-amber-500",
  alta:    "border-l-orange-500 dark:border-l-orange-400",
  urgente: "border-l-red-500 dark:border-l-red-400",
};

function iniciais(nome: string) {
  return (nome || "?").split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();
}

function isVencida(data_entrega: string): boolean {
  if (!data_entrega) return false;
  return new Date(data_entrega) < new Date(new Date().toDateString());
}

function getWorkload(pendentes: number): { label: string; color: string; level: number } {
  if (pendentes === 0) return { label: "Ocioso", color: "#6b7280", level: 0 };
  if (pendentes <= 3) return { label: "Leve", color: "#10b981", level: 2 };
  if (pendentes <= 6) return { label: "Moderado", color: "#f59e0b", level: 3 };
  if (pendentes <= 9) return { label: "Alto", color: "#f97316", level: 4 };
  return { label: "Sobrecarregado", color: "#ef4444", level: 5 };
}

export default function GestorEquipePage() {
  const router = useRouter();
  const [colaboradores, setColaboradores] = useState<Colaborador[]>([]);
  const [selecionado, setSelecionado]     = useState<Colaborador | null>(null);
  const [tarefas, setTarefas]             = useState<TarefaEquipe[]>([]);
  const [carregando, setCarregando]       = useState(true);
  const [carregandoTarefas, setCarregandoTarefas] = useState(false);
  const [erro, setErro]                   = useState("");
  const [filtroTask, setFiltroTask]       = useState<FiltroTask>("todas");

  // Form nova tarefa
  const [mostrarForm, setMostrarForm] = useState(false);
  const [titulo, setTitulo]           = useState("");
  const [descricao, setDescricao]     = useState("");
  const [prioridade, setPrioridade]   = useState("media");
  const [categoria, setCategoria]     = useState("");
  const [dataEntrega, setDataEntrega] = useState("");
  const [hora, setHora]               = useState("09:00");
  const [salvando, setSalvando]       = useState(false);

  const token = () => localStorage.getItem("controllo_token") ?? "";

  useEffect(() => {
    const t = localStorage.getItem("controllo_token");
    const u = localStorage.getItem("controllo_user");
    if (!t || !u) { router.push("/"); return; }
    try {
      const parsed = JSON.parse(u);
      if (!parsed.is_aprovado || (!parsed.is_admin && !parsed.is_gestor)) {
        router.push("/");
      }
    } catch { router.push("/"); }
  }, [router]);

  const carregarColaboradores = useCallback(async () => {
    setCarregando(true);
    try {
      const res = await fetch(`${API}/api/equipe/colaboradores`, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (!res.ok) throw new Error("Erro ao carregar colaboradores");
      setColaboradores(await res.json());
    } catch { setErro("Não foi possível carregar a equipe."); }
    finally { setCarregando(false); }
  }, []);

  useEffect(() => { carregarColaboradores(); }, [carregarColaboradores]);

  const carregarTarefas = async (userId: number) => {
    setCarregandoTarefas(true);
    try {
      const res = await fetch(`${API}/api/equipe/tarefas/${userId}`, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (!res.ok) throw new Error();
      setTarefas(await res.json());
    } catch { setErro("Erro ao carregar tarefas."); }
    finally { setCarregandoTarefas(false); }
  };

  const selecionarColaborador = (c: Colaborador) => {
    setSelecionado(c);
    setMostrarForm(false);
    setFiltroTask("todas");
    setErro("");
    carregarTarefas(c.id);
  };

  const criarTarefa = async () => {
    if (!selecionado || !titulo.trim()) return;
    setSalvando(true); setErro("");
    try {
      const res = await fetch(`${API}/api/equipe/tarefas/${selecionado.id}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token()}`, "Content-Type": "application/json" },
        body: JSON.stringify({ titulo: titulo.trim(), descricao, prioridade, categoria, data_entrega: dataEntrega, hora }),
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail ?? "Erro ao criar tarefa");
      }
      setTitulo(""); setDescricao(""); setPrioridade("media"); setCategoria(""); setDataEntrega(""); setHora("09:00");
      setMostrarForm(false);
      await carregarTarefas(selecionado.id);
      await carregarColaboradores();
    } catch (e) { setErro((e as Error).message); }
    finally { setSalvando(false); }
  };

  const removerTarefa = async (tarefaId: number) => {
    if (!selecionado) return;
    try {
      const res = await fetch(`${API}/api/equipe/tarefas/${selecionado.id}/${tarefaId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (!res.ok && res.status !== 204) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? "Erro ao remover tarefa");
      }
      await carregarTarefas(selecionado.id);
      await carregarColaboradores();
    } catch (e) { setErro((e as Error).message); }
  };

  const toggleConcluida = async (tarefa: TarefaEquipe) => {
    if (!selecionado) return;
    try {
      await fetch(`${API}/api/equipe/tarefas/${selecionado.id}/${tarefa.id}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token()}`, "Content-Type": "application/json" },
        body: JSON.stringify({ concluida: !tarefa.concluida }),
      });
      await carregarTarefas(selecionado.id);
    } catch { setErro("Erro ao atualizar tarefa."); }
  };

  // ── Computed stats ──────────────────────────────────────────────────
  const pendentes  = tarefas.filter(t => !t.concluida).length;
  const concluidas = tarefas.filter(t => t.concluida).length;
  const urgentes   = tarefas.filter(t => t.prioridade === "urgente" && !t.concluida).length;
  const taxa       = tarefas.length > 0 ? Math.round((concluidas / tarefas.length) * 100) : 0;

  const tarefasFiltradas = tarefas.filter(t => {
    if (filtroTask === "pendentes")  return !t.concluida;
    if (filtroTask === "urgentes")   return t.prioridade === "urgente" && !t.concluida;
    if (filtroTask === "concluidas") return t.concluida;
    return true;
  });

  // Workload for selected collaborator
  const selWorkload = selecionado ? getWorkload(selecionado.tarefas_pendentes) : null;

  const fieldCls = "w-full px-3 py-2 rounded-xl text-sm border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-navy-300 dark:focus:ring-navy-700 transition-all";

  return (
    <div className="min-h-full bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">

      {/* ── HEADER ── */}
      <header className="px-8 pt-6 pb-5 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 bg-navy-50 border border-navy-200 dark:bg-navy-900/40 dark:border-navy-700/60">
              <svg className="w-5 h-5 text-navy-600 dark:text-navy-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-navy-500 dark:text-navy-400">Gestor</p>
              <h1 className="text-xl font-extrabold tracking-tight leading-tight">
                Gestão de <span className="text-navy-600 dark:text-navy-400">Equipe</span>
              </h1>
            </div>
          </div>
          {/* Equipe overview */}
          {colaboradores.length > 0 && (
            <div className="hidden sm:flex items-center gap-2">
              <div className="flex -space-x-2">
                {colaboradores.slice(0, 6).map(c => (
                  <button
                    key={c.id}
                    onClick={() => selecionarColaborador(c)}
                    title={c.nome_exibicao || c.nome}
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold ring-2 ring-white dark:ring-slate-900 transition-all hover:scale-110 hover:z-10 relative ${
                      selecionado?.id === c.id ? "bg-navy-500 text-white" : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300"
                    }`}
                  >
                    {iniciais(c.nome_exibicao || c.nome)}
                    {c.tarefas_pendentes > 0 && (
                      <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-red-500 rounded-full text-[8px] text-white flex items-center justify-center font-bold">{c.tarefas_pendentes}</span>
                    )}
                  </button>
                ))}
                {colaboradores.length > 6 && (
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold ring-2 ring-white dark:ring-slate-900 bg-slate-100 dark:bg-slate-700 text-slate-500">
                    +{colaboradores.length - 6}
                  </div>
                )}
              </div>
              <span className="text-xs text-slate-400 dark:text-slate-500">{colaboradores.length} colaborador{colaboradores.length !== 1 ? "es" : ""}</span>
            </div>
          )}
        </div>
      </header>

      <div className="flex h-[calc(100vh-125px)]">

        {/* ── SIDEBAR colaboradores ── */}
        <aside className="w-60 flex-shrink-0 border-r border-slate-200 dark:border-slate-700 overflow-y-auto bg-slate-50/70 dark:bg-slate-800/30">
          <div className="p-3">
            <p className="text-[10px] font-bold uppercase tracking-widest mb-2.5 px-1 text-slate-400 dark:text-slate-500">
              Colaboradores ({colaboradores.length})
            </p>

            {carregando ? (
              <div className="space-y-1.5">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl">
                    <div className="skeleton w-8 h-8 rounded-full flex-shrink-0" />
                    <div className="flex-1 space-y-1.5">
                      <div className="skeleton h-3 rounded" style={{ width: `${55 + i * 8}%` }} />
                      <div className="skeleton h-2.5 w-14 rounded" />
                    </div>
                  </div>
                ))}
              </div>
            ) : colaboradores.length === 0 ? (
              <p className="text-xs text-center py-8 text-slate-400 dark:text-slate-500">
                Nenhum colaborador encontrado.
              </p>
            ) : (
              <div className="space-y-0.5">
                {colaboradores.map(c => {
                  const isSelected = selecionado?.id === c.id;
                  const cargo = c.cargo || (c.is_admin ? "Administrador" : c.is_gestor ? "Gestor" : "Analista");
                  const wl = getWorkload(c.tarefas_pendentes);
                  return (
                    <button
                      key={c.id}
                      onClick={() => selecionarColaborador(c)}
                      className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-left transition-all border ${
                        isSelected
                          ? "bg-navy-50 border-navy-200 dark:bg-navy-900/30 dark:border-navy-700/60"
                          : "bg-transparent border-transparent hover:bg-white dark:hover:bg-slate-700/50"
                      }`}
                    >
                      <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold ${
                        isSelected ? "bg-navy-500 text-white" : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300"
                      }`}>
                        {iniciais(c.nome_exibicao || c.nome)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold truncate text-slate-900 dark:text-slate-100">
                          {c.nome_exibicao || c.nome}
                        </p>
                        <p className="text-[10px] truncate text-slate-400 dark:text-slate-500">{cargo}</p>
                        <p className="text-[9px] font-semibold mt-0.5" style={{ color: wl.color }}>
                          {wl.label}
                        </p>
                      </div>
                      {c.tarefas_pendentes > 0 && (
                        <span className="flex-shrink-0 min-w-[20px] h-5 flex items-center justify-center rounded-full bg-amber-500 text-white text-[9px] font-bold px-1">
                          {c.tarefas_pendentes}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </aside>

        {/* ── PAINEL de tarefas ── */}
        <main className="flex-1 overflow-y-auto">
          {!selecionado ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-8">
              <div className="w-20 h-20 rounded-3xl flex items-center justify-center mb-6 bg-navy-50 border border-navy-100 dark:bg-navy-900/20 dark:border-navy-800/40">
                <svg className="w-10 h-10 text-navy-400 dark:text-navy-500 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.3}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <h3 className="text-base font-bold mb-1.5 text-slate-900 dark:text-slate-100">Selecione um colaborador</h3>
              <p className="text-sm leading-relaxed max-w-xs text-slate-500 dark:text-slate-400">
                Escolha um membro na lista ao lado para visualizar e gerenciar suas tarefas.
              </p>
            </div>
          ) : (
            <div className="flex flex-col h-full">

              {/* ── Team summary ── */}
              <div className="px-6 py-3 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20">
                <div className="flex items-center gap-4 text-xs">
                  <span className="font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest text-[10px]">Equipe</span>
                  <span className="text-slate-600 dark:text-slate-300 font-semibold">{colaboradores.length} colaboradores</span>
                  <span className="text-slate-400 dark:text-slate-500">·</span>
                  <span className="text-amber-600 dark:text-amber-400 font-semibold">{colaboradores.reduce((s, c) => s + c.tarefas_pendentes, 0)} pendentes total</span>
                </div>
              </div>

              {/* ── Colaborador header + action ── */}
              <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm bg-navy-500 text-white">
                    {iniciais(selecionado.nome_exibicao || selecionado.nome)}
                  </div>
                  <div>
                    <p className="font-bold text-slate-900 dark:text-slate-100 leading-tight">
                      {selecionado.nome_exibicao || selecionado.nome}
                    </p>
                    <p className="text-xs text-slate-400 dark:text-slate-500">
                      {selecionado.cargo || (selecionado.is_admin ? "Administrador" : selecionado.is_gestor ? "Gestor" : "Analista")}
                    </p>
                    {/* Progress bar */}
                    <div className="flex items-center gap-2 mt-2">
                      <div className="h-1.5 flex-1 max-w-[200px] rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                        <div className="h-full rounded-full transition-all duration-500 bg-gradient-to-r from-indigo-500 to-violet-500"
                          style={{ width: `${taxa}%` }}
                        />
                      </div>
                      <span className="text-xs font-bold tabular-nums" style={{ color: taxa >= 70 ? "#10b981" : taxa >= 40 ? "#f59e0b" : "#ef4444" }}>
                        {taxa}% concluídas
                      </span>
                    </div>
                    {/* Workload indicator */}
                    {selWorkload && (
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Workload:</span>
                        <div className="flex gap-0.5 items-end">
                          {[...Array(5)].map((_, i) => (
                            <div key={i} className={`w-2 h-6 rounded-sm ${i < selWorkload.level ? 'bg-indigo-500' : 'bg-slate-200 dark:bg-slate-700/30'}`} />
                          ))}
                        </div>
                        <span className="text-[10px] font-bold" style={{ color: selWorkload.color }}>
                          {selWorkload.label}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => { setMostrarForm(f => !f); setErro(""); }}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-navy-600 hover:bg-navy-700 dark:bg-navy-500 dark:hover:bg-navy-600 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                  </svg>
                  Nova Tarefa
                </button>
              </div>

              {/* ── Stats horizontais ── */}
              <div className="grid grid-cols-4 divide-x divide-slate-100 dark:divide-slate-800 border-b border-slate-100 dark:border-slate-800">
                {/* Total */}
                <div className="px-5 py-3.5">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-1">Total</p>
                  <p className="text-2xl font-black text-slate-900 dark:text-slate-100 tabular-nums">{tarefas.length}</p>
                </div>
                {/* Pendentes */}
                <div className={`px-5 py-3.5 ${pendentes > 0 ? "bg-amber-50/50 dark:bg-amber-500/5" : ""}`}>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-1">Pendentes</p>
                  <p className={`text-2xl font-black tabular-nums ${pendentes > 0 ? "text-amber-600 dark:text-amber-400" : "text-slate-900 dark:text-slate-100"}`}>{pendentes}</p>
                  {urgentes > 0 && (
                    <p className="text-[10px] text-rose-500 dark:text-rose-400 font-semibold mt-0.5">{urgentes} urgente{urgentes !== 1 ? "s" : ""}</p>
                  )}
                </div>
                {/* Concluidas */}
                <div className="px-5 py-3.5">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-1">Concluidas</p>
                  <p className="text-2xl font-black text-slate-900 dark:text-slate-100 tabular-nums">{concluidas}</p>
                </div>
                {/* Taxa */}
                <div className="px-5 py-3.5">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-1">Taxa de Conclusao</p>
                  <p className={`text-2xl font-black tabular-nums ${taxa >= 70 ? "text-emerald-600 dark:text-emerald-400" : taxa >= 40 ? "text-amber-600 dark:text-amber-400" : "text-rose-600 dark:text-rose-400"}`}>{taxa}%</p>
                  <div className="mt-1.5 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-500 bg-gradient-to-r from-indigo-500 to-violet-500" style={{ width: `${taxa}%` }} />
                  </div>
                </div>
              </div>

              {erro && (
                <div className="mx-6 mt-4 p-3 rounded-xl text-sm text-red-700 bg-red-50 border border-red-200 dark:text-red-400 dark:bg-red-900/20 dark:border-red-800/40">
                  {erro}
                </div>
              )}

              {/* ── Formulário nova tarefa ── */}
              {mostrarForm && (
                <div className="mx-6 mt-4 rounded-2xl p-4 space-y-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <p className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    Nova tarefa para <span className="text-navy-600 dark:text-navy-400">{selecionado.nome_exibicao || selecionado.nome}</span>
                  </p>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">Titulo da tarefa *</label>
                    <input
                      value={titulo}
                      onChange={e => setTitulo(e.target.value)}
                      placeholder="Ex: Fechar balanco Empresa ABC"
                      className={fieldCls}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">Descricao (opcional)</label>
                    <textarea
                      value={descricao}
                      onChange={e => setDescricao(e.target.value)}
                      placeholder="Detalhes adicionais sobre a tarefa..."
                      rows={2}
                      className={`${fieldCls} resize-none`}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">Prioridade</label>
                      <select value={prioridade} onChange={e => setPrioridade(e.target.value)} className={fieldCls}>
                        <option value="baixa">Baixa</option>
                        <option value="media">Média</option>
                        <option value="alta">Alta</option>
                        <option value="urgente">Urgente</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">Categoria (opcional)</label>
                      <input value={categoria} onChange={e => setCategoria(e.target.value)} placeholder="Ex: Financeiro, Fiscal..." className={fieldCls} />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">Data de entrega</label>
                      <input type="date" value={dataEntrega} onChange={e => setDataEntrega(e.target.value)} className={`${fieldCls} [&::-webkit-calendar-picker-indicator]:dark:invert [&::-webkit-calendar-picker-indicator]:opacity-50`} />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">Horario</label>
                      <input type="time" value={hora} onChange={e => setHora(e.target.value)} className={`${fieldCls} [&::-webkit-calendar-picker-indicator]:dark:invert [&::-webkit-calendar-picker-indicator]:opacity-50`} />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={criarTarefa}
                      disabled={salvando || !titulo.trim()}
                      className="flex-1 py-2 rounded-xl text-sm font-semibold text-white bg-navy-600 hover:bg-navy-700 dark:bg-navy-500 dark:hover:bg-navy-600 transition-colors disabled:opacity-50"
                    >
                      {salvando ? "Salvando..." : "Designar Tarefa"}
                    </button>
                    <button
                      onClick={() => { setMostrarForm(false); setErro(""); }}
                      className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              )}

              {/* ── Filter tabs ── */}
              {tarefas.length > 0 && (
                <div className="mx-6 mt-4 flex gap-1 bg-slate-100 dark:bg-slate-800/60 rounded-xl p-1">
                  {([
                    { key: "todas",     label: "Todas",      count: tarefas.length },
                    { key: "pendentes", label: "Pendentes",  count: pendentes },
                    { key: "urgentes",  label: "Urgentes",   count: urgentes },
                    { key: "concluidas",label: "Concluídas", count: concluidas },
                  ] as { key: FiltroTask; label: string; count: number }[]).map(f => (
                    <button
                      key={f.key}
                      onClick={() => setFiltroTask(f.key)}
                      className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                        filtroTask === f.key
                          ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 shadow-sm"
                          : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                      }`}
                    >
                      {f.label}
                      {f.count > 0 && (
                        <span className={`ml-1 text-[10px] font-bold ${
                          filtroTask === f.key
                            ? f.key === "urgentes" ? "text-red-500" : f.key === "pendentes" ? "text-amber-500" : ""
                            : "text-slate-400"
                        }`}>
                          ({f.count})
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}

              {/* ── Lista de tarefas ── */}
              <div className="flex-1 overflow-y-auto p-6 pt-3 space-y-2">
                {carregandoTarefas ? (
                  <div className="space-y-2 pt-2">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className="flex items-center gap-3 p-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
                        <div className="skeleton w-5 h-5 rounded-full flex-shrink-0" />
                        <div className="flex-1 space-y-2">
                          <div className="skeleton h-3.5 rounded" style={{ width: `${60 + i * 10}%` }} />
                          <div className="skeleton h-2.5 w-24 rounded" />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : tarefas.length === 0 ? (
                  <div className="text-center py-12 rounded-2xl border border-dashed border-slate-200 dark:border-slate-700">
                    <svg className="w-12 h-12 mx-auto mb-3 text-slate-300 dark:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p className="text-sm font-semibold text-slate-600 dark:text-slate-300">Nenhuma tarefa atribuida</p>
                    <p className="text-xs mt-1 text-slate-400 dark:text-slate-500">Atribua tarefas para acompanhar o progresso da equipe</p>
                  </div>
                ) : tarefasFiltradas.length === 0 ? (
                  <div className="text-center py-10 rounded-2xl border border-dashed border-slate-200 dark:border-slate-700">
                    <p className="text-sm text-slate-400 dark:text-slate-500">Nenhuma tarefa nesta categoria.</p>
                  </div>
                ) : (
                  tarefasFiltradas.map(t => {
                    const vencida = !t.concluida && isVencida(t.data_entrega);
                    return (
                      <div
                        key={t.id}
                        className={`flex items-start gap-3 p-4 rounded-xl transition-all border border-l-4 ${
                          PRIORIDADE_BORDER[t.prioridade]
                        } ${
                          t.concluida
                            ? "bg-emerald-50/60 border-emerald-100 dark:bg-emerald-900/10 dark:border-emerald-800/30 opacity-75"
                            : "bg-white border-slate-200 dark:bg-slate-800 dark:border-slate-700"
                        }`}
                      >
                        <button
                          onClick={() => toggleConcluida(t)}
                          className={`flex-shrink-0 mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                            t.concluida
                              ? "border-emerald-500 bg-emerald-500"
                              : "border-slate-300 dark:border-slate-500 bg-transparent hover:border-navy-400"
                          }`}
                        >
                          {t.concluida && (
                            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </button>

                        <div className="flex-1 min-w-0">
                          <p className={`text-sm font-semibold leading-tight ${t.concluida ? "line-through text-slate-400 dark:text-slate-500" : "text-slate-900 dark:text-slate-100"}`}>
                            {t.titulo}
                          </p>
                          {t.descricao && (
                            <p className="text-xs mt-0.5 text-slate-500 dark:text-slate-400 line-clamp-1">{t.descricao}</p>
                          )}
                          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                            <Badge variant={PRIORIDADE_VARIANT[t.prioridade]}>
                              {PRIORIDADE_LABEL[t.prioridade]}
                            </Badge>
                            {t.categoria && <Badge variant="primary">{t.categoria}</Badge>}
                            {t.data_entrega && (
                              <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full ${
                                vencida
                                  ? "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400"
                                  : "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400"
                              }`}>
                                {vencida ? "⚠ " : ""}{t.data_entrega}{t.hora ? ` ${t.hora}` : ""}
                              </span>
                            )}
                          </div>
                        </div>

                        <button
                          onClick={() => removerTarefa(t.id)}
                          className="flex-shrink-0 p-1.5 rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
