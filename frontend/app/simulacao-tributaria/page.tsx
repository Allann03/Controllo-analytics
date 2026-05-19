"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

interface Empresa {
  id: number;
  nome: string;
  regime_tributario: string;
  anexo_simples: string;
  atividade_principal: string;
  atividade_secundaria: string;
}

interface DetalheAtual { tributo: string; aliquota_pct: number; base: string; valor: number; }
interface DetalheNovo { tributo: string; aliquota_pct: number; valor_bruto: number; credito: number; valor_liquido: number; }
interface SimulacaoData {
  regime_atual: { nome: string; label: string; detalhes: DetalheAtual[]; total: number; pct_receita: number; };
  regime_novo: { nome: string; label: string; detalhes: DetalheNovo[]; total: number; pct_receita: number; };
  comparativo: { diferenca_rs: number; variacao_pct: number; impacto_lucro_rs: number; impacto: string; alerta_forte: boolean; recomendacao: string; };
  inputs: { receita_bruta: number; custo_servicos: number; };
}

interface SimplesAnexo {
  label: string; descricao: string; total: number; pct_receita: number;
  aliquota_efetiva_pct: number; faixa: string; detalhes: DetalheAtual[]; eh_atual: boolean;
}
interface ComparacaoData {
  simples: Record<string, SimplesAnexo>;
  presumido: { label: string; total: number; pct_receita: number; detalhes: DetalheAtual[]; base_irpj: number; eh_atual: boolean; };
  real: { label: string; total: number; pct_receita: number; lucro_real: number; margem_lucro_pct: number; detalhes: DetalheAtual[]; eh_atual: boolean; };
  reforma: { label: string; total: number; pct_receita: number; detalhes: DetalheNovo[]; };
  ranking: { regime: string; label: string; total: number; }[];
  inputs: { receita_bruta: number; custo_servicos: number; aliquota_iss: number; rbt12: number | null; regime_atual: string; anexo_simples_atual: string; };
}

function formatBRL(v: number) {
  return Math.abs(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function BarComparativa({ val1, val2, label1, label2, cor1, cor2 }: {
  val1: number; val2: number; label1: string; label2: string; cor1: string; cor2: string;
}) {
  const max = Math.max(val1, val2);
  const pct1 = max > 0 ? (val1 / max) * 100 : 0;
  const pct2 = max > 0 ? (val2 / max) * 100 : 0;
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <span className="text-xs text-[#64748B] dark:text-slate-400 w-28 text-right">{label1}</span>
        <div className="flex-1 bg-slate-200 dark:bg-slate-700/40 rounded-full h-5 overflow-hidden">
          <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct1}%`, background: cor1 }} />
        </div>
        <span className="text-xs font-mono text-[#475569] dark:text-slate-300 w-24">{formatBRL(val1)}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs text-[#64748B] dark:text-slate-400 w-28 text-right">{label2}</span>
        <div className="flex-1 bg-slate-200 dark:bg-slate-700/40 rounded-full h-5 overflow-hidden">
          <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct2}%`, background: cor2 }} />
        </div>
        <span className="text-xs font-mono text-[#475569] dark:text-slate-300 w-24">{formatBRL(val2)}</span>
      </div>
    </div>
  );
}

const ANEXOS_LABELS: Record<string, string> = {
  I: "Anexo I — Comércio",
  II: "Anexo II — Indústria",
  III: "Anexo III — Serviços em geral",
  IV: "Anexo IV — Serviços c/ CPP separada",
  V: "Anexo V — Serviços fator R",
};

export default function SimulacaoTributariaPage() {
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [receitaInput, setReceitaInput] = useState("");
  const [custoInput, setCustoInput] = useState("");
  const [aliquotaIss, setAliquotaIss] = useState("5");
  const [modoManual, setModoManual] = useState(false);
  const [modoComparacao, setModoComparacao] = useState(true);

  // Reforma vs. Atual
  const [dados, setDados] = useState<SimulacaoData | null>(null);
  // Todos os regimes
  const [comparacao, setComparacao] = useState<ComparacaoData | null>(null);

  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const receitaRef = useRef(receitaInput);
  const custoRef = useRef(custoInput);
  const aliquotaRef = useRef(aliquotaIss);

  useEffect(() => { receitaRef.current = receitaInput; }, [receitaInput]);
  useEffect(() => { custoRef.current = custoInput; }, [custoInput]);
  useEffect(() => { aliquotaRef.current = aliquotaIss; }, [aliquotaIss]);

  const h = () => ({ Authorization: `Bearer ${localStorage.getItem("controllo_token") || ""}` });

  useEffect(() => {
    fetch(`${API}/api/financeiro/empresas`, { headers: h() })
      .then(r => r.json())
      .then(d => { if (Array.isArray(d)) setEmpresas(d); })
      .catch(() => {});
  }, []);

  const carregar = useCallback(async (manual = false, signal?: AbortSignal) => {
    if (!empresaId) { setCarregando(false); return; }
    setCarregando(true); setErro(null);
    try {
      const rb = manual && receitaRef.current ? parseFloat(receitaRef.current.replace(",", ".")) : undefined;
      const cs = manual && custoRef.current ? parseFloat(custoRef.current.replace(",", ".")) : undefined;
      const iss = parseFloat(aliquotaRef.current.replace(",", ".")) / 100;
      const params = new URLSearchParams();
      if (rb && !isNaN(rb)) params.set("receita_bruta", String(rb));
      if (cs && !isNaN(cs)) params.set("custo_servicos", String(cs));
      if (!isNaN(iss)) params.set("aliquota_iss", String(iss));

      const [r1, r2] = await Promise.all([
        fetch(`${API}/api/financeiro/simulacao/${empresaId}?${params}`, { headers: h(), signal }),
        fetch(`${API}/api/financeiro/comparar-regimes/${empresaId}?${params}`, { headers: h(), signal }),
      ]);
      const [d1, d2] = await Promise.all([r1.json(), r2.json()]);
      if (!r1.ok) throw new Error(d1.detail || "Erro ao simular.");
      setDados(d1);
      if (r2.ok) setComparacao(d2);
      if (!manual && d1.inputs) {
        setReceitaInput(String(d1.inputs.receita_bruta));
        setCustoInput(String(d1.inputs.custo_servicos));
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") return;
      setErro(e instanceof Error ? e.message : "Erro desconhecido.");
    }
    finally { setCarregando(false); }
  }, [empresaId]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60_000);
    carregar(false, controller.signal);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [carregar]);

  const empresaSel = empresas.find(e => e.id === empresaId);

  return (
    <div className="min-h-full p-6" style={{ background: "var(--bg-canvas)", color: "var(--text-primary)" }}>

      {/* Header */}
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          Simulação Tributária
        </h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
          Descubra qual regime (Simples, Presumido, Real) gera a menor carga para sua empresa
        </p>
      </header>

      {!empresaId && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <svg className="w-10 h-10 mb-4 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
          <p className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>Nenhuma empresa selecionada</p>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Use o seletor no menu superior para escolher uma empresa</p>
        </div>
      )}

      {/* Inputs */}
      {empresaId && <div className="mb-6 space-y-4">
        <div className="flex flex-wrap items-center gap-4 p-5 bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm">
          {/* Info atividade da empresa */}
          {empresaSel && (empresaSel.atividade_principal || empresaSel.atividade_secundaria) && (
            <div className="flex-1 min-w-[200px] px-3 py-2 bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700/50 rounded-xl">
              {empresaSel.atividade_principal && (
                <p className="text-xs text-[#64748B] dark:text-slate-400">
                  <span className="font-bold text-[#475569] dark:text-slate-300">Atividade principal:</span> {empresaSel.atividade_principal}
                </p>
              )}
              {empresaSel.atividade_secundaria && (
                <p className="text-xs text-[#64748B] dark:text-slate-500 mt-0.5">
                  <span className="font-semibold">Secundária:</span> {empresaSel.atividade_secundaria}
                </p>
              )}
              {empresaSel.regime_tributario === "simples" && empresaSel.anexo_simples && (
                <p className="text-xs text-[#1E4976] dark:text-[#9BB3FF] mt-0.5">
                  {ANEXOS_LABELS[empresaSel.anexo_simples] ?? `Anexo ${empresaSel.anexo_simples}`}
                </p>
              )}
            </div>
          )}

          {empresaId && (
            <div className="flex gap-2">
              <button
                onClick={() => setModoManual(v => !v)}
                className={`px-4 py-2.5 rounded-xl text-sm font-semibold border transition-all ${
                  modoManual ? "bg-[#1e3a5f] border-[#102a43] text-white" : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-white"
                }`}
              >
                Valores manuais
              </button>
              <button
                onClick={() => setModoComparacao(v => !v)}
                className={`px-4 py-2.5 rounded-xl text-sm font-semibold border transition-all ${
                  modoComparacao ? "bg-emerald-50 dark:bg-emerald-900/60 border-emerald-300 dark:border-emerald-500/50 text-emerald-700 dark:text-emerald-300" : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-white"
                }`}
              >
                Comparar todos os regimes
              </button>
            </div>
          )}
        </div>

        {empresaId && modoManual && (
          <div className="flex flex-wrap items-end gap-4 p-5 bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 border-dashed rounded-2xl">
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-widest mb-1">Receita Bruta (R$)</label>
              <input type="number" value={receitaInput} onChange={e => setReceitaInput(e.target.value)}
                placeholder="ex: 100000"
                className="w-40 px-3 py-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-sm focus:outline-none focus:border-navy-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-widest mb-1">Custo dos Serviços (R$)</label>
              <input type="number" value={custoInput} onChange={e => setCustoInput(e.target.value)}
                placeholder="ex: 40000"
                className="w-40 px-3 py-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-sm focus:outline-none focus:border-navy-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-widest mb-1">Alíquota ISS (%)</label>
              <input type="number" value={aliquotaIss} onChange={e => setAliquotaIss(e.target.value)}
                placeholder="5" min="2" max="5" step="0.5"
                className="w-24 px-3 py-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-sm focus:outline-none focus:border-navy-500" />
            </div>
            <button onClick={() => carregar(true)} disabled={carregando}
              className="px-5 py-2.5 bg-[#1E4976] hover:bg-[#0F2D4A] disabled:opacity-50 text-white rounded-xl font-semibold text-sm transition-all">
              {carregando ? "Simulando..." : "Simular"}
            </button>
          </div>
        )}
      </div>}

      {carregando && (
        <div className="py-24 flex items-center justify-center">
          <div className="w-10 h-10 border-2 border-[#102a43]/30 border-t-[#102a43] rounded-full animate-spin" />
        </div>
      )}

      {erro && (
        <div className="p-5 bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl">
          <div className="flex items-start gap-3">
            <svg className="w-6 h-6 text-amber-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" /></svg>
            <div>
              <p className="text-sm font-bold text-slate-900 dark:text-white">{erro}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">Para que a simulação funcione, verifique se a empresa possui:</p>
              <ul className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 space-y-1 list-disc list-inside">
                <li>Lançamentos financeiros cadastrados (receitas e despesas)</li>
                <li>Regime tributário definido no cadastro da empresa</li>
                <li>Receita bruta maior que zero no período</li>
              </ul>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">Você também pode usar o modo <strong>Valores manuais</strong> para informar receita e custos diretamente.</p>
            </div>
          </div>
        </div>
      )}

      {/* ── MODO COMPARAÇÃO — todos os regimes ── */}
      {modoComparacao && comparacao && !carregando && (
        <div className="space-y-6">

          {/* Ranking */}
          <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-5">
            <p className="text-xs font-black text-[#64748B] dark:text-slate-400 uppercase tracking-widest mb-4">
              Ranking — do menor para o maior custo tributário
            </p>
            <div className="space-y-2">
              {comparacao.ranking.map((r, i) => {
                const max = comparacao.ranking[comparacao.ranking.length - 1].total;
                const pct = max > 0 ? (r.total / max) * 100 : 0;
                const isBest = i === 0;
                return (
                  <div key={r.regime} className={`flex items-center gap-3 ${isBest ? "bg-emerald-50 dark:bg-emerald-900/20 -mx-3 px-3 py-2 rounded-xl border border-emerald-200 dark:border-emerald-700/40" : ""}`}>
                    <span className={`text-xs font-bold w-5 ${isBest ? "text-emerald-600 dark:text-emerald-400" : "text-[#64748B] dark:text-slate-500"}`}>#{i + 1}</span>
                    <span className="text-xs text-[#64748B] dark:text-slate-400 w-56 truncate flex items-center gap-2">
                      {r.label}
                      {isBest && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-600 text-white uppercase tracking-wide">Recomendado</span>}
                    </span>
                    <div className="flex-1 bg-slate-200 dark:bg-slate-700/40 rounded-full h-4 overflow-hidden">
                      <div className="h-full rounded-full" style={{
                        width: `${pct}%`,
                        background: isBest ? "#1A6B3C" : i === comparacao.ranking.length - 1 ? "#B83030" : "#1E4976",
                      }} />
                    </div>
                    <span className={`text-xs font-mono font-bold w-24 text-right ${isBest ? "text-emerald-600 dark:text-emerald-400" : "text-[#475569] dark:text-slate-300"}`}>
                      {formatBRL(r.total)}
                    </span>
                    <span className="text-xs text-[#64748B] dark:text-slate-500 w-16 text-right">
                      {comparacao.inputs.receita_bruta > 0
                        ? `${((r.total / comparacao.inputs.receita_bruta) * 100).toFixed(1)}%`
                        : "—"}
                    </span>
                  </div>
                );
              })}
            </div>
            {comparacao.ranking.length >= 2 && (() => {
              const economiaAnual = (comparacao.ranking[comparacao.ranking.length - 1].total - comparacao.ranking[0].total) * 12;
              return economiaAnual > 0 ? (
                <div className="mt-4 p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700/40 rounded-xl flex items-center gap-3">
                  <span className="text-lg">💰</span>
                  <div>
                    <p className="text-xs font-bold text-emerald-800 dark:text-emerald-300">Economia anual estimada</p>
                    <p className="text-lg font-black font-mono text-emerald-700 dark:text-emerald-400">{formatBRL(economiaAnual)}</p>
                    <p className="text-[10px] text-emerald-600 dark:text-emerald-500">Diferença entre o regime mais caro e o mais barato, projetada em 12 meses</p>
                  </div>
                </div>
              ) : null;
            })()}
            <p className="text-xs text-[#475569] dark:text-slate-600 mt-3">
              Base: {formatBRL(comparacao.inputs.receita_bruta)} receita · {formatBRL(comparacao.inputs.custo_servicos)} custo · ISS {(comparacao.inputs.aliquota_iss * 100).toFixed(1)}%
            </p>
          </div>

          {/* Cards de cada regime */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Lucro Presumido */}
            <RegimeCard
              label="Lucro Presumido"
              total={comparacao.presumido.total}
              pctReceita={comparacao.presumido.pct_receita}
              ehAtual={comparacao.presumido.eh_atual}
              detalhes={comparacao.presumido.detalhes}
              cor="amber"
              recomendado={comparacao.ranking.length > 0 && comparacao.ranking[0].regime === "presumido"}
            />
            {/* Lucro Real */}
            <RegimeCard
              label="Lucro Real"
              sublabel={`Margem: ${comparacao.real.margem_lucro_pct.toFixed(1)}%`}
              total={comparacao.real.total}
              pctReceita={comparacao.real.pct_receita}
              ehAtual={comparacao.real.eh_atual}
              detalhes={comparacao.real.detalhes}
              cor="blue"
              recomendado={comparacao.ranking.length > 0 && comparacao.ranking[0].regime === "real"}
            />
            {/* Reforma */}
            <div className={`bg-white dark:bg-slate-800/40 border rounded-2xl overflow-hidden ${comparacao.ranking.length > 0 && comparacao.ranking[0].regime === "reforma" ? "border-2 border-emerald-500 dark:border-emerald-400 ring-2 ring-emerald-200 dark:ring-emerald-800/40" : "border-slate-200 dark:border-slate-700"}`}>
              <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 flex items-center justify-between">
                <div>
                  {comparacao.ranking.length > 0 && comparacao.ranking[0].regime === "reforma" && <p className="inline-flex items-center px-2 py-0.5 mb-1 rounded-full text-[10px] font-bold bg-emerald-600 text-white uppercase tracking-wide">Recomendado</p>}
                  <p className="text-[10px] font-black text-[#64748B] dark:text-slate-500 uppercase tracking-widest">Projeção Futura</p>
                  <p className="text-sm font-black text-[#0F172A] dark:text-white">Reforma Tributária</p>
                  <p className="text-[10px] text-[#64748B] dark:text-slate-500">IBS + CBS</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-black font-mono text-[#1E4976] dark:text-indigo-400">{formatBRL(comparacao.reforma.total)}</p>
                  <p className="text-xs text-[#64748B] dark:text-slate-500">{comparacao.reforma.pct_receita.toFixed(1)}%</p>
                </div>
              </div>
              <table className="w-full text-xs">
                <tbody>
                  {comparacao.reforma.detalhes.map((d: any, i: number) => (
                    <tr key={i} className="border-b border-slate-100 dark:border-slate-800 last:border-0">
                      <td className="px-4 py-2 text-[#64748B] dark:text-slate-400">{d.tributo}</td>
                      <td className="px-4 py-2 text-right font-mono text-emerald-600 dark:text-emerald-400">-{formatBRL(d.credito ?? 0)}</td>
                      <td className="px-4 py-2 text-right font-mono text-[#1E4976] dark:text-indigo-400">{formatBRL(d.valor_liquido ?? d.valor ?? 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Simples Nacional — todos os anexos */}
          <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-200 dark:border-slate-700">
              <p className="text-xs font-black text-[#64748B] dark:text-slate-400 uppercase tracking-widest">
                Simples Nacional — Comparativo de Anexos
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 text-[11px] text-[#64748B] dark:text-slate-500 uppercase">
                    <th className="px-4 py-2.5 text-left">Anexo</th>
                    <th className="px-4 py-2.5 text-left">Atividade</th>
                    <th className="px-4 py-2.5 text-right">Alíq. Efetiva</th>
                    <th className="px-4 py-2.5 text-right">DAS (R$)</th>
                    <th className="px-4 py-2.5 text-right">% Receita</th>
                    <th className="px-4 py-2.5 text-left">Faixa</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(comparacao.simples).map(([anexo, dados]) => (
                    <tr key={anexo} className={`border-b border-slate-100 dark:border-slate-800 ${dados.eh_atual ? "bg-[#1E4976]/10 dark:bg-[#1e3a5f]/40" : "hover:bg-slate-50 dark:hover:bg-slate-800/20"}`}>
                      <td className="px-4 py-2.5 font-bold text-[#0F172A] dark:text-white">
                        {anexo}
                        {dados.eh_atual && <span className="ml-2 text-[10px] text-[#1E4976] dark:text-[#9BB3FF] font-normal">(atual)</span>}
                      </td>
                      <td className="px-4 py-2.5 text-[#64748B] dark:text-slate-400 text-xs max-w-[200px] truncate">{dados.descricao}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-[#475569] dark:text-slate-300">{dados.aliquota_efetiva_pct.toFixed(2)}%</td>
                      <td className="px-4 py-2.5 text-right font-mono font-bold text-amber-700 dark:text-amber-400">{formatBRL(dados.total)}</td>
                      <td className="px-4 py-2.5 text-right text-[#64748B] dark:text-slate-400">{dados.pct_receita.toFixed(1)}%</td>
                      <td className="px-4 py-2.5 text-xs text-[#64748B] dark:text-slate-500">{dados.faixa}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── MODO REFORMA — regime atual vs. novo modelo ── */}
      {!modoComparacao && dados && !carregando && (
        <div className="space-y-6">
          {/* Card de recomendação */}
          <div className={`p-5 rounded-2xl border ${
            dados.comparativo.alerta_forte ? "bg-rose-50 dark:bg-rose-500/5 border-rose-200 dark:border-rose-500/30" : "bg-emerald-50 dark:bg-emerald-500/5 border-emerald-200 dark:border-emerald-500/30"
          }`}>
            <div className="flex items-start gap-3">
              <span className="text-2xl">{dados.comparativo.alerta_forte ? "⚠️" : "✅"}</span>
              <div>
                <p className="text-base font-bold text-[#0F172A] dark:text-white">{dados.comparativo.recomendacao}</p>
                <p className="text-sm text-[#64748B] dark:text-slate-400 mt-1">
                  Impacto no lucro líquido:{" "}
                  <span className={dados.comparativo.impacto_lucro_rs >= 0 ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"}>
                    {dados.comparativo.impacto_lucro_rs >= 0 ? "+" : ""}{formatBRL(dados.comparativo.impacto_lucro_rs)}
                  </span>
                </p>
              </div>
            </div>
          </div>

          {/* Side-by-side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Regime Atual */}
            <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[10px] font-black text-[#64748B] dark:text-slate-500 uppercase tracking-widest">Regime Atual</p>
                    <p className="text-lg font-black text-[#0F172A] dark:text-white mt-0.5">{dados.regime_atual.label}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-[#64748B] dark:text-slate-500">Carga Total</p>
                    <p className="text-2xl font-black font-mono text-amber-700 dark:text-amber-400">{formatBRL(dados.regime_atual.total)}</p>
                    <p className="text-xs text-[#64748B] dark:text-slate-500">{dados.regime_atual.pct_receita.toFixed(1)}% da receita</p>
                  </div>
                </div>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th className="px-5 py-2.5 text-left text-xs font-bold text-[#64748B] dark:text-slate-500">Tributo</th>
                    <th className="px-5 py-2.5 text-right text-xs font-bold text-[#64748B] dark:text-slate-500">Alíq.</th>
                    <th className="px-5 py-2.5 text-right text-xs font-bold text-[#64748B] dark:text-slate-500">Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {dados.regime_atual.detalhes.map((d, i) => (
                    <tr key={i} className="border-b border-slate-100 dark:border-slate-700/40 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700/10">
                      <td className="px-5 py-2.5 text-[#475569] dark:text-slate-300">{d.tributo}</td>
                      <td className="px-5 py-2.5 text-right text-xs text-[#64748B] dark:text-slate-500">{d.aliquota_pct.toFixed(2)}%</td>
                      <td className="px-5 py-2.5 text-right font-mono text-xs text-amber-700 dark:text-amber-400">{formatBRL(d.valor)}</td>
                    </tr>
                  ))}
                  <tr className="border-t-2 border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/40 font-black">
                    <td className="px-5 py-3 text-[#0F172A] dark:text-white uppercase text-xs">Total</td>
                    <td />
                    <td className="px-5 py-3 text-right font-mono text-base text-amber-700 dark:text-amber-400">{formatBRL(dados.regime_atual.total)}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Reforma */}
            <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[10px] font-black text-[#64748B] dark:text-slate-500 uppercase tracking-widest">Novo Modelo</p>
                    <p className="text-lg font-black text-[#0F172A] dark:text-white mt-0.5">{dados.regime_novo.label}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-[#64748B] dark:text-slate-500">Carga Total</p>
                    <p className={`text-2xl font-black font-mono ${dados.regime_novo.total > dados.regime_atual.total ? "text-rose-700 dark:text-rose-400" : "text-emerald-700 dark:text-emerald-400"}`}>
                      {formatBRL(dados.regime_novo.total)}
                    </p>
                    <p className="text-xs text-[#64748B] dark:text-slate-500">{dados.regime_novo.pct_receita.toFixed(1)}% da receita</p>
                  </div>
                </div>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th className="px-5 py-2.5 text-left text-xs font-bold text-[#64748B] dark:text-slate-500">Tributo</th>
                    <th className="px-5 py-2.5 text-right text-xs font-bold text-[#64748B] dark:text-slate-500">Bruto</th>
                    <th className="px-5 py-2.5 text-right text-xs font-bold text-[#64748B] dark:text-slate-500">Crédito</th>
                    <th className="px-5 py-2.5 text-right text-xs font-bold text-[#64748B] dark:text-slate-500">Líquido</th>
                  </tr>
                </thead>
                <tbody>
                  {dados.regime_novo.detalhes.map((d, i) => (
                    <tr key={i} className="border-b border-slate-100 dark:border-slate-700/40 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700/10">
                      <td className="px-5 py-2.5 text-[#475569] dark:text-slate-300 text-xs">{d.tributo}</td>
                      <td className="px-5 py-2.5 text-right font-mono text-xs text-[#64748B] dark:text-slate-500">{formatBRL(d.valor_bruto)}</td>
                      <td className="px-5 py-2.5 text-right font-mono text-xs text-emerald-700 dark:text-emerald-400">-{formatBRL(d.credito)}</td>
                      <td className="px-5 py-2.5 text-right font-mono text-xs text-[#1E4976] dark:text-blue-400">{formatBRL(d.valor_liquido)}</td>
                    </tr>
                  ))}
                  <tr className="border-t-2 border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/40 font-black">
                    <td className="px-5 py-3 text-[#0F172A] dark:text-white uppercase text-xs" colSpan={3}>Total</td>
                    <td className="px-5 py-3 text-right font-mono text-base text-[#1E4976] dark:text-blue-400">{formatBRL(dados.regime_novo.total)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Comparativo Visual */}
          <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-5">
            <p className="text-xs font-black text-[#64748B] dark:text-slate-400 uppercase tracking-widest mb-5">Comparativo Visual</p>
            <BarComparativa
              val1={dados.regime_atual.total}
              val2={dados.regime_novo.total}
              label1="Regime Atual"
              label2="Reforma"
              cor1="#f59e0b"
              cor2={dados.regime_novo.total > dados.regime_atual.total ? "#f43f5e" : "#10b981"}
            />
            <div className="mt-5 pt-4 border-t border-slate-200 dark:border-slate-700 flex flex-wrap gap-8">
              <div>
                <p className="text-[10px] text-[#64748B] dark:text-slate-500 uppercase font-bold">Diferença</p>
                <p className={`text-xl font-black font-mono ${dados.comparativo.diferenca_rs > 0 ? "text-rose-700 dark:text-rose-400" : "text-emerald-700 dark:text-emerald-400"}`}>
                  {dados.comparativo.diferenca_rs > 0 ? "+" : "-"}{formatBRL(dados.comparativo.diferenca_rs)}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-[#64748B] dark:text-slate-500 uppercase font-bold">Variação %</p>
                <p className={`text-xl font-black ${dados.comparativo.variacao_pct > 0 ? "text-rose-700 dark:text-rose-400" : "text-emerald-700 dark:text-emerald-400"}`}>
                  {dados.comparativo.variacao_pct > 0 ? "▲" : "▼"} {Math.abs(dados.comparativo.variacao_pct).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-[10px] text-[#64748B] dark:text-slate-500 uppercase font-bold">Base de Cálculo</p>
                <p className="text-sm text-[#475569] dark:text-slate-300">Receita: {formatBRL(dados.inputs.receita_bruta)}</p>
                <p className="text-sm text-[#64748B] dark:text-slate-400">Custo: {formatBRL(dados.inputs.custo_servicos)}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function RegimeCard({ label, sublabel, total, pctReceita, ehAtual, detalhes, cor, recomendado }: {
  label: string; sublabel?: string; total: number; pctReceita: number;
  ehAtual: boolean; detalhes: any[]; cor: "amber" | "blue"; recomendado?: boolean;
}) {
  const corTotal = cor === "amber" ? "text-amber-700 dark:text-amber-400" : "text-[#1E4976] dark:text-blue-400";
  return (
    <div className={`bg-white dark:bg-slate-800/40 border rounded-2xl overflow-hidden ${recomendado ? "border-2 border-emerald-500 dark:border-emerald-400 ring-2 ring-emerald-200 dark:ring-emerald-800/40" : ehAtual ? "border-[#1E4976] dark:border-[#102a43]" : "border-slate-200 dark:border-slate-700"}`}>
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 flex items-center justify-between">
        <div>
          {recomendado && <p className="inline-flex items-center px-2 py-0.5 mb-1 rounded-full text-[10px] font-bold bg-emerald-600 text-white uppercase tracking-wide">Recomendado</p>}
          {ehAtual && !recomendado && <p className="text-[10px] font-black text-[#1E4976] dark:text-[#9BB3FF] uppercase tracking-widest">Regime Atual</p>}
          {ehAtual && recomendado && <p className="text-[10px] font-black text-[#1E4976] dark:text-[#9BB3FF] uppercase tracking-widest">Regime Atual</p>}
          <p className="text-sm font-black text-[#0F172A] dark:text-white">{label}</p>
          {sublabel && <p className="text-[10px] text-[#64748B] dark:text-slate-500">{sublabel}</p>}
        </div>
        <div className="text-right">
          <p className={`text-lg font-black font-mono ${corTotal}`}>{Math.abs(total).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</p>
          <p className="text-xs text-[#64748B] dark:text-slate-500">{pctReceita.toFixed(1)}% receita</p>
        </div>
      </div>
      <table className="w-full text-xs">
        <tbody>
          {detalhes.map((d, i) => (
            <tr key={i} className="border-b border-slate-100 dark:border-slate-800 last:border-0">
              <td className="px-4 py-1.5 text-[#64748B] dark:text-slate-400 truncate max-w-[140px]">{d.tributo}</td>
              <td className="px-4 py-1.5 text-right text-[#64748B] dark:text-slate-500">{d.aliquota_pct?.toFixed(2)}%</td>
              <td className={`px-4 py-1.5 text-right font-mono ${corTotal}`}>
                {Math.abs(d.valor ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
