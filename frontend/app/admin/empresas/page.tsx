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
    <div className="min-h-full" style={{ background: "var(--bg-canvas)", color: "var(--text-primary)" }}>

      {toast && (
        <div
          className="fixed top-6 right-6 z-50 flex items-center gap-3 px-5 py-3.5 text-sm font-medium"
          style={{
            background: toast.tipo === "ok" ? "var(--success-subtle)" : "var(--danger-subtle)",
            border: `1px solid ${toast.tipo === "ok" ? "var(--success-border)" : "var(--danger-border)"}`,
            color: toast.tipo === "ok" ? "var(--success)" : "var(--danger)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-md)",
          }}
        >
          {toast.tipo === "ok"
            ? <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
            : <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          }
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <header className="px-6 pt-6 pb-4" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div>
            <p
              className="text-xs uppercase font-medium mb-2"
              style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}
            >
              Administrador
            </p>
            <h1 className="text-3xl font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
              Gestão de empresas
            </h1>
            <p className="text-sm mt-1.5" style={{ color: "var(--text-secondary)" }}>
              Cadastre e gerencie as empresas do escritório — {total} cadastrada{total !== 1 ? "s" : ""}
            </p>
          </div>
          <button
            onClick={abrirNovo}
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold transition-opacity active:scale-95 flex-shrink-0 hover:opacity-90"
            style={{
              background: "var(--accent)",
              color: "var(--text-inverse)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Nova empresa
          </button>
        </div>
      </header>

      <div className="px-6 py-5 space-y-4">

        {/* Busca + contador */}
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-sm">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: "var(--text-tertiary)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              value={buscaInput} onChange={e => setBuscaInput(e.target.value)}
              placeholder="Buscar por nome, CNPJ ou CCM..."
              className="w-full pl-9 pr-4 py-2 text-sm focus:outline-none transition-all"
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-default)",
                color: "var(--text-primary)",
                borderRadius: "var(--radius-md)",
              }}
              onFocus={ev => { ev.currentTarget.style.borderColor = "var(--border-focus)"; }}
              onBlur={ev => { ev.currentTarget.style.borderColor = "var(--border-default)"; }}
            />
          </div>
          <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>{total} empresa{total !== 1 ? "s" : ""} cadastrada{total !== 1 ? "s" : ""}</p>
        </div>

        {/* Tabela */}
        {carregando ? (
          <div
            className="overflow-hidden space-y-0 page-enter"
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <div className="px-5 py-3.5 flex gap-4" style={{ background: "var(--bg-elevated)", borderBottom: "1px solid var(--border-subtle)" }}>
              {["w-20","w-28","w-16","w-24","w-20","w-14"].map((w, i) => (
                <div key={i} className={`skeleton h-3 ${w} rounded`} />
              ))}
            </div>
            {[...Array(6)].map((_, i) => (
              <div key={i} className="px-5 py-4 flex items-center gap-4" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
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
          <div
            className="flex flex-col items-center justify-center py-16 px-6 text-center"
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <Building2 className="w-6 h-6 mb-4" style={{ color: "var(--text-tertiary)" }} strokeWidth={1.75} />
            <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
              {buscaInput ? "Nenhuma empresa encontrada" : "Nenhuma empresa cadastrada"}
            </p>
            <p className="text-xs mt-1" style={{ color: "var(--text-tertiary)" }}>
              {buscaInput ? "Tente ajustar os filtros de busca." : "Cadastre a primeira empresa para começar."}
            </p>
            {!buscaInput && (
              <button
                onClick={abrirNovo}
                className="mt-5 flex items-center gap-2 px-4 py-2 text-sm font-semibold transition-opacity hover:opacity-90"
                style={{
                  background: "var(--accent)",
                  color: "var(--text-inverse)",
                  borderRadius: "var(--radius-md)",
                }}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                Cadastrar primeira empresa
              </button>
            )}
          </div>
        ) : (
          <div
            className="overflow-hidden"
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <table className="w-full text-sm">
              <thead>
                <tr style={{ background: "var(--bg-elevated)", borderBottom: "1px solid var(--border-subtle)" }}>
                  <th className="text-left px-5 py-3.5 text-xs uppercase font-medium" style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}>Nome</th>
                  <th className="text-left px-5 py-3.5 text-xs uppercase font-medium" style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}>CNPJ</th>
                  <th className="text-left px-5 py-3.5 text-xs uppercase font-medium" style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}>CCM</th>
                  <th className="text-left px-5 py-3.5 text-xs uppercase font-medium" style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}>Regime</th>
                  <th className="text-left px-5 py-3.5 text-xs uppercase font-medium hidden lg:table-cell" style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}>Observação</th>
                  <th className="text-left px-5 py-3.5 text-xs uppercase font-medium" style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}>Carteira</th>
                  <th className="text-right px-5 py-3.5 text-xs uppercase font-medium" style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}>Ações</th>
                </tr>
              </thead>
              <tbody>
                {empresas.map(e => (
                  <tr
                    key={e.id}
                    className="last:border-0 transition-colors"
                    style={{ borderBottom: "1px solid var(--border-subtle)" }}
                    onMouseEnter={ev => { (ev.currentTarget as HTMLElement).style.background = "var(--bg-elevated)"; }}
                    onMouseLeave={ev => { (ev.currentTarget as HTMLElement).style.background = "transparent"; }}
                  >
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-8 h-8 flex items-center justify-center flex-shrink-0"
                          style={{ background: "var(--bg-inset)", borderRadius: "var(--radius-sm)" }}
                        >
                          <Building2 className="w-4 h-4" style={{ color: "var(--text-tertiary)" }} />
                        </div>
                        <div>
                          <span className="font-medium text-sm" style={{ color: "var(--text-primary)" }}>{e.nome}</span>
                          {e.segmento && (
                            <p className="text-[10px] mt-0.5" style={{ color: "var(--text-tertiary)" }}>{e.segmento}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 font-mono tabular-nums text-xs" style={{ color: "var(--text-secondary)" }}>
                      {e.cnpj || <span style={{ color: "var(--text-tertiary)" }}>—</span>}
                    </td>
                    <td className="px-5 py-3.5 text-xs" style={{ color: "var(--text-secondary)" }}>
                      {e.ccm || <span style={{ color: "var(--text-tertiary)" }}>—</span>}
                    </td>
                    <td className="px-5 py-3.5 text-xs">
                      {e.regime_tributario ? (() => {
                        const regime = e.regime_tributario;
                        const isSimples   = regime === "simples";
                        const isPresumido = regime === "presumido";
                        const isReal      = regime === "real";
                        const bg     = isSimples ? "var(--success-subtle)" : isPresumido ? "var(--accent-subtle)" : isReal ? "var(--warning-subtle)" : "var(--bg-elevated)";
                        const border = isSimples ? "var(--success-border)" : isPresumido ? "var(--accent-border)" : isReal ? "var(--warning-border)" : "var(--border-subtle)";
                        const color  = isSimples ? "var(--success)"        : isPresumido ? "var(--accent-text)"   : isReal ? "var(--warning)"        : "var(--text-secondary)";
                        const label  = isSimples ? "Simples" : isPresumido ? "Presumido" : isReal ? "Lucro Real" : regime;
                        return (
                          <span
                            className="inline-flex items-center px-2 py-0.5 text-[10px] font-medium"
                            style={{ background: bg, border: `1px solid ${border}`, color, borderRadius: "var(--radius-sm)" }}
                          >
                            {label}
                          </span>
                        );
                      })() : (
                        <span style={{ color: "var(--text-tertiary)" }}>—</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-xs max-w-xs hidden lg:table-cell" style={{ color: "var(--text-secondary)" }}>
                      {e.observacoes
                        ? <span className="whitespace-pre-wrap">{e.observacoes}</span>
                        : <span style={{ color: "var(--text-tertiary)" }}>—</span>
                      }
                    </td>
                    <td className="px-5 py-3.5">
                      {e.carteira_usuario_nome ? (
                        <span
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium"
                          style={{
                            background: "var(--accent-subtle)",
                            border: "1px solid var(--accent-border)",
                            color: "var(--accent-text)",
                            borderRadius: "var(--radius-sm)",
                          }}
                        >
                          <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--accent)" }} />
                          {e.carteira_usuario_nome}
                        </span>
                      ) : (
                        <span
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium"
                          style={{
                            background: "var(--success-subtle)",
                            border: "1px solid var(--success-border)",
                            color: "var(--success)",
                            borderRadius: "var(--radius-sm)",
                          }}
                        >
                          <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--success)" }} />
                          Disponível
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => abrirEditar(e)}
                          className="p-2 transition-colors"
                          style={{ color: "var(--text-tertiary)", borderRadius: "var(--radius-sm)" }}
                          onMouseEnter={ev => { ev.currentTarget.style.color = "var(--accent)"; ev.currentTarget.style.background = "var(--accent-subtle)"; }}
                          onMouseLeave={ev => { ev.currentTarget.style.color = "var(--text-tertiary)"; ev.currentTarget.style.background = "transparent"; }}
                          title="Editar empresa"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => abrirExclusao(e)}
                          className="p-2 transition-colors"
                          style={{ color: "var(--text-tertiary)", borderRadius: "var(--radius-sm)" }}
                          onMouseEnter={ev => { ev.currentTarget.style.color = "var(--danger)"; ev.currentTarget.style.background = "var(--danger-subtle)"; }}
                          onMouseLeave={ev => { ev.currentTarget.style.color = "var(--text-tertiary)"; ev.currentTarget.style.background = "transparent"; }}
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
            <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
              {total} empresa{total !== 1 ? "s" : ""} — página {page} de {totalPages}
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                className="p-1.5 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                style={{ color: "var(--text-tertiary)", borderRadius: "var(--radius-sm)" }}
                onMouseEnter={ev => { if (!ev.currentTarget.disabled) { ev.currentTarget.style.color = "var(--text-primary)"; ev.currentTarget.style.background = "var(--bg-elevated)"; } }}
                onMouseLeave={ev => { ev.currentTarget.style.color = "var(--text-tertiary)"; ev.currentTarget.style.background = "transparent"; }}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
              </button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const start = Math.max(1, Math.min(page - 2, totalPages - 4));
                const num = start + i;
                const isActive = num === page;
                return (
                  <button
                    key={num} onClick={() => setPage(num)}
                    className="w-8 h-8 text-xs font-semibold transition-colors"
                    style={{
                      background: isActive ? "var(--accent)" : "transparent",
                      color: isActive ? "var(--text-inverse)" : "var(--text-tertiary)",
                      borderRadius: "var(--radius-sm)",
                    }}
                    onMouseEnter={ev => { if (!isActive) { ev.currentTarget.style.color = "var(--text-primary)"; ev.currentTarget.style.background = "var(--bg-elevated)"; } }}
                    onMouseLeave={ev => { if (!isActive) { ev.currentTarget.style.color = "var(--text-tertiary)"; ev.currentTarget.style.background = "transparent"; } }}
                  >{num}</button>
                );
              })}
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                className="p-1.5 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                style={{ color: "var(--text-tertiary)", borderRadius: "var(--radius-sm)" }}
                onMouseEnter={ev => { if (!ev.currentTarget.disabled) { ev.currentTarget.style.color = "var(--text-primary)"; ev.currentTarget.style.background = "var(--bg-elevated)"; } }}
                onMouseLeave={ev => { ev.currentTarget.style.color = "var(--text-tertiary)"; ev.currentTarget.style.background = "transparent"; }}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── MODAL CRIAR/EDITAR ── */}
      {modalAberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}>
          <div
            className="w-full max-w-md overflow-hidden"
            style={{
              background: "var(--bg-overlay)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-lg)",
              boxShadow: "var(--shadow-lg)",
            }}
          >
            <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
              <h2 className="font-semibold text-lg" style={{ color: "var(--text-primary)" }}>{editando ? "Editar empresa" : "Nova empresa"}</h2>
              <button
                onClick={() => setModalAberto(false)}
                className="p-1.5 transition-colors"
                style={{ color: "var(--text-tertiary)", borderRadius: "var(--radius-sm)" }}
                onMouseEnter={ev => { ev.currentTarget.style.color = "var(--text-primary)"; ev.currentTarget.style.background = "var(--bg-elevated)"; }}
                onMouseLeave={ev => { ev.currentTarget.style.color = "var(--text-tertiary)"; ev.currentTarget.style.background = "transparent"; }}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <form onSubmit={salvar} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium mb-1.5 uppercase" style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}>Nome da empresa *</label>
                <input
                  value={nome} onChange={e => setNome(e.target.value)} required minLength={2}
                  placeholder="Ex: Empresa ABC Comércio Ltda"
                  className="w-full px-4 py-2.5 text-sm focus:outline-none transition-all"
                  style={{
                    background: "var(--bg-inset)",
                    border: "1px solid var(--border-default)",
                    color: "var(--text-primary)",
                    borderRadius: "var(--radius-md)",
                  }}
                  onFocus={ev => { ev.currentTarget.style.borderColor = "var(--border-focus)"; }}
                  onBlur={ev => { ev.currentTarget.style.borderColor = "var(--border-default)"; }}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium mb-1.5 uppercase" style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}>
                    CNPJ <span className="normal-case font-normal" style={{ color: "var(--text-disabled)" }}>(opcional)</span>
                  </label>
                  <input
                    value={cnpj} onChange={e => handleCnpjChange(e.target.value)}
                    placeholder="00.000.000/0001-00"
                    className="w-full px-4 py-2.5 text-sm font-mono tabular-nums focus:outline-none transition-all"
                    style={{
                      background: "var(--bg-inset)",
                      border: `1px solid ${
                        cnpjStatus === "valido"     ? "var(--success-border)" :
                        cnpjStatus === "invalido"   ? "var(--danger-border)"  :
                        cnpjStatus === "incompleto" ? "var(--warning-border)" :
                                                      "var(--border-default)"
                      }`,
                      color: "var(--text-primary)",
                      borderRadius: "var(--radius-md)",
                    }}
                  />
                  {cnpjStatus === "valido" && (
                    <p className="text-[11px] mt-1 flex items-center gap-1" style={{ color: "var(--success)" }}>
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                      Válido
                    </p>
                  )}
                  {cnpjStatus === "incompleto" && (
                    <p className="text-[11px] mt-1" style={{ color: "var(--warning)" }}>
                      Incompleto — <button type="button" onClick={() => { setCnpj(""); setCnpjErro(""); }} className="underline" style={{ color: "var(--warning)" }}>limpar</button>
                    </p>
                  )}
                  {cnpjStatus === "invalido" && <p className="text-[11px] mt-1" style={{ color: "var(--danger)" }}>CNPJ inválido</p>}
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1.5 uppercase" style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}>
                    CCM <span className="normal-case font-normal" style={{ color: "var(--text-disabled)" }}>(opcional)</span>
                  </label>
                  <input
                    value={ccm} onChange={e => setCcm(e.target.value)}
                    placeholder="Inscrição municipal"
                    className="w-full px-4 py-2.5 text-sm font-mono tabular-nums focus:outline-none transition-all"
                    style={{
                      background: "var(--bg-inset)",
                      border: "1px solid var(--border-default)",
                      color: "var(--text-primary)",
                      borderRadius: "var(--radius-md)",
                    }}
                    onFocus={ev => { ev.currentTarget.style.borderColor = "var(--border-focus)"; }}
                    onBlur={ev => { ev.currentTarget.style.borderColor = "var(--border-default)"; }}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium mb-1.5 uppercase" style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}>
                  Observação <span className="normal-case font-normal" style={{ color: "var(--text-disabled)" }}>(opcional)</span>
                </label>
                <textarea
                  value={observacoes} onChange={e => setObservacoes(e.target.value.slice(0, 500))} rows={3}
                  placeholder="Ex: Cliente desde 2020, regime Simples Nacional, atenção especial na folha..."
                  className="w-full px-4 py-2.5 text-sm focus:outline-none transition-all resize-none"
                  style={{
                    background: "var(--bg-inset)",
                    border: "1px solid var(--border-default)",
                    color: "var(--text-primary)",
                    borderRadius: "var(--radius-md)",
                  }}
                  onFocus={ev => { ev.currentTarget.style.borderColor = "var(--border-focus)"; }}
                  onBlur={ev => { ev.currentTarget.style.borderColor = "var(--border-default)"; }}
                />
                <p className="text-right text-[11px] mt-0.5" style={{ color: "var(--text-tertiary)" }}>{observacoes.length}/500</p>
              </div>

              <div className="flex gap-3 pt-1">
                <button
                  type="button" onClick={() => setModalAberto(false)}
                  className="flex-1 py-2.5 text-sm font-medium transition-colors"
                  style={{
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border-default)",
                    color: "var(--text-secondary)",
                    borderRadius: "var(--radius-md)",
                  }}
                  onMouseEnter={ev => { ev.currentTarget.style.color = "var(--text-primary)"; ev.currentTarget.style.borderColor = "var(--border-strong)"; }}
                  onMouseLeave={ev => { ev.currentTarget.style.color = "var(--text-secondary)"; ev.currentTarget.style.borderColor = "var(--border-default)"; }}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={salvando || (!!cnpjErro && cnpj.replace(/\D/g, "").length > 0)}
                  className="flex-1 py-2.5 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-semibold transition-opacity hover:opacity-90"
                  style={{
                    background: "var(--accent)",
                    color: "var(--text-inverse)",
                    borderRadius: "var(--radius-md)",
                  }}
                >
                  {salvando ? "Salvando..." : editando ? "Salvar alterações" : "Cadastrar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL EXCLUSÃO ── */}
      {modalExclusao && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}>
          <div
            className="w-full max-w-md overflow-hidden"
            style={{
              background: "var(--bg-overlay)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-lg)",
              boxShadow: "var(--shadow-lg)",
            }}
          >
            <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
              <h2 className="font-semibold text-lg" style={{ color: "var(--danger)" }}>Excluir empresa</h2>
              <button
                onClick={() => setModalExclusao(null)}
                className="p-1.5 transition-colors"
                style={{ color: "var(--text-tertiary)", borderRadius: "var(--radius-sm)" }}
                onMouseEnter={ev => { ev.currentTarget.style.color = "var(--text-primary)"; ev.currentTarget.style.background = "var(--bg-elevated)"; }}
                onMouseLeave={ev => { ev.currentTarget.style.color = "var(--text-tertiary)"; ev.currentTarget.style.background = "transparent"; }}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                Tem certeza que deseja excluir{" "}
                <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{modalExclusao.nome}</span>?
              </p>

              {dadosEmpresa?.has_data && (
                <div
                  className="px-4 py-3 text-sm"
                  style={{
                    background: "var(--danger-subtle)",
                    border: "1px solid var(--danger-border)",
                    color: "var(--danger)",
                    borderRadius: "var(--radius-md)",
                  }}
                >
                  <p className="font-semibold mb-1">Esta empresa possui dados importados.</p>
                  <p className="text-xs">Ao excluir, todos os lançamentos, extratos e importações serão removidos permanentemente.</p>
                </div>
              )}

              {!dadosEmpresa?.has_data && (
                <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>Esta ação não pode ser desfeita.</p>
              )}

              {dadosEmpresa?.has_data && (
                <div>
                  <label className="block text-xs font-medium mb-1.5 uppercase" style={{ color: "var(--text-tertiary)", letterSpacing: "var(--tracking-widest)" }}>
                    Digite o nome da empresa para confirmar
                  </label>
                  <input
                    value={nomeConfirmacao}
                    onChange={e => setNomeConfirmacao(e.target.value)}
                    placeholder={modalExclusao.nome}
                    className="w-full px-4 py-2.5 text-sm focus:outline-none transition-all"
                    style={{
                      background: "var(--bg-inset)",
                      border: "1px solid var(--danger-border)",
                      color: "var(--text-primary)",
                      borderRadius: "var(--radius-md)",
                    }}
                  />
                </div>
              )}

              <div className="flex gap-3 pt-1">
                <button
                  type="button" onClick={() => setModalExclusao(null)}
                  className="flex-1 py-2.5 text-sm font-medium transition-colors"
                  style={{
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border-default)",
                    color: "var(--text-secondary)",
                    borderRadius: "var(--radius-md)",
                  }}
                  onMouseEnter={ev => { ev.currentTarget.style.color = "var(--text-primary)"; ev.currentTarget.style.borderColor = "var(--border-strong)"; }}
                  onMouseLeave={ev => { ev.currentTarget.style.color = "var(--text-secondary)"; ev.currentTarget.style.borderColor = "var(--border-default)"; }}
                >
                  Cancelar
                </button>
                <button
                  onClick={confirmarExclusao}
                  disabled={excluindo || (!!dadosEmpresa?.has_data && nomeConfirmacao.trim().toLowerCase() !== modalExclusao.nome.trim().toLowerCase())}
                  className="flex-1 py-2.5 disabled:opacity-40 disabled:cursor-not-allowed text-sm font-semibold transition-opacity hover:opacity-90"
                  style={{
                    background: "var(--danger)",
                    color: "var(--text-inverse)",
                    borderRadius: "var(--radius-md)",
                  }}
                >
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
