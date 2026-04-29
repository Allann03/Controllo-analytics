"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Check, X, Ban, Trash2, Search } from "lucide-react";

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
        className="px-8 pt-8 pb-6"
        style={{ borderBottom: "1px solid var(--border-subtle)" }}
      >
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-5">
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
            <h1 className="text-3xl tracking-tight">
              <span className="font-semibold" style={{ color: "var(--text-primary)" }}>Gestão de </span>
              <span className="font-normal" style={{ color: "var(--text-secondary)" }}>Usuários</span>
            </h1>
            <p className="text-sm mt-1.5" style={{ color: "var(--text-secondary)" }}>
              Controle de acessos e permissões — Controllo Analytics
            </p>
          </div>

          {/* KPI cards — variante neutra padrao do sistema */}
          <div className="flex items-stretch gap-3">
            {[
              { label: "Total",     value: total },
              { label: "Ativos",    value: totalAtivos },
              ...(totalPendentes > 0 ? [{ label: "Pendentes", value: totalPendentes }] : []),
              { label: "Admins",    value: totalAdmins },
            ].map(({ label, value }) => (
              <div
                key={label}
                className="flex flex-col rounded-xl px-4 py-2.5 min-w-[80px]"
                style={{
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <p
                  className="text-[10px] uppercase font-medium mb-0.5"
                  style={{
                    color: "var(--text-tertiary)",
                    letterSpacing: "var(--tracking-widest)",
                  }}
                >
                  {label}
                </p>
                <p className="text-xl font-mono font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{value}</p>
              </div>
            ))}
          </div>
        </div>
      </header>

      {/* TOOLBAR */}
      <div
        className="px-8 py-4 flex flex-col sm:flex-row gap-6 items-start sm:items-center"
        style={{ borderBottom: "1px solid var(--border-subtle)" }}
      >
        {/* Busca */}
        <div className="relative flex-1 max-w-xs">
          <Search size={16} strokeWidth={2} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-tertiary)" }} />
          <input
            type="text"
            placeholder="Buscar por nome..."
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm focus:outline-none transition-colors"
            style={{
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              color: "var(--text-primary)",
            }}
          />
        </div>

        {/* Filtro status — tab strip com underline */}
        <div className="flex gap-0.5">
          {(["todos", "ativo", "pendente"] as FiltroStatus[]).map((f) => {
            const active = filtroStatus === f;
            const labels: Record<FiltroStatus, string> = { todos: "Todos", ativo: "Ativos", pendente: "Pendentes" };
            return (
              <button
                key={f}
                onClick={() => setFiltroStatus(f)}
                className="relative px-3 py-2 text-xs font-semibold transition-colors"
                style={{ color: active ? "var(--text-primary)" : "var(--text-tertiary)" }}
                onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = "var(--text-primary)"; }}
                onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = "var(--text-tertiary)"; }}
              >
                {labels[f]}
                {active && <span className="absolute left-2 right-2 -bottom-1 h-0.5" style={{ background: "var(--accent)" }} />}
              </button>
            );
          })}
        </div>

        {/* Filtro perfil — tab strip com underline */}
        <div className="flex gap-0.5">
          {(["todos", "admin", "operador"] as FiltroPerfil[]).map((f) => {
            const active = filtroPerfil === f;
            const labels: Record<FiltroPerfil, string> = { todos: "Todos", admin: "Admin", operador: "Operador" };
            return (
              <button
                key={f}
                onClick={() => setFiltroPerfil(f)}
                className="relative px-3 py-2 text-xs font-semibold transition-colors"
                style={{ color: active ? "var(--text-primary)" : "var(--text-tertiary)" }}
                onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = "var(--text-primary)"; }}
                onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = "var(--text-tertiary)"; }}
              >
                {labels[f]}
                {active && <span className="absolute left-2 right-2 -bottom-1 h-0.5" style={{ background: "var(--accent)" }} />}
              </button>
            );
          })}
        </div>

        {(busca || filtroStatus !== "todos" || filtroPerfil !== "todos") && (
          <button
            onClick={() => { setBusca(""); setFiltroStatus("todos"); setFiltroPerfil("todos"); }}
            className="text-xs transition-colors flex items-center gap-1"
            style={{ color: "var(--text-tertiary)" }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "var(--text-primary)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-tertiary)"; }}
          >
            <X size={14} strokeWidth={2} />
            Limpar
          </button>
        )}
      </div>

      {/* TABELA */}
      <div className="px-8 py-6">
        <div
          className="rounded-2xl overflow-hidden"
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <table className="w-full text-left">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                {[
                  { label: "Usuário", align: "left" as const },
                  { label: "Perfil",  align: "left" as const },
                  { label: "Status",  align: "left" as const },
                  { label: "Ações",   align: "right" as const },
                ].map(({ label, align }) => (
                  <th
                    key={label}
                    className={`px-5 py-3.5 text-xs uppercase font-medium ${align === "right" ? "text-right" : "text-left"}`}
                    style={{
                      color: "var(--text-tertiary)",
                      letterSpacing: "var(--tracking-widest)",
                    }}
                  >
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtrados.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-5 py-14 text-center">
                    <div className="flex flex-col items-center gap-2" style={{ color: "var(--text-tertiary)" }}>
                      <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      <p className="text-sm">Nenhum usuário encontrado</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filtrados.map((u, idx) => (
                  <tr
                    key={u.id}
                    className="transition-colors group"
                    style={{ borderBottom: idx === filtrados.length - 1 ? "none" : "1px solid var(--border-subtle)" }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "var(--bg-elevated)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                  >
                    {/* Avatar + nome */}
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                          style={{
                            background: u.is_admin
                              ? "var(--accent-subtle)"
                              : u.status === "pendente"
                              ? "var(--warning-subtle)"
                              : "var(--bg-inset)",
                            border: `1px solid ${u.is_admin
                              ? "var(--accent-border)"
                              : u.status === "pendente"
                              ? "var(--warning-border)"
                              : "var(--border-subtle)"}`,
                            color: u.is_admin
                              ? "var(--accent)"
                              : u.status === "pendente"
                              ? "var(--warning)"
                              : "var(--text-secondary)",
                          }}
                        >
                          <Iniciais nome={u.nome} />
                        </div>
                        <div>
                          <p className="font-medium text-sm leading-tight" style={{ color: "var(--text-primary)" }}>{u.nome}</p>
                          <p className="text-[11px] mt-0.5 font-mono tabular-nums" style={{ color: "var(--text-tertiary)" }}>ID #{u.id}</p>
                        </div>
                      </div>
                    </td>

                    {/* Perfil — pills semanticas via tokens */}
                    <td className="px-5 py-3.5">
                      {u.status === "ativo" ? (
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {podeMoverCEO && (
                            <button
                              onClick={() => definirCEO(u.id, !u.is_ceo)}
                              title={u.is_ceo ? "Revogar CEO" : "Promover a CEO"}
                              className="text-[10px] font-semibold px-2.5 py-1 rounded-full transition-all"
                              style={{
                                background: u.is_ceo ? "var(--warning-subtle)" : "var(--bg-inset)",
                                border: `1px solid ${u.is_ceo ? "var(--warning-border)" : "var(--border-subtle)"}`,
                                color: u.is_ceo ? "var(--warning)" : "var(--text-tertiary)",
                              }}
                            >
                              {u.is_ceo ? "✓ C.E.O." : "C.E.O."}
                            </button>
                          )}
                          <button
                            onClick={() => promover(u.id, !u.is_admin)}
                            title={u.is_admin ? "Revogar Admin" : "Promover a Admin"}
                            className="text-[10px] font-semibold px-2.5 py-1 rounded-full transition-all"
                            style={{
                              background: u.is_admin ? "var(--accent-subtle)" : "var(--bg-inset)",
                              border: `1px solid ${u.is_admin ? "var(--accent-border)" : "var(--border-subtle)"}`,
                              color: u.is_admin ? "var(--accent-text)" : "var(--text-tertiary)",
                            }}
                          >
                            {u.is_admin ? "✓ ADMIN" : "ADMIN"}
                          </button>
                          {!u.is_admin && (
                            <button
                              onClick={() => definirGestor(u.id, !u.is_gestor)}
                              title={u.is_gestor ? "Revogar Gestor" : "Promover a Gestor"}
                              className="text-[10px] font-semibold px-2.5 py-1 rounded-full transition-all"
                              style={{
                                background: u.is_gestor ? "var(--accent-subtle)" : "var(--bg-inset)",
                                border: `1px solid ${u.is_gestor ? "var(--accent-border)" : "var(--border-subtle)"}`,
                                color: u.is_gestor ? "var(--accent-text)" : "var(--text-tertiary)",
                              }}
                            >
                              {u.is_gestor ? "✓ GESTOR" : "GESTOR"}
                            </button>
                          )}
                        </div>
                      ) : (
                        <span style={{ color: "var(--text-tertiary)" }}>—</span>
                      )}
                    </td>

                    {/* Status — dot 6px sem pill */}
                    <td className="px-5 py-3.5">
                      <span className="inline-flex items-center gap-2 text-xs font-medium" style={{ color: u.status === "ativo" ? "var(--success)" : "var(--warning)" }}>
                        <span
                          className="w-1.5 h-1.5 rounded-full"
                          style={{ background: u.status === "ativo" ? "var(--success)" : "var(--warning)" }}
                        />
                        {u.status === "ativo" ? "Ativo" : "Pendente"}
                      </span>
                    </td>

                    {/* Ações — Lucide 16px text-tertiary, hover semantico */}
                    <td className="px-5 py-3.5">
                      <div className="flex items-center justify-end gap-1.5">
                        {u.status === "pendente" ? (
                          <>
                            <button
                              onClick={() => aprovar(u.id, true)}
                              title="Aprovar acesso"
                              className="p-2 rounded-lg transition-all"
                              style={{ color: "var(--text-tertiary)" }}
                              onMouseEnter={(e) => { e.currentTarget.style.background = "var(--success-subtle)"; e.currentTarget.style.color = "var(--success)"; }}
                              onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "var(--text-tertiary)"; }}
                            >
                              <Check size={16} strokeWidth={2.25} />
                            </button>
                            <ConfirmButton
                              onConfirm={() => excluir(u.id)}
                              label="Recusar e remover"
                              confirmLabel="Recusar"
                              icon={<X size={16} strokeWidth={2.25} />}
                              className="p-2 rounded-lg transition-all admin-action-danger"
                            />
                          </>
                        ) : (
                          <>
                            <ConfirmButton
                              onConfirm={() => aprovar(u.id, false)}
                              label="Bloquear acesso"
                              confirmLabel="Bloquear"
                              icon={<Ban size={16} strokeWidth={2} />}
                              className="p-2 rounded-lg transition-all admin-action-warning"
                            />
                            <ConfirmButton
                              onConfirm={() => excluir(u.id)}
                              label="Excluir usuário"
                              confirmLabel="Excluir"
                              icon={<Trash2 size={16} strokeWidth={2} />}
                              className="p-2 rounded-lg transition-all admin-action-danger"
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
            <div
              className="px-5 py-3 flex items-center justify-between"
              style={{
                borderTop: "1px solid var(--border-subtle)",
                background: "var(--bg-inset)",
              }}
            >
              <p className="text-[11px] font-mono tabular-nums" style={{ color: "var(--text-tertiary)" }}>
                Exibindo {filtrados.length} de {total} usuários
              </p>
              {(busca || filtroStatus !== "todos" || filtroPerfil !== "todos") && (
                <p className="text-[11px]" style={{ color: "var(--accent)" }}>Filtros ativos</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Inline styles para hover dos botoes de acao (Lucide icons) */}
      <style jsx>{`
        :global(.admin-action-warning) { color: var(--text-tertiary); }
        :global(.admin-action-warning:hover) { background: var(--warning-subtle); color: var(--warning); }
        :global(.admin-action-danger) { color: var(--text-tertiary); }
        :global(.admin-action-danger:hover) { background: var(--danger-subtle); color: var(--danger); }
      `}</style>
    </div>
  );
}
