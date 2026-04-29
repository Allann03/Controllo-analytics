"use client";
import { useEffect, useState, useCallback } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");
const MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
const ANO_ATUAL = new Date().getFullYear();

interface Empresa { id: number; nome: string; regime_tributario: string; cnae: string; cnae_descricao: string; total_lancamentos: number; }

interface Lancamento {
  id: number; ano: number; mes: number; mes_label: string;
  receita_bruta: number; receita_liquida: number; lucro_liquido: number;
  margem_liquida: number; total_despesas: number;
}

const CAMPOS_DRE = [
  { key: "receita_bruta",        label: "Receita Bruta",           grupo: "DRE" },
  { key: "deducoes_receita",     label: "Deduções (impostos s/ receita, devoluções)", grupo: "DRE" },
  { key: "custo_servicos",       label: "Custo dos Serviços (CMV/CSV/CSP)", grupo: "DRE" },
  { key: "despesas_adm",         label: "Despesas Administrativas", grupo: "DRE" },
  { key: "despesas_comerciais",  label: "Despesas Comerciais",      grupo: "DRE" },
  { key: "despesas_financeiras", label: "Despesas Financeiras",     grupo: "DRE" },
  { key: "outras_despesas",      label: "Outras Despesas",          grupo: "DRE" },
  { key: "ir_csll",              label: "IR / CSLL",               grupo: "DRE" },
  { key: "folha_pagamento",      label: "Folha de Pagamento",       grupo: "DRE" },
];
const CAMPOS_CAIXA = [
  { key: "saldo_inicial_caixa",  label: "Saldo Inicial do Período", grupo: "Fluxo de Caixa" },
  { key: "entradas_caixa",       label: "Entradas de Caixa",        grupo: "Fluxo de Caixa" },
  { key: "saidas_caixa",         label: "Saídas de Caixa",          grupo: "Fluxo de Caixa" },
];
const CAMPOS_BALANCO = [
  { key: "caixa_equivalentes",    label: "Caixa e Equivalentes",      grupo: "Ativo Circulante" },
  { key: "contas_receber",        label: "Contas a Receber",           grupo: "Ativo Circulante" },
  { key: "estoques",              label: "Estoques",                   grupo: "Ativo Circulante" },
  { key: "outros_ativo_circ",     label: "Outros (Ativo Circulante)",  grupo: "Ativo Circulante" },
  { key: "ativo_nao_circulante",  label: "Ativo Não Circulante (total)",grupo: "Ativo Não Circ." },
  { key: "fornecedores",          label: "Fornecedores",               grupo: "Passivo Circulante" },
  { key: "emprestimos_cp",        label: "Empréstimos (Curto Prazo)",  grupo: "Passivo Circulante" },
  { key: "tributos_pagar",        label: "Tributos a Pagar",           grupo: "Passivo Circulante" },
  { key: "outros_passivo_circ",   label: "Outros (Passivo Circulante)",grupo: "Passivo Circulante" },
  { key: "passivo_nao_circulante",label: "Passivo Não Circulante",     grupo: "Passivo Não Circ." },
  { key: "capital_social",        label: "Capital Social",             grupo: "Patrimônio Líquido" },
  { key: "reservas",              label: "Reservas",                   grupo: "Patrimônio Líquido" },
  { key: "lucros_acumulados",     label: "Lucros / Prejuízos Acumulados", grupo: "Patrimônio Líquido" },
];

const TODOS_CAMPOS = [...CAMPOS_DRE, ...CAMPOS_CAIXA, ...CAMPOS_BALANCO];

type FormValues = Record<string, string>;

function buildEmpty(): FormValues {
  const r: FormValues = {};
  TODOS_CAMPOS.forEach(c => { r[c.key] = ""; });
  return r;
}

function formatBRL(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function LancamentosPage() {
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [lancamentos, setLancamentos] = useState<Lancamento[]>([]);
  const [aba, setAba] = useState<"lista" | "form">("lista");
  const [form, setForm] = useState<FormValues>(buildEmpty());
  const [formAno, setFormAno] = useState(ANO_ATUAL);
  const [formMes, setFormMes] = useState(new Date().getMonth() + 1);
  const [fiscal, setFiscal] = useState({ cnae: "", cnae_descricao: "", regime_tributario: "simples" });
  const [abaForm, setAbaForm] = useState<"dre" | "caixa" | "balanco">("dre");
  const [salvando, setSalvando] = useState(false);
  const [toast, setToast] = useState<{ msg: string; tipo: "ok" | "erro" } | null>(null);
  const [carregando, setCarregando] = useState(false);

  const token = () => localStorage.getItem("controllo_token") || "";
  const headers = () => ({ Authorization: `Bearer ${token()}`, "Content-Type": "application/json" });

  const showToast = (msg: string, tipo: "ok" | "erro") => {
    setToast({ msg, tipo });
    setTimeout(() => setToast(null), 3500);
  };

  // Carrega lista de empresas para dados fiscais
  useEffect(() => {
    fetch(`${API}/api/financeiro/empresas`, { headers: headers() })
      .then(r => r.json())
      .then(d => { if (Array.isArray(d)) setEmpresas(d); })
      .catch(() => {});
  }, []);

  // Carrega lançamentos da empresa selecionada
  const carregarLancamentos = useCallback(async (id: number) => {
    setCarregando(true);
    try {
      const r = await fetch(`${API}/api/financeiro/lancamentos/${id}`, { headers: headers() });
      const d = await r.json();
      if (Array.isArray(d)) setLancamentos(d);
    } finally { setCarregando(false); }
  }, []);

  useEffect(() => {
    if (empresaId) {
      carregarLancamentos(empresaId);
      const emp = empresas.find(e => e.id === empresaId);
      if (emp) setFiscal({ cnae: emp.cnae, cnae_descricao: emp.cnae_descricao, regime_tributario: emp.regime_tributario });
    }
  }, [empresaId, empresas, carregarLancamentos]);

  const abrirNovoLancamento = () => {
    setForm(buildEmpty());
    setFormAno(ANO_ATUAL);
    setFormMes(new Date().getMonth() + 1);
    setAbaForm("dre");
    setAba("form");
  };

  const abrirEditar = (l: Lancamento) => {
    // Carrega o lançamento completo para edição
    fetch(`${API}/api/financeiro/lancamentos/${empresaId}`, { headers: headers() })
      .then(r => r.json())
      .then((lista: Record<string, unknown>[]) => {
        const item = lista.find(x => x.id === l.id);
        if (!item) return;
        const f: FormValues = {};
        TODOS_CAMPOS.forEach(c => { f[c.key] = String(item[c.key] ?? "0"); });
        setForm(f);
        setFormAno(l.ano);
        setFormMes(l.mes);
        setAbaForm("dre");
        setAba("form");
      });
  };

  const salvarLancamento = async () => {
    if (!empresaId) return;
    setSalvando(true);
    try {
      const body: Record<string, number | string> = { ano: formAno, mes: formMes };
      TODOS_CAMPOS.forEach(c => {
        body[c.key] = parseFloat((form[c.key] || "0").replace(",", ".")) || 0;
      });
      const r = await fetch(`${API}/api/financeiro/lancamentos/${empresaId}`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Erro ao salvar.");
      showToast("Lançamento salvo com sucesso!", "ok");
      setAba("lista");
      carregarLancamentos(empresaId);
    } catch (e: unknown) {
      showToast((e as Error).message, "erro");
    } finally { setSalvando(false); }
  };

  const salvarFiscal = async () => {
    if (!empresaId) return;
    const r = await fetch(`${API}/api/financeiro/fiscal/${empresaId}`, {
      method: "PUT",
      headers: headers(),
      body: JSON.stringify(fiscal),
    });
    const d = await r.json();
    if (r.ok) {
      showToast("Dados fiscais atualizados.", "ok");
      // Atualiza lista de empresas
      setEmpresas(prev => prev.map(e => e.id === empresaId ? { ...e, ...fiscal } : e));
    } else {
      showToast(d.detail || "Erro.", "erro");
    }
  };

  const excluirLancamento = async (lancId: number) => {
    if (!empresaId) return;
    if (!confirm("Excluir este lançamento?")) return;
    const r = await fetch(`${API}/api/financeiro/lancamentos/${empresaId}/${lancId}`, {
      method: "DELETE",
      headers: headers(),
    });
    if (r.ok) { showToast("Excluído.", "ok"); carregarLancamentos(empresaId); }
  };

  const setField = (key: string, val: string) => setForm(prev => ({ ...prev, [key]: val }));

  const empresaAtual = empresas.find(e => e.id === empresaId);

  const renderCampos = (campos: typeof CAMPOS_DRE) => {
    const grupos: Record<string, typeof CAMPOS_DRE> = {};
    campos.forEach(c => { if (!grupos[c.grupo]) grupos[c.grupo] = []; grupos[c.grupo].push(c); });
    return Object.entries(grupos).map(([grupo, items]) => (
      <div key={grupo} className="mb-6">
        <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
          <span className="flex-1 border-t border-slate-800" />{grupo}<span className="flex-1 border-t border-slate-800" />
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {items.map(c => (
            <div key={c.key}>
              <label className="block text-xs text-slate-400 mb-1">{c.label}</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-sm">R$</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={form[c.key]}
                  onChange={e => setField(c.key, e.target.value)}
                  placeholder="0,00"
                  className="w-full pl-9 pr-3 py-2.5 bg-slate-800/60 border border-slate-700 rounded-xl text-white text-sm placeholder-slate-600 focus:outline-none focus:border-[#102a43] focus:ring-1 focus:ring-[#102a43]/30 transition-all"
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    ));
  };

  return (
    <div className="min-h-full" style={{ background: "var(--bg-canvas)", color: "var(--text-primary)" }}>

      {/* Toast */}
      {toast && (
        <div className={`fixed top-6 right-6 z-50 px-5 py-3 rounded-xl text-sm font-semibold border shadow-2xl backdrop-blur-sm transition-all ${
          toast.tipo === "ok"
            ? "bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-600/20 dark:border-emerald-500/40 dark:text-emerald-300"
            : "bg-red-50 border-red-200 text-red-700 dark:bg-red-600/20 dark:border-red-500/40 dark:text-red-300"
        }`}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <header className="page-header px-8 pt-8 pb-6 border-b border-slate-200 dark:border-slate-700">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-navy-50 border border-navy-200 dark:bg-navy-500/10 dark:border-navy-500/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-navy-600 dark:text-navy-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight">Lançamentos <span className="text-navy-600 dark:text-navy-400">Financeiros</span></h1>
              <p className="text-slate-500 text-sm">Insira os dados mensais de cada empresa para alimentar os módulos analíticos</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {empresaId && aba === "lista" && (
              <button
                onClick={abrirNovoLancamento}
                className="flex items-center gap-2 px-5 py-2.5 text-white rounded-xl font-semibold text-sm transition-all"
                style={{ background: "linear-gradient(135deg, #102a43 0%, #1e3a5f 100%)", boxShadow: "0 0 20px rgba(79,106,255,0.3)" }}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Novo Lançamento
              </button>
            )}
            {aba === "form" && (
              <button onClick={() => setAba("lista")} className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 border border-slate-700 text-slate-300 hover:text-white rounded-xl text-sm transition-all">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Voltar
              </button>
            )}
          </div>
        </div>
      </header>

      <div className="px-8 py-8">

      {!empresaId && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <svg className="w-10 h-10 mb-4 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
          <p className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>Nenhuma empresa selecionada</p>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Use o seletor no menu superior para escolher uma empresa</p>
        </div>
      )}

      {empresaId && aba === "lista" && (
        <>
          {/* Dados fiscais da empresa */}
          <div className="mb-6 p-5 card-premium">
            <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Dados Fiscais</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Regime Tributário</label>
                <select
                  value={fiscal.regime_tributario}
                  onChange={e => setFiscal(f => ({ ...f, regime_tributario: e.target.value }))}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-[#102a43]"
                >
                  <option value="simples">Simples Nacional</option>
                  <option value="presumido">Lucro Presumido</option>
                  <option value="real">Lucro Real</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">CNAE</label>
                <input
                  value={fiscal.cnae}
                  onChange={e => setFiscal(f => ({ ...f, cnae: e.target.value }))}
                  placeholder="ex: 6201500"
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-[#102a43]"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Descrição do Setor</label>
                <input
                  value={fiscal.cnae_descricao}
                  onChange={e => setFiscal(f => ({ ...f, cnae_descricao: e.target.value }))}
                  placeholder="ex: Desenvolvimento de Software"
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-[#102a43]"
                />
              </div>
            </div>
            <button
              onClick={salvarFiscal}
              className="mt-4 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-semibold rounded-xl transition-all"
            >
              Salvar Dados Fiscais
            </button>
          </div>

          {/* Lista de lançamentos */}
          <div className="card-premium overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-700/60 flex items-center justify-between">
              <p className="text-xs font-black text-slate-400 uppercase tracking-widest">
                Histórico — {empresaAtual?.nome}
              </p>
              <span className="text-xs text-slate-500">{lancamentos.length} período(s)</span>
            </div>
            {carregando ? (
              <div className="py-8 px-5 space-y-3">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="flex justify-between items-center py-2">
                    <div className="skeleton h-4 w-20 rounded" />
                    <div className="flex gap-4">
                      <div className="skeleton h-3 w-24 rounded" />
                      <div className="skeleton h-3 w-24 rounded" />
                      <div className="skeleton h-3 w-20 rounded" />
                    </div>
                  </div>
                ))}
              </div>
            ) : lancamentos.length === 0 ? (
              <div className="py-16 text-center text-slate-500">
                <p className="text-sm">Nenhum lançamento. Clique em <strong>"Novo Lançamento"</strong> para começar.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-slate-800/60 border-b border-slate-700">
                      <th className="px-5 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Período</th>
                      <th className="px-5 py-3 text-right text-xs font-bold text-emerald-500 uppercase tracking-wider">Receita Bruta</th>
                      <th className="px-5 py-3 text-right text-xs font-bold text-blue-400 uppercase tracking-wider">Rec. Líquida</th>
                      <th className="px-5 py-3 text-right text-xs font-bold text-[#3b6ea5] uppercase tracking-wider">Lucro Líquido</th>
                      <th className="px-5 py-3 text-right text-xs font-bold text-slate-400 uppercase tracking-wider">Margem</th>
                      <th className="px-5 py-3 text-right text-xs font-bold text-rose-400 uppercase tracking-wider">Despesas</th>
                      <th className="px-5 py-3 text-right text-xs text-slate-500 uppercase tracking-wider">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lancamentos.map(l => (
                      <tr key={l.id} className="border-b border-slate-700/50 last:border-0 hover:bg-slate-700/20 transition-colors">
                        <td className="px-5 py-3.5 font-semibold text-white">{l.mes_label}/{l.ano}</td>
                        <td className="px-5 py-3.5 text-right font-mono text-emerald-400 text-xs">{formatBRL(l.receita_bruta)}</td>
                        <td className="px-5 py-3.5 text-right font-mono text-blue-400 text-xs">{formatBRL(l.receita_liquida)}</td>
                        <td className={`px-5 py-3.5 text-right font-mono text-xs ${l.lucro_liquido >= 0 ? "text-[#3b6ea5]" : "text-rose-400"}`}>
                          {formatBRL(l.lucro_liquido)}
                        </td>
                        <td className={`px-5 py-3.5 text-right text-xs font-semibold ${l.margem_liquida >= 10 ? "text-emerald-400" : l.margem_liquida >= 0 ? "text-amber-400" : "text-rose-400"}`}>
                          {l.margem_liquida.toFixed(1)}%
                        </td>
                        <td className="px-5 py-3.5 text-right font-mono text-rose-400 text-xs">{formatBRL(l.total_despesas)}</td>
                        <td className="px-5 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button onClick={() => abrirEditar(l)} className="p-1.5 text-slate-500 hover:text-[#3b6ea5] hover:bg-[#102a43]/10 rounded-lg transition-all" title="Editar">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                              </svg>
                            </button>
                            <button onClick={() => excluirLancamento(l.id)} className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-400/10 rounded-lg transition-all" title="Excluir">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
          </div>
        </>
      )}

      {/* Formulário de lançamento */}
      {empresaId && aba === "form" && (
        <div className="card-premium overflow-hidden">
          {/* Período */}
          <div className="px-6 py-4 border-b border-slate-700/60 bg-slate-800/40 flex flex-wrap items-center gap-6">
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Mês</label>
              <select
                value={formMes}
                onChange={e => setFormMes(Number(e.target.value))}
                className="px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-[#102a43]"
              >
                {MESES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Ano</label>
              <input
                type="number"
                value={formAno}
                onChange={e => setFormAno(Number(e.target.value))}
                className="w-24 px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-[#102a43]"
              />
            </div>
            <div className="flex-1 text-right">
              <span className="text-xs text-slate-500">Empresa: </span>
              <span className="text-sm font-semibold text-white">{empresaAtual?.nome}</span>
            </div>
          </div>

          {/* Abas do formulário */}
          <div className="flex border-b border-slate-700 bg-slate-900/50">
            {(["dre","caixa","balanco"] as const).map(t => (
              <button
                key={t}
                onClick={() => setAbaForm(t)}
                className={`flex-1 py-3 text-xs font-bold uppercase tracking-widest transition-all ${
                  abaForm === t
                    ? "text-[#3b6ea5] border-b-2 border-[#102a43] bg-slate-800/50"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {t === "dre" ? "DRE" : t === "caixa" ? "Fluxo de Caixa" : "Balanço Patrimonial"}
              </button>
            ))}
          </div>

          <div className="p-6">
            {abaForm === "dre" && renderCampos(CAMPOS_DRE)}
            {abaForm === "caixa" && renderCampos(CAMPOS_CAIXA)}
            {abaForm === "balanco" && renderCampos(CAMPOS_BALANCO)}

            <div className="flex items-center gap-3 pt-4 border-t border-slate-700 mt-2">
              <button
                onClick={salvarLancamento}
                disabled={salvando}
                className="px-6 py-2.5 bg-[#1e3a5f] hover:bg-[#3D3A63] disabled:opacity-50 text-white rounded-xl font-semibold text-sm transition-all shadow-lg shadow-[#1e3a5f]/20"
              >
                {salvando ? "Salvando..." : "Salvar Lançamento"}
              </button>
              <button onClick={() => setAba("lista")} className="px-4 py-2.5 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-xl text-sm transition-all">
                Cancelar
              </button>
              {abaForm !== "balanco" && (
                <button
                  onClick={() => setAbaForm(abaForm === "dre" ? "caixa" : "balanco")}
                  className="ml-auto px-4 py-2.5 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-xl text-sm transition-all flex items-center gap-1"
                >
                  Próxima aba
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
