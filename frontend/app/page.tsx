"use client";

import { useState, useRef, useEffect } from "react";
import { processarExtrato, downloadExcel, type ResultadoProcessamento, type Transacao } from "./actions";
import GlobeBackground from "@/components/GlobeBackground";
import { useToast } from "@/contexts/ToastContext";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";


// ------------------------------------------------------------------ //
//  LISTA DE BANCOS SUPORTADOS (agrupada por categoria)              //
// ------------------------------------------------------------------ //
type BancoItem = { value: string; label: string };
type BancoGrupo = { grupo: string; icone: string; itens: BancoItem[] };

const BANCOS_GRUPOS: BancoGrupo[] = [
  {
    grupo: "Bancos Tradicionais",
    icone: "🏦",
    itens: [
      { value: "itau",     label: "Itaú" },
      { value: "bradesco", label: "Bradesco" },
      { value: "bb",       label: "Banco do Brasil" },
      { value: "santander",label: "Santander" },
      { value: "caixa",    label: "Caixa Econômica Federal" },
      { value: "sicredi",  label: "Sicredi" },
      { value: "safra",    label: "Banco Safra" },
    ],
  },
  {
    grupo: "Bancos Digitais",
    icone: "📱",
    itens: [
      { value: "nubank",       label: "Nubank" },
      { value: "inter",        label: "Inter" },
      { value: "c6bank",       label: "C6 Bank" },
      { value: "pagbank",      label: "PagBank" },
      { value: "mercado_pago", label: "Mercado Pago" },
      { value: "cora",         label: "Cora" },
      { value: "bs2",          label: "BS2 Banco" },
    ],
  },
  {
    grupo: "Conta Empresarial (PJ)",
    icone: "🏢",
    itens: [
      { value: "itau_empresas",       label: "Itaú Empresas" },
      { value: "bradesco_empresas",   label: "Bradesco Net Empresas" },
      { value: "santander_empresas",  label: "Santander Empresas" },
    ],
  },
  {
    grupo: "Investimentos & Outros",
    icone: "📊",
    itens: [
      { value: "xp_extrato", label: "XP — Extrato de Conta" },
      { value: "xp_posicao", label: "XP — Posição Consolidada" },
      { value: "stone",      label: "Stone" },
      { value: "sumup",      label: "SumUp" },
    ],
  },
];

// Lista plana derivada dos grupos (para busca e lookup)
const BANCOS_LIST: BancoItem[] = BANCOS_GRUPOS.flatMap(g => g.itens);

// ------------------------------------------------------------------ //
//  COMPONENTE PRINCIPAL                                              //
// ------------------------------------------------------------------ //
// Etapas de progresso do processamento
const ETAPAS_PROGRESSO = [
  { label: "Lendo PDF", icone: "📄" },
  { label: "Identificando banco", icone: "🏦" },
  { label: "Extraindo transações", icone: "🔍" },
  { label: "Validando dados", icone: "✓" },
  { label: "Gerando Excel", icone: "📊" },
];

export default function Home() {
  const toast = useToast();
  const [estado, setEstado] = useState<"idle" | "carregando" | "sucesso" | "erro">("idle");
  const [resultado, setResultado] = useState<ResultadoProcessamento | null>(null);
  const [arquivoNome, setArquivoNome] = useState<string>("");
  const [arquivoTamanho, setArquivoTamanho] = useState<number>(0);
  const [arquivoSelecionado, setArquivoSelecionado] = useState<File | null>(null);
  const [bancoSelecionado, setBancoSelecionado] = useState<string>("");
  const [senhaPdf, setSenhaPdf] = useState<string>("");
  const [arquivoPendente, setArquivoPendente] = useState<File | null>(null);
  const [requerSenha, setRequerSenha] = useState(false);
  const [baixandoExcel, setBaixandoExcel] = useState(false);
  const [modoClaro, setModoClaro] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [bancoSearch, setBancoSearch] = useState("");
  const [bancoDropdownOpen, setBancoDropdownOpen] = useState(false);
  const [etapaProgresso, setEtapaProgresso] = useState(0);
  const [ultimoProcessado, setUltimoProcessado] = useState<{ banco: string; transacoes: number; data: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const bancoDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const check = () => setModoClaro(document.documentElement.classList.contains("light"));
    check();
    const obs = new MutationObserver(check);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);

  // Close bank dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (bancoDropdownRef.current && !bancoDropdownRef.current.contains(e.target as Node)) {
        setBancoDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  async function _enviarArquivo(arquivo: File, senha: string) {
    setArquivoNome(arquivo.name);
    setArquivoTamanho(arquivo.size);
    setEstado("carregando");
    setResultado(null);
    setEtapaProgresso(0);

    // Progresso simulado (avança etapas enquanto aguarda resposta)
    const progressTimer = setInterval(() => {
      setEtapaProgresso(prev => (prev < ETAPAS_PROGRESSO.length - 1 ? prev + 1 : prev));
    }, 1200);

    const formData = new FormData();
    formData.append("arquivo", arquivo);
    if (bancoSelecionado) formData.append("banco", bancoSelecionado);
    if (senha) formData.append("senha_pdf", senha);

    const res = await processarExtrato(formData);
    clearInterval(progressTimer);
    setEtapaProgresso(ETAPAS_PROGRESSO.length - 1);

    if (res.sucesso) {
      setRequerSenha(false);
      setArquivoPendente(null);
      setSenhaPdf("");
      setResultado(res);
      setEstado("sucesso");
      setArquivoSelecionado(null);
      setUltimoProcessado({
        banco: res.banco_detectado,
        transacoes: res.total_transacoes,
        data: new Date().toLocaleDateString("pt-BR"),
      });
      toast.success("Extrato processado", `${res.total_transacoes} transações extraídas de ${res.banco_detectado}`);
    } else if ((res as { requer_senha?: boolean }).requer_senha) {
      setRequerSenha(true);
      setArquivoPendente(arquivo);
      setEstado("idle");
      toast.warning("PDF protegido", "Insira a senha para continuar.");
    } else {
      setResultado(res);
      setEstado("erro");
      toast.error("Falha no processamento", res.erro || "Erro desconhecido");
    }
  }

  function _selecionarArquivo(arquivo: File) {
    if (!arquivo.name.toLowerCase().endsWith(".pdf")) {
      toast.warning("Formato inválido", "Por favor, selecione um arquivo PDF.");
      return;
    }
    setArquivoSelecionado(arquivo);
    setArquivoNome(arquivo.name);
    setArquivoTamanho(arquivo.size);
    setRequerSenha(false);
    setArquivoPendente(null);
  }

  async function handleProcessar() {
    if (!arquivoSelecionado) return;
    await _enviarArquivo(arquivoSelecionado, senhaPdf);
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const arquivo = e.target.files?.[0];
    if (!arquivo) return;
    _selecionarArquivo(arquivo);
  }

  async function handleEnviarComSenha() {
    if (!arquivoPendente) return;
    await _enviarArquivo(arquivoPendente, senhaPdf);
  }

  async function handleDownload() {
    if (!resultado?.excel_id) return;
    setBaixandoExcel(true);
    try {
      await downloadExcel(resultado.excel_id, `extrato_${resultado.banco_detectado}.xlsx`);
    } catch {
      toast.error("Falha no download", "Erro ao baixar o arquivo. Tente novamente.");
    } finally {
      setBaixandoExcel(false);
    }
  }

  function handleNovo() {
    setEstado("idle");
    setResultado(null);
    setArquivoNome("");
    setArquivoTamanho(0);
    setArquivoSelecionado(null);
    setBancoSelecionado("");
    setSenhaPdf("");
    setRequerSenha(false);
    setArquivoPendente(null);
    setBancoSearch("");
    setBancoDropdownOpen(false);
    setIsDragging(false);
    setEtapaProgresso(0);
    if (fileRef.current) fileRef.current.value = "";
  }

  const bancoLabel = BANCOS_LIST.find(b => b.value === bancoSelecionado)?.label ?? "";
  const query = bancoSearch.toLowerCase();
  const isFiltering = query.length > 0;
  const filteredGrupos = isFiltering
    ? BANCOS_GRUPOS.map(g => ({ ...g, itens: g.itens.filter(b => b.label.toLowerCase().includes(query) || b.value.includes(query)) })).filter(g => g.itens.length > 0)
    : BANCOS_GRUPOS;

  return (
    <div className="min-h-full relative overflow-hidden" style={{ background: "var(--bg-primary)" }}>

      {/* ── Globo decorativo no fundo ── */}
      <div className="absolute inset-0 pointer-events-none opacity-30" style={{ zIndex: 0 }}>
        <GlobeBackground light={modoClaro} />
      </div>
      <div className="absolute top-[10%] left-[20%] w-96 h-96 rounded-full blur-[130px] pointer-events-none opacity-20" aria-hidden
        style={{ background: modoClaro ? "rgba(30,58,95,0.25)" : "rgba(59,110,165,0.20)", zIndex: 0 }} />

      {/* ── Header ── */}
      <header className="relative z-10 px-6 md:px-8 pt-7 pb-5 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
               style={{ background: "rgba(30,58,95,0.12)", border: "1px solid rgba(30,58,95,0.2)" }}>
            <svg className="w-5 h-5 text-[#3b6ea5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
              Leitor de <span style={{ color: "#3b6ea5" }}>Extrato</span>
            </h1>
            <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
              Faça upload do PDF do extrato bancário — processamento local e seguro
            </p>
          </div>
        </div>
      </header>

      {/* ── Conteúdo ── */}
      <div className="relative z-10 px-6 md:px-8 py-8 max-w-4xl mx-auto">

        {/* ── IDLE / CARREGANDO ── */}
        {(estado === "idle" || estado === "carregando") && (
          <div className="max-w-lg mx-auto space-y-5">

            {/* Card principal */}
            <div className="rounded-2xl p-6 space-y-5"
                 style={{ background: "var(--bg-card)", border: "1px solid var(--border)", boxShadow: "0 4px 24px rgba(0,0,0,0.06)" }}>

              {/* Banco */}
              <div>
                <label className="block text-sm font-semibold mb-2" style={{ color: "var(--text-primary)" }}>
                  Banco
                </label>
                <div ref={bancoDropdownRef} className="relative">
                  <div className="relative">
                    <input
                      type="text"
                      value={bancoDropdownOpen ? bancoSearch : bancoLabel}
                      onChange={e => { setBancoSearch(e.target.value); setBancoDropdownOpen(true); }}
                      onFocus={() => { setBancoSearch(""); setBancoDropdownOpen(true); }}
                      placeholder="Detectar automaticamente"
                      className="w-full rounded-xl px-3.5 py-2.5 text-sm outline-none transition-all"
                      style={{
                        background: "var(--bg-secondary)",
                        border: `1px solid ${bancoDropdownOpen ? "#3b6ea5" : "var(--border)"}`,
                        boxShadow: bancoDropdownOpen ? "0 0 0 3px rgba(59,110,165,0.15)" : "none",
                        color: "var(--text-primary)",
                      }}
                    />
                    {bancoSelecionado && !bancoDropdownOpen && (
                      <button
                        onClick={() => { setBancoSelecionado(""); setBancoSearch(""); }}
                        className="absolute right-3 top-1/2 -translate-y-1/2 transition-colors"
                        style={{ color: "var(--text-muted)" }}
                        title="Limpar seleção"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                    {!bancoDropdownOpen && (
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: "var(--text-muted)" }}>
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                        </svg>
                      </span>
                    )}
                  </div>

                  {bancoDropdownOpen && (
                    <div className="absolute top-full left-0 right-0 mt-1.5 rounded-xl shadow-2xl max-h-72 overflow-y-auto z-50"
                         style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                      {/* Detectar automaticamente */}
                      <div
                        className="flex items-center gap-2.5 px-3.5 py-2.5 text-sm cursor-pointer transition-colors rounded-t-xl"
                        style={{ color: "var(--text-muted)" }}
                        onMouseDown={() => { setBancoSelecionado(""); setBancoSearch(""); setBancoDropdownOpen(false); }}
                        onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "var(--bg-secondary)"}
                        onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = ""}
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                        <span>Detectar automaticamente</span>
                      </div>
                      <div className="h-px mx-3" style={{ background: "var(--border)" }} />

                      {filteredGrupos.length === 0 && (
                        <p className="text-sm text-center py-5" style={{ color: "var(--text-muted)" }}>Nenhum banco encontrado</p>
                      )}

                      {filteredGrupos.map((grupo, gi) => (
                        <div key={grupo.grupo}>
                          <div className="flex items-center gap-1.5 px-3.5 pt-2.5 pb-1">
                            <span className="text-xs">{grupo.icone}</span>
                            <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                              {grupo.grupo}
                            </span>
                          </div>
                          {grupo.itens.map(b => (
                            <div
                              key={b.value}
                              className="flex items-center justify-between px-3.5 py-2 mx-1 rounded-lg text-sm cursor-pointer transition-all"
                              style={{
                                background: bancoSelecionado === b.value ? "rgba(59,110,165,0.15)" : undefined,
                                color: bancoSelecionado === b.value ? "#3b6ea5" : "var(--text-primary)",
                              }}
                              onMouseDown={() => { setBancoSelecionado(b.value); setBancoSearch(""); setBancoDropdownOpen(false); }}
                              onMouseEnter={e => { if (bancoSelecionado !== b.value) (e.currentTarget as HTMLElement).style.background = "var(--bg-secondary)"; }}
                              onMouseLeave={e => { if (bancoSelecionado !== b.value) (e.currentTarget as HTMLElement).style.background = ""; }}
                            >
                              <span>{b.label}</span>
                              {bancoSelecionado === b.value && (
                                <svg className="w-3.5 h-3.5 flex-shrink-0 text-[#3b6ea5]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                            </div>
                          ))}
                          {gi < filteredGrupos.length - 1 && (
                            <div className="h-px mx-3 mt-1.5" style={{ background: "var(--border)" }} />
                          )}
                        </div>
                      ))}
                      <div className="h-1.5" />
                    </div>
                  )}
                </div>
                <p className="text-xs mt-1.5" style={{ color: "var(--text-muted)" }}>
                  Opcional — detectado automaticamente pelo conteúdo do PDF
                </p>
              </div>

              {/* Senha do PDF */}
              <div>
                {requerSenha && (
                  <div className="flex items-start gap-2.5 mb-3 px-3.5 py-2.5 rounded-xl"
                       style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.3)" }}>
                    <svg className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M12 15v2m0 0v2m0-2h2m-2 0H10m2-6V7a4 4 0 00-8 0v4H3a1 1 0 00-1 1v6a1 1 0 001 1h14a1 1 0 001-1v-6a1 1 0 00-1-1h-1V7a4 4 0 00-8 0" />
                    </svg>
                    <p className="text-xs text-amber-600 dark:text-amber-400">
                      Este PDF está protegido. Insira a senha para continuar.
                    </p>
                  </div>
                )}
                <label className="block text-sm font-semibold mb-2" style={{ color: "var(--text-primary)" }}>
                  {requerSenha ? "Senha do PDF (obrigatória)" : "Senha do PDF"}
                </label>
                <input
                  type="password"
                  value={senhaPdf}
                  onChange={(e) => setSenhaPdf(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && requerSenha) handleEnviarComSenha(); }}
                  placeholder={requerSenha ? "Digite a senha do PDF..." : "Deixe em branco se não tiver senha"}
                  className="w-full rounded-xl px-3.5 py-2.5 text-sm outline-none transition-all"
                  style={{
                    background: "var(--bg-secondary)",
                    border: `1px solid ${requerSenha ? "rgba(245,158,11,0.5)" : "var(--border)"}`,
                    color: "var(--text-primary)",
                  }}
                  onFocus={e => {
                    e.target.style.borderColor = requerSenha ? "#f59e0b" : "#3b6ea5";
                    e.target.style.boxShadow = `0 0 0 3px ${requerSenha ? "rgba(245,158,11,0.12)" : "rgba(59,110,165,0.15)"}`;
                  }}
                  onBlur={e => {
                    e.target.style.borderColor = requerSenha ? "rgba(245,158,11,0.5)" : "var(--border)";
                    e.target.style.boxShadow = "";
                  }}
                />
                {!requerSenha && (
                  <p className="text-xs mt-1.5" style={{ color: "var(--text-muted)" }}>
                    Deixe em branco se o PDF não tiver senha
                  </p>
                )}
              </div>

              {/* Upload / Loading / Botão senha */}
              {estado === "carregando" ? (
                <div className="rounded-xl p-6 space-y-4"
                     style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                  <p className="text-sm font-medium text-center" style={{ color: "var(--text-muted)" }}>
                    Processando{" "}
                    <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{arquivoNome}</span>
                  </p>
                  {/* Barra de progresso */}
                  <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: "var(--border)" }}>
                    <div className="h-full rounded-full transition-all duration-700 ease-out"
                         style={{ width: `${((etapaProgresso + 1) / ETAPAS_PROGRESSO.length) * 100}%`, background: "#3b6ea5" }} />
                  </div>
                  {/* Etapas */}
                  <div className="flex items-center justify-between gap-1">
                    {ETAPAS_PROGRESSO.map((etapa, i) => (
                      <div key={etapa.label} className="flex flex-col items-center gap-1 flex-1">
                        <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs transition-all duration-300 ${
                          i <= etapaProgresso ? "scale-100" : "scale-90 opacity-40"
                        }`} style={{
                          background: i <= etapaProgresso ? "rgba(59,110,165,0.15)" : "var(--bg-card)",
                          border: `1px solid ${i <= etapaProgresso ? "rgba(59,110,165,0.4)" : "var(--border)"}`,
                        }}>
                          {i < etapaProgresso ? (
                            <svg className="w-3.5 h-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          ) : i === etapaProgresso ? (
                            <div className="w-3 h-3 border-2 border-t-transparent rounded-full animate-spin"
                                 style={{ borderColor: "rgba(59,110,165,0.3)", borderTopColor: "#3b6ea5" }} />
                          ) : (
                            <span className="text-[10px]">{etapa.icone}</span>
                          )}
                        </div>
                        <span className={`text-[9px] text-center leading-tight transition-colors ${
                          i <= etapaProgresso ? "font-semibold" : ""
                        }`} style={{ color: i <= etapaProgresso ? "var(--text-primary)" : "var(--text-muted)" }}>
                          {etapa.label}
                        </span>
                      </div>
                    ))}
                  </div>
                  <p className="text-center text-xs font-mono" style={{ color: "#3b6ea5" }}>
                    {Math.round(((etapaProgresso + 1) / ETAPAS_PROGRESSO.length) * 100)}%
                  </p>
                </div>
              ) : requerSenha ? (
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleEnviarComSenha}
                    disabled={!senhaPdf}
                    data-notheme
                    className="inline-flex items-center gap-2 text-white font-semibold px-5 py-2.5 rounded-xl transition-all shadow-sm disabled:opacity-40 bg-[#1e3a5f] hover:bg-[#162f52]"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z" />
                    </svg>
                    Processar com senha
                  </button>
                  <button
                    onClick={() => { setRequerSenha(false); setArquivoPendente(null); setSenhaPdf(""); if (fileRef.current) fileRef.current.value = ""; }}
                    className="px-4 py-2.5 rounded-xl text-sm transition-colors"
                    style={{ color: "var(--text-muted)", border: "1px solid var(--border)" }}
                    onMouseEnter={e => (e.currentTarget as HTMLButtonElement).style.borderColor = "#3b6ea5"}
                    onMouseLeave={e => (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border)"}
                  >
                    Cancelar
                  </button>
                </div>
              ) : arquivoSelecionado ? (
                /* ── Arquivo selecionado — aguardando processamento ── */
                <div className="rounded-xl p-5 space-y-4"
                     style={{ background: "var(--bg-secondary)", border: "1px solid rgba(59,110,165,0.3)" }}>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                         style={{ background: "rgba(59,110,165,0.12)", border: "1px solid rgba(59,110,165,0.25)" }}>
                      <svg className="w-5 h-5 text-[#3b6ea5]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>{arquivoNome}</p>
                      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                        {(arquivoTamanho / 1024).toFixed(0)} KB · PDF
                      </p>
                    </div>
                    <button onClick={() => { setArquivoSelecionado(null); setArquivoNome(""); setArquivoTamanho(0); if (fileRef.current) fileRef.current.value = ""; }}
                            className="w-7 h-7 rounded-lg flex items-center justify-center transition-colors"
                            style={{ color: "var(--text-muted)", border: "1px solid var(--border)" }}>
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  <button
                    onClick={handleProcessar}
                    data-notheme
                    className="w-full inline-flex items-center justify-center gap-2 text-white font-semibold px-5 py-3 rounded-xl transition-all shadow-sm bg-[#1e3a5f] hover:bg-[#162f52]"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 3l14 9-14 9V3z" />
                    </svg>
                    Processar Extrato
                  </button>
                </div>
              ) : (
                /* ── Drag and drop ── */
                <div
                  onDrop={(e) => { e.preventDefault(); setIsDragging(false); const f = e.dataTransfer.files[0]; if (f) _selecionarArquivo(f); }}
                  onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onClick={() => fileRef.current?.click()}
                  className="relative rounded-xl text-center cursor-pointer select-none transition-all"
                  style={{
                    border: isDragging ? "2px solid #3b6ea5" : "2px dashed var(--border)",
                    background: isDragging ? "rgba(59,110,165,0.08)" : "var(--bg-secondary)",
                    padding: "40px 32px",
                    transform: isDragging ? "scale(1.01)" : "scale(1)",
                    boxShadow: isDragging ? "0 0 0 4px rgba(59,110,165,0.10)" : "none",
                  }}
                >
                  <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={handleUpload} />
                  <div className="flex flex-col items-center gap-3">
                    <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-all ${isDragging ? "scale-110" : ""}`}
                         style={{ background: isDragging ? "rgba(59,110,165,0.15)" : "var(--bg-card)", border: "1px solid var(--border)" }}>
                      <svg
                        className="w-8 h-8 transition-colors"
                        style={{ color: isDragging ? "#3b6ea5" : "var(--text-muted)" }}
                        fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                      </svg>
                    </div>
                    <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                      {isDragging ? "Solte o arquivo aqui" : "Arraste o extrato bancário aqui"}
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>ou clique para selecionar o arquivo</p>
                    <span className="text-[10px] font-bold px-2.5 py-1 rounded-full mt-1 font-mono"
                          style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
                      PDF · max 50 MB
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Card de último processamento */}
            {ultimoProcessado && (
              <div className="rounded-xl px-4 py-3 flex items-center gap-3"
                   style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.2)" }}>
                <div className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  Último extrato:{" "}
                  <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{ultimoProcessado.banco}</span>
                  {" "}— {ultimoProcessado.transacoes} transações
                  {" "}— {ultimoProcessado.data}
                </p>
              </div>
            )}

            {/* Grid de bancos suportados */}
            <div className="rounded-xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <p className="text-[10px] font-bold uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>
                Bancos suportados
              </p>
              <div className="grid grid-cols-4 sm:grid-cols-5 gap-2">
                {BANCOS_LIST.slice(0, 20).map(b => (
                  <div key={b.value} className="flex items-center justify-center px-2 py-1.5 rounded-lg text-[10px] font-medium text-center leading-tight"
                       style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
                    {b.label}
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-center gap-3 mt-3 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
                {[
                  { icone: "🔒", texto: "Processamento local" },
                  { icone: "📊", texto: "Exporta XLSX" },
                ].map(item => (
                  <span key={item.texto} className="flex items-center gap-1.5 text-[10px]" style={{ color: "var(--text-muted)" }}>
                    <span>{item.icone}</span>{item.texto}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── ERRO ── */}
        {estado === "erro" && (
          <div className="max-w-lg mx-auto">
            <div className="rounded-2xl p-8 flex flex-col items-center gap-5 text-center"
                 style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
                   style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)" }}>
                <svg className="w-8 h-8 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <div>
                <h2 className="text-lg font-bold mb-1.5" style={{ color: "var(--text-primary)" }}>
                  Erro no processamento
                </h2>
                <p className="text-sm max-w-sm" style={{ color: "var(--text-muted)" }}>{resultado?.erro}</p>
              </div>
              <button
                onClick={handleNovo}
                data-notheme
                className="px-5 py-2.5 bg-[#1e3a5f] hover:bg-[#162f52] text-white rounded-xl font-semibold text-sm transition-all"
              >
                Tentar novamente
              </button>
            </div>
          </div>
        )}

        {/* ── SUCESSO ── */}
        {estado === "sucesso" && resultado && (
          <div className="space-y-6">

            {/* Cabeçalho resultado */}
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <div className="flex items-center gap-2.5 mb-1">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                  <h2 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>
                    Extrato Processado
                  </h2>
                </div>
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                  <span className="font-medium" style={{ color: "var(--text-primary)" }}>{resultado.nome_arquivo}</span>
                  {" "}· Banco:{" "}
                  <span className="font-semibold text-[#3b6ea5]">{resultado.banco_detectado}</span>
                  {" "}· <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{resultado.total_transacoes}</span> transações
                </p>
              </div>
              <div />
            </div>

            {/* Avisos */}
            {resultado.avisos && resultado.avisos.length > 0 && (
              <div className="rounded-xl px-4 py-3"
                   style={{ background: "rgba(245,158,11,0.07)", border: "1px solid rgba(245,158,11,0.3)" }}>
                <p className="text-[11px] font-bold uppercase tracking-wider mb-1.5 text-amber-500">
                  Avisos do processamento
                </p>
                <ul className="space-y-0.5">
                  {resultado.avisos.map((a, i) => (
                    <li key={i} className="text-sm text-amber-600 dark:text-amber-400">• {a}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Cards de resumo */}
            {(() => {
              const isPosicaoOnly = resultado.resumo.posicao > 0 && resultado.resumo.entradas === 0 && resultado.resumo.saidas === 0;
              if (isPosicaoOnly) {
                return (
                  <div className="grid gap-4 grid-cols-1 md:grid-cols-3">
                    {resultado.resumo.aplicado > 0 && (
                      <ResumoCard titulo="Total Aplicado" valor={resultado.resumo.aplicado} cor="green" />
                    )}
                    <ResumoCard titulo="Posição Atual" valor={resultado.resumo.posicao} cor="indigo" />
                    {resultado.resumo.aplicado > 0 && (
                      <ResumoCard
                        titulo="Rentabilidade"
                        valor={resultado.resumo.posicao - resultado.resumo.aplicado}
                        cor={resultado.resumo.posicao >= resultado.resumo.aplicado ? "green" : "red"}
                      />
                    )}
                  </div>
                );
              }

              const temSaldoInicial = resultado.resumo.saldo_inicial != null;
              const saldoFinal = resultado.resumo.saldo_final != null
                ? resultado.resumo.saldo_final
                : temSaldoInicial
                  ? (resultado.resumo.saldo_inicial! + resultado.resumo.saldo)
                  : resultado.resumo.saldo;
              const temPosicao = resultado.resumo.posicao > 0;

              const numCols = (temSaldoInicial ? 1 : 0) + 2 + (temPosicao ? 1 : 0) + 1;

              return (
                <div className={`grid gap-4 grid-cols-2 md:grid-cols-${numCols}`}>
                  {temSaldoInicial && (
                    <ResumoCard titulo="Saldo Inicial" valor={resultado.resumo.saldo_inicial!} cor="indigo" />
                  )}
                  <ResumoCard titulo="Total de Entradas" valor={resultado.resumo.entradas} cor="green" />
                  <ResumoCard titulo="Total de Saídas" valor={resultado.resumo.saidas} cor="red" />
                  {temPosicao && (
                    <ResumoCard titulo="Posição em Investimentos" valor={resultado.resumo.posicao} cor="indigo" />
                  )}
                  <ResumoCard
                    titulo={temSaldoInicial ? "Saldo Final" : "Saldo do Período"}
                    valor={saldoFinal}
                    cor={saldoFinal >= 0 ? "green" : "red"}
                  />
                </div>
              );
            })()}

            {/* Preview rápido — 5 primeiras transações */}
            <div className="rounded-xl overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid var(--border)" }}>
                <h3 className="text-sm font-semibold flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
                  <svg className="w-4 h-4 text-[#3b6ea5]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  Preview
                </h3>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400">
                    {resultado.transacoes.filter(t => t.tipo === "entrada").length} entradas
                  </span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400">
                    {resultado.transacoes.filter(t => t.tipo === "saida").length} saídas
                  </span>
                </div>
              </div>
              <table className="w-full text-xs">
                <tbody>
                  {resultado.transacoes.slice(0, 5).map((t, i) => (
                    <tr key={i} style={{ borderTop: i > 0 ? "1px solid var(--border)" : undefined }}>
                      <td className="px-4 py-2 font-mono whitespace-nowrap" style={{ color: "var(--text-muted)" }}>{t.data}</td>
                      <td className="px-4 py-2 truncate max-w-[200px]" style={{ color: "var(--text-primary)" }}>{t.descricao}</td>
                      <td className={`px-4 py-2 text-right font-mono font-medium whitespace-nowrap ${
                        t.tipo === "entrada" ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
                      }`}>
                        {t.tipo === "entrada" ? "+" : "-"}
                        {t.valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {resultado.transacoes.length > 5 && (
                <div className="px-4 py-2 text-center text-[10px] font-medium" style={{ color: "var(--text-muted)", borderTop: "1px solid var(--border)" }}>
                  +{resultado.transacoes.length - 5} transações · ver tabela completa abaixo
                </div>
              )}
            </div>

            {/* Ações rápidas */}
            <div className="flex items-center gap-3">
              {resultado.excel_id && (
                <button
                  onClick={handleDownload}
                  disabled={baixandoExcel}
                  data-notheme
                  className="flex-1 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white font-semibold px-4 py-3 rounded-xl transition-all shadow-sm text-sm"
                >
                  {baixandoExcel ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                  )}
                  {baixandoExcel ? "Baixando…" : "Baixar Excel"}
                </button>
              )}
              <button
                onClick={handleNovo}
                className="flex items-center justify-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold transition-colors"
                style={{ color: "var(--text-primary)", border: "1px solid var(--border)" }}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                </svg>
                Novo
              </button>
            </div>

            {/* Gráfico */}
            <GraficoFluxoCaixa transacoes={resultado.transacoes} />

            {/* Tabela header */}
            <div className="flex items-center justify-between pt-2">
              <h3 className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>
                Detalhamento ({resultado.total_transacoes})
              </h3>
            </div>

            {/* Tabela de transações */}
            <div className="rounded-xl overflow-hidden max-h-96 overflow-y-auto"
                 style={{ border: "1px solid var(--border)" }}>
              <table className="w-full text-sm">
                <thead className="sticky top-0">
                  <tr style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border)" }}>
                    <th className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wide"
                        style={{ color: "var(--text-muted)" }}>Data</th>
                    <th className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wide"
                        style={{ color: "var(--text-muted)" }}>Descrição</th>
                    <th className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wide hidden md:table-cell"
                        style={{ color: "var(--text-muted)" }}>Categoria</th>
                    <th className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wide"
                        style={{ color: "var(--text-muted)" }}>Tipo</th>
                    <th className="text-right px-4 py-3 text-[11px] font-bold uppercase tracking-wide"
                        style={{ color: "var(--text-muted)" }}>Valor</th>
                  </tr>
                </thead>
                <tbody style={{ background: "var(--bg-card)" }}>
                  {resultado.transacoes.map((t, i) => (
                    <tr
                      key={i}
                      className="transition-colors"
                      style={{ borderTop: "1px solid var(--border)" }}
                      onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "var(--bg-secondary)"}
                      onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = ""}
                    >
                      <td className="px-4 py-2.5 whitespace-nowrap font-mono text-xs"
                          style={{ color: "var(--text-muted)" }}>
                        {t.data}
                      </td>
                      <td className="px-4 py-2.5 max-w-xs truncate text-xs font-medium"
                          style={{ color: "var(--text-primary)" }}>
                        {t.descricao}
                      </td>
                      <td className="px-4 py-2.5 text-xs hidden md:table-cell"
                          style={{ color: "var(--text-muted)" }}>
                        {t.categoria || "—"}
                      </td>
                      <td className="px-4 py-2.5">
                        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                          t.tipo === "entrada"
                            ? "bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400"
                            : t.tipo === "posicao"
                            ? "bg-blue-100 dark:bg-blue-950/40 text-blue-700 dark:text-blue-400"
                            : "bg-rose-100 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400"
                        }`}>
                          {t.tipo === "entrada" ? "Entrada" : t.tipo === "posicao" ? "Posição" : "Saída"}
                        </span>
                      </td>
                      <td className={`px-4 py-2.5 text-right font-mono font-medium text-xs ${
                        t.tipo === "entrada"
                          ? "text-emerald-600 dark:text-emerald-400"
                          : t.tipo === "posicao"
                          ? "text-blue-600 dark:text-blue-400"
                          : "text-rose-600 dark:text-rose-400"
                      }`}>
                        {t.tipo === "entrada" ? "+" : t.tipo === "posicao" ? "" : "-"}
                        {t.valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ //
//  Card de resumo financeiro                                        //
// ------------------------------------------------------------------ //
function ResumoCard({
  titulo,
  valor,
  cor,
}: {
  titulo: string;
  valor: number;
  cor: "green" | "red" | "indigo";
}) {
  const styles = {
    green:  { bg: "rgba(16,185,129,0.08)",   border: "rgba(16,185,129,0.25)",   text: "#10b981", darkText: "#34d399" },
    red:    { bg: "rgba(239,68,68,0.08)",     border: "rgba(239,68,68,0.25)",    text: "#ef4444", darkText: "#fb7185" },
    indigo: { bg: "rgba(59,110,165,0.08)",    border: "rgba(59,110,165,0.25)",   text: "#3b6ea5", darkText: "#93c5fd" },
  };
  const s = styles[cor];
  return (
    <div className="rounded-xl p-4" style={{ background: s.bg, border: `1px solid ${s.border}` }}>
      <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: "var(--text-muted)" }}>
        {titulo}
      </p>
      <p className={`text-lg font-bold font-mono ${
           cor === "green" ? "text-emerald-600 dark:text-emerald-400" :
           cor === "red"   ? "text-rose-600 dark:text-rose-400" :
                             "text-[#3b6ea5] dark:text-blue-400"
         }`}>
        {valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
      </p>
    </div>
  );
}

// ------------------------------------------------------------------ //
//  Gráfico de Fluxo de Caixa                                        //
// ------------------------------------------------------------------ //
function GraficoFluxoCaixa({ transacoes }: { transacoes: Transacao[] }) {
  const [isLight, setIsLight] = useState(false);

  useEffect(() => {
    const check = () => setIsLight(document.documentElement.classList.contains("light"));
    check();
    const obs = new MutationObserver(check);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);

  const dadosAgrupados = transacoes.reduce(
    (acc, t) => {
      const data = t.data.substring(0, 5);
      if (!acc[data]) acc[data] = { data, Entradas: 0, Saídas: 0, Posição: 0 };
      if (t.tipo === "entrada") acc[data].Entradas += t.valor;
      else if (t.tipo === "posicao") acc[data]["Posição"] += t.valor;
      else acc[data]["Saídas"] += Math.abs(t.valor);
      return acc;
    },
    {} as Record<string, { data: string; Entradas: number; Saídas: number; Posição: number }>
  );

  const dadosGrafico = Object.values(dadosAgrupados);
  const temPosicao = dadosGrafico.some((d) => d["Posição"] > 0);

  const tickColor  = isLight ? "#6B6B80" : "#94a3b8";
  const gridColor  = isLight ? "#E2E2EA" : "#1e3a5f";
  const tooltipBg  = isLight ? "#FFFFFF"  : "#1e293b";
  const tooltipBdr = isLight ? "#E2E8F0"  : "#475569";
  const tooltipClr = isLight ? "#0F172A"  : "#f1f5f9";
  const legendClr  = isLight ? "#444460"  : "#94a3b8";

  return (
    <div className="rounded-xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <h3 className="font-semibold text-sm mb-5 flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
        <svg className="w-4 h-4 text-[#3b6ea5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        Análise de Fluxo de Caixa
      </h3>
      <div className="h-72 w-full text-xs font-mono">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={dadosGrafico} margin={{ top: 0, right: 0, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
            <XAxis dataKey="data" stroke={tickColor} tick={{ fill: tickColor }} tickLine={false} axisLine={false} />
            <YAxis
              stroke={tickColor}
              tick={{ fill: tickColor }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => v >= 1000 ? `R$${(v / 1000).toFixed(0)}k` : `R$${v}`}
            />
            <Tooltip
              cursor={{ fill: isLight ? "rgba(59,110,165,0.06)" : "rgba(59,110,165,0.08)" }}
              contentStyle={{ backgroundColor: tooltipBg, borderColor: tooltipBdr, borderRadius: "10px", color: tooltipClr, fontSize: "12px", padding: "10px 14px", boxShadow: isLight ? "0 4px 12px rgba(0,0,0,0.08)" : "none" }}
              labelStyle={{ color: isLight ? "#64748b" : tooltipClr, fontWeight: 600, marginBottom: "6px", fontSize: 11 }}
              itemStyle={{ color: isLight ? "#475569" : tooltipClr, fontSize: 12 }}
              formatter={(value) =>
                typeof value === "number"
                  ? value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
                  : value
              }
            />
            <Legend wrapperStyle={{ paddingTop: "20px", color: legendClr }} />
            <Bar dataKey="Entradas" fill="#34d399" radius={[4, 4, 0, 0]} maxBarSize={36} />
            <Bar dataKey="Saídas" fill="#fb7185" radius={[4, 4, 0, 0]} maxBarSize={36} />
            {temPosicao && (
              <Bar dataKey="Posição" fill="#818cf8" radius={[4, 4, 0, 0]} maxBarSize={36} />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
