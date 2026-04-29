"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");
function tk() { return localStorage.getItem("controllo_token") ?? ""; }
const hdr = () => ({ Authorization: `Bearer ${tk()}` });
const hdrJson = () => ({ Authorization: `Bearer ${tk()}`, "Content-Type": "application/json" });

const fmt = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 2 }).format(v);

// ─── Types ──────────────────────────────────────────────────────
interface ContaPlano { id: number; codigo: string; descricao: string; tipo: string; natureza: string; }
interface Regra { id: number; padrao: string; tipo_transacao: string; conta_debito_codigo: string; conta_debito_descricao: string; conta_credito_codigo: string; conta_credito_descricao: string; prioridade: number; ativo: boolean; }
interface ContaBanco { id: number; nome_banco: string; conta_codigo: string; conta_descricao: string; }
interface Cadastro { id: number; nome: string; documento: string; tipo: string; conta_codigo: string; conta_descricao: string; }
interface TxContmatic { data: string; lancamento: number; historico: number; descricao: string; debito: string; credito: string; valor: number; status: string; }
interface Stats { total: number; regra_usuario: number; cadastro: number; automatico: number; pendente: number; filtradas: number; }

type Tab = "classificar" | "plano" | "regras";

const STATUS_COR: Record<string, string> = {
  regra_usuario: "bg-emerald-500/15 text-emerald-400 border-emerald-500/40",
  cadastro: "bg-blue-500/15 text-blue-400 border-blue-500/40",
  automatico: "bg-amber-500/15 text-amber-400 border-amber-500/40",
  pendente: "bg-rose-500/15 text-rose-400 border-rose-500/40",
};
const STATUS_LABEL: Record<string, string> = {
  regra_usuario: "Regra Usuário",
  cadastro: "Cadastro",
  automatico: "Automático",
  pendente: "Pendente",
};
const NATUREZA_COR: Record<string, string> = {
  ativo: "text-blue-400 bg-blue-400/10 border-blue-400/30",
  passivo: "text-rose-400 bg-rose-400/10 border-rose-400/30",
  receita: "text-emerald-400 bg-emerald-400/10 border-emerald-400/30",
  despesa: "text-amber-400 bg-amber-400/10 border-amber-400/30",
};

// ─── Plano Padrão com contas reduzidas ──────────────────────────
const PLANO_PADRAO = [
  { codigo: "10101", descricao: "Caixa Geral", tipo: "analitica", natureza: "ativo", codigo_pai: "" },
  { codigo: "10201", descricao: "Banco Itaú C/C", tipo: "analitica", natureza: "ativo", codigo_pai: "" },
  { codigo: "10202", descricao: "Banco Bradesco C/C", tipo: "analitica", natureza: "ativo", codigo_pai: "" },
  { codigo: "10203", descricao: "Banco Sicoob C/C", tipo: "analitica", natureza: "ativo", codigo_pai: "" },
  { codigo: "10301", descricao: "Aplicações Financeiras - CDB", tipo: "analitica", natureza: "ativo", codigo_pai: "" },
  { codigo: "10302", descricao: "Aplicações Financeiras - Poupança", tipo: "analitica", natureza: "ativo", codigo_pai: "" },
  { codigo: "10401", descricao: "Clientes a Receber", tipo: "analitica", natureza: "ativo", codigo_pai: "" },
  { codigo: "20101", descricao: "Fornecedores Diversos", tipo: "analitica", natureza: "passivo", codigo_pai: "" },
  { codigo: "20201", descricao: "Salários a Pagar", tipo: "analitica", natureza: "passivo", codigo_pai: "" },
  { codigo: "20202", descricao: "FGTS a Recolher", tipo: "analitica", natureza: "passivo", codigo_pai: "" },
  { codigo: "20203", descricao: "INSS a Recolher", tipo: "analitica", natureza: "passivo", codigo_pai: "" },
  { codigo: "20301", descricao: "ISS a Recolher", tipo: "analitica", natureza: "passivo", codigo_pai: "" },
  { codigo: "20302", descricao: "Simples Nacional / DAS", tipo: "analitica", natureza: "passivo", codigo_pai: "" },
  { codigo: "20303", descricao: "Tributos Municipais a Recolher", tipo: "analitica", natureza: "passivo", codigo_pai: "" },
  { codigo: "20304", descricao: "IRRF a Recolher", tipo: "analitica", natureza: "passivo", codigo_pai: "" },
  { codigo: "21001", descricao: "Conta Sócios / Capital Social", tipo: "analitica", natureza: "passivo", codigo_pai: "" },
  { codigo: "31001", descricao: "Receitas Financeiras / Rendimentos", tipo: "analitica", natureza: "receita", codigo_pai: "" },
  { codigo: "31002", descricao: "Receita de Serviços Prestados", tipo: "analitica", natureza: "receita", codigo_pai: "" },
  { codigo: "31003", descricao: "Receita de Vendas", tipo: "analitica", natureza: "receita", codigo_pai: "" },
  { codigo: "39901", descricao: "Receitas Diversas / A Classificar", tipo: "analitica", natureza: "receita", codigo_pai: "" },
  { codigo: "2501", descricao: "Tarifas Bancárias", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "2502", descricao: "IOF", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "2503", descricao: "Juros Pagos", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "40101", descricao: "Energia Elétrica", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "40102", descricao: "Água e Esgoto", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "40103", descricao: "Telecomunicações", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "40104", descricao: "Aluguel", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "40105", descricao: "Material de Escritório", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "40201", descricao: "Salários e Ordenados", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "40202", descricao: "FGTS", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "40203", descricao: "INSS Patronal", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "40301", descricao: "Viagens e Deslocamentos", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "40302", descricao: "Combustível", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "40303", descricao: "Hospedagem", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "40401", descricao: "ISS", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "40402", descricao: "Simples Nacional / DAS", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "40403", descricao: "Tributos Municipais", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
  { codigo: "49901", descricao: "Despesas Diversas / A Classificar", tipo: "analitica", natureza: "despesa", codigo_pai: "" },
];

export default function ClassificacaoContabilPage() {
  const { empresaSelecionada } = useEmpresa();
  const [tab, setTab] = useState<Tab>("classificar");
  const [toast, setToast] = useState<{ msg: string; tipo: "ok" | "erro" } | null>(null);

  const [plano, setPlano] = useState<ContaPlano[]>([]);
  const [planoLoading, setPlanoLoading] = useState(false);
  const [novaConta, setNovaConta] = useState({ codigo: "", descricao: "", tipo: "analitica", natureza: "ativo" });
  const [showNovaContaForm, setShowNovaContaForm] = useState(false);

  const [regras, setRegras] = useState<Regra[]>([]);
  const [contasBanco, setContasBanco] = useState<ContaBanco[]>([]);
  const [cadastros, setCadastros] = useState<Cadastro[]>([]);
  const [showNovaRegra, setShowNovaRegra] = useState(false);
  const [novaRegra, setNovaRegra] = useState({ padrao: "", tipo_transacao: "ambos", conta_debito_codigo: "", conta_credito_codigo: "", prioridade: 0 });
  const [showNovoBanco, setShowNovoBanco] = useState(false);
  const [novoBanco, setNovoBanco] = useState({ nome_banco: "", conta_codigo: "", conta_descricao: "" });
  const [showNovoCadastro, setShowNovoCadastro] = useState(false);
  const [novoCadastro, setNovoCadastro] = useState({ nome: "", documento: "", tipo: "socio", conta_codigo: "", conta_descricao: "" });

  const [resultado, setResultado] = useState<TxContmatic[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [classificando, setClassificando] = useState(false);
  const [filtroStatus, setFiltroStatus] = useState("todos");
  const fileRef = useRef<HTMLInputElement>(null);
  const [arquivoNome, setArquivoNome] = useState("");
  const [arquivoFile, setArquivoFile] = useState<File | null>(null);

  const empId = empresaSelecionada?.id;
  const show = (msg: string, tipo: "ok" | "erro") => { setToast({ msg, tipo }); setTimeout(() => setToast(null), 3500); };

  const carregarPlano = useCallback(async () => {
    if (!empId) return;
    setPlanoLoading(true);
    try { const r = await fetch(`${API}/api/classificacao/plano/${empId}`, { headers: hdr() }); if (r.ok) setPlano(await r.json()); }
    catch { /* */ } finally { setPlanoLoading(false); }
  }, [empId]);

  const carregarRegras = useCallback(async () => {
    if (!empId) return;
    try {
      const [r1, r2, r3] = await Promise.all([
        fetch(`${API}/api/classificacao/regras/${empId}`, { headers: hdr() }),
        fetch(`${API}/api/classificacao/bancos/${empId}`, { headers: hdr() }),
        fetch(`${API}/api/classificacao/cadastros/${empId}`, { headers: hdr() }),
      ]);
      if (r1.ok) setRegras(await r1.json());
      if (r2.ok) setContasBanco(await r2.json());
      if (r3.ok) setCadastros(await r3.json());
    } catch { /* */ }
  }, [empId]);

  useEffect(() => { if (empId) { carregarPlano(); carregarRegras(); } else { setPlano([]); setRegras([]); setContasBanco([]); setCadastros([]); } }, [empId, carregarPlano, carregarRegras]);

  // ─── Actions ──────────────────────────────────────────────────
  async function carregarPlanoPadrao() {
    if (!empId || !confirm("Carregar plano de contas padrão? Contas já existentes serão ignoradas.")) return;
    try {
      const r = await fetch(`${API}/api/classificacao/plano/${empId}/lote`, { method: "POST", headers: hdrJson(), body: JSON.stringify({ contas: PLANO_PADRAO }) });
      if (!r.ok) throw new Error();
      const d = await r.json();
      show(`${d.criadas} contas criadas, ${d.ignoradas} já existiam.`, "ok");
      carregarPlano();
    } catch { show("Erro ao carregar plano.", "erro"); }
  }

  async function adicionarConta(ev: React.FormEvent) {
    ev.preventDefault();
    if (!empId) return;
    try {
      const r = await fetch(`${API}/api/classificacao/plano/${empId}`, { method: "POST", headers: hdrJson(), body: JSON.stringify(novaConta) });
      if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error((e as {detail?:string}).detail || "Erro"); }
      show("Conta adicionada!", "ok"); setNovaConta({ codigo: "", descricao: "", tipo: "analitica", natureza: "ativo" }); setShowNovaContaForm(false); carregarPlano();
    } catch (e) { show(e instanceof Error ? e.message : "Erro", "erro"); }
  }

  async function removerConta(id: number) { if (!empId || !confirm("Remover?")) return; try { await fetch(`${API}/api/classificacao/plano/${empId}/${id}`, { method: "DELETE", headers: hdr() }); setPlano(p => p.filter(c => c.id !== id)); } catch { show("Erro", "erro"); } }

  async function adicionarRegra(ev: React.FormEvent) {
    ev.preventDefault(); if (!empId) return;
    try { const r = await fetch(`${API}/api/classificacao/regras/${empId}`, { method: "POST", headers: hdrJson(), body: JSON.stringify(novaRegra) }); if (!r.ok) throw new Error(); show("Regra criada!", "ok"); setNovaRegra({ padrao: "", tipo_transacao: "ambos", conta_debito_codigo: "", conta_credito_codigo: "", prioridade: 0 }); setShowNovaRegra(false); carregarRegras(); } catch { show("Erro", "erro"); }
  }
  async function removerRegra(id: number) { if (!empId || !confirm("Remover?")) return; try { await fetch(`${API}/api/classificacao/regras/${empId}/${id}`, { method: "DELETE", headers: hdr() }); setRegras(r => r.filter(x => x.id !== id)); } catch { show("Erro", "erro"); } }

  async function adicionarBanco(ev: React.FormEvent) {
    ev.preventDefault(); if (!empId) return;
    try { const r = await fetch(`${API}/api/classificacao/bancos/${empId}`, { method: "POST", headers: hdrJson(), body: JSON.stringify(novoBanco) }); if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error((e as {detail?:string}).detail || "Erro"); } show("Banco vinculado!", "ok"); setNovoBanco({ nome_banco: "", conta_codigo: "", conta_descricao: "" }); setShowNovoBanco(false); carregarRegras(); } catch (e) { show(e instanceof Error ? e.message : "Erro", "erro"); }
  }
  async function removerBanco(id: number) { if (!empId || !confirm("Remover?")) return; try { await fetch(`${API}/api/classificacao/bancos/${empId}/${id}`, { method: "DELETE", headers: hdr() }); setContasBanco(c => c.filter(x => x.id !== id)); } catch { show("Erro", "erro"); } }

  async function adicionarCadastro(ev: React.FormEvent) {
    ev.preventDefault(); if (!empId) return;
    try { const r = await fetch(`${API}/api/classificacao/cadastros/${empId}`, { method: "POST", headers: hdrJson(), body: JSON.stringify(novoCadastro) }); if (!r.ok) throw new Error(); show("Cadastro criado!", "ok"); setNovoCadastro({ nome: "", documento: "", tipo: "socio", conta_codigo: "", conta_descricao: "" }); setShowNovoCadastro(false); carregarRegras(); } catch { show("Erro", "erro"); }
  }
  async function removerCadastro(id: number) { if (!empId || !confirm("Remover?")) return; try { await fetch(`${API}/api/classificacao/cadastros/${empId}/${id}`, { method: "DELETE", headers: hdr() }); setCadastros(c => c.filter(x => x.id !== id)); } catch { show("Erro", "erro"); } }

  // ─── Classificação ──────────────────────────────────────────
  async function executarPreview() {
    if (!empId || !arquivoFile) return;
    setClassificando(true); setResultado([]); setStats(null);
    try {
      const fd = new FormData(); fd.append("arquivo", arquivoFile);
      const r = await fetch(`${API}/api/classificacao/preview/${empId}`, { method: "POST", headers: { Authorization: `Bearer ${tk()}` }, body: fd });
      if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error((e as {detail?:string}).detail || "Erro"); }
      const d = await r.json();
      setResultado(d.transacoes); setStats(d.stats);
      show(`${d.stats.total} transações classificadas!`, "ok");
    } catch (e) { show(e instanceof Error ? e.message : "Erro", "erro"); }
    finally { setClassificando(false); }
  }

  async function baixarExcel() {
    if (!empId || !arquivoFile) return;
    setClassificando(true);
    try {
      const fd = new FormData(); fd.append("arquivo", arquivoFile);
      const r = await fetch(`${API}/api/classificacao/classificar/${empId}`, { method: "POST", headers: { Authorization: `Bearer ${tk()}` }, body: fd });
      if (!r.ok) throw new Error("Erro ao gerar Excel");
      const blob = await r.blob(); const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url;
      a.download = `contmatic_${empresaSelecionada?.nome?.replace(/\s+/g, "_") || empId}.xlsx`;
      a.click(); URL.revokeObjectURL(url);
      show("Excel Contmatic baixado!", "ok");
    } catch (e) { show(e instanceof Error ? e.message : "Erro", "erro"); }
    finally { setClassificando(false); }
  }

  const txFiltradas = filtroStatus === "todos" ? resultado : resultado.filter(t => t.status === filtroStatus);
  const planoDesc = Object.fromEntries(plano.map(c => [c.codigo, c.descricao]));

  // ════════════════════════════════════════════════════════════════
  return (
    <div className="min-h-full" style={{ background: "var(--bg-canvas)", color: "var(--text-primary)" }}>
      {toast && <div className={`fixed top-6 right-6 z-50 px-5 py-3 rounded-xl border text-sm font-semibold shadow-2xl ${toast.tipo === "ok" ? "bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-600/20 dark:border-emerald-500/40 dark:text-emerald-300" : "bg-red-50 border-red-200 text-red-700 dark:bg-red-600/20 dark:border-red-500/40 dark:text-red-300"}`}>{toast.msg}</div>}

      <header className="px-8 pt-8 pb-6 border-b border-slate-200 dark:border-slate-700">
        <h1 className="text-2xl font-extrabold tracking-tight">Classificação <span className="text-[#1e3a5f] dark:text-blue-400">Contábil</span></h1>
        <p className="text-slate-500 text-sm mt-1">Classifique transações e gere Excel no padrão Contmatic com contas reduzidas</p>
      </header>

      {!empresaSelecionada && (
        <div className="px-8 py-24 flex flex-col items-center text-slate-500 border-b border-dashed border-slate-700/40">
          <svg className="w-12 h-12 mb-4 opacity-25" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
          <p className="text-sm font-semibold">Selecione uma empresa para começar</p>
        </div>
      )}

      {empresaSelecionada && (
        <div className="px-8 py-6 space-y-6">
          {/* Tabs */}
          <div className="flex gap-2 border-b border-slate-700/40 pb-3">
            {([
              { key: "classificar" as Tab, label: "Classificar Excel" },
              { key: "plano" as Tab, label: "Plano de Contas" },
              { key: "regras" as Tab, label: "Regras e Cadastros" },
            ]).map(t => (
              <button key={t.key} onClick={() => setTab(t.key)}
                className={`px-4 py-2.5 rounded-xl text-sm font-semibold transition-all ${tab === t.key ? "text-white shadow-lg" : "text-slate-400 hover:text-white hover:bg-slate-800/40"}`}
                style={tab === t.key ? { background: "#1e3a5f" } : {}}>{t.label}</button>
            ))}
          </div>

          {/* ═══ TAB: CLASSIFICAR ═══ */}
          {tab === "classificar" && (
            <div className="space-y-6">
              <div className="bg-slate-800/40 border border-slate-700/60 rounded-2xl p-6">
                <p className="text-sm font-bold text-slate-200 mb-4">Importar Excel do Extrator</p>
                <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-end">
                  <div className="flex-1">
                    <input ref={fileRef} type="file" accept=".xlsx" onChange={e => { const f = e.target.files?.[0]; if (f) { setArquivoFile(f); setArquivoNome(f.name); } }} className="hidden" />
                    <button onClick={() => fileRef.current?.click()} className="flex items-center gap-2 px-5 py-3 rounded-xl border-2 border-dashed border-slate-600 hover:border-blue-400 text-slate-400 hover:text-blue-400 transition-all text-sm">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
                      {arquivoNome || "Selecionar arquivo .xlsx"}
                    </button>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={executarPreview} disabled={!arquivoFile || classificando} className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-40 transition-all" style={{ background: "#1e3a5f" }}>{classificando ? "Classificando..." : "Preview"}</button>
                    {resultado.length > 0 && <button onClick={baixarExcel} disabled={classificando} className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 transition-all">Baixar Contmatic</button>}
                  </div>
                </div>
                {contasBanco.length === 0 && <div className="mt-4 px-4 py-2.5 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-400 text-xs">Configure pelo menos um banco na aba <button onClick={() => setTab("regras")} className="underline font-semibold">Regras e Cadastros</button>.</div>}
                {plano.length === 0 && <div className="mt-2 px-4 py-2.5 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs">Cadastre o plano de contas na aba <button onClick={() => setTab("plano")} className="underline font-semibold">Plano de Contas</button> antes de classificar.</div>}
              </div>

              {stats && (
                <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                  {[
                    { label: "Total", valor: stats.total, cor: "text-slate-200" },
                    { label: "Regra Usuário", valor: stats.regra_usuario, cor: "text-emerald-400" },
                    { label: "Cadastro", valor: stats.cadastro, cor: "text-blue-400" },
                    { label: "Automático", valor: stats.automatico, cor: "text-amber-400" },
                    { label: "Pendente", valor: stats.pendente, cor: "text-rose-400" },
                    { label: "Filtradas", valor: stats.filtradas, cor: "text-slate-500" },
                  ].map(s => (
                    <div key={s.label} className="bg-slate-800/40 border border-slate-700/60 rounded-xl px-4 py-3 text-center">
                      <p className={`text-xl font-black font-mono ${s.cor}`}>{s.valor}</p>
                      <p className="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">{s.label}</p>
                    </div>
                  ))}
                </div>
              )}

              {resultado.length > 0 && (
                <div className="flex gap-2 flex-wrap">
                  {["todos", "regra_usuario", "cadastro", "automatico", "pendente"].map(s => (
                    <button key={s} onClick={() => setFiltroStatus(s)}
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${filtroStatus === s ? (STATUS_COR[s] || "border-[#1e3a5f] text-white") : "border-slate-700 text-slate-400 hover:text-white"}`}
                      style={filtroStatus === s && s === "todos" ? { background: "#1e3a5f", borderColor: "#1e3a5f" } : {}}>
                      {s === "todos" ? "Todos" : STATUS_LABEL[s] || s} ({s === "todos" ? resultado.length : resultado.filter(t => t.status === s).length})
                    </button>
                  ))}
                </div>
              )}

              {txFiltradas.length > 0 && (
                <div className="border border-slate-700/60 rounded-2xl overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-slate-800/60 border-b border-slate-700/60">
                        {["Data", "Lanç.", "Hist.", "Descrição", "Débito", "Crédito", "Valor (R$)", "Status"].map(h => (
                          <th key={h} className="px-3 py-3 text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest whitespace-nowrap">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {txFiltradas.map((tx, i) => (
                        <tr key={i} className="border-b border-slate-800/40 hover:bg-slate-800/20 transition-colors">
                          <td className="px-3 py-2.5 whitespace-nowrap font-mono text-slate-400">{tx.data}</td>
                          <td className="px-3 py-2.5 whitespace-nowrap font-mono text-center">{tx.lancamento}</td>
                          <td className="px-3 py-2.5 whitespace-nowrap font-mono text-center">{tx.historico}</td>
                          <td className="px-3 py-2.5 max-w-[320px] truncate" title={tx.descricao}>{tx.descricao}</td>
                          <td className="px-3 py-2.5 whitespace-nowrap font-mono font-bold text-blue-300" title={planoDesc[tx.debito] || ""}>{tx.debito}</td>
                          <td className="px-3 py-2.5 whitespace-nowrap font-mono font-bold text-rose-300" title={planoDesc[tx.credito] || ""}>{tx.credito}</td>
                          <td className="px-3 py-2.5 whitespace-nowrap font-mono text-right">{fmt(tx.valor)}</td>
                          <td className="px-3 py-2.5 whitespace-nowrap">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${STATUS_COR[tx.status] || ""}`}>{STATUS_LABEL[tx.status] || tx.status}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* ═══ TAB: PLANO DE CONTAS ═══ */}
          {tab === "plano" && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <button onClick={carregarPlanoPadrao} className="px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all" style={{ background: "#1e3a5f" }}>Carregar Plano Padrão</button>
                <button onClick={() => setShowNovaContaForm(v => !v)} className="px-4 py-2 rounded-xl text-sm font-semibold border border-slate-600 text-slate-300 hover:text-white transition-all">+ Adicionar Conta</button>
                <span className="text-xs text-slate-500">{plano.length} contas</span>
              </div>

              {showNovaContaForm && (
                <form onSubmit={adicionarConta} className="bg-slate-800/60 border border-slate-700/40 rounded-2xl p-5 space-y-3">
                  <p className="text-sm font-bold text-slate-200">Nova Conta Reduzida</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 mb-1 uppercase">Código Reduzido *</label>
                      <input value={novaConta.codigo} onChange={e => setNovaConta({ ...novaConta, codigo: e.target.value })} placeholder="10204" required className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm font-mono placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/50" />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 mb-1 uppercase">Descrição *</label>
                      <input value={novaConta.descricao} onChange={e => setNovaConta({ ...novaConta, descricao: e.target.value })} placeholder="Banco Santander C/C" required className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/50" />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 mb-1 uppercase">Natureza</label>
                      <select value={novaConta.natureza} onChange={e => setNovaConta({ ...novaConta, natureza: e.target.value })} className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm focus:outline-none">
                        <option value="ativo">Ativo</option><option value="passivo">Passivo</option><option value="receita">Receita</option><option value="despesa">Despesa</option>
                      </select>
                    </div>
                    <div className="flex items-end gap-2">
                      <button type="submit" className="px-4 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: "#1e3a5f" }}>Salvar</button>
                      <button type="button" onClick={() => setShowNovaContaForm(false)} className="px-3 py-2 rounded-xl text-sm border border-slate-700 text-slate-400">Cancelar</button>
                    </div>
                  </div>
                </form>
              )}

              {planoLoading ? <div className="flex justify-center py-12"><div className="w-8 h-8 border-4 border-[#1e3a5f]/30 border-t-[#1e3a5f] rounded-full animate-spin" /></div>
              : plano.length === 0 ? <div className="text-center py-12 text-slate-500 border border-dashed border-slate-700/60 rounded-2xl"><p className="text-sm font-semibold">Nenhuma conta cadastrada.</p><p className="text-xs mt-1">Clique em &quot;Carregar Plano Padrão&quot; para iniciar.</p></div>
              : (
                <div className="border border-slate-700/60 rounded-2xl overflow-hidden">
                  <div className="bg-slate-800/60 border-b border-slate-700/60 px-5 py-3 grid grid-cols-[80px_1fr_80px_auto] gap-4">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Código</span>
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Descrição</span>
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest text-center">Natureza</span>
                    <span className="w-8" />
                  </div>
                  {plano.map(c => (
                    <div key={c.id} className="grid grid-cols-[80px_1fr_80px_auto] gap-4 items-center px-5 py-2.5 border-b border-slate-800/40 hover:bg-slate-800/20 transition-colors">
                      <span className="font-mono text-xs font-bold text-slate-200">{c.codigo}</span>
                      <span className="text-sm text-slate-300">{c.descricao}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold text-center ${NATUREZA_COR[c.natureza] || ""}`}>{c.natureza.charAt(0).toUpperCase() + c.natureza.slice(1)}</span>
                      <button onClick={() => removerConta(c.id)} className="p-1.5 rounded-lg text-slate-600 hover:text-rose-400 hover:bg-rose-400/10 transition-all">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ═══ TAB: REGRAS E CADASTROS ═══ */}
          {tab === "regras" && (
            <div className="space-y-8">
              {/* Bancos */}
              <section>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-bold text-slate-200">Bancos &rarr; Conta Reduzida</h2>
                  <button onClick={() => setShowNovoBanco(v => !v)} className="px-3 py-1.5 rounded-xl text-xs font-semibold border border-slate-600 text-slate-300 hover:text-white transition-all">+ Vincular Banco</button>
                </div>
                {showNovoBanco && (
                  <form onSubmit={adicionarBanco} className="bg-slate-800/60 border border-slate-700/40 rounded-xl p-4 mb-3">
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-400 mb-1 uppercase">Nome do Banco *</label>
                        <input value={novoBanco.nome_banco} onChange={e => setNovoBanco({ ...novoBanco, nome_banco: e.target.value })} placeholder="Itaú" required className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm placeholder-slate-600 focus:outline-none" />
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-400 mb-1 uppercase">Conta Reduzida *</label>
                        <select value={novoBanco.conta_codigo} onChange={e => { const s = plano.find(c => c.codigo === e.target.value); setNovoBanco({ ...novoBanco, conta_codigo: e.target.value, conta_descricao: s?.descricao || "" }); }} required className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm focus:outline-none">
                          <option value="">Selecionar...</option>
                          {plano.filter(c => c.natureza === "ativo").map(c => <option key={c.id} value={c.codigo}>{c.codigo} - {c.descricao}</option>)}
                        </select>
                      </div>
                      <div className="flex items-end gap-2">
                        <button type="submit" className="px-4 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: "#1e3a5f" }}>Salvar</button>
                        <button type="button" onClick={() => setShowNovoBanco(false)} className="px-3 py-2 rounded-xl text-sm border border-slate-700 text-slate-400">Cancelar</button>
                      </div>
                    </div>
                  </form>
                )}
                {contasBanco.length === 0 ? <p className="text-xs text-slate-500 py-2">Nenhum banco vinculado.</p> : (
                  <div className="space-y-1">
                    {contasBanco.map(b => (
                      <div key={b.id} className="flex items-center justify-between bg-slate-800/30 border border-slate-700/40 rounded-xl px-4 py-2.5">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-semibold text-slate-200">{b.nome_banco}</span>
                          <span className="text-slate-600">&rarr;</span>
                          <span className="text-xs font-mono text-blue-400">{b.conta_codigo}</span>
                          <span className="text-xs text-slate-500">{b.conta_descricao}</span>
                        </div>
                        <button onClick={() => removerBanco(b.id)} className="text-slate-600 hover:text-rose-400 transition-all"><svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg></button>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* Pessoas */}
              <section>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-bold text-slate-200">Sócios / Clientes / Fornecedores</h2>
                  <button onClick={() => setShowNovoCadastro(v => !v)} className="px-3 py-1.5 rounded-xl text-xs font-semibold border border-slate-600 text-slate-300 hover:text-white transition-all">+ Novo Cadastro</button>
                </div>
                <p className="text-[11px] text-slate-500 mb-3">Cadastre nomes e CPF/CNPJ para identificação automática nas descrições do extrato.</p>
                {showNovoCadastro && (
                  <form onSubmit={adicionarCadastro} className="bg-slate-800/60 border border-slate-700/40 rounded-xl p-4 mb-3">
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                      <div><label className="block text-[11px] font-semibold text-slate-400 mb-1 uppercase">Nome *</label><input value={novoCadastro.nome} onChange={e => setNovoCadastro({ ...novoCadastro, nome: e.target.value })} placeholder="João Silva" required className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm placeholder-slate-600 focus:outline-none" /></div>
                      <div><label className="block text-[11px] font-semibold text-slate-400 mb-1 uppercase">CPF/CNPJ</label><input value={novoCadastro.documento} onChange={e => setNovoCadastro({ ...novoCadastro, documento: e.target.value })} placeholder="123.456.789-00" className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm font-mono placeholder-slate-600 focus:outline-none" /></div>
                      <div><label className="block text-[11px] font-semibold text-slate-400 mb-1 uppercase">Tipo</label>
                        <select value={novoCadastro.tipo} onChange={e => setNovoCadastro({ ...novoCadastro, tipo: e.target.value })} className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm focus:outline-none">
                          <option value="socio">Sócio</option><option value="cliente">Cliente</option><option value="fornecedor">Fornecedor</option>
                        </select>
                      </div>
                      <div><label className="block text-[11px] font-semibold text-slate-400 mb-1 uppercase">Conta Reduzida</label>
                        <select value={novoCadastro.conta_codigo} onChange={e => { const s = plano.find(c => c.codigo === e.target.value); setNovoCadastro({ ...novoCadastro, conta_codigo: e.target.value, conta_descricao: s?.descricao || "" }); }} className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm focus:outline-none">
                          <option value="">Padrão</option>
                          {plano.map(c => <option key={c.id} value={c.codigo}>{c.codigo} - {c.descricao}</option>)}
                        </select>
                      </div>
                      <div className="flex items-end gap-2">
                        <button type="submit" className="px-4 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: "#1e3a5f" }}>Salvar</button>
                        <button type="button" onClick={() => setShowNovoCadastro(false)} className="px-3 py-2 rounded-xl text-sm border border-slate-700 text-slate-400">Cancelar</button>
                      </div>
                    </div>
                  </form>
                )}
                {cadastros.length === 0 ? <p className="text-xs text-slate-500 py-2">Nenhum cadastro.</p> : (
                  <div className="space-y-1">
                    {cadastros.map(c => (
                      <div key={c.id} className="flex items-center justify-between bg-slate-800/30 border border-slate-700/40 rounded-xl px-4 py-2.5">
                        <div className="flex items-center gap-4 flex-1 min-w-0">
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${c.tipo === "socio" ? "border-indigo-500/40 text-indigo-400 bg-indigo-500/10" : c.tipo === "cliente" ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10" : "border-amber-500/40 text-amber-400 bg-amber-500/10"}`}>{c.tipo === "socio" ? "Sócio" : c.tipo === "cliente" ? "Cliente" : "Fornecedor"}</span>
                          <span className="text-sm text-slate-200">{c.nome}</span>
                          {c.documento && <span className="text-xs font-mono text-slate-500">{c.documento}</span>}
                          {c.conta_codigo && <span className="text-xs text-slate-400">&rarr; {c.conta_codigo}</span>}
                        </div>
                        <button onClick={() => removerCadastro(c.id)} className="text-slate-600 hover:text-rose-400 transition-all ml-2"><svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg></button>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* Regras */}
              <section>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-bold text-slate-200">Regras de Classificação</h2>
                  <button onClick={() => setShowNovaRegra(v => !v)} className="px-3 py-1.5 rounded-xl text-xs font-semibold border border-slate-600 text-slate-300 hover:text-white transition-all">+ Nova Regra</button>
                </div>
                <p className="text-[11px] text-slate-500 mb-3">Regras customizadas têm PRIORIDADE MÁXIMA. Use texto ou regex no padrão.</p>
                {showNovaRegra && (
                  <form onSubmit={adicionarRegra} className="bg-slate-800/60 border border-slate-700/40 rounded-xl p-4 mb-3">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <div><label className="block text-[11px] font-semibold text-slate-400 mb-1 uppercase">Padrão *</label><input value={novaRegra.padrao} onChange={e => setNovaRegra({ ...novaRegra, padrao: e.target.value })} placeholder="JULIANE|FORNECEDOR X" required className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm font-mono placeholder-slate-600 focus:outline-none" /></div>
                      <div><label className="block text-[11px] font-semibold text-slate-400 mb-1 uppercase">Tipo</label>
                        <select value={novaRegra.tipo_transacao} onChange={e => setNovaRegra({ ...novaRegra, tipo_transacao: e.target.value })} className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm focus:outline-none">
                          <option value="ambos">Ambos</option><option value="entrada">Entrada</option><option value="saida">Saída</option>
                        </select>
                      </div>
                      <div><label className="block text-[11px] font-semibold text-slate-400 mb-1 uppercase">Conta Débito</label>
                        <select value={novaRegra.conta_debito_codigo} onChange={e => setNovaRegra({ ...novaRegra, conta_debito_codigo: e.target.value })} className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm focus:outline-none">
                          <option value="">Auto</option>{plano.map(c => <option key={c.id} value={c.codigo}>{c.codigo} - {c.descricao}</option>)}
                        </select>
                      </div>
                      <div><label className="block text-[11px] font-semibold text-slate-400 mb-1 uppercase">Conta Crédito</label>
                        <select value={novaRegra.conta_credito_codigo} onChange={e => setNovaRegra({ ...novaRegra, conta_credito_codigo: e.target.value })} className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm focus:outline-none">
                          <option value="">Auto</option>{plano.map(c => <option key={c.id} value={c.codigo}>{c.codigo} - {c.descricao}</option>)}
                        </select>
                      </div>
                    </div>
                    <div className="flex gap-2 mt-3">
                      <button type="submit" className="px-4 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: "#1e3a5f" }}>Salvar</button>
                      <button type="button" onClick={() => setShowNovaRegra(false)} className="px-3 py-2 rounded-xl text-sm border border-slate-700 text-slate-400">Cancelar</button>
                    </div>
                  </form>
                )}
                {regras.length === 0 ? <p className="text-xs text-slate-500 py-2">Nenhuma regra customizada. As regras automáticas serão usadas.</p> : (
                  <div className="space-y-1">
                    {regras.map(r => (
                      <div key={r.id} className="flex items-center justify-between bg-slate-800/30 border border-slate-700/40 rounded-xl px-4 py-2.5">
                        <div className="flex items-center gap-4 flex-1 min-w-0">
                          <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">{r.padrao}</span>
                          <span className="text-[10px] text-slate-500">{r.tipo_transacao}</span>
                          <span className="text-xs text-slate-400 truncate">D: {r.conta_debito_codigo || "auto"} | C: {r.conta_credito_codigo || "auto"}</span>
                        </div>
                        <button onClick={() => removerRegra(r.id)} className="text-slate-600 hover:text-rose-400 transition-all ml-2"><svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg></button>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
