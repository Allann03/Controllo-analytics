"use client";
import { useEffect, useState, useCallback } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");
function tk() { return localStorage.getItem("controllo_token") ?? ""; }

interface ContaReferencial {
  id: number;
  codigo: string;
  descricao: string;
  grupo: string;
  nivel: number;
  label: string;
}

interface Mapeamento {
  id: number;
  conta_cliente: string;
  descricao_cliente: string;
  conta_referencial_id: number | null;
  conta_referencial: { id: number; codigo: string; descricao: string } | null;
  sugestao_automatica: boolean;
  mapeado: boolean;
}

const GRUPO_LABEL: Record<string, string> = {
  ativo: "Ativo",
  passivo: "Passivo",
  pl: "Patrimônio Líquido",
  receita: "Receitas",
  custo_despesa: "Custos e Despesas",
};

const GRUPO_COR: Record<string, string> = {
  ativo:         "text-blue-400  bg-blue-400/10  border-blue-400/30",
  passivo:       "text-rose-400  bg-rose-400/10  border-rose-400/30",
  pl:            "text-indigo-500 bg-indigo-500/10 border-indigo-400/30",
  receita:       "text-emerald-400 bg-emerald-400/10 border-emerald-400/30",
  custo_despesa: "text-amber-400 bg-amber-400/10  border-amber-400/30",
};

export default function PlanoContasPage() {
  const { empresaSelecionada } = useEmpresa();

  const [planoRef, setPlanoRef] = useState<ContaReferencial[]>([]);
  const [mapeamentos, setMapeamentos] = useState<Mapeamento[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [toast, setToast] = useState<{ msg: string; tipo: "ok" | "erro" } | null>(null);

  // Form nova conta
  const [novaContaCodigo, setNovaContaCodigo] = useState("");
  const [novaContaDesc, setNovaContaDesc] = useState("");
  const [adicionando, setAdicionando] = useState(false);
  const [mostrarForm, setMostrarForm] = useState(false);

  // Filtro
  const [filtro, setFiltro] = useState<"todos" | "mapeados" | "pendentes">("todos");
  const [busca, setBusca] = useState("");

  const showToast = (msg: string, tipo: "ok" | "erro") => {
    setToast({ msg, tipo });
    setTimeout(() => setToast(null), 3500);
  };

  const carregarPlano = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/plano-contas`, {
        headers: { Authorization: `Bearer ${tk()}` },
      });
      if (res.ok) setPlanoRef(await res.json());
    } catch { /* silencioso */ }
  }, []);

  const carregarMapeamentos = useCallback(async (empresaId: number) => {
    setCarregando(true);
    try {
      const res = await fetch(`${API}/api/plano-contas/mapeamento/${empresaId}`, {
        headers: { Authorization: `Bearer ${tk()}` },
      });
      if (res.ok) setMapeamentos(await res.json());
    } catch {
      showToast("Erro ao carregar mapeamentos", "erro");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => { carregarPlano(); }, [carregarPlano]);

  useEffect(() => {
    if (empresaSelecionada?.id) {
      carregarMapeamentos(empresaSelecionada.id);
    } else {
      setMapeamentos([]);
    }
  }, [empresaSelecionada, carregarMapeamentos]);

  async function adicionarConta(ev: React.FormEvent) {
    ev.preventDefault();
    if (!empresaSelecionada) return;
    if (!novaContaCodigo.trim()) { showToast("Código da conta é obrigatório.", "erro"); return; }

    setAdicionando(true);
    try {
      const res = await fetch(`${API}/api/plano-contas/conta-cliente/${empresaSelecionada.id}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${tk()}`, "Content-Type": "application/json" },
        body: JSON.stringify({ conta_cliente: novaContaCodigo.trim(), descricao_cliente: novaContaDesc.trim() }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail || "Erro ao adicionar conta.");
      }
      showToast("Conta adicionada! Sugestão de mapeamento gerada automaticamente.", "ok");
      setNovaContaCodigo(""); setNovaContaDesc(""); setMostrarForm(false);
      carregarMapeamentos(empresaSelecionada.id);
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : "Erro ao adicionar", "erro");
    } finally {
      setAdicionando(false);
    }
  }

  async function salvarMapeamento(mapeamentoId: number, contaReferencialId: number | null, contaCliente: string, descricaoCliente: string) {
    try {
      const res = await fetch(`${API}/api/plano-contas/mapeamento/${mapeamentoId}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${tk()}`, "Content-Type": "application/json" },
        body: JSON.stringify({ conta_cliente: contaCliente, descricao_cliente: descricaoCliente, conta_referencial_id: contaReferencialId }),
      });
      if (!res.ok) throw new Error();
      showToast("Mapeamento salvo!", "ok");
      // Atualiza localmente sem recarregar tudo
      setMapeamentos(prev => prev.map(m =>
        m.id === mapeamentoId
          ? {
              ...m,
              conta_referencial_id: contaReferencialId,
              sugestao_automatica: false,
              mapeado: contaReferencialId !== null,
              conta_referencial: contaReferencialId
                ? planoRef.find(r => r.id === contaReferencialId)
                  ? { id: contaReferencialId, codigo: planoRef.find(r => r.id === contaReferencialId)!.codigo, descricao: planoRef.find(r => r.id === contaReferencialId)!.descricao }
                  : null
                : null,
            }
          : m
      ));
    } catch {
      showToast("Erro ao salvar mapeamento", "erro");
    }
  }

  async function removerMapeamento(mapeamentoId: number) {
    if (!confirm("Remover esta conta do mapeamento?")) return;
    try {
      const res = await fetch(`${API}/api/plano-contas/mapeamento/${mapeamentoId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${tk()}` },
      });
      if (!res.ok) throw new Error();
      showToast("Conta removida.", "ok");
      setMapeamentos(prev => prev.filter(m => m.id !== mapeamentoId));
    } catch {
      showToast("Erro ao remover", "erro");
    }
  }

  const mapeamentosFiltrados = mapeamentos.filter(m => {
    if (filtro === "mapeados" && !m.mapeado) return false;
    if (filtro === "pendentes" && m.mapeado) return false;
    if (busca.trim()) {
      const q = busca.toLowerCase();
      return m.conta_cliente.toLowerCase().includes(q) || m.descricao_cliente.toLowerCase().includes(q);
    }
    return true;
  });

  const stats = {
    total: mapeamentos.length,
    mapeados: mapeamentos.filter(m => m.mapeado && !m.sugestao_automatica).length,
    sugestoes: mapeamentos.filter(m => m.mapeado && m.sugestao_automatica).length,
    pendentes: mapeamentos.filter(m => !m.mapeado).length,
  };

  const pct = stats.total > 0 ? Math.round(((stats.mapeados + stats.sugestoes) / stats.total) * 100) : 0;

  // Agrupa plano referencial por grupo para o select
  const planoAgrupado = planoRef.reduce<Record<string, ContaReferencial[]>>((acc, c) => {
    if (!acc[c.grupo]) acc[c.grupo] = [];
    acc[c.grupo].push(c);
    return acc;
  }, {});

  return (
    <div className="min-h-full bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-6 right-6 z-50 px-5 py-3 rounded-xl border text-sm font-semibold shadow-2xl ${
          toast.tipo === "ok"
            ? "bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-600/20 dark:border-emerald-500/40 dark:text-emerald-300"
            : "bg-red-50 border-red-200 text-red-700 dark:bg-red-600/20 dark:border-red-500/40 dark:text-red-300"
        }`}>{toast.msg}</div>
      )}

      {/* Header */}
      <header className="px-8 pt-8 pb-6 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight">
              Plano de <span className="text-navy-600 dark:text-navy-400">Contas</span>
            </h1>
            <p className="text-slate-500 text-sm mt-1">
              Mapeamento De-Para entre o plano do cliente e o plano referencial do sistema
            </p>
          </div>
          {empresaSelecionada && (
            <button
              onClick={() => setMostrarForm(v => !v)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all"
              style={{ background: "#1e3a5f" }}
              onMouseEnter={e => (e.currentTarget.style.background = "#3D3A63")}
              onMouseLeave={e => (e.currentTarget.style.background = "#1e3a5f")}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Adicionar Conta
            </button>
          )}
        </div>
      </header>

      <div className="px-8 py-6 space-y-6">

        {/* Sem empresa selecionada */}
        {!empresaSelecionada && (
          <div className="flex flex-col items-center justify-center py-24 border border-dashed border-slate-700/60 rounded-2xl text-slate-500">
            <svg className="w-12 h-12 mb-4 opacity-25" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
            <p className="text-sm font-semibold mb-1">Nenhuma empresa selecionada</p>
            <p className="text-xs text-slate-600">Selecione uma empresa na barra lateral para ver o mapeamento de contas</p>
          </div>
        )}

        {empresaSelecionada && (
          <>
            {/* Empresa selecionada + stats */}
            <div className="flex flex-col md:flex-row gap-4">
              {/* Info empresa */}
              <div className="flex items-center gap-3 px-4 py-3 bg-[#1e3a5f]/40 border border-[#102a43]/20 rounded-xl flex-1">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-black flex-shrink-0" style={{ background: "#1e3a5f" }}>
                  {(empresaSelecionada.nome_fantasia || empresaSelecionada.nome).slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-200">{empresaSelecionada.nome_fantasia || empresaSelecionada.nome}</p>
                  {empresaSelecionada.cnpj && <p className="text-[11px] text-slate-500 font-mono">{empresaSelecionada.cnpj}</p>}
                </div>
              </div>

              {/* Progresso */}
              <div className="flex items-center gap-4 px-4 py-3 bg-slate-800/50 border border-slate-700/60 rounded-xl flex-1">
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs text-slate-400">Progresso do mapeamento</span>
                    <span className="text-xs font-bold" style={{ color: pct === 100 ? "#4ade80" : "#102a43" }}>{pct}%</span>
                  </div>
                  <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: pct === 100 ? "#4ade80" : "#102a43" }} />
                  </div>
                </div>
                <div className="flex gap-4 text-center">
                  <div>
                    <p className="text-lg font-black text-slate-200 font-mono">{stats.total}</p>
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">Total</p>
                  </div>
                  <div>
                    <p className="text-lg font-black text-emerald-400 font-mono">{stats.mapeados}</p>
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">Confirmados</p>
                  </div>
                  <div>
                    <p className="text-lg font-black text-amber-400 font-mono">{stats.sugestoes}</p>
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">Sugestões</p>
                  </div>
                  <div>
                    <p className="text-lg font-black text-rose-400 font-mono">{stats.pendentes}</p>
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">Pendentes</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Form nova conta */}
            {mostrarForm && (
              <form onSubmit={adicionarConta} className="bg-slate-800/60 border border-[#102a43]/20 rounded-2xl p-5">
                <p className="text-sm font-bold text-slate-200 mb-4">Nova Conta do Cliente</p>
                <div className="flex gap-3 items-end">
                  <div className="w-44">
                    <label className="block text-[11px] font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Código *</label>
                    <input
                      value={novaContaCodigo} onChange={e => setNovaContaCodigo(e.target.value)}
                      placeholder="Ex: 1.01.01"
                      required
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm font-mono placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#102a43]/50 transition-all"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="block text-[11px] font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Descrição</label>
                    <input
                      value={novaContaDesc} onChange={e => setNovaContaDesc(e.target.value)}
                      placeholder="Ex: Caixa Geral, Banco Itaú CC, Clientes a Receber..."
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#102a43]/50 transition-all"
                    />
                  </div>
                  <button type="submit" disabled={adicionando}
                    className="px-5 py-2 rounded-xl text-sm font-semibold text-white disabled:opacity-50 transition-all"
                    style={{ background: "#1e3a5f" }}
                  >
                    {adicionando ? "Adicionando..." : "Adicionar"}
                  </button>
                  <button type="button" onClick={() => setMostrarForm(false)}
                    className="px-4 py-2 rounded-xl border border-slate-700 text-slate-400 hover:text-white text-sm transition-all">
                    Cancelar
                  </button>
                </div>
                <p className="text-[11px] text-slate-500 mt-2">
                  O sistema sugerirá automaticamente o mapeamento com base no código e descrição informados.
                </p>
              </form>
            )}

            {/* Legenda */}
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" /> Mapeamento confirmado pelo usuário
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-400" /> Sugestão automática (confirme ou corrija)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-rose-400" /> Pendente — sem mapeamento
              </span>
            </div>

            {/* Filtros + busca */}
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1 max-w-xs">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input value={busca} onChange={e => setBusca(e.target.value)} placeholder="Buscar conta..."
                  className="w-full pl-9 pr-4 py-2 bg-slate-800/60 border border-slate-700 rounded-xl text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:border-[#102a43]/50 transition-all"
                />
              </div>
              <div className="flex gap-2">
                {(["todos", "pendentes", "mapeados"] as const).map(f => (
                  <button key={f} onClick={() => setFiltro(f)}
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                      filtro === f
                        ? f === "pendentes" ? "bg-rose-500/15 border-rose-500/40 text-rose-400"
                          : f === "mapeados" ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-400"
                          : "border-[#102a43]/50 text-white"
                        : "bg-transparent border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200"
                    }`}
                    style={filtro === f && f === "todos" ? { background: "#1e3a5f" } : {}}
                  >
                    {f === "todos" ? `Todos (${stats.total})` : f === "pendentes" ? `Pendentes (${stats.pendentes})` : `Mapeados (${stats.mapeados + stats.sugestoes})`}
                  </button>
                ))}
              </div>
            </div>

            {/* Tabela De-Para */}
            {carregando ? (
              <div className="flex items-center justify-center py-16">
                <div className="w-8 h-8 border-4 border-[#102a43]/30 border-t-[#102a43] rounded-full animate-spin" />
              </div>
            ) : mapeamentosFiltrados.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 border border-dashed border-slate-700/60 rounded-2xl text-slate-500">
                <svg className="w-10 h-10 mb-3 opacity-25" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
                </svg>
                <p className="text-sm font-medium">
                  {mapeamentos.length === 0 ? "Nenhuma conta cadastrada ainda." : "Nenhuma conta encontrada com os filtros selecionados."}
                </p>
                {mapeamentos.length === 0 && (
                  <button onClick={() => setMostrarForm(true)} className="mt-3 text-xs" style={{ color: "#102a43" }}>
                    + Adicionar primeira conta
                  </button>
                )}
              </div>
            ) : (
              <div className="border border-slate-700/60 rounded-2xl overflow-hidden">
                {/* Header da tabela */}
                <div className="grid grid-cols-[auto_1fr_auto_1fr_auto] gap-0 bg-slate-800/60 border-b border-slate-700/60 px-5 py-3">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest w-28">Código</span>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Descrição do Cliente</span>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest text-center px-6">→</span>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Conta Referencial</span>
                  <span className="w-8" />
                </div>

                {mapeamentosFiltrados.map((m, idx) => {
                  const statusDot = m.mapeado
                    ? m.sugestao_automatica ? "bg-amber-400" : "bg-emerald-400"
                    : "bg-rose-400";
                  const refConta = m.conta_referencial;

                  return (
                    <div key={m.id}
                      className={`grid grid-cols-[auto_1fr_auto_1fr_auto] gap-0 items-center px-5 py-3.5 border-b border-slate-800/60 hover:bg-slate-800/30 transition-colors ${idx === mapeamentosFiltrados.length - 1 ? "border-b-0" : ""}`}
                    >
                      {/* Código */}
                      <div className="flex items-center gap-2 w-28">
                        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot}`} />
                        <span className="text-xs font-mono font-bold text-slate-300">{m.conta_cliente}</span>
                      </div>

                      {/* Descrição cliente */}
                      <div className="min-w-0 pr-4">
                        <p className="text-sm text-slate-300 truncate">{m.descricao_cliente || <span className="text-slate-600 italic">Sem descrição</span>}</p>
                        {m.sugestao_automatica && (
                          <span className="text-[10px] text-amber-400/80 font-semibold">Sugestão automática — confirme ou corrija</span>
                        )}
                      </div>

                      {/* Seta */}
                      <div className="px-4 text-slate-600">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                        </svg>
                      </div>

                      {/* Select conta referencial */}
                      <div className="pr-4">
                        <select
                          value={m.conta_referencial_id ?? ""}
                          onChange={e => {
                            const val = e.target.value ? parseInt(e.target.value) : null;
                            salvarMapeamento(m.id, val, m.conta_cliente, m.descricao_cliente);
                          }}
                          className={`w-full px-3 py-2 rounded-xl text-xs font-medium border bg-slate-900 text-slate-200 focus:outline-none focus:ring-2 focus:ring-[#102a43]/40 transition-all ${
                            !m.mapeado ? "border-rose-500/40" :
                            m.sugestao_automatica ? "border-amber-500/40" :
                            "border-emerald-500/30"
                          }`}
                        >
                          <option value="">— Selecionar conta —</option>
                          {Object.entries(planoAgrupado).map(([grupo, contas]) => (
                            <optgroup key={grupo} label={GRUPO_LABEL[grupo] || grupo}>
                              {contas.map(c => (
                                <option key={c.id} value={c.id}
                                  disabled={c.nivel === 1}
                                  style={{ paddingLeft: c.nivel === 3 ? "16px" : "8px", fontWeight: c.nivel === 1 ? "bold" : "normal" }}
                                >
                                  {c.nivel === 1 ? "▸ " : c.nivel === 2 ? "  ▹ " : "    "}{c.codigo} — {c.descricao}
                                </option>
                              ))}
                            </optgroup>
                          ))}
                        </select>

                        {/* Badge do grupo da conta referencial */}
                        {refConta && (() => {
                          const contaPleno = planoRef.find(r => r.id === refConta.id);
                          const grupo = contaPleno?.grupo;
                          if (!grupo) return null;
                          return (
                            <span className={`inline-flex mt-1 items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${GRUPO_COR[grupo] || ""}`}>
                              {GRUPO_LABEL[grupo] || grupo}
                            </span>
                          );
                        })()}
                      </div>

                      {/* Remover */}
                      <button onClick={() => removerMapeamento(m.id)}
                        className="p-1.5 rounded-lg text-slate-600 hover:text-rose-400 hover:bg-rose-400/10 transition-all"
                        title="Remover conta"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Plano Referencial — Legenda */}
            <details className="group">
              <summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-2 select-none">
                <svg className="w-3.5 h-3.5 transition-transform group-open:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                Ver plano de contas referencial completo do sistema
              </summary>
              <div className="mt-4 border border-slate-700/60 rounded-xl overflow-hidden">
                <div className="bg-slate-800/60 px-4 py-2 border-b border-slate-700/60">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Plano de Contas Referencial — Controllo</p>
                </div>
                <div className="divide-y divide-slate-800/60">
                  {planoRef.map(c => (
                    <div key={c.id} className="flex items-center gap-3 px-4 py-2.5 hover:bg-slate-800/30 transition-colors"
                      style={{ paddingLeft: `${(c.nivel - 1) * 20 + 16}px` }}>
                      <span className={`text-xs font-mono font-bold w-16 flex-shrink-0 ${
                        c.nivel === 1 ? "text-slate-200" : c.nivel === 2 ? "text-slate-400" : "text-slate-500"
                      }`}>{c.codigo}</span>
                      <span className={`text-xs flex-1 ${
                        c.nivel === 1 ? "font-bold text-slate-200" : c.nivel === 2 ? "font-medium text-slate-300" : "text-slate-400"
                      }`}>{c.descricao}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold ${GRUPO_COR[c.grupo] || ""}`}>
                        {GRUPO_LABEL[c.grupo] || c.grupo}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </details>
          </>
        )}
      </div>
    </div>
  );
}
