"use client";

import { useEffect, useState, useCallback } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";
import AbaCarga from "./_components/AbaCarga";
import AbaReforma from "./_components/AbaReforma";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

type Aba = "carga" | "reforma";

export default function PainelTributarioPage() {
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const [aba, setAba]           = useState<Aba>("carga");
  const [ano, setAno]           = useState(new Date().getFullYear());
  const [mes, setMes]           = useState(new Date().getMonth() + 1);
  const [cargaDados, setCargaDados] = useState<Record<string, unknown> | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro]         = useState("");

  const token = () => localStorage.getItem("controllo_token") ?? "";

  const carregar = useCallback(async (signal?: AbortSignal) => {
    if (!empresaId) { setCarregando(false); return; }
    setCarregando(true);
    setErro("");
    try {
      const h = { Authorization: `Bearer ${token()}` };
      const [dreRes, lancRes] = await Promise.all([
        fetch(`${API}/api/financeiro/dre/${empresaId}?ano=${ano}&mes=${mes}`, { headers: h, signal }),
        fetch(`${API}/api/financeiro/lancamentos/${empresaId}`, { headers: h, signal }),
      ]);

      if (!dreRes.ok) {
        const detail = await dreRes.json().catch(() => null);
        setErro(detail?.detail || `Erro ao carregar dados tributários (HTTP ${dreRes.status}).`);
        setCargaDados(null);
        return;
      }
      if (!lancRes.ok) {
        const detail = await lancRes.json().catch(() => null);
        setErro(detail?.detail || `Erro ao carregar lançamentos (HTTP ${lancRes.status}).`);
        setCargaDados(null);
        return;
      }

      const dre = await dreRes.json();
      const lanc = await lancRes.json();

      if (dre.sem_dados) { setCargaDados(null); return; }
      const historico = Array.isArray(lanc) ? [...lanc].reverse().slice(0, 12) : [];
      setCargaDados({ kpis: dre.metricas, historico });
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") return;
      setErro("Não foi possível conectar ao servidor. Verifique se o backend está ativo.");
      setCargaDados(null);
    } finally {
      setCarregando(false);
    }
  }, [empresaId, ano, mes]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60_000);
    carregar(controller.signal);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [carregar]);

  const DEMO_CARGA: Record<string, unknown> = {
    kpis: {
      receita_bruta:      200000,
      deducoes_receita:   18000,
      receita_liquida:    182000,
      ir_csll:            9000,
      total_tributos:     27000,
      carga_tributaria:   13.5,
      lucro_liquido:      51000,
      margem_liquida:     25.5,
    },
    historico: [
      { mes_label: "Jan/24", receita_bruta: 120000, deducoes_receita: 10200, ir_csll: 6000, total_tributos: 16200, carga_tributaria: 13.5 },
      { mes_label: "Fev/24", receita_bruta: 115000, deducoes_receita:  9775, ir_csll: 5750, total_tributos: 15525, carga_tributaria: 13.5 },
      { mes_label: "Mar/24", receita_bruta: 130000, deducoes_receita: 11050, ir_csll: 6500, total_tributos: 17550, carga_tributaria: 13.5 },
      { mes_label: "Abr/24", receita_bruta: 145000, deducoes_receita: 12325, ir_csll: 7250, total_tributos: 19575, carga_tributaria: 13.5 },
      { mes_label: "Mai/24", receita_bruta: 160000, deducoes_receita: 13600, ir_csll: 8000, total_tributos: 21600, carga_tributaria: 13.5 },
      { mes_label: "Jun/24", receita_bruta: 175000, deducoes_receita: 14875, ir_csll: 8750, total_tributos: 23625, carga_tributaria: 13.5 },
    ],
  };

  const isDemo = !empresaId || (!cargaDados && !carregando);
  const cargaVisiveis = cargaDados ?? (isDemo ? DEMO_CARGA : null);

  const ANOS = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i);
  const MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];

  const ABAS: { key: Aba; label: string; icon: string }[] = [
    { key: "carga",   label: "Carga Tributária",        icon: "M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z" },
    { key: "reforma", label: "Simulação da Reforma",    icon: "M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z" },
  ];

  return (
    <div className="min-h-full bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">

      {/* ── HEADER ── */}
      <header className="px-8 pt-8 pb-0 border-b border-slate-200 dark:border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-5">
          <div className="flex items-center gap-4">
            {/* Icon */}
            <div className="relative flex-shrink-0">
              <div className="w-12 h-12 rounded-2xl flex items-center justify-center bg-red-50 border border-red-200 dark:bg-red-900/20 dark:border-red-800/40">
                <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                    d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-red-500 border-2 border-white dark:border-slate-900" />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-widest mb-1 text-red-600 dark:text-red-400">
                Tributário
              </p>
              <h1 className="text-2xl font-extrabold tracking-tight">Análise Tributária</h1>
              <p className="text-sm mt-0.5 text-slate-500 dark:text-slate-400">
                <span className="text-navy-600 dark:text-navy-400 font-medium">
                  {empresaSelecionada?.nome ?? "Empresa"}
                </span>
                <span className="mx-2 text-slate-300 dark:text-slate-600">·</span>
                Carga Atual · Impacto da Reforma Tributária (IBS/CBS)
              </p>
            </div>
          </div>

          {/* Seletores de mês/ano */}
          {aba === "carga" && (
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden bg-slate-50 dark:bg-slate-800/50">
                {MESES.map((m, i) => (
                  <button
                    key={i + 1}
                    onClick={() => setMes(i + 1)}
                    className={`px-2.5 py-1.5 text-[11px] font-semibold transition-colors ${
                      mes === i + 1
                        ? "bg-navy-600 text-white dark:bg-navy-500"
                        : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700/50"
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
              <div className="flex rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden bg-slate-50 dark:bg-slate-800/50">
                {ANOS.map((a) => (
                  <button
                    key={a}
                    onClick={() => setAno(a)}
                    className={`px-3 py-1.5 text-xs font-semibold transition-colors ${
                      ano === a
                        ? "bg-navy-600 text-white dark:bg-navy-500"
                        : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700/50"
                    }`}
                  >
                    {a}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Tab Bar */}
        <div className="flex gap-0.5 relative">
          {ABAS.map((a) => (
            <button
              key={a.key}
              onClick={() => setAba(a.key)}
              className={`relative px-5 py-3 text-sm font-semibold flex items-center gap-2 transition-colors ${
                aba === a.key
                  ? "text-navy-700 dark:text-navy-300"
                  : "text-slate-500 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              }`}
            >
              {aba === a.key && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full bg-navy-500 dark:bg-navy-400" />
              )}
              <svg
                className={`w-3.5 h-3.5 ${aba === a.key ? "text-navy-600 dark:text-navy-400" : "text-slate-400 dark:text-slate-600"}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={a.icon} />
              </svg>
              <span>{a.label}</span>
            </button>
          ))}
        </div>
      </header>

      <div className="px-8 py-8">
        {/* Demo banner */}
        {isDemo && !carregando && aba === "carga" && (
          <div className="mb-6 flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-200 dark:bg-amber-500/10 dark:border-amber-500/30 rounded-xl text-amber-800 dark:text-amber-300 text-sm">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span><strong>Dados de Demonstração</strong> — Selecione uma empresa para visualizar seus dados reais.</span>
          </div>
        )}

        {/* Skeleton loading */}
        {carregando && aba === "carga" && (
          <div className="space-y-6 page-enter">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 space-y-3">
                  <div className="skeleton h-3 w-20 rounded" />
                  <div className="skeleton h-7 w-28 rounded" />
                  <div className="skeleton h-3 w-16 rounded" />
                </div>
              ))}
            </div>
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5">
              <div className="skeleton h-4 w-48 rounded mb-5" />
              <div className="skeleton h-64 w-full rounded-xl" />
            </div>
          </div>
        )}

        {/* Erro */}
        {erro && !carregando && aba === "carga" && empresaId && (
          <div className="rounded-2xl border border-red-200 dark:border-red-500/20 px-5 py-4 flex items-center justify-between gap-4 bg-red-50 dark:bg-red-900/20">
            <div className="flex items-center gap-3">
              <svg className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-red-700 dark:text-red-300 text-sm">{erro}</span>
            </div>
            <button
              onClick={() => carregar()}
              className="flex-shrink-0 text-xs font-bold text-red-700 dark:text-red-400 border border-red-300 dark:border-red-500/30 hover:bg-red-100 dark:hover:bg-red-500/10 px-3 py-1.5 rounded-xl transition-colors"
            >
              Tentar novamente
            </button>
          </div>
        )}

        {/* Aba Carga */}
        {!carregando && aba === "carga" && cargaVisiveis && (
          <div className="rounded-2xl border border-slate-200 dark:border-slate-700/50 overflow-hidden bg-white dark:bg-slate-800/50">
            <AbaCarga dados={cargaVisiveis} />
          </div>
        )}

        {/* Aba Reforma */}
        {aba === "reforma" && (
          <div className="rounded-2xl border border-slate-200 dark:border-slate-700/50 overflow-hidden bg-white dark:bg-slate-800/50">
            <AbaReforma empresaId={empresaId} token={token} />
          </div>
        )}
      </div>
    </div>
  );
}
