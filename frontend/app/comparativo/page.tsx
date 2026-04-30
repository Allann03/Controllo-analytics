"use client";
import { useEffect, useState, useCallback } from "react";

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");
const MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
const ANO_ATUAL = new Date().getFullYear();

interface EmpresaOption { id: number; nome: string; }
interface ComparativoItem {
  empresa_id: number;
  nome: string;
  sem_dados?: boolean;
  receita_liquida?: number;
  lucro_liquido?: number;
  margem_liquida?: number;
  margem_bruta?: number;
  liquidez_corrente?: number;
  endividamento_geral?: number;
  ebitda?: number;
  roe?: number;
  saldo_caixa?: number;
  score_saude?: number;
  classificacao_saude?: string;
  cor_saude?: string;
  [key: string]: string | number | boolean | undefined;
}

function formatBRL(v: number | null | undefined) {
  if (v == null) return "—";
  return Math.abs(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
function formatPct(v: number | null | undefined) {
  if (v == null) return "—";
  return `${v.toFixed(1)}%`;
}
function formatNum(v: number | null | undefined, dec = 2) {
  if (v == null) return "—";
  return v.toFixed(dec);
}

const INDICADORES: { key: string; label: string; format: (v: number | null | undefined) => string; invertido?: boolean }[] = [
  { key: "score_saude", label: "Score de Saúde", format: (v) => v != null ? `${v}` : "—" },
  { key: "receita_liquida", label: "Receita Líquida", format: formatBRL },
  { key: "lucro_liquido", label: "Lucro Líquido", format: formatBRL },
  { key: "margem_liquida", label: "Margem Líquida", format: formatPct },
  { key: "margem_bruta", label: "Margem Bruta", format: formatPct },
  { key: "ebitda", label: "EBITDA", format: formatBRL },
  { key: "liquidez_corrente", label: "Liquidez Corrente", format: (v) => formatNum(v) },
  { key: "endividamento_geral", label: "Endividamento Geral", format: formatPct, invertido: true },
  { key: "roe", label: "ROE", format: formatPct },
  { key: "saldo_caixa", label: "Saldo de Caixa", format: formatBRL },
];

// Dados ilustrativos exibidos quando nenhuma empresa esta selecionada.
// Substituidos pelo dado real assim que o usuario seleciona 2+ empresas e clica Comparar.
const DEMO_DADOS: ComparativoItem[] = [
  {
    empresa_id: -1, nome: "Empresa A",
    score_saude: 82, classificacao_saude: "Saudável", cor_saude: "var(--success)",
    receita_liquida: 2400000, lucro_liquido: 420000,
    margem_liquida: 17.5, margem_bruta: 38.2, ebitda: 540000,
    liquidez_corrente: 2.14, endividamento_geral: 40.0, roe: 13.4, saldo_caixa: 380000,
  },
  {
    empresa_id: -2, nome: "Empresa B",
    score_saude: 64, classificacao_saude: "Atenção", cor_saude: "var(--warning)",
    receita_liquida: 1850000, lucro_liquido: 195000,
    margem_liquida: 10.5, margem_bruta: 31.8, ebitda: 290000,
    liquidez_corrente: 1.42, endividamento_geral: 58.7, roe: 8.1, saldo_caixa: 145000,
  },
  {
    empresa_id: -3, nome: "Empresa C",
    score_saude: 71, classificacao_saude: "Saudável", cor_saude: "var(--success)",
    receita_liquida: 3120000, lucro_liquido: 380000,
    margem_liquida: 12.2, margem_bruta: 34.5, ebitda: 460000,
    liquidez_corrente: 1.78, endividamento_geral: 47.3, roe: 11.0, saldo_caixa: 510000,
  },
];

function h() { return { Authorization: `Bearer ${localStorage.getItem("controllo_token") || ""}` }; }

export default function ComparativoPage() {
  const [ano, setAno] = useState(ANO_ATUAL);
  const [mes, setMes] = useState(new Date().getMonth() + 1);
  const [empresasDisponiveis, setEmpresasDisponiveis] = useState<EmpresaOption[]>([]);
  const [selecionadas, setSelecionadas] = useState<number[]>([]);
  const [dados, setDados] = useState<ComparativoItem[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  // Carregar lista de empresas
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/financeiro/empresas`, { headers: h() });
        if (!r.ok) return;
        const data: { id: number; nome: string }[] = await r.json();
        setEmpresasDisponiveis(data.map(e => ({ id: e.id, nome: e.nome })));
      } catch { /* ignore */ }
    })();
  }, []);

  const comparar = useCallback(async () => {
    if (selecionadas.length < 2) return;
    setCarregando(true); setErro(null); setDados([]);
    try {
      const ids = selecionadas.join(",");
      const r = await fetch(`${API}/api/financeiro/comparativo?empresas=${ids}&ano=${ano}&mes=${mes}`, { headers: h() });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Erro ao comparar.");
      setDados(d.comparativo || []);
    } catch (e: unknown) {
      setErro(e instanceof Error ? e.message : "Erro desconhecido.");
    } finally { setCarregando(false); }
  }, [selecionadas, ano, mes]);

  function toggleEmpresa(id: number) {
    setSelecionadas(prev =>
      prev.includes(id)
        ? prev.filter(x => x !== id)
        : prev.length >= 5 ? prev : [...prev, id]
    );
  }

  // Melhor valor por indicador (para highlight) — recebe array para reutilizar com demo.
  function melhorIdxFor(arr: ComparativoItem[], key: string, invertido?: boolean) {
    if (arr.length < 2) return -1;
    let best = -1;
    let bestVal = invertido ? Infinity : -Infinity;
    arr.forEach((d, i) => {
      const v = (d as Record<string, unknown>)[key];
      if (v == null || d.sem_dados) return;
      const num = v as number;
      if (invertido ? num < bestVal : num > bestVal) { bestVal = num; best = i; }
    });
    return best;
  }

  // Estado demo: nenhuma empresa selecionada e nenhum dado real carregado.
  const isDemo = selecionadas.length < 2 && dados.length === 0 && !carregando && !erro;
  const dadosVis = dados.length > 0 ? dados : (isDemo ? DEMO_DADOS : []);

  return (
    <div className="min-h-full" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>
      <header className="px-8 pt-8 pb-6" style={{ borderBottom: "1px solid var(--border)" }}>
        <h1 className="text-[22px] font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
          Comparativo Multi-Empresa
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
          Compare indicadores financeiros entre empresas da sua carteira
        </p>
      </header>

      <div className="px-8 py-6 space-y-6">
        {/* Seleção */}
        <div className="chart-container">
          <div className="chart-header">
            <p className="section-title">Selecionar Empresas (2 a 5)</p>
          </div>
          <div className="p-4 space-y-4">
            <div className="flex items-center gap-3 flex-wrap">
              <select value={mes} onChange={e => setMes(Number(e.target.value))}
                className="px-3 py-2 rounded-lg text-sm border" style={{ background: "var(--bg-secondary)", borderColor: "var(--border)", color: "var(--text-primary)" }}>
                {MESES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
              </select>
              <select value={ano} onChange={e => setAno(Number(e.target.value))}
                className="px-3 py-2 rounded-lg text-sm border" style={{ background: "var(--bg-secondary)", borderColor: "var(--border)", color: "var(--text-primary)" }}>
                {[ANO_ATUAL, ANO_ATUAL - 1, ANO_ATUAL - 2].map(a => <option key={a} value={a}>{a}</option>)}
              </select>
              <button
                onClick={comparar}
                disabled={selecionadas.length < 2 || carregando}
                className="px-5 py-2 rounded-lg text-sm font-bold text-white disabled:opacity-40 transition-all hover:brightness-110"
                style={{ background: "linear-gradient(135deg, #102a43, #1e3a5f)" }}
              >
                {carregando ? "Comparando..." : "Comparar"}
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {empresasDisponiveis.map(e => {
                const sel = selecionadas.includes(e.id);
                return (
                  <button
                    key={e.id}
                    onClick={() => toggleEmpresa(e.id)}
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                      sel
                        ? "bg-[#102a43] text-white border-[#102a43]"
                        : "border-slate-300 dark:border-slate-600 hover:border-slate-400"
                    }`}
                    style={!sel ? { color: "var(--text-secondary)" } : {}}
                  >
                    {e.nome}
                    {sel && <span className="ml-1.5 opacity-70">x</span>}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {erro && (
          <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-sm text-rose-700 dark:text-rose-300">
            {erro}
          </div>
        )}

        {/* Banner demo */}
        {isDemo && (
          <div
            className="px-4 py-3 rounded-xl flex items-start gap-2.5"
            style={{
              background: "var(--warning-subtle)",
              border: "1px solid var(--warning-border)",
            }}
          >
            <svg className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: "var(--warning)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm" style={{ color: "var(--warning)" }}>
              <span className="font-semibold">Dados de demonstração</span> — Selecione empresas reais no seletor acima para ver dados da sua carteira.
            </p>
          </div>
        )}

        {/* Tabela comparativa (real ou demo) */}
        {dadosVis.length > 0 && (
          <div className="chart-container">
            <div className="chart-header">
              <p className="section-title">
                {isDemo ? "Demonstração" : `Resultado — ${MESES[mes - 1]}/${ano}`}
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full table-premium">
                <thead>
                  <tr>
                    <th className="text-left px-4 py-3 text-xs font-bold" style={{ minWidth: 180 }}>Indicador</th>
                    {dadosVis.map(d => (
                      <th key={d.empresa_id} className="text-center px-4 py-3 text-xs font-bold" style={{ minWidth: 150 }}>
                        <div>{d.nome}</div>
                        {d.score_saude != null && (
                          <span className="inline-block mt-1 px-2 py-0.5 rounded-full text-[10px] font-black text-white"
                            style={{ background: d.cor_saude || "#6b7280" }}>
                            {d.score_saude} — {d.classificacao_saude}
                          </span>
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {INDICADORES.map(ind => {
                    const best = melhorIdxFor(dadosVis, ind.key, ind.invertido);
                    return (
                      <tr key={ind.key}>
                        <td className="px-4 py-2.5 text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
                          {ind.label}
                        </td>
                        {dadosVis.map((d, i) => {
                          const v = (d as Record<string, unknown>)[ind.key];
                          const isBest = i === best && dadosVis.length > 1;
                          return (
                            <td key={d.empresa_id} className={`px-4 py-2.5 text-center font-mono text-xs font-semibold ${
                              isBest ? "text-emerald-600 dark:text-emerald-400" : ""
                            }`} style={!isBest ? { color: "var(--text-primary)" } : {}}>
                              {d.sem_dados ? (
                                <span style={{ color: "var(--text-muted)" }}>Sem dados</span>
                              ) : (
                                <>
                                  {ind.format(v as number | null | undefined)}
                                  {isBest && <span className="ml-1 text-[10px]">&#9733;</span>}
                                </>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!carregando && dados.length === 0 && selecionadas.length >= 2 && !erro && (
          <div className="text-center py-16" style={{ color: "var(--text-muted)" }}>
            <p className="text-sm">Clique em &ldquo;Comparar&rdquo; para ver os resultados.</p>
          </div>
        )}
      </div>
    </div>
  );
}
