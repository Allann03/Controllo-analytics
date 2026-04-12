"use client";

import { useEffect, useState, useCallback } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";
import RelatorioView from "./_components/RelatorioView";
import { MESES, ANOS } from "./_components/types";
import type { LancamentoMensal } from "./_components/types";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

// ─────────────────────────────────────────────────────────────────
//  Dados de demonstração
// ─────────────────────────────────────────────────────────────────

const DEMO_RELATORIO: LancamentoMensal = {
  ano: new Date().getFullYear(), mes: new Date().getMonth() + 1,
  receita_bruta:            200000,
  deducoes_receita:          18000,
  custo_servicos:            72000,
  despesas_adm:              24000,
  despesas_comerciais:       18000,
  despesas_financeiras:       8000,
  outras_despesas:            4500,
  ir_csll:                    9000,
  entradas_caixa:           190000,
  saidas_caixa:             145000,
  saldo_inicial_caixa:       85000,
  caixa_equivalentes:        85000,
  contas_receber:           120000,
  estoques:                  95000,
  outros_ativo_circ:         30000,
  ativo_nao_circulante:     280000,
  fornecedores:              80000,
  emprestimos_cp:            50000,
  tributos_pagar:            35000,
  outros_passivo_circ:       25000,
  passivo_nao_circulante:   150000,
  capital_social:           200000,
  reservas:                 100000,
  lucros_acumulados:         70000,
  folha_pagamento:           39000,
  depreciacao_amortizacao:    8000,
};

// ─────────────────────────────────────────────────────────────────
//  Página
// ─────────────────────────────────────────────────────────────────

export default function RelatoriosPage() {
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const [ano, setAno]               = useState(new Date().getFullYear());
  const [mes, setMes]               = useState(new Date().getMonth() + 1);
  const [dados, setDados]           = useState<LancamentoMensal | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [baixando, setBaixando]     = useState(false);
  const [erro, setErro]             = useState("");

  const carregar = useCallback(async (signal?: AbortSignal) => {
    if (!empresaId) { setCarregando(false); return; }
    setCarregando(true);
    setErro("");
    try {
      const r = await fetch(`${API}/api/financeiro/lancamentos/${empresaId}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("controllo_token") ?? ""}` },
        signal,
      });
      if (!r.ok) {
        const detail = await r.json().catch(() => null);
        setErro(detail?.detail || "Erro ao carregar dados do servidor.");
        return;
      }
      const payload = await r.json();
      const all: LancamentoMensal[] = Array.isArray(payload) ? payload : [];
      const lanc = all.find(l => l.ano === ano && l.mes === mes) ?? null;
      setDados(lanc);
      if (!lanc) setErro("Nenhum lançamento para este período. Acesse Lançamentos para inserir dados.");
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") return;
      setErro("Não foi possível conectar ao servidor. Verifique se o backend está ativo e tente novamente.");
    }
    finally { setCarregando(false); }
  }, [empresaId, ano, mes]);

  useEffect(() => {
    const controller = new AbortController();
    carregar(controller.signal);
    return () => controller.abort();
  }, [carregar]);

  async function baixarExcel() {
    if (!empresaId) return;
    setBaixando(true);
    try {
      const r = await fetch(`${API}/api/relatorios/excel/${empresaId}?ano=${ano}&mes=${mes}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("controllo_token") ?? ""}` },
      });
      if (!r.ok) {
        const d = await r.json();
        setErro(d.detail || "Erro ao gerar Excel.");
        return;
      }
      const blob = await r.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href = url;
      a.download = `Controllo_${(empresaSelecionada?.nome || "relatorio").slice(0, 20)}_${MESES[mes-1]}${ano}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } finally { setBaixando(false); }
  }

  return (
    <>
      {/* CSS exclusivo para impressão */}
      <style>{`
        @media print {
          body { background: white !important; color: black !important; }
          .no-print { display: none !important; }
          .print-page { background: white !important; padding: 0 !important; }
          .print-section { break-inside: avoid; }
          h1, h2, h3 { color: black !important; }
        }
      `}</style>

      <div className="min-h-full bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 print-page">

        {/* ── HEADER — oculto na impressão ── */}
        <header className="px-8 pt-8 pb-6 border-b border-slate-200 dark:border-slate-700 no-print">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 mb-3">
                <span className="px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-widest bg-rose-50 border border-rose-200 text-rose-700 dark:bg-rose-900/20 dark:border-rose-800/40 dark:text-rose-400">
                  Exportação
                </span>
              </div>
              <h1 className="text-3xl font-extrabold tracking-tight">
                Relatórios{" "}
                <span className="text-rose-600 dark:text-rose-400">Financeiros</span>
              </h1>
              <p className="text-sm mt-1.5 text-slate-500 dark:text-slate-400">
                Exportação e impressão de relatórios por período
              </p>
            </div>

            {/* Controles */}
            <div className="flex items-center gap-2 flex-wrap">
              <select
                value={mes}
                onChange={e => setMes(Number(e.target.value))}
                className="rounded-xl px-3 py-2.5 text-sm border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-navy-300 dark:focus:ring-navy-700 transition-all"
              >
                {MESES.map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
              </select>
              <select
                value={ano}
                onChange={e => setAno(Number(e.target.value))}
                className="rounded-xl px-3 py-2.5 text-sm border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-navy-300 dark:focus:ring-navy-700 transition-all"
              >
                {ANOS.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
              <button
                onClick={baixarExcel}
                disabled={!dados || baixando}
                className="flex items-center gap-1.5 text-white text-sm font-bold px-4 py-2.5 rounded-xl transition-colors disabled:opacity-40 bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-600 dark:hover:bg-emerald-500"
              >
                {baixando ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                )}
                {baixando ? "Gerando..." : "Exportar Excel"}
              </button>
              <button
                onClick={() => window.print()}
                disabled={!dados}
                className="flex items-center gap-1.5 text-white text-sm font-bold px-4 py-2.5 rounded-xl transition-colors disabled:opacity-40 bg-rose-600 hover:bg-rose-700 dark:bg-rose-600 dark:hover:bg-rose-500"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                PDF / Imprimir
              </button>
            </div>
          </div>
        </header>

        <div className="px-8 py-6 space-y-6 max-w-5xl mx-auto">
          {carregando ? (
            <div className="space-y-6 no-print page-enter">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="bg-slate-50 border border-slate-200 dark:bg-slate-800/40 dark:border-slate-700 rounded-2xl p-5 space-y-3">
                  <div className="skeleton h-4 w-40 rounded" />
                  {[...Array(3)].map((_, j) => (
                    <div key={j} className="flex justify-between">
                      <div className="skeleton h-3 w-32 rounded" />
                      <div className="skeleton h-3 w-24 rounded" />
                    </div>
                  ))}
                </div>
              ))}
            </div>
          ) : erro && empresaId ? (
            <div className="px-5 py-4 rounded-xl bg-amber-50 border border-amber-200 dark:bg-amber-900/20 dark:border-amber-700/40 text-amber-800 dark:text-amber-300 text-sm no-print flex items-center justify-between gap-4">
              <span>{erro}</span>
              <button
                onClick={() => carregar()}
                className="flex-shrink-0 text-xs font-bold text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-600/40 hover:bg-amber-100 dark:hover:bg-amber-500/10 px-3 py-1.5 rounded-lg transition-colors"
              >
                Tentar novamente
              </button>
            </div>
          ) : (
            <>
              {(!empresaId || !dados) && !carregando && (
                <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-200 dark:bg-amber-500/10 dark:border-amber-500/30 rounded-xl text-amber-800 dark:text-amber-300 text-sm no-print">
                  <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span><strong>Dados de Demonstração</strong> — Selecione uma empresa para visualizar seus dados reais.</span>
                </div>
              )}
              <RelatorioView
                dados={dados ?? DEMO_RELATORIO}
                empresaNome={empresaSelecionada?.nome ?? "Empresa Demonstração"}
                empresaCnpj={empresaSelecionada?.cnpj ?? "00.000.000/0001-00"}
                mes={mes}
                ano={ano}
              />
            </>
          )}
        </div>
      </div>
    </>
  );
}
