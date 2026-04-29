"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";

interface Usuario {
  id: number;
  nome: string;
  is_admin: boolean;
  is_gestor?: boolean;
  is_ceo?: boolean;
  is_aprovado: boolean;
}

interface Toast {
  mensagem: string;
  tipo: "sucesso" | "erro";
}

type FiltroStatus = "todos" | "ativo" | "pendente";
type FiltroPerfil = "todos" | "admin" | "operador";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

function Iniciais({ nome }: { nome: string }) {
  const partes = nome.trim().split(" ");
  const ini =
    partes.length >= 2
      ? partes[0][0] + partes[partes.length - 1][0]
      : partes[0].slice(0, 2);
  return <span className="text-sm font-bold uppercase">{ini}</span>;
}

function ConfirmButton({
  onConfirm,
  label,
  confirmLabel,
  className,
  icon,
}: {
  onConfirm: () => void;
  label: string;
  confirmLabel: string;
  className: string;
  icon: React.ReactNode;
}) {
  const [pedindo, setPedindo] = useState(false);

  if (pedindo) {
    return (
      <div className="flex items-center gap-1">
        <button
          onClick={() => { onConfirm(); setPedindo(false); }}
          className="px-2 py-1 text-[10px] font-bold rounded bg-red-500 text-white hover:bg-red-600 transition-colors"
        >
          {confirmLabel}
        </button>
        <button
          onClick={() => setPedindo(false)}
          className="px-2 py-1 text-[10px] font-bold rounded bg-slate-200 dark:bg-slate-700 text-[#475569] dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors"
        >
          Não
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => setPedindo(true)}
      title={label}
      className={className}
    >
      {icon}
    </button>
  );
}

export default function AdminPage() {
  const router = useRouter();
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);
  const [pendentes, setPendentes] = useState<Usuario[]>([]);
  const [ativos, setAtivos] = useState<Usuario[]>([]);
  const [podeMoverCEO, setPodeMoverCEO] = useState(false);

  // Filtros
  const [busca, setBusca] = useState("");
  const [filtroStatus, setFiltroStatus] = useState<FiltroStatus>("todos");
  const [filtroPerfil, setFiltroPerfil] = useState<FiltroPerfil>("todos");

  const mostrarToast = (mensagem: string, tipo: "sucesso" | "erro") => {
    setToast({ mensagem, tipo });
    setTimeout(() => setToast(null), 3500);
  };

  const carregarUsuarios = useCallback(async (token: string) => {
    const res = await fetch(`${API}/api/admin/usuarios`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Falha ao carregar usuários.");
    const data: Usuario[] = await res.json();
    setPendentes(data.filter((u) => !u.is_aprovado));
    setAtivos(data.filter((u) => u.is_aprovado));
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("controllo_token");
    const userStr = localStorage.getItem("controllo_user");

    if (!token || !userStr) {
      router.push("/");
      return;
    }

    try {
      const user = JSON.parse(userStr);
      if (!user.is_admin) {
        router.push("/");
        return;
      }
      setPodeMoverCEO(!!(user.is_ceo || user.nome?.toLowerCase() === "allan"));
    } catch {
      router.push("/");
      return;
    }

    carregarUsuarios(token)
      .catch((e) => setErro(e.message))
      .finally(() => setCarregando(false));
  }, [router, carregarUsuarios]);

  const chamarAPI = async (path: string, metodo: string, body?: object) => {
    const token = localStorage.getItem("controllo_token");
    const res = await fetch(`${API}/api/admin${path}`, {
      method: metodo,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? "Erro desconhecido.");
    return data;
  };

  const aprovar = async (id: number, aprovar: boolean) => {
    try {
      const r = await chamarAPI(`/usuarios/${id}/aprovar`, "PATCH", { is_aprovado: aprovar });
      mostrarToast(r.mensagem, "sucesso");
      const token = localStorage.getItem("controllo_token")!;
      await carregarUsuarios(token);
    } catch (e: unknown) {
      mostrarToast((e as Error).message, "erro");
    }
  };

  const promover = async (id: number, tornarAdmin: boolean) => {
    try {
      const r = await chamarAPI(`/usuarios/${id}/promover`, "PATCH", { is_admin: tornarAdmin });
      mostrarToast(r.mensagem, "sucesso");
      const token = localStorage.getItem("controllo_token")!;
      await carregarUsuarios(token);
    } catch (e: unknown) {
      mostrarToast((e as Error).message, "erro");
    }
  };

  const definirGestor = async (id: number, tornarGestor: boolean) => {
    try {
      const r = await chamarAPI(`/usuarios/${id}/gestor`, "PATCH", { is_gestor: tornarGestor });
      mostrarToast(r.mensagem, "sucesso");
      const token = localStorage.getItem("controllo_token")!;
      await carregarUsuarios(token);
    } catch (e: unknown) {
      mostrarToast((e as Error).message, "erro");
    }
  };

  const definirCEO = async (id: number, tornarCEO: boolean) => {
    try {
      const token = localStorage.getItem("controllo_token");
      const res = await fetch(`${API}/api/admin/usuarios/${id}/ceo`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ is_ceo: tornarCEO }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Erro desconhecido.");
      mostrarToast(data.mensagem, "sucesso");
      await carregarUsuarios(token!);
    } catch (e: unknown) {
      mostrarToast((e as Error).message, "erro");
    }
  };

  const excluir = async (id: number) => {
    try {
      const r = await chamarAPI(`/usuarios/${id}`, "DELETE");
      mostrarToast(r.mensagem, "sucesso");
      const token = localStorage.getItem("controllo_token")!;
      await carregarUsuarios(token);
    } catch (e: unknown) {
      mostrarToast((e as Error).message, "erro");
    }
  };

  // Todos os usuários em lista unificada para tabela principal
  const todos: (Usuario & { status: "ativo" | "pendente" })[] = useMemo(() => [
    ...ativos.map((u) => ({ ...u, status: "ativo" as const })),
    ...pendentes.map((u) => ({ ...u, status: "pendente" as const })),
  ], [ativos, pendentes]);

  const filtrados = useMemo(() => {
    return todos.filter((u) => {
      const matchBusca = busca === "" || u.nome.toLowerCase().includes(busca.toLowerCase());
      const matchStatus =
        filtroStatus === "todos" ||
        (filtroStatus === "ativo" && u.status === "ativo") ||
        (filtroStatus === "pendente" && u.status === "pendente");
      const matchPerfil =
        filtroPerfil === "todos" ||
        (filtroPerfil === "admin" && u.is_admin) ||
        (filtroPerfil === "operador" && !u.is_admin);
      return matchBusca && matchStatus && matchPerfil;
    });
  }, [todos, busca, filtroStatus, filtroPerfil]);

  if (carregando) {
    return (
      <div className="min-h-full" style={{ background: "var(--bg-canvas)", color: "var(--text-primary)" }}>
        <div className="px-8 pt-8 pb-6 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
          <div className="skeleton h-4 w-24 rounded mb-3" />
          <div className="skeleton h-8 w-64 rounded mb-2" />
          <div className="skeleton h-3 w-48 rounded" />
        </div>
        <div className="px-8 py-6">
          <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <div style={{ height: "1px", background: "linear-gradient(90deg, #102a43 0%, #3b6ea5 60%, transparent 100%)" }} />
            <div className="px-5 py-3.5 flex gap-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              {["w-24","w-20","w-16","w-14"].map((w, i) => <div key={i} className={`skeleton h-3 ${w} rounded`} />)}
            </div>
            {[...Array(6)].map((_, i) => (
              <div key={i} className="px-5 py-4 flex items-center gap-4 border-b border-slate-700/30 last:border-0">
                <div className="skeleton w-8 h-8 rounded-full flex-shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <div className="skeleton h-3.5 w-40 rounded" />
                  <div className="skeleton h-2.5 w-16 rounded" />
                </div>
                <div className="skeleton h-5 w-16 rounded-full" />
                <div className="skeleton h-5 w-14 rounded-full" />
                <div className="flex gap-1.5 ml-auto">
                  <div className="skeleton w-7 h-7 rounded-lg" />
                  <div className="skeleton w-7 h-7 rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const total = todos.length;
  const totalAtivos = ativos.length;
  const totalPendentes = pendentes.length;
  const totalAdmins = ativos.filter((u) => u.is_admin).length;

  return (
    <div className="min-h-full" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>

      {/* TOAST */}
      {toast && (
        <div
          className={`fixed top-6 right-6 z-50 flex items-center gap-3 px-5 py-3.5 rounded-2xl shadow-2xl text-sm font-semibold border backdrop-blur-sm transition-all ${
            toast.tipo === "sucesso"
              ? "bg-emerald-950/90 border-emerald-500/30 text-emerald-300"
              : "bg-red-950/90 border-red-500/30 text-red-300"
          }`}
        >
          {toast.tipo === "sucesso" ? (
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
          )}
          {toast.mensagem}
        </div>
      )}

      {/* ERRO */}
      {erro && (
        <div className="mx-8 mt-6 px-5 py-3 rounded-xl bg-red-900/30 border border-red-500/30 text-red-300 text-sm font-medium">
          {erro}
        </div>
      )}

      {/* HEADER */}
      <header
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--border)" }}
        className="px-8 pt-8 pb-6"
      >
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-5">
          <div>
            <div className="inline-flex items-center gap-2 mb-3">
              <span className="px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-widest bg-navy-50 border border-navy-200 text-navy-700 dark:bg-navy-900/30 dark:border-navy-700/50 dark:text-navy-400">
                Administrador
              </span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight" style={{ color: "var(--text-primary)" }}>
              Gestão de{" "}
              <span style={{ color: "#1E4976" }}>Usuários</span>
            </h1>
            <p className="text-sm mt-1.5" style={{ color: "var(--text-muted)" }}>
              Controle de acessos e permissões — Controllo Analytics
            </p>
          </div>

          {/* KPI cards */}
          <div className="flex items-stretch gap-3">
            <div className="flex flex-col items-center justify-center rounded-xl px-4 py-2.5 min-w-[64px]" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <p className="text-[10px] uppercase font-bold tracking-widest mb-0.5" style={{ color: "var(--text-muted)" }}>Total</p>
              <p className="text-xl font-mono font-bold" style={{ color: "var(--text-primary)" }}>{total}</p>
            </div>
            <div className="flex flex-col items-center justify-center bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-500/20 rounded-xl px-4 py-2.5 min-w-[64px]">
              <p className="text-[10px] text-emerald-700 dark:text-emerald-500 uppercase font-bold tracking-widest mb-0.5">Ativos</p>
              <p className="text-xl font-mono font-bold text-emerald-700 dark:text-emerald-400">{totalAtivos}</p>
            </div>
            {totalPendentes > 0 && (
              <div className="flex flex-col items-center justify-center bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-500/20 rounded-xl px-4 py-2.5 min-w-[64px]">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                  <p className="text-[10px] text-amber-700 dark:text-amber-500 uppercase font-bold tracking-widest">Pendentes</p>
                </div>
                <p className="text-xl font-mono font-bold text-amber-700 dark:text-amber-400">{totalPendentes}</p>
              </div>
            )}
            <div className="flex flex-col items-center justify-center bg-blue-50 dark:bg-navy-800/40 border border-blue-200 dark:border-navy-500/20 rounded-xl px-4 py-2.5 min-w-[64px]">
              <p className="text-[10px] text-[#1E4976] dark:text-navy-400 uppercase font-bold tracking-widest mb-0.5">Admins</p>
              <p className="text-xl font-mono font-bold text-[#1E4976] dark:text-navy-300">{totalAdmins}</p>
            </div>
          </div>
        </div>
      </header>

      {/* TOOLBAR */}
      <div className="px-8 py-4 flex flex-col sm:flex-row gap-3" style={{ borderBottom: "1px solid var(--border)", background: "var(--bg-card)" }}>
        {/* Busca */}
        <div className="relative flex-1 max-w-xs">
          <svg className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Buscar por nome..."
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="w-full rounded-xl pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy-500/30 transition-colors"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
          />
        </div>

        {/* Filtro status */}
        <div className="flex rounded-xl overflow-hidden text-xs font-semibold border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
          {(["todos", "ativo", "pendente"] as FiltroStatus[]).map((f) => (
            <button
              key={f}
              onClick={() => setFiltroStatus(f)}
              className={`px-3 py-2 transition-colors ${
                filtroStatus === f
                  ? "bg-navy-600 text-white dark:bg-navy-500"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700"
              }`}
            >
              {f === "todos" ? "Todos" : f === "ativo" ? "Ativos" : "Pendentes"}
            </button>
          ))}
        </div>

        {/* Filtro perfil */}
        <div className="flex rounded-xl overflow-hidden text-xs font-semibold border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
          {(["todos", "admin", "operador"] as FiltroPerfil[]).map((f) => (
            <button
              key={f}
              onClick={() => setFiltroPerfil(f)}
              className={`px-3 py-2 transition-colors ${
                filtroPerfil === f
                  ? "bg-navy-600 text-white dark:bg-navy-500"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700"
              }`}
            >
              {f === "todos" ? "Todos" : f === "admin" ? "Admin" : "Operador"}
            </button>
          ))}
        </div>

        {(busca || filtroStatus !== "todos" || filtroPerfil !== "todos") && (
          <button
            onClick={() => { setBusca(""); setFiltroStatus("todos"); setFiltroPerfil("todos"); }}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            Limpar
          </button>
        )}
      </div>

      {/* TABELA */}
      <div className="px-8 py-6">
        <div
          className="rounded-2xl overflow-hidden"
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            boxShadow: "0 4px 32px rgba(0,0,0,0.3)",
          }}
        >
          {/* Top accent line */}
          <div style={{ height: "1px", background: "linear-gradient(90deg, #102a43 0%, #3b6ea5 60%, transparent 100%)" }} />
          <table className="w-full text-left">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
                <th className="px-5 py-3.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Usuário</th>
                <th className="px-5 py-3.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Perfil</th>
                <th className="px-5 py-3.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Status</th>
                <th className="px-5 py-3.5 text-[10px] font-bold uppercase tracking-wider text-right text-slate-500 dark:text-slate-400">Ações</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-5 py-14 text-center">
                    <div className="flex flex-col items-center gap-2 text-slate-600">
                      <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      <p className="text-sm">Nenhum usuário encontrado</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filtrados.map((u) => (
                  <tr
                    key={u.id}
                    className="border-b border-slate-200 dark:border-slate-700/40 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700/20 transition-colors group"
                  >
                    {/* Avatar + nome */}
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                            u.is_admin
                              ? "bg-[#1E4976]"
                              : u.status === "pendente"
                              ? "bg-amber-600"
                              : "bg-[#64748B]"
                          }`}
                          style={{ color: "white" }}
                        >
                          <Iniciais nome={u.nome} />
                        </div>
                        <div>
                          <p className="font-medium text-[#0F172A] dark:text-slate-200 text-sm leading-tight">{u.nome}</p>
                          <p className="text-[11px] text-[#64748B] dark:text-slate-500 mt-0.5">ID #{u.id}</p>
                        </div>
                      </div>
                    </td>

                    {/* Perfil */}
                    <td className="px-5 py-3.5">
                      {u.status === "ativo" ? (
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {podeMoverCEO && (
                            <button
                              onClick={() => definirCEO(u.id, !u.is_ceo)}
                              title={u.is_ceo ? "Revogar CEO" : "Promover a CEO"}
                              className={`text-[10px] font-bold px-2.5 py-1 rounded-full border transition-all ${
                                u.is_ceo
                                  ? "border-yellow-300 dark:border-yellow-500/40 text-yellow-700 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-500/10 hover:bg-yellow-100 dark:hover:bg-yellow-500/20"
                                  : "border-slate-300 dark:border-slate-600 text-[#475569] dark:text-slate-500 bg-slate-100 dark:bg-slate-700/50 hover:border-slate-400 dark:hover:border-slate-500 hover:text-[#1E293B] dark:hover:text-slate-300"
                              }`}
                            >
                              {u.is_ceo ? "✓ C.E.O." : "C.E.O."}
                            </button>
                          )}
                          <button
                            onClick={() => promover(u.id, !u.is_admin)}
                            title={u.is_admin ? "Revogar Admin" : "Promover a Admin"}
                            className={`text-[10px] font-bold px-2.5 py-1 rounded-full border transition-all ${
                              u.is_admin
                                ? "border-emerald-200 dark:border-emerald-500/40 text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 hover:bg-emerald-100 dark:hover:bg-emerald-500/20"
                                : "border-slate-300 dark:border-slate-600 text-[#475569] dark:text-slate-500 bg-slate-100 dark:bg-slate-700/50 hover:border-slate-400 dark:hover:border-slate-500 hover:text-[#1E293B] dark:hover:text-slate-300"
                            }`}
                          >
                            {u.is_admin ? "✓ ADMIN" : "ADMIN"}
                          </button>
                          {!u.is_admin && (
                            <button
                              onClick={() => definirGestor(u.id, !u.is_gestor)}
                              title={u.is_gestor ? "Revogar Gestor" : "Promover a Gestor"}
                              className={`text-[10px] font-bold px-2.5 py-1 rounded-full border transition-all ${
                                u.is_gestor
                                  ? "border-indigo-200 dark:border-indigo-500/40 text-indigo-700 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/10 hover:bg-indigo-100 dark:hover:bg-indigo-500/20"
                                  : "border-slate-300 dark:border-slate-600 text-[#475569] dark:text-slate-500 bg-slate-100 dark:bg-slate-700/50 hover:border-slate-400 dark:hover:border-slate-500 hover:text-[#1E293B] dark:hover:text-slate-300"
                              }`}
                            >
                              {u.is_gestor ? "✓ GESTOR" : "GESTOR"}
                            </button>
                          )}
                        </div>
                      ) : (
                        <span className="text-[10px] font-bold px-3 py-1 rounded-full border border-slate-200 dark:border-slate-700 text-[#64748B] dark:text-slate-600 bg-slate-100 dark:bg-slate-800">
                          —
                        </span>
                      )}
                    </td>

                    {/* Status */}
                    <td className="px-5 py-3.5">
                      {u.status === "ativo" ? (
                        <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          Ativo
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-500/20 text-amber-700 dark:text-amber-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                          Pendente
                        </span>
                      )}
                    </td>

                    {/* Ações */}
                    <td className="px-5 py-3.5">
                      <div className="flex items-center justify-end gap-1.5">
                        {u.status === "pendente" ? (
                          <>
                            <button
                              onClick={() => aprovar(u.id, true)}
                              title="Aprovar acesso"
                              className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500 hover:text-white border border-emerald-500/20 hover:border-emerald-500 transition-all"
                            >
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                              </svg>
                            </button>
                            <ConfirmButton
                              onConfirm={() => excluir(u.id)}
                              label="Recusar e remover"
                              confirmLabel="Recusar"
                              icon={
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                              }
                              className="p-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500 hover:text-white border border-red-500/20 hover:border-red-500 transition-all"
                            />
                          </>
                        ) : (
                          <>
                            <ConfirmButton
                              onConfirm={() => aprovar(u.id, false)}
                              label="Bloquear acesso"
                              confirmLabel="Bloquear"
                              icon={
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                                </svg>
                              }
                              className="p-2 rounded-lg text-slate-500 hover:text-amber-400 hover:bg-amber-400/10 border border-transparent hover:border-amber-400/20 transition-all"
                            />
                            <ConfirmButton
                              onConfirm={() => excluir(u.id)}
                              label="Excluir usuário"
                              confirmLabel="Excluir"
                              icon={
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              }
                              className="p-2 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-400/10 border border-transparent hover:border-red-400/20 transition-all"
                            />
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {/* Footer da tabela */}
          {filtrados.length > 0 && (
            <div className="px-5 py-3 flex items-center justify-between" style={{ borderTop: "1px solid var(--border)", background: "var(--bg-secondary)" }}>
              <p className="text-[11px] text-slate-500">
                Exibindo {filtrados.length} de {total} usuários
              </p>
              {(busca || filtroStatus !== "todos" || filtroPerfil !== "todos") && (
                <p className="text-[11px] text-[#3b6ea5]">Filtros ativos</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
