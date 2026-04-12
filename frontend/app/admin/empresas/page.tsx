"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import { Building2 } from "lucide-react";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

interface Empresa {
  id: number;
  nome: string;
  nome_fantasia: string;
  cnpj: string;
  ccm: string;
  observacoes: string;
  ativa: boolean;
  carteira_usuario_id: number | null;
  carteira_usuario_nome: string | null;
  criado_em: string;
  atualizado_em: string;
  regime_tributario?: string | null;
  segmento?: string | null;
}

interface PaginatedResponse {
  items: Empresa[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

function tk() { return localStorage.getItem("controllo_token") ?? ""; }

function aplicarMascaraCNPJ(valor: string): string {
  const n = valor.replace(/\D/g, "").slice(0, 14);
  if (n.length <= 2) return n;
  if (n.length <= 5) return `${n.slice(0,2)}.${n.slice(2)}`;
  if (n.length <= 8) return `${n.slice(0,2)}.${n.slice(2,5)}.${n.slice(5)}`;
  if (n.length <= 12) return `${n.slice(0,2)}.${n.slice(2,5)}.${n.slice(5,8)}/${n.slice(8)}`;
  return `${n.slice(0,2)}.${n.slice(2,5)}.${n.slice(5,8)}/${n.slice(8,12)}-${n.slice(12,14)}`;
}

function validarCNPJ(cnpj: string): boolean {
  const n = cnpj.replace(/\D/g, "");
  if (n.length !== 14 || n === n[0].repeat(14)) return false;
  const calc = (base: string, pesos: number[]) => {
    const soma = pesos.reduce((acc, p, i) => acc + parseInt(base[i]) * p, 0);
    const r = soma % 11;
    return r < 2 ? 0 : 11 - r;
  };
  const p1 = [5,4,3,2,9,8,7,6,5,4,3,2];
  const p2 = [6,5,4,3,2,9,8,7,6,5,4,3,2];
  return parseInt(n[12]) === calc(n, p1) && parseInt(n[13]) === calc(n, p2);
}

export default function AdminEmpresasPage() {
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [buscaInput, setBuscaInput] = useState("");
  const [busca, setBusca] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Toast
  const [toast, setToast] = useState<{ msg: string; tipo: "ok" | "erro" } | null>(null);

  // Modal criar/editar
  const [modalAberto, setModalAberto] = useState(false);
  const [editando, setEditando] = useState<Empresa | null>(null);
  const [salvando, setSalvando] = useState(false);

  // Campos do form
  const [nome, setNome] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [cnpjErro, setCnpjErro] = useState("");
  const [ccm, setCcm] = useState("");
  const [observacoes, setObservacoes] = useState("");

  // Modal exclusão
  const [modalExclusao, setModalExclusao] = useState<Empresa | null>(null);
  const [dadosEmpresa, setDadosEmpresa] = useState<{ has_data: boolean } | null>(null);
  const [nomeConfirmacao, setNomeConfirmacao] = useState("");
  const [excluindo, setExcluindo] = useState(false);

  const mostrarToast = (msg: string, tipo: "ok" | "erro") => {
    setToast({ msg, tipo });
    setTimeout(() => setToast(null), 3500);
  };

  const carregar = useCallback(async (p: number, q: string) => {
    setCarregando(true);
    try {
      const params = new URLSearchParams({ page: String(p), per_page: "20", busca: q });
      const res = await fetch(`${API}/api/empresas?${params}`, {
        headers: { Authorization: `Bearer ${tk()}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail || `HTTP ${res.status}`);
      }
      const data: PaginatedResponse = await res.json();
      setEmpresas(data.items);
      setTotalPages(data.pages);
      setTotal(data.total);
    } catch (e: unknown) {
      mostrarToast(e instanceof Error ? e.message : "Erro ao carregar empresas", "erro");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => { setBusca(buscaInput); setPage(1); }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [buscaInput]);

  useEffect(() => { carregar(page, busca); }, [page, busca, carregar]);

  function abrirNovo() {
    setEditando(null);
    setNome(""); setCnpj(""); setCnpjErro(""); setCcm(""); setObservacoes("");
    setModalAberto(true);
  }

  function abrirEditar(e: Empresa) {
    setEditando(e);
    setNome(e.nome); setCnpj(e.cnpj); setCnpjErro(""); setCcm(e.ccm); setObservacoes(e.observacoes);
    setModalAberto(true);
  }

  function handleCnpjChange(val: string) {
    const mascarado = aplicarMascaraCNPJ(val);
    setCnpj(mascarado);
    const nums = mascarado.replace(/\D/g, "");
    if (nums.length === 0) { setCnpjErro(""); return; }
    if (nums.length < 14) { setCnpjErro("CNPJ incompleto"); return; }
    setCnpjErro(validarCNPJ(mascarado) ? "" : "CNPJ inválido — dígito verificador incorreto");
  }

  async function salvar(ev: React.SyntheticEvent) {
    ev.preventDefault();
    if (cnpjErro && cnpj.replace(/\D/g, "").length > 0) { mostrarToast(cnpjErro, "erro"); return; }
    if (!nome.trim() || nome.trim().length < 2) { mostrarToast("Nome deve ter pelo menos 2 caracteres.", "erro"); return; }
    setSalvando(true);
    const body = { nome: nome.trim(), cnpj, ccm: ccm.trim(), observacoes: observacoes.trim() };
    try {
      const url = editando ? `${API}/api/empresas/${editando.id}` : `${API}/api/empresas`;
      const res = await fetch(url, {
        method: editando ? "PUT" : "POST",
        headers: { Authorization: `Bearer ${tk()}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail || "Erro ao salvar.");
      }
      mostrarToast(editando ? "Empresa atualizada!" : "Empresa cadastrada!", "ok");
      setModalAberto(false);
      carregar(page, busca);
    } catch (e: unknown) {
      mostrarToast(e instanceof Error ? e.message : "Erro ao salvar", "erro");
    } finally {
      setSalvando(false);
    }
  }

  async function abrirExclusao(e: Empresa) {
    setModalExclusao(e);
    setNomeConfirmacao("");
    setDadosEmpresa(null);
    try {
      const res = await fetch(`${API}/api/empresas/${e.id}/dados`, {
        headers: { Authorization: `Bearer ${tk()}` },
      });
      if (res.ok) {
        const d = await res.json();
        setDadosEmpresa(d);
      }
    } catch { /* silencioso */ }
  }

  async function confirmarExclusao() {
    if (!modalExclusao) return;
    if (dadosEmpresa?.has_data && nomeConfirmacao.trim().toLowerCase() !== modalExclusao.nome.trim().toLowerCase()) {
      mostrarToast("Nome não confere. Digite o nome exato da empresa.", "erro");
      return;
    }
    setExcluindo(true);
    try {
      const params = dadosEmpresa?.has_data ? `?nome_confirmacao=${encodeURIComponent(nomeConfirmacao.trim())}` : "";
      const res = await fetch(`${API}/api/empresas/${modalExclusao.id}${params}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${tk()}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail || "Erro ao excluir.");
      }
      mostrarToast("Empresa excluída com sucesso.", "ok");
      setModalExclusao(null);
      carregar(page, busca);
    } catch (e: unknown) {
      mostrarToast(e instanceof Error ? e.message : "Erro ao excluir", "erro");
    } finally {
      setExcluindo(false);
    }
  }

  const cnpjNums = cnpj.replace(/\D/g, "");
  const cnpjStatus = cnpjNums.length === 0 ? "vazio" : cnpjNums.length < 14 ? "incompleto" : cnpjErro ? "invalido" : "valido";

  return (
    <div className="min-h-full bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">

      {toast && (
        <div className={`fixed top-6 right-6 z-50 flex items-center gap-3 px-5 py-3.5 rounded-2xl border text-sm font-semibold shadow-2xl ${
          toast.tipo === "ok"
            ? "bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-950/90 dark:border-emerald-500/30 dark:text-emerald-300"
            : "bg-red-50 border-red-200 text-red-700 dark:bg-red-950/90 dark:border-red-500/30 dark:text-red-300"
        }`}>
          {toast.tipo === "ok"
            ? <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
            : <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          }
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <header className="px-6 pt-6 pb-4 border-b border-slate-100 dark:border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div>
            <div className="inline-flex items-center gap-2 mb-3">
              <span className="px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-widest bg-navy-50 border border-navy-200 text-navy-700 dark:bg-navy-500/10 dark:border-navy-500/35 dark:text-navy-300">
                Administrador
              </span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight">
              Gestão de{" "}
              <span className="text-navy-600 dark:text-navy-400">Empresas</span>
            </h1>
            <p className="text-sm mt-1.5 text-slate-500 dark:text-slate-400">
              Cadastre e gerencie as empresas do escritório — {total} cadastrada{total !== 1 ? "s" : ""}
            </p>
          </div>
          <button
            onClick={abrirNovo}
            data-notheme
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold text-white transition-colors active:scale-95 flex-shrink-0 bg-navy-600 hover:bg-navy-700 dark:bg-navy-500 dark:hover:bg-navy-600"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Nova Empresa
          </button>
        </div>
      </header>

      <div className="px-6 py-5 space-y-4">

        {/* Busca + contador */}
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-sm">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              value={buscaInput} onChange={e => setBuscaInput(e.target.value)}
              placeholder="Buscar por nome, CNPJ ou CCM..."
              className="w-full pl-9 pr-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-200 text-sm placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-900/20 transition-all"
            />
          </div>
          <p className="text-slate-500 text-sm">{total} empresa{total !== 1 ? "s" : ""} cadastrada{total !== 1 ? "s" : ""}</p>
        </div>

        {/* Tabela */}
        {carregando ? (
          <div className="rounded-2xl overflow-hidden space-y-0 page-enter"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <div style={{ height: "1px", background: "linear-gradient(90deg, #102a43 0%, #3b6ea5 60%, transparent 100%)" }} />
            <div className="px-5 py-3.5 flex gap-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              {["w-20","w-28","w-16","w-24","w-20","w-14"].map((w, i) => (
                <div key={i} className={`skeleton h-3 ${w} rounded`} />
              ))}
            </div>
            {[...Array(6)].map((_, i) => (
              <div key={i} className="px-5 py-4 flex items-center gap-4" style={{ borderBottom: "1px solid rgba(79,106,255,0.05)" }}>
                <div className="skeleton w-8 h-8 rounded-xl flex-shrink-0" />
                <div className="skeleton h-3.5 w-40 rounded" />
                <div className="skeleton h-3 w-32 rounded ml-auto" />
                <div className="skeleton h-3 w-20 rounded" />
                <div className="skeleton h-5 w-24 rounded-full" />
                <div className="skeleton h-6 w-16 rounded-lg ml-auto" />
              </div>
            ))}
          </div>
        ) : empresas.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 border border-dashed border-slate-300 dark:border-slate-700/60 rounded-2xl">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <Building2 className="w-8 h-8 text-slate-400 dark:text-slate-500" />
            </div>
            <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
              {buscaInput ? "Nenhuma empresa encontrada." : "Nenhuma empresa cadastrada."}
            </p>
            <p className="text-xs mt-1 text-slate-400 dark:text-slate-500">
              {buscaInput ? "Tente ajustar os filtros de busca." : "Cadastre a primeira empresa para começar."}
            </p>
            {!buscaInput && (
              <button onClick={abrirNovo} className="mt-4 flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-navy-600 hover:bg-navy-700 transition-colors">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                Cadastrar primeira empresa
              </button>
            )}
          </div>
        ) : (
          <div className="rounded-2xl overflow-hidden"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              boxShadow: "0 4px 32px rgba(0,0,0,0.25)",
            }}>
            {/* Accent line */}
            <div style={{ height: "1px", background: "linear-gradient(90deg, #102a43 0%, #3b6ea5 60%, transparent 100%)" }} />
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
                  <th className="text-left px-5 py-3.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Nome</th>
                  <th className="text-left px-5 py-3.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">CNPJ</th>
                  <th className="text-left px-5 py-3.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">CCM</th>
                  <th className="text-left px-5 py-3.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Regime</th>
                  <th className="text-left px-5 py-3.5 text-[10px] font-bold uppercase tracking-wider hidden lg:table-cell text-slate-500 dark:text-slate-400">Observação</th>
                  <th className="text-left px-5 py-3.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Carteira</th>
                  <th className="text-right px-5 py-3.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Ações</th>
                </tr>
              </thead>
              <tbody>
                {empresas.map(e => (
                  <tr key={e.id} className="border-b border-slate-100 dark:border-slate-700/30 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700/20 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-700/50 flex items-center justify-center flex-shrink-0">
                          <Building2 className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                        </div>
                        <div>
                          <span className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>{e.nome}</span>
                          {e.segmento && (
                            <p className="text-[10px] mt-0.5" style={{ color: "var(--text-muted)" }}>{e.segmento}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-xs" style={{ color: "var(--text-secondary)" }}>
                      {e.cnpj || <span style={{ color: "var(--text-muted)" }}>—</span>}
                    </td>
                    <td className="px-5 py-3.5 text-xs" style={{ color: "var(--text-secondary)" }}>
                      {e.ccm || <span style={{ color: "var(--text-muted)" }}>—</span>}
                    </td>
                    <td className="px-5 py-3.5 text-xs" style={{ color: "var(--text-secondary)" }}>
                      {e.regime_tributario ? (
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold ${
                          e.regime_tributario === 'simples' ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20' :
                          e.regime_tributario === 'presumido' ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-500/20' :
                          e.regime_tributario === 'real' ? 'bg-violet-50 dark:bg-violet-500/10 text-violet-700 dark:text-violet-400 border border-violet-200 dark:border-violet-500/20' :
                          'bg-slate-50 dark:bg-slate-700/30 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-600/30'
                        }`}>
                          {e.regime_tributario === 'simples' ? 'Simples' : e.regime_tributario === 'presumido' ? 'Presumido' : e.regime_tributario === 'real' ? 'Lucro Real' : e.regime_tributario}
                        </span>
                      ) : (
                        <span style={{ color: "var(--text-muted)" }}>—</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-xs max-w-xs hidden lg:table-cell" style={{ color: "var(--text-secondary)" }}>
                      {e.observacoes
                        ? <span className="whitespace-pre-wrap">{e.observacoes}</span>
                        : <span style={{ color: "var(--text-muted)" }}>—</span>
                      }
                    </td>
                    <td className="px-5 py-3.5">
                      {e.carteira_usuario_nome ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-blue-50 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/20 text-blue-700 dark:text-blue-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 dark:bg-blue-400" />
                          {e.carteira_usuario_nome}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 dark:bg-emerald-400" />
                          Disponível
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => abrirEditar(e)}
                          className="p-2 rounded-xl text-slate-500 hover:text-[#3b6ea5] hover:bg-[#102a43]/10 border border-transparent hover:border-[#102a43]/20 transition-all"
                          title="Editar empresa"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => abrirExclusao(e)}
                          className="p-2 rounded-xl text-slate-500 hover:text-rose-400 hover:bg-rose-400/10 border border-transparent hover:border-rose-400/20 transition-all"
                          title="Excluir empresa"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Paginação */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-1">
            <p className="text-xs text-slate-500">
              {total} empresa{total !== 1 ? "s" : ""} — página {page} de {totalPages}
            </p>
            <div className="flex items-center gap-1">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                className="p-1.5 rounded-lg text-slate-500 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-all">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
              </button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const start = Math.max(1, Math.min(page - 2, totalPages - 4));
                const num = start + i;
                return (
                  <button key={num} onClick={() => setPage(num)}
                    className={`w-8 h-8 rounded-lg text-xs font-semibold transition-all ${num === page ? "text-white" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}
                    style={num === page ? { background: "#1e3a5f" } : {}}
                  >{num}</button>
                );
              })}
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                className="p-1.5 rounded-lg text-slate-500 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-all">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── MODAL CRIAR/EDITAR ── */}
      {modalAberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
              <h2 className="font-bold text-lg text-slate-900 dark:text-white">{editando ? "Editar Empresa" : "Nova Empresa"}</h2>
              <button onClick={() => setModalAberto(false)} className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-white rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-all">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <form onSubmit={salvar} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wider">Nome da Empresa *</label>
                <input
                  value={nome} onChange={e => setNome(e.target.value)} required minLength={2}
                  placeholder="Ex: Empresa ABC Comércio Ltda"
                  className="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-sm placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-900/20 focus:border-blue-700 transition-all"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wider">
                    CNPJ <span className="text-slate-400 dark:text-slate-600 normal-case font-normal">(opcional)</span>
                  </label>
                  <input
                    value={cnpj} onChange={e => handleCnpjChange(e.target.value)}
                    placeholder="00.000.000/0001-00"
                    className={`w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-800 border rounded-xl text-slate-900 dark:text-white text-sm font-mono placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 transition-all ${
                      cnpjStatus === "valido"     ? "border-emerald-500 focus:ring-emerald-700/20" :
                      cnpjStatus === "invalido"   ? "border-rose-600 focus:ring-rose-700/20" :
                      cnpjStatus === "incompleto" ? "border-amber-500 focus:ring-amber-700/20" :
                                                    "border-slate-200 dark:border-slate-700 focus:ring-blue-900/20 focus:border-blue-700"
                    }`}
                  />
                  {cnpjStatus === "valido" && (
                    <p className="text-[11px] text-emerald-700 dark:text-emerald-400 mt-1 flex items-center gap-1">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                      Válido
                    </p>
                  )}
                  {cnpjStatus === "incompleto" && (
                    <p className="text-[11px] text-amber-700 dark:text-amber-400 mt-1">
                      Incompleto — <button type="button" onClick={() => { setCnpj(""); setCnpjErro(""); }} className="underline hover:text-slate-900 dark:hover:text-white">limpar</button>
                    </p>
                  )}
                  {cnpjStatus === "invalido" && <p className="text-[11px] text-rose-700 dark:text-rose-400 mt-1">CNPJ inválido</p>}
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wider">
                    CCM <span className="text-slate-400 dark:text-slate-600 normal-case font-normal">(opcional)</span>
                  </label>
                  <input
                    value={ccm} onChange={e => setCcm(e.target.value)}
                    placeholder="Inscrição municipal"
                    className="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-sm font-mono placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-900/20 focus:border-blue-700 transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wider">
                  Observação <span className="text-slate-400 dark:text-slate-600 normal-case font-normal">(opcional)</span>
                </label>
                <textarea
                  value={observacoes} onChange={e => setObservacoes(e.target.value.slice(0, 500))} rows={3}
                  placeholder="Ex: Cliente desde 2020, regime Simples Nacional, atenção especial na folha..."
                  className="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-sm placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-900/20 focus:border-blue-700 transition-all resize-none"
                />
                <p className="text-right text-[11px] text-slate-400 mt-0.5">{observacoes.length}/500</p>
              </div>

              <div className="flex gap-3 pt-1">
                <button type="button" onClick={() => setModalAberto(false)}
                  className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:border-slate-300 dark:hover:border-slate-600 text-sm font-medium transition-all">
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={salvando || (!!cnpjErro && cnpj.replace(/\D/g, "").length > 0)}
                  data-notheme
                  className="flex-1 py-2.5 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-bold bg-blue-900 hover:bg-blue-950 transition-all">
                  {salvando ? "Salvando..." : editando ? "Salvar alterações" : "Cadastrar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL EXCLUSÃO ── */}
      {modalExclusao && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
              <h2 className="font-bold text-lg text-rose-700 dark:text-rose-400">Excluir Empresa</h2>
              <button onClick={() => setModalExclusao(null)} className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-white rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-all">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-slate-700 dark:text-slate-300 text-sm">
                Tem certeza que deseja excluir{" "}
                <span className="font-bold text-slate-900 dark:text-white">{modalExclusao.nome}</span>?
              </p>

              {dadosEmpresa?.has_data && (
                <div className="bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 rounded-xl px-4 py-3 text-sm text-rose-800 dark:text-rose-300">
                  <p className="font-semibold mb-1">Esta empresa possui dados importados.</p>
                  <p className="text-xs text-rose-700 dark:text-rose-400">Ao excluir, todos os lançamentos, extratos e importações serão removidos permanentemente.</p>
                </div>
              )}

              {!dadosEmpresa?.has_data && (
                <p className="text-xs text-slate-500">Esta ação não pode ser desfeita.</p>
              )}

              {dadosEmpresa?.has_data && (
                <div>
                  <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wider">
                    Digite o nome da empresa para confirmar
                  </label>
                  <input
                    value={nomeConfirmacao}
                    onChange={e => setNomeConfirmacao(e.target.value)}
                    placeholder={modalExclusao.nome}
                    className="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-800 border border-rose-300 dark:border-rose-500/40 rounded-xl text-slate-900 dark:text-white text-sm placeholder-slate-400 dark:placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-rose-600/20 transition-all"
                  />
                </div>
              )}

              <div className="flex gap-3 pt-1">
                <button type="button" onClick={() => setModalExclusao(null)}
                  className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:border-slate-300 dark:hover:border-slate-600 text-sm font-medium transition-all">
                  Cancelar
                </button>
                <button
                  onClick={confirmarExclusao}
                  disabled={excluindo || (!!dadosEmpresa?.has_data && nomeConfirmacao.trim().toLowerCase() !== modalExclusao.nome.trim().toLowerCase())}
                  className="flex-1 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold transition-all">
                  {excluindo ? "Excluindo..." : "Excluir definitivamente"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
