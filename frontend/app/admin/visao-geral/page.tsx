"use client";
import { useEffect, useState } from "react";
import { Badge, type BadgeVariant } from "@/components/ui";

const API = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  .replace(/\/api\/?$/, "").replace(/\/$/, "");

const STATUS_MAP: Record<string, { label: string; variant: BadgeVariant; dot: string; pulse?: boolean }> = {
  iniciada:           { label: "Iniciada",           variant: "muted",   dot: "#829ab1" },
  em_andamento:       { label: "Em andamento",       variant: "warning", dot: "#d97706", pulse: true },
  extratos_pendentes: { label: "Extratos pendentes", variant: "danger",  dot: "#dc2626" },
  pendencia_fiscal:   { label: "Pendência fiscal",   variant: "danger",  dot: "#dc2626" },
  pendencia_juridica: { label: "Pendência jurídica", variant: "primary", dot: "#7c3aed" },
  finalizada:         { label: "Finalizada",         variant: "success", dot: "#065f46" },
};

interface AdminEmpresa {
  id: number;
  nome: string;
  cnpj: string;
  status: string;
  usuario_id: number;
  usuario_nome: string;
  usuario_cargo: string;
  carteira_observacoes: string;
}

function tk() { return localStorage.getItem("controllo_token") ?? ""; }

export default function VisaoGeralAdminPage() {
  const [itens, setItens]                 = useState<AdminEmpresa[]>([]);
  const [carregando, setCarregando]       = useState(true);
  const [filtro, setFiltro]               = useState("");
  const [usuarioFiltro, setUsuarioFiltro] = useState<number | "">("");

  useEffect(() => {
    fetch(`${API}/api/admin/carteiras`, { headers: { Authorization: `Bearer ${tk()}` } })
      .then(r => r.json())
      .then((d: AdminEmpresa[]) => setItens(Array.isArray(d) ? d : []))
      .catch(() => {})
      .finally(() => setCarregando(false));
  }, []);

  const usuarios = Array.from(
    new Map(itens.map(i => [i.usuario_id, { id: i.usuario_id, nome: i.usuario_nome, cargo: i.usuario_cargo }])).values()
  );

  const visiveis = itens.filter(i => {
    const okUser  = usuarioFiltro === "" || i.usuario_id === usuarioFiltro;
    const okBusca = !filtro
      || i.nome.toLowerCase().includes(filtro.toLowerCase())
      || i.usuario_nome.toLowerCase().includes(filtro.toLowerCase());
    return okUser && okBusca;
  });

  const totalEmpresas  = itens.length;
  const totalAnalistas = usuarios.length;
  const totalFinaliz   = itens.filter(i => i.status === "finalizada").length;
  const totalPendentes = itens.filter(i =>
    ["extratos_pendentes", "pendencia_fiscal", "pendencia_juridica"].includes(i.status)
  ).length;

  const kpis = [
    {
      label: "Total de empresas", value: totalEmpresas, sub: "cadastradas",
      accent: "#1e3a5f",
      icon: (
        <svg className="w-5 h-5 text-[#9fb3c8]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
        </svg>
      ),
    },
    {
      label: "Analistas ativos", value: totalAnalistas, sub: "com carteira",
      accent: "#065f46",
      icon: (
        <svg className="w-5 h-5 text-emerald-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
    },
    {
      label: "Finalizadas", value: totalFinaliz, sub: "competências",
      accent: "#14532d",
      icon: (
        <svg className="w-5 h-5 text-green-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    {
      label: "Com pendência", value: totalPendentes, sub: "requerem atenção",
      accent: totalPendentes > 0 ? "#92400e" : "#475569",
      icon: (
        <svg className="w-5 h-5" style={{ color: totalPendentes > 0 ? "#fcd34d" : "#94a3b8" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
    },
  ];

  return (
    <div className="min-h-full" style={{ background: "var(--bg-canvas)", color: "var(--text-primary)" }}>

      {/* ── HEADER ── */}
      <div className="px-6 pt-6 pb-5 bg-white dark:bg-slate-900 border-b border-[#e2e8f0] dark:border-slate-700">
        <div className="flex items-start gap-4">
          <div className="w-11 h-11 rounded-xl bg-[#102a43] flex items-center justify-center shadow-sm flex-shrink-0">
            <svg className="w-5 h-5 text-[#9fb3c8]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <div>
            <span className="text-[10px] font-semibold uppercase tracking-widest text-[#486581] dark:text-navy-400 bg-[#f0f4f8] dark:bg-navy-900/40 px-2 py-0.5 rounded">
              Administração
            </span>
            <h1 className="text-[22px] font-bold text-[#102a43] dark:text-slate-100 tracking-tight mt-1">
              Visão Geral da Equipe
            </h1>
            <p className="text-sm text-[#627d98] dark:text-slate-400 mt-0.5">
              Carteiras de todos os analistas em um só lugar
            </p>
          </div>
        </div>

        {/* KPI Cards — sem fundos coloridos sólidos */}
        {!carregando && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
            {kpis.map(k => (
              <div
                key={k.label}
                className={`rounded-xl border p-4 ${
                  k.label === "Com pendência" && k.value > 0
                    ? "bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700"
                    : "bg-white dark:bg-slate-800 border-[#e2e8f0] dark:border-slate-700"
                }`}
                style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}
              >
                <div data-notheme className="w-9 h-9 rounded-lg flex items-center justify-center mb-3 flex-shrink-0"
                  style={{ background: k.accent }}>
                  {k.icon}
                </div>
                <p className="text-2xl font-black text-[#102a43] dark:text-slate-100 tabular-nums leading-tight">{k.value}</p>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-[#829ab1] dark:text-slate-400 mt-0.5">{k.label}</p>
                <p className="text-[10px] text-[#9fb3c8] dark:text-slate-500 mt-0.5">{k.sub}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── CONTEÚDO ── */}
      <div className="px-6 py-5">

        {/* Card principal — lista de analistas */}
        <div
          className="bg-white dark:bg-slate-800 rounded-xl border border-[#e2e8f0] dark:border-slate-700 overflow-hidden"
          style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}
        >
          {/* Accent line */}
          <div className="h-[2px] bg-gradient-to-r from-[#102a43] via-[#486581] to-[#829ab1]" />

          {/* Filtros dentro do card */}
          <div className="px-5 py-4 border-b border-[#f1f5f9] dark:border-slate-700 flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#829ab1]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                value={filtro}
                onChange={e => setFiltro(e.target.value)}
                placeholder="Buscar empresa ou analista..."
                className="w-full pl-9 pr-4 py-2 rounded-lg text-sm bg-[#f8f9fb] dark:bg-slate-900 border border-[#e2e8f0] dark:border-slate-600 text-[#102a43] dark:text-slate-100 placeholder:text-[#829ab1] focus:outline-none focus:ring-2 focus:ring-[#102a43]/10 focus:border-[#9fb3c8] transition-all"
              />
            </div>
            <select
              value={usuarioFiltro}
              onChange={e => setUsuarioFiltro(e.target.value === "" ? "" : Number(e.target.value))}
              className="rounded-lg px-3 py-2 text-sm bg-[#f8f9fb] dark:bg-slate-900 border border-[#e2e8f0] dark:border-slate-600 text-[#334e68] dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-[#102a43]/10 transition-all min-w-[180px]"
            >
              <option value="">Todos os analistas</option>
              {usuarios.map(u => (
                <option key={u.id} value={u.id}>{u.nome}{u.cargo ? ` — ${u.cargo}` : ""}</option>
              ))}
            </select>
          </div>

          {/* Lista */}
          {carregando ? (
            <div className="flex justify-center py-16">
              <div className="w-7 h-7 border-2 border-[#d9e2ec] border-t-[#102a43] rounded-full animate-spin" />
            </div>
          ) : visiveis.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-[#829ab1]">
              <svg className="w-9 h-9 mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <p className="text-sm font-medium">Nenhum resultado encontrado.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 p-4">
              {usuarios
                .filter(u => usuarioFiltro === "" || u.id === usuarioFiltro)
                .map(u => {
                  const empresasDoUsuario = visiveis.filter(i => i.usuario_id === u.id);
                  if (empresasDoUsuario.length === 0) return null;

                  const finalizadas = empresasDoUsuario.filter(e => e.status === "finalizada").length;
                  const emAndamento = empresasDoUsuario.filter(e => e.status === "em_andamento").length;
                  const pendentes   = empresasDoUsuario.filter(e =>
                    ["extratos_pendentes", "pendencia_fiscal", "pendencia_juridica"].includes(e.status)
                  ).length;
                  const pct = empresasDoUsuario.length > 0
                    ? Math.round((finalizadas / empresasDoUsuario.length) * 100)
                    : 0;
                  const perfColor = pendentes > 0 ? "#dc2626" : pct >= 80 ? "#16a34a" : pct >= 40 ? "#d97706" : "#dc2626";
                  const perfLabel = pendentes > 0 ? "Atenção" : pct >= 80 ? "No prazo" : pct >= 40 ? "Andamento" : "Iniciando";

                  return (
                    <div key={u.id} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col">
                      {/* Cabeçalho do analista */}
                      <div className="px-4 py-4 border-b border-slate-100 dark:border-slate-700/50">
                        <div className="flex items-center gap-3">
                          <div
                            className="w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 bg-slate-100 text-slate-700"
                          >
                            {u.nome.split(" ").map((w: string) => w[0]).join("").toUpperCase().slice(0, 2)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <p className="font-semibold text-sm text-[#102a43] dark:text-slate-100 truncate">{u.nome}</p>
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full"
                                style={{ backgroundColor: `${perfColor}18`, color: perfColor, border: `1px solid ${perfColor}30` }}>
                                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: perfColor }} />
                                {perfLabel}
                              </span>
                            </div>
                            {u.cargo && (
                              <p className="text-xs font-medium text-[#486581] dark:text-slate-400 mt-0.5">{u.cargo}</p>
                            )}
                          </div>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <span className="text-xs font-semibold text-[#486581] dark:text-navy-400 bg-[#f0f4f8] dark:bg-navy-900/40 px-2.5 py-1 rounded-md tabular-nums">
                              {empresasDoUsuario.length} empresa{empresasDoUsuario.length !== 1 ? "s" : ""}
                            </span>
                            {finalizadas > 0 && (
                              <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 dark:bg-emerald-900/20 dark:text-emerald-400 px-2 py-0.5 rounded-md ring-1 ring-emerald-200/60 dark:ring-emerald-800/40 tabular-nums">
                                {finalizadas} finaliz.
                              </span>
                            )}
                            {pendentes > 0 && (
                              <span className="text-xs font-semibold text-rose-700 bg-rose-50 dark:bg-rose-900/20 dark:text-rose-400 px-2 py-0.5 rounded-md ring-1 ring-rose-200/60 dark:ring-rose-800/40 tabular-nums">
                                {pendentes} pendente{pendentes !== 1 ? "s" : ""}
                              </span>
                            )}
                          </div>
                        </div>
                        {/* Barra de progresso */}
                        <div className="mt-3 flex items-center gap-3 pl-12 pr-1">
                          <div className="flex-1 h-1.5 bg-[#e2e8f0] dark:bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-500"
                              style={{ width: `${pct}%`, backgroundColor: perfColor }}
                            />
                          </div>
                          <span className="text-[10px] font-bold tabular-nums" style={{ color: perfColor, minWidth: "32px", textAlign: "right" }}>
                            {pct}%
                          </span>
                          <span className="text-[10px] text-[#829ab1] dark:text-slate-500">
                            {finalizadas}/{empresasDoUsuario.length} finaliz.
                            {emAndamento > 0 && <span className="ml-1.5 text-amber-600 dark:text-amber-500">{emAndamento} em and.</span>}
                          </span>
                        </div>
                      </div>

                      {/* Empresas do analista */}
                      <div className="flex-1 overflow-y-auto max-h-56 divide-y divide-slate-100 dark:divide-slate-700/50">
                        {empresasDoUsuario.map(e => {
                          const cfg = STATUS_MAP[e.status || "iniciada"] ?? STATUS_MAP.iniciada;
                          return (
                            <div
                              key={e.id}
                              className="flex items-center gap-3 px-4 py-2.5 hover:bg-[#f8f9fb] dark:hover:bg-slate-700/20 transition-colors"
                            >
                              <span className="relative w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: cfg.dot }}>
                                {cfg.pulse && <span className="absolute inset-0 rounded-full animate-ping opacity-75" style={{ backgroundColor: cfg.dot }} />}
                              </span>
                              <div className="flex-1 min-w-0">
                                <p className="text-xs font-medium text-[#243b53] dark:text-slate-200 truncate">{e.nome}</p>
                                {e.cnpj && (
                                  <p className="text-[10px] font-mono text-[#829ab1] mt-0.5">{e.cnpj}</p>
                                )}
                              </div>
                              <Badge variant={cfg.variant}>{cfg.label}</Badge>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
            </div>
          )}

          {/* Footer */}
          {!carregando && visiveis.length > 0 && (
            <div className="px-5 py-3 border-t border-[#f1f5f9] dark:border-slate-700 bg-[#f8f9fb]/50 dark:bg-slate-800/30">
              <p className="text-xs text-[#829ab1] dark:text-slate-500">
                {visiveis.length} empresa{visiveis.length !== 1 ? "s" : ""} ·{" "}
                {usuarios.filter(u => usuarioFiltro === "" || u.id === usuarioFiltro).filter(u => visiveis.some(v => v.usuario_id === u.id)).length} analista{usuarios.length !== 1 ? "s" : ""}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
