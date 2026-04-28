"use client";

import { useState, useRef, useCallback, useEffect } from "react";

function useTheme() {
  const [isLight, setIsLight] = useState(false);
  useEffect(() => {
    const check = () => setIsLight(document.documentElement.classList.contains("light"));
    check();
    const obs = new MutationObserver(check);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);
  return isLight;
}

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

const fmt = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);

// ─────────────────────────────────────────────────────────────────
//  Lista de bancos disponíveis (espelha o dict PARSERS do backend)
// ─────────────────────────────────────────────────────────────────

const BANCOS: { id: string; label: string; group: string }[] = [
  // Tradicionais
  { id: "itau",               label: "Itaú",                    group: "Tradicionais" },
  { id: "bradesco",           label: "Bradesco",                group: "Tradicionais" },
  { id: "bb",                 label: "Banco do Brasil",         group: "Tradicionais" },
  { id: "santander",          label: "Santander",               group: "Tradicionais" },
  { id: "caixa",              label: "Caixa Econômica Federal", group: "Tradicionais" },
  { id: "sicredi",            label: "Sicredi",                 group: "Tradicionais" },
  // Digitais
  { id: "nubank",             label: "Nubank",                  group: "Digitais" },
  { id: "inter",              label: "Inter",                   group: "Digitais" },
  { id: "c6bank",             label: "C6 Bank",                 group: "Digitais" },
  { id: "pagbank",            label: "PagBank",                 group: "Digitais" },
  { id: "mercado_pago",       label: "Mercado Pago",            group: "Digitais" },
  { id: "cora",               label: "Cora",                    group: "Digitais" },
  { id: "bs2",                label: "BS2 Banco",               group: "Digitais" },
  // Empresarial (PJ)
  { id: "itau_empresas",      label: "Itaú Empresas",           group: "Empresarial PJ" },
  { id: "bradesco_empresas",  label: "Bradesco Net Empresas",   group: "Empresarial PJ" },
  { id: "santander_empresas", label: "Santander Empresas",      group: "Empresarial PJ" },
  // Investimentos & outros
  { id: "btg",                label: "BTG Pactual",             group: "Outros" },
  { id: "safra",              label: "Banco Safra",             group: "Outros" },
  { id: "xp_extrato",         label: "XP — Extrato",            group: "Outros" },
  { id: "xp_posicao",         label: "XP — Posição",            group: "Outros" },
  { id: "stone",              label: "Stone",                   group: "Outros" },
  { id: "sumup",              label: "SumUp",                   group: "Outros" },
];

const BANCO_GROUPS = Array.from(new Set(BANCOS.map(b => b.group)));

const _MESES: Record<number, [string, string]> = {
  1:  ["Janeiro",   "jan"],  2:  ["Fevereiro", "fev"],  3:  ["Marco",     "mar"],
  4:  ["Abril",     "abr"],  5:  ["Maio",      "mai"],  6:  ["Junho",     "jun"],
  7:  ["Julho",     "jul"],  8:  ["Agosto",    "ago"],  9:  ["Setembro",  "set"],
  10: ["Outubro",   "out"],  11: ["Novembro",  "nov"],  12: ["Dezembro",  "dez"],
};

function periodoDeTransacoes(transacoes: { data?: string }[]): { label: string; slug: string } {
  const contagem: Record<string, number> = {};
  for (const t of transacoes) {
    const partes = (t.data ?? "").split("/");
    if (partes.length === 3) {
      const key = `${partes[1]}/${partes[2]}`;
      contagem[key] = (contagem[key] ?? 0) + 1;
    }
  }
  const top = Object.entries(contagem).sort((a, b) => b[1] - a[1])[0];
  if (!top) return { label: "", slug: "" };
  const [mes, ano] = top[0].split("/").map(Number);
  const [nomeLongo, nomeSlug] = _MESES[mes] ?? [String(mes), String(mes)];
  return { label: `${nomeLongo} ${ano}`, slug: `${nomeSlug}_${ano}` };
}

function slugBanco(bancoId: string): string {
  return bancoId.replace(/_/g, "-");
}

// ─────────────────────────────────────────────────────────────────
//  Tipos
// ─────────────────────────────────────────────────────────────────

type Status = "aguardando" | "processando" | "ok" | "vazio" | "erro";

interface VerificacaoContabil {
  status: string;        // 'OK' | 'DIVERGENT' | 'REPROCESSED_OK' | 'REPROCESSED_FAIL' | 'SKIPPED'
  bank_name: string;
  opening_balance?: string | null;
  calculated_closing_balance?: string | null;
  expected_closing_balance?: string | null;
  total_credits?: string;
  total_debits?: string;
  transaction_count?: number;
  credit_count?: number;
  debit_count?: number;
  difference?: string;
  was_reprocessed?: boolean;
  divergence_points?: Array<{
    date: string;
    expected_balance: string;
    calculated_balance: string;
    difference: string;
  }>;
}

interface Arquivo {
  id: string;
  file: File;
  bancoId: string;
  status: Status;
  bancoDetectado?: string;
  periodoLabel?: string;
  totalTransacoes?: number;
  resumo?: { entradas: number; saidas: number; saldo: number };
  excelId?: string;
  filenameSugerido?: string;
  numeroConta?: string;
  avisos?: string[];
  erroMsg?: string;
  verificacao?: VerificacaoContabil | null;
  // Campos de detecção automática
  arquivoTempId?: string;       // UUID do arquivo temporário no backend
  arquivoTempPath?: string;     // Caminho do arquivo temporário
  confianca?: "alta" | "media" | "nenhuma";
  senhaInput?: string;          // Senha digitada pelo usuário
  erroPdf?: string;             // Erro de PDF protegido
}

type Etapa = "upload" | "detectando" | "confirmar" | "processando" | "resultado";

// ─────────────────────────────────────────────────────────────────
//  Sub-componentes
// ─────────────────────────────────────────────────────────────────

function VerificacaoBadge({ verificacao }: { verificacao: VerificacaoContabil }) {
  const s = verificacao.status;
  const isOk = s === "OK" || s === "REPROCESSED_OK";
  const isDivergent = s === "DIVERGENT" || s === "REPROCESSED_FAIL";

  if (isOk) {
    return (
      <span
        className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30"
        title={s === "REPROCESSED_OK" ? "Verificado OK (reprocessado)" : "Saldos conferidos"}
      >
        <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
        {s === "REPROCESSED_OK" ? "Verificado (reprocessado)" : "Verificado"}
      </span>
    );
  }

  if (isDivergent) {
    const diff = verificacao.difference ?? "?";
    const points = verificacao.divergence_points ?? [];
    const tooltip = [
      `Diferenca: R$ ${diff}`,
      `Creditos: ${verificacao.credit_count ?? "?"} | Debitos: ${verificacao.debit_count ?? "?"}`,
      verificacao.was_reprocessed ? "Reprocessado sem sucesso" : "",
      ...points.map(p => `${p.date}: esperado ${p.expected_balance}, calculado ${p.calculated_balance} (diff ${p.difference})`),
    ].filter(Boolean).join("\n");

    return (
      <span
        className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-500/30 cursor-help"
        title={tooltip}
      >
        <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
        Divergencia R$ {diff}
      </span>
    );
  }

  return null;
}

function StatusPill({ status }: { status: Status }) {
  const map: Record<Status, { label: string; cls: string }> = {
    aguardando:  { label: "Aguardando",     cls: "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700" },
    processando: { label: "Processando…",   cls: "bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-500/30 animate-pulse" },
    ok:          { label: "Concluído",      cls: "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/30" },
    vazio:       { label: "Sem transações", cls: "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-500/30" },
    erro:        { label: "Erro",           cls: "bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-500/30" },
  };
  const { label, cls } = map[status];
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full border whitespace-nowrap ${cls}`}>
      {status === "processando" && (
        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 dark:bg-blue-400 animate-ping" />
      )}
      {status === "ok" && (
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
        </svg>
      )}
      {status === "erro" && (
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
        </svg>
      )}
      {label}
    </span>
  );
}

function StepIndicator({ step }: { step: number }) {
  const steps = [
    { n: 1, label: "Adicionar PDFs",     icon: "M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" },
    { n: 2, label: "Identificar bancos", icon: "M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" },
    { n: 3, label: "Processar e baixar", icon: "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" },
  ];

  return (
    <div className="flex items-center gap-0 mt-6">
      {steps.map(({ n, label, icon }, idx) => {
        const done    = step > n;
        const active  = step === n;
        const pending = step < n;
        return (
          <div key={n} className="flex items-center">
            {idx > 0 && (
              <div className={`h-px w-12 transition-all duration-300 ${done ? "bg-emerald-500/60" : "var(--border)"}`}
                   style={{ background: done ? undefined : "var(--border)" }} />
            )}
            <div className={`flex items-center gap-2.5 px-4 py-2 rounded-xl border transition-all duration-300 ${
              done    ? "bg-emerald-500/10 dark:bg-emerald-500/10 border-emerald-500/30 dark:border-emerald-500/20" :
              active  ? "bg-[#1e3a5f]/10 dark:bg-[#1e3a5f]/30 border-[#1e3a5f]/40 dark:border-[#3b6ea5]/50 shadow-sm" :
                        "bg-transparent border-transparent opacity-50"
            }`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 transition-all ${
                done   ? "bg-emerald-500 shadow-sm" :
                active ? "bg-[#1e3a5f] dark:bg-[#3b6ea5] shadow-md" :
                         "bg-slate-200 dark:bg-slate-700"
              }`}>
                {done ? (
                  <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className={`w-3.5 h-3.5 ${active ? "text-white" : "text-slate-400 dark:text-slate-500"}`}
                       fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d={icon} />
                  </svg>
                )}
              </div>
              <span className={`text-xs font-semibold hidden sm:block ${
                done   ? "text-emerald-700 dark:text-emerald-400" :
                active ? "text-[#1e3a5f] dark:text-slate-100" :
                         "text-slate-400 dark:text-slate-500"
              }`}>{label}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
//  Página
// ─────────────────────────────────────────────────────────────────

export default function ExtratoLotePage() {
  const isLight = useTheme();
  const [arquivos, setArquivos] = useState<Arquivo[]>([]);
  const [etapa, setEtapa] = useState<Etapa>("upload");
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const token = () => localStorage.getItem("controllo_token") ?? "";

  // ── Adicionar arquivos ───────────────────────────────────────
  function adicionarArquivos(files: FileList | null) {
    if (!files) return;
    const novos: Arquivo[] = Array.from(files)
      .filter(f => f.name.toLowerCase().endsWith(".pdf"))
      .filter(f => !arquivos.some(a => a.file.name === f.name && a.file.size === f.size))
      .map(f => ({
        id: `${f.name}-${f.size}-${Math.random()}`,
        file: f,
        bancoId: "",
        status: "aguardando" as Status,
      }));
    if (novos.length > 0) setArquivos(prev => [...prev, ...novos]);
  }

  function setBanco(id: string, bancoId: string) {
    setArquivos(prev => prev.map(a => a.id === id ? { ...a, bancoId } : a));
  }

  function setSenha(id: string, senha: string) {
    setArquivos(prev => prev.map(a => a.id === id ? { ...a, senhaInput: senha } : a));
  }

  function remover(id: string) {
    setArquivos(prev => prev.filter(a => a.id !== id));
  }

  // ── Detectar bancos — envia todos os PDFs ao backend ────────
  const detectarBancos = useCallback(async () => {
    const pendentes = arquivos.filter(a => a.status === "aguardando" && !a.arquivoTempId);
    if (pendentes.length === 0 && arquivos.some(a => a.arquivoTempId)) {
      // Já detectados, pular para confirmar
      setEtapa("confirmar");
      return;
    }
    if (pendentes.length === 0) return;

    setEtapa("detectando");

    try {
      const form = new FormData();
      for (const arq of pendentes) {
        form.append("arquivos", arq.file);
      }

      const res = await fetch(`${API}/api/detectar-bancos`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token()}` },
        body: form,
      });

      if (!res.ok) {
        setEtapa("upload");
        return;
      }

      const data = await res.json();
      const deteccoes: any[] = data.arquivos ?? [];

      // Mapeia resultados da detecção de volta para os arquivos locais
      // A ordem dos resultados corresponde à ordem em que foram enviados
      setArquivos(prev => {
        const novos = [...prev];
        let idx = 0;
        for (let i = 0; i < novos.length; i++) {
          if (novos[i].status === "aguardando" && !novos[i].arquivoTempId && idx < deteccoes.length) {
            const det = deteccoes[idx];
            idx++;
            novos[i] = {
              ...novos[i],
              arquivoTempId: det.arquivo_id,
              arquivoTempPath: det.arquivo_temp,
              bancoId: det.banco_detectado ?? "",
              bancoDetectado: det.banco_nome_exibicao ?? undefined,
              confianca: det.confianca ?? "nenhuma",
              erroPdf: det.erro ?? undefined,
            };
          }
        }
        return novos;
      });

      setEtapa("confirmar");
    } catch {
      setEtapa("upload");
    }
  }, [arquivos]);

  // ── Processar lote confirmado ───────────────────────────────
  const processarConfirmado = useCallback(async () => {
    const aptos = arquivos.filter(a => a.bancoId && a.arquivoTempId);
    if (aptos.length === 0) return;

    setEtapa("processando");
    setArquivos(prev => prev.map(a =>
      a.bancoId && a.arquivoTempId ? { ...a, status: "processando" as Status } : a
    ));

    try {
      const body = {
        arquivos: aptos.map(a => ({
          arquivo_id: a.arquivoTempId!,
          arquivo_temp: a.arquivoTempPath ?? `uploads/${a.arquivoTempId}.pdf`,
          banco: a.bancoId,
          senha: a.senhaInput || null,
        })),
      };

      const res = await fetch(`${API}/api/processar-lote-confirmado`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        setArquivos(prev => prev.map(a =>
          a.status === "processando" ? { ...a, status: "erro" as Status, erroMsg: `HTTP ${res.status}` } : a
        ));
        setEtapa("resultado");
        return;
      }

      const data = await res.json();
      const resultados: any[] = data.resultados ?? [];

      // Mapear resultados por arquivo_id
      const resultMap = new Map<string, any>();
      for (const r of resultados) resultMap.set(r.arquivo_id, r);

      setArquivos(prev => prev.map(a => {
        if (!a.arquivoTempId) return a;
        const r = resultMap.get(a.arquivoTempId);
        if (!r) return { ...a, status: "erro" as Status, erroMsg: "Sem resposta do servidor" };

        if (!r.sucesso) {
          return { ...a, status: "erro" as Status, erroMsg: r.erro ?? "Erro ao processar" };
        }
        if (r.total_transacoes === 0) {
          return { ...a, status: "vazio" as Status, avisos: r.avisos };
        }
        return {
          ...a,
          status: "ok" as Status,
          bancoDetectado: r.banco_detectado,
          periodoLabel: r.periodo_label,
          totalTransacoes: r.total_transacoes,
          resumo: r.resumo,
          excelId: r.excel_id,
          filenameSugerido: r.filename_sugerido,
          avisos: r.avisos,
          verificacao: r.verificacao_contabil ?? null,
        };
      }));

      setEtapa("resultado");
    } catch (err: any) {
      setArquivos(prev => prev.map(a =>
        a.status === "processando" ? { ...a, status: "erro" as Status, erroMsg: err.message ?? "Erro" } : a
      ));
      setEtapa("resultado");
    }
  }, [arquivos]);

  // ── Download ─────────────────────────────────────────────────
  async function baixar(item: Arquivo) {
    if (!item.excelId) return;
    const url = `${API}/api/download/${item.excelId}?filename=${encodeURIComponent(item.filenameSugerido ?? "extrato.xlsx")}`;
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token()}` } });
    if (!res.ok) return;
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = item.filenameSugerido ?? "extrato.xlsx";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function baixarTodos() {
    const prontos = arquivos.filter(a => a.status === "ok" && a.excelId);
    for (let i = 0; i < prontos.length; i++) {
      await baixar(prontos[i]);
      if (i < prontos.length - 1) await new Promise(r => setTimeout(r, 400));
    }
  }

  function voltarParaUpload() {
    setArquivos([]);
    setEtapa("upload");
  }

  // ── Métricas ─────────────────────────────────────────────────
  const qtdProntos  = arquivos.filter(a => a.status === "ok").length;
  const qtdSemBanco = arquivos.filter(a => !a.bancoId && a.status !== "ok").length;
  const qtdComBanco = arquivos.filter(a => a.bancoId).length;
  const podeProcessar = etapa === "confirmar" && qtdComBanco > 0 && qtdSemBanco === 0;

  const step = etapa === "upload" ? 1
    : etapa === "detectando" ? 1
    : etapa === "confirmar" ? 2
    : 3;

  const totais = arquivos.reduce((acc, a) => {
    if (a.status === "ok" && a.resumo) {
      acc.transacoes += a.totalTransacoes ?? 0;
      acc.entradas   += a.resumo.entradas;
      acc.saidas     += a.resumo.saidas;
    }
    return acc;
  }, { transacoes: 0, entradas: 0, saidas: 0 });

  // Agrupamento por banco para a etapa de confirmação
  const grupos = (() => {
    if (etapa !== "confirmar") return [];
    const map = new Map<string, Arquivo[]>();
    for (const a of arquivos) {
      const key = a.bancoId || "__sem_banco__";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(a);
    }
    // Ordena: bancos identificados primeiro, "sem banco" por último
    const entries = Array.from(map.entries());
    entries.sort((a, b) => {
      if (a[0] === "__sem_banco__") return 1;
      if (b[0] === "__sem_banco__") return -1;
      return a[0].localeCompare(b[0]);
    });
    return entries;
  })();

  return (
    <div className="min-h-full" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>

      {/* ── Header ── */}
      <header className="px-6 md:px-8 pt-7 pb-5 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                 style={{ background: "rgba(30,58,95,0.12)", border: "1px solid rgba(30,58,95,0.2)" }}>
              <svg className="w-5 h-5 text-[#3b6ea5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                  d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
                Leitor em Lote
              </h1>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                Processe múltiplos extratos bancários de uma vez — detecção automática de banco
              </p>
            </div>
          </div>

          {arquivos.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <StatChip label="Total" value={arquivos.length} />
              {qtdProntos > 0 && <StatChip label="Prontos" value={qtdProntos} color="emerald" />}
              {qtdComBanco > 0 && etapa === "confirmar" && <StatChip label="Identificados" value={qtdComBanco} color="blue" />}
              {qtdSemBanco > 0 && <StatChip label="Sem banco" value={qtdSemBanco} color="amber" />}
            </div>
          )}
        </div>

        <StepIndicator step={step} />
      </header>

      <div className="px-6 md:px-8 py-6 max-w-6xl mx-auto space-y-5">

        {/* ══════════════════════════════════════════════════════ */}
        {/*  ETAPA 1 — UPLOAD                                     */}
        {/* ══════════════════════════════════════════════════════ */}
        {(etapa === "upload" || etapa === "detectando") && (
          <>
            {/* Zona de upload */}
            <div
              onDragOver={e => { e.preventDefault(); setDrag(true); }}
              onDragLeave={() => setDrag(false)}
              onDrop={e => { e.preventDefault(); setDrag(false); adicionarArquivos(e.dataTransfer.files); }}
              onClick={() => etapa !== "detectando" && inputRef.current?.click()}
              className={`relative border-2 border-dashed rounded-2xl transition-all select-none overflow-hidden ${
                etapa === "detectando" ? "opacity-60 pointer-events-none" : "cursor-pointer"
              } ${
                drag
                  ? "border-[#3b6ea5] bg-[#1e3a5f]/10 dark:bg-[#1e3a5f]/20 scale-[1.005]"
                  : arquivos.length > 0
                  ? "border-slate-200 dark:border-slate-700/50 hover:border-[#3b6ea5]/50 bg-slate-50/50 dark:bg-slate-800/10 py-3"
                  : "border-slate-300 dark:border-slate-700 hover:border-[#3b6ea5]/60 bg-slate-50 dark:bg-slate-800/20 hover:bg-slate-100/70 dark:hover:bg-slate-800/30"
              }`}
            >
              <input ref={inputRef} type="file" accept=".pdf" multiple className="hidden"
                onChange={e => { adicionarArquivos(e.target.files); e.target.value = ""; }} />

              {arquivos.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
                  <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-4 transition-all ${
                    drag ? "bg-[#3b6ea5]/20 scale-110" : "bg-slate-200/80 dark:bg-slate-700/60"
                  }`}>
                    <svg className={`w-8 h-8 transition-colors ${drag ? "text-[#3b6ea5]" : "text-slate-400 dark:text-slate-500"}`}
                         fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <p className="font-semibold text-sm mb-1" style={{ color: "var(--text-primary)" }}>
                    {drag ? "Solte os arquivos aqui" : "Arraste os PDFs aqui ou clique para selecionar"}
                  </p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    Múltiplos arquivos — o banco de cada extrato é identificado automaticamente
                  </p>
                  <div className="flex items-center gap-2 mt-4">
                    <span className="text-[10px] px-2.5 py-1 rounded-full bg-slate-200/70 dark:bg-slate-700/70 text-slate-500 dark:text-slate-400 font-medium">PDF</span>
                    <span className="text-[10px] px-2.5 py-1 rounded-full bg-slate-200/70 dark:bg-slate-700/70 text-slate-500 dark:text-slate-400 font-medium">Detecção automática</span>
                    <span className="text-[10px] px-2.5 py-1 rounded-full bg-slate-200/70 dark:bg-slate-700/70 text-slate-500 dark:text-slate-400 font-medium">Exporta em XLSX</span>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center gap-3 py-3 px-6">
                  <svg className={`w-5 h-5 flex-shrink-0 transition-colors ${drag ? "text-[#3b6ea5]" : "text-slate-400 dark:text-slate-500"}`}
                       fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
                    {drag ? "Solte para adicionar" : `${arquivos.length} PDF(s) selecionado(s) — clique para adicionar mais`}
                  </p>
                </div>
              )}
            </div>

            {/* Loading de detecção */}
            {etapa === "detectando" && (
              <div className="flex items-center justify-center gap-3 py-8">
                <svg className="animate-spin w-5 h-5 text-[#3b6ea5]" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
                  Identificando bancos de {arquivos.length} extrato(s)...
                </p>
              </div>
            )}

            {/* Botão detectar */}
            {etapa === "upload" && arquivos.length > 0 && (
              <div className="flex items-center gap-3">
                <button
                  onClick={detectarBancos}
                  data-notheme
                  className="px-5 py-2.5 bg-[#1e3a5f] hover:bg-[#162f52] active:bg-[#0f2035] text-white rounded-xl font-semibold text-sm transition-all flex items-center gap-2 shadow-sm hover:shadow-md"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  Identificar bancos ({arquivos.length})
                </button>
                <button
                  onClick={voltarParaUpload}
                  className="px-4 py-2.5 text-sm font-medium transition-colors border"
                  style={{
                    background: "var(--bg-elevated)",
                    borderColor: "var(--border-default)",
                    color: "var(--text-primary)",
                    borderRadius: "var(--radius-md)",
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = "var(--bg-overlay)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "var(--bg-elevated)"; }}
                >
                  Limpar
                </button>
              </div>
            )}

            {/* Estado vazio */}
            {arquivos.length === 0 && etapa === "upload" && (
              <div className="text-center py-16 space-y-3">
                <div className="w-16 h-16 mx-auto rounded-2xl flex items-center justify-center"
                     style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                  <svg className="w-8 h-8 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor"
                       style={{ color: "var(--text-primary)" }}>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <p className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>
                  Nenhum arquivo adicionado
                </p>
                <p className="text-xs" style={{ color: "var(--text-muted)", opacity: 0.6 }}>
                  Arraste PDFs de extrato bancário para cima ou clique na área de upload
                </p>
              </div>
            )}
          </>
        )}

        {/* ══════════════════════════════════════════════════════ */}
        {/*  ETAPA 2 — CONFIRMAÇÃO (agrupado por banco)           */}
        {/* ══════════════════════════════════════════════════════ */}
        {etapa === "confirmar" && (
          <>
            <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
              <div className="px-4 py-3 flex items-center justify-between"
                   style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border)" }}>
                <p className="text-[11px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                  {arquivos.length} extrato(s) — confirme o banco de cada arquivo
                </p>
                <button
                  onClick={voltarParaUpload}
                  className="text-xs font-medium transition-colors px-2.5 py-1 border"
                  style={{
                    background: "var(--bg-elevated)",
                    borderColor: "var(--border-default)",
                    color: "var(--text-primary)",
                    borderRadius: "var(--radius-md)",
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = "var(--bg-overlay)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "var(--bg-elevated)"; }}
                >
                  Voltar
                </button>
              </div>

              {grupos.map(([bancoKey, items]) => {
                const isSemBanco = bancoKey === "__sem_banco__";
                const bancoLabel = isSemBanco
                  ? "Não identificado"
                  : BANCOS.find(b => b.id === bancoKey)?.label ?? items[0]?.bancoDetectado ?? bancoKey;

                return (
                  <div key={bancoKey}>
                    {/* Header do grupo */}
                    <div className="px-4 py-2.5 flex items-center gap-3"
                         style={{ background: isSemBanco ? "rgba(245,158,11,0.06)" : "var(--bg-secondary)", borderBottom: "1px solid var(--border)" }}>
                      <div className={`w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 ${
                        isSemBanco
                          ? "bg-amber-100 dark:bg-amber-900/30"
                          : "bg-[#1e3a5f]/10 dark:bg-[#3b6ea5]/20"
                      }`}>
                        {isSemBanco ? (
                          <svg className="w-3.5 h-3.5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        ) : (
                          <svg className="w-3.5 h-3.5 text-[#3b6ea5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                          </svg>
                        )}
                      </div>
                      <span className="text-xs font-bold" style={{ color: isSemBanco ? "rgb(217 119 6)" : "var(--text-primary)" }}>
                        {bancoLabel}
                      </span>
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full"
                            style={{ background: "var(--bg-primary)", color: "var(--text-muted)" }}>
                        {items.length} arquivo(s)
                      </span>
                    </div>

                    {/* Arquivos do grupo */}
                    {items.map(item => (
                      <div key={item.id} className="flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50/50 dark:hover:bg-slate-800/20"
                           style={{ borderBottom: "1px solid var(--border)" }}>
                        <svg className="w-4 h-4 flex-shrink-0 text-slate-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-mono font-medium truncate" style={{ color: "var(--text-primary)" }} title={item.file.name}>
                            {item.file.name}
                          </p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>{(item.file.size / 1024).toFixed(0)} KB</span>
                            {item.confianca === "alta" && (
                              <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">Detecção automática</span>
                            )}
                            {item.confianca === "media" && (
                              <span className="text-[10px] text-blue-600 dark:text-blue-400 font-medium">Detecção por nome</span>
                            )}
                            {item.erroPdf && (
                              <span className="text-[10px] text-rose-600 dark:text-rose-400 font-medium">{item.erroPdf}</span>
                            )}
                          </div>
                        </div>

                        {/* Dropdown individual para corrigir banco */}
                        <div className="relative flex-shrink-0 w-44">
                          <select
                            value={item.bancoId}
                            onChange={e => setBanco(item.id, e.target.value)}
                            className="w-full pl-2.5 pr-7 py-1.5 rounded-lg text-xs border transition-all outline-none cursor-pointer"
                            style={{
                              background: "var(--bg-secondary)",
                              borderColor: !item.bancoId ? "rgba(245,158,11,0.5)" : "var(--border)",
                              color: "var(--text-primary)",
                              colorScheme: isLight ? "light" : "dark",
                              appearance: item.bancoId ? "none" : undefined,
                              WebkitAppearance: item.bancoId ? "none" : undefined,
                            } as React.CSSProperties}
                          >
                            <option value="">— Selecione o banco —</option>
                            {BANCO_GROUPS.map(group => (
                              <optgroup key={group} label={group}>
                                {BANCOS.filter(b => b.group === group).map(b => (
                                  <option key={b.id} value={b.id}>{b.label}</option>
                                ))}
                              </optgroup>
                            ))}
                          </select>
                          {/* Seta ▼: visível apenas quando nenhum banco selecionado */}
                          {!item.bancoId && (
                            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                              <svg className="w-3 h-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                            </div>
                          )}
                          {/* X limpar: visível apenas quando banco selecionado */}
                          {item.bancoId && (
                            <button
                              onClick={() => setBanco(item.id, "")}
                              title="Limpar seleção"
                              className="absolute inset-y-0 right-0 flex items-center pr-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                            >
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          )}
                        </div>

                        {/* Campo de senha (se PDF protegido) */}
                        {item.erroPdf?.toLowerCase().includes("senha") && (
                          <input
                            type="password"
                            placeholder="Senha do PDF"
                            value={item.senhaInput ?? ""}
                            onChange={e => setSenha(item.id, e.target.value)}
                            className="w-28 px-2.5 py-1.5 rounded-lg text-xs border outline-none flex-shrink-0"
                            style={{
                              background: "var(--bg-secondary)",
                              borderColor: "var(--border)",
                              color: "var(--text-primary)",
                            }}
                          />
                        )}

                        <button
                          onClick={() => remover(item.id)}
                          title="Remover"
                          className="p-1.5 rounded-lg transition-colors text-slate-400 dark:text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 flex-shrink-0"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>

            {/* Aviso sem banco */}
            {qtdSemBanco > 0 && (
              <div className="flex items-start gap-3 px-4 py-3.5 rounded-xl border"
                   style={{ background: "rgba(245,158,11,0.06)", borderColor: "rgba(245,158,11,0.3)" }}>
                <svg className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                </svg>
                <p className="text-xs text-amber-700 dark:text-amber-400">
                  <strong>{qtdSemBanco} arquivo(s)</strong> sem banco identificado — selecione o banco antes de processar.
                </p>
              </div>
            )}

            {/* Barra de ações */}
            <div className="flex flex-wrap items-center gap-3 pt-1">
              <button
                onClick={processarConfirmado}
                disabled={!podeProcessar}
                data-notheme
                className="px-5 py-2.5 bg-[#1e3a5f] hover:bg-[#162f52] active:bg-[#0f2035] disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl font-semibold text-sm transition-all flex items-center gap-2 shadow-sm hover:shadow-md"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Processar {qtdComBanco} extrato(s)
              </button>
              <button
                onClick={voltarParaUpload}
                className="px-4 py-2.5 text-sm font-medium transition-colors border"
                style={{
                  background: "var(--bg-elevated)",
                  borderColor: "var(--border-default)",
                  color: "var(--text-primary)",
                  borderRadius: "var(--radius-md)",
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = "var(--bg-overlay)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = "var(--bg-elevated)"; }}
              >
                Cancelar
              </button>
            </div>
          </>
        )}

        {/* ══════════════════════════════════════════════════════ */}
        {/*  ETAPA PROCESSANDO (loading)                          */}
        {/* ══════════════════════════════════════════════════════ */}
        {etapa === "processando" && (
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            <svg className="animate-spin w-8 h-8 text-[#3b6ea5]" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
              Processando {arquivos.length} extrato(s)...
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Extraindo transações, categorizando e gerando Excel de cada extrato
            </p>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════ */}
        {/*  ETAPA 3 — RESULTADOS                                 */}
        {/* ══════════════════════════════════════════════════════ */}
        {etapa === "resultado" && (
          <>
            {/* Resumo de totais */}
            {qtdProntos > 0 && totais.transacoes > 0 && (
              <div className="grid grid-cols-3 gap-3">
                <SummaryCard label="Transações" value={totais.transacoes.toString()} subtitle={`em ${qtdProntos} extrato(s)`} color="blue" />
                <SummaryCard label="Total Entradas" value={fmt(totais.entradas)} subtitle="soma dos extratos" color="emerald" />
                <SummaryCard label="Total Saídas" value={fmt(totais.saidas)} subtitle="soma dos extratos" color="rose" />
              </div>
            )}

            {/* Lista de resultados */}
            <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
              <div className="px-4 py-3 flex items-center justify-between"
                   style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border)" }}>
                <p className="text-[11px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                  Resultados — {arquivos.length} arquivo(s)
                </p>
              </div>

              <div className="divide-y" style={{ "--tw-divide-opacity": "1" } as any}>
                {arquivos.map(item => (
                  <ArquivoRow
                    key={item.id}
                    item={item}
                    isLight={isLight}
                    onBanco={bancoId => setBanco(item.id, bancoId)}
                    onRemover={() => remover(item.id)}
                    onBaixar={() => baixar(item)}
                  />
                ))}
              </div>
            </div>

            {/* Barra de ações */}
            <div className="flex flex-wrap items-center gap-3 pt-1">
              {qtdProntos > 0 && (
                <button
                  onClick={baixarTodos}
                  data-notheme
                  className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-700/25 dark:hover:bg-emerald-700/40 text-white dark:text-emerald-300 border border-emerald-600 dark:border-emerald-500/30 rounded-xl font-semibold text-sm transition-all flex items-center gap-2 shadow-sm"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Baixar todos ({qtdProntos})
                </button>
              )}
              <button
                onClick={voltarParaUpload}
                data-notheme
                className="px-5 py-2.5 rounded-xl font-semibold text-sm transition-all flex items-center gap-2 border"
                style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Novo lote
              </button>
            </div>

            {/* Rodapé */}
            <p className="text-[11px] pt-3 border-t" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
              Os arquivos são processados pelo mesmo motor do{" "}
              <span className="font-semibold" style={{ color: "var(--text-secondary)" }}>Leitor de PDF</span>.
              {" "}Download nomeado como:{" "}
              <span className="font-mono opacity-70">extrato_{"{banco}"}_{"{mês}"}_{"{ano}"}.xlsx</span>
            </p>
          </>
        )}

      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
//  Componentes auxiliares
// ─────────────────────────────────────────────────────────────────

function StatChip({ label, value, color }: { label: string; value: number; color?: string }) {
  const colors: Record<string, string> = {
    emerald: "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/30",
    blue:    "bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-500/30",
    amber:   "bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-500/30",
  };
  const cls = color ? (colors[color] ?? "") : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700";
  return (
    <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-semibold ${cls}`}>
      <span className="font-bold">{value}</span>
      <span className="opacity-70 font-normal">{label}</span>
    </div>
  );
}

function SummaryCard({ label, value, subtitle, color }: { label: string; value: string; subtitle: string; color: "blue" | "emerald" | "rose" }) {
  const colors = {
    blue:    { bg: "bg-blue-50/70 dark:bg-blue-950/20",    border: "border-blue-100 dark:border-blue-500/20",    text: "text-blue-700 dark:text-blue-400",    sub: "text-blue-500/70 dark:text-blue-500/50" },
    emerald: { bg: "bg-emerald-50/70 dark:bg-emerald-950/20", border: "border-emerald-100 dark:border-emerald-500/20", text: "text-emerald-700 dark:text-emerald-400", sub: "text-emerald-500/70 dark:text-emerald-500/50" },
    rose:    { bg: "bg-rose-50/70 dark:bg-rose-950/20",    border: "border-rose-100 dark:border-rose-500/20",    text: "text-rose-700 dark:text-rose-400",    sub: "text-rose-500/70 dark:text-rose-500/50" },
  };
  const c = colors[color];
  return (
    <div className={`${c.bg} border ${c.border} rounded-xl px-4 py-3`}>
      <p className={`text-[10px] font-bold uppercase tracking-wider mb-1 ${c.sub}`}>{label}</p>
      <p className={`text-base font-bold font-mono ${c.text} leading-none`}>{value}</p>
      <p className={`text-[10px] mt-1 ${c.sub}`}>{subtitle}</p>
    </div>
  );
}

function ArquivoRow({
  item,
  isLight,
  onBanco,
  onRemover,
  onBaixar,
}: {
  item: Arquivo;
  isLight: boolean;
  onBanco: (id: string) => void;
  onRemover: () => void;
  onBaixar: () => void;
}) {
  const isOk   = item.status === "ok";
  const isProc = item.status === "processando";

  return (
    <div
      className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-slate-50/50 dark:hover:bg-slate-800/20"
      style={{ borderBottom: "1px solid var(--border)" }}
    >
      {/* Ícone de arquivo */}
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
        isOk   ? "bg-emerald-100 dark:bg-emerald-900/30" :
        isProc ? "bg-blue-100 dark:bg-blue-900/30 animate-pulse" :
                 "bg-slate-100 dark:bg-slate-800"
      }`}>
        <svg className={`w-4 h-4 ${
          isOk   ? "text-emerald-600 dark:text-emerald-400" :
          isProc ? "text-blue-500" :
                   "text-slate-400 dark:text-slate-500"
        }`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>

      {/* Informações do arquivo */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-xs font-mono font-medium truncate max-w-[260px]"
             style={{ color: "var(--text-primary)" }} title={item.file.name}>
            {item.file.name}
          </p>
          <StatusPill status={item.status} />
        </div>
        <div className="flex items-center gap-3 mt-0.5 flex-wrap">
          <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
            {(item.file.size / 1024).toFixed(0)} KB
          </span>
          {item.periodoLabel && (
            <span className="text-[10px] text-slate-500 dark:text-slate-400">· {item.periodoLabel}</span>
          )}
          {item.numeroConta && (
            <span className="text-[10px] text-slate-500 dark:text-slate-400">· Conta {item.numeroConta}</span>
          )}
          {item.erroMsg && (
            <span className="text-[10px] text-rose-600 dark:text-rose-400 truncate max-w-[300px]"
                  title={item.erroMsg}>
              ⚠ {item.erroMsg}
            </span>
          )}
          {item.avisos && item.avisos.length > 0 && item.status !== "erro" && (
            <span className="text-[10px] text-amber-600 dark:text-amber-400 truncate max-w-[300px]"
                  title={item.avisos.join(" | ")}>
              ⚠ {item.avisos[0]}
            </span>
          )}
          {item.verificacao && item.verificacao.status !== "SKIPPED" && (
            <VerificacaoBadge verificacao={item.verificacao} />
          )}
        </div>
      </div>

      {/* Resumo financeiro — visível quando ok */}
      {isOk && item.resumo && (
        <div className="hidden md:flex items-center gap-4 flex-shrink-0 text-right">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400 dark:text-slate-500">Transações</p>
            <p className="text-sm font-bold font-mono" style={{ color: "var(--text-primary)" }}>
              {item.totalTransacoes}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wide text-emerald-500/70">Entradas</p>
            <p className="text-sm font-bold font-mono text-emerald-600 dark:text-emerald-400">
              {fmt(item.resumo.entradas)}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wide text-rose-500/70">Saídas</p>
            <p className="text-sm font-bold font-mono text-rose-600 dark:text-rose-400">
              {fmt(item.resumo.saidas)}
            </p>
          </div>
        </div>
      )}

      {/* Seletor de banco ou banco detectado */}
      <div className="flex-shrink-0 w-44">
        {isOk || item.status === "vazio" ? (
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
            <span className="text-xs font-semibold truncate" style={{ color: "var(--text-primary)" }}>
              {item.bancoDetectado ?? BANCOS.find(b => b.id === item.bancoId)?.label ?? item.bancoId}
            </span>
          </div>
        ) : (
          <div className="relative">
            <select
              value={item.bancoId}
              onChange={e => onBanco(e.target.value)}
              disabled={isProc}
              className="w-full pl-2.5 pr-7 py-1.5 rounded-lg text-xs border transition-all outline-none disabled:opacity-50 cursor-pointer"
              style={{
                background: "var(--bg-secondary)",
                borderColor: !item.bancoId ? "rgba(245,158,11,0.5)" : "var(--border)",
                color: "var(--text-primary)",
                colorScheme: isLight ? "light" : "dark",
                appearance: item.bancoId ? "none" : undefined,
                WebkitAppearance: item.bancoId ? "none" : undefined,
              } as React.CSSProperties}
            >
              <option value="">— Selecione o banco —</option>
              {BANCO_GROUPS.map(group => (
                <optgroup key={group} label={group}>
                  {BANCOS.filter(b => b.group === group).map(b => (
                    <option key={b.id} value={b.id}>{b.label}</option>
                  ))}
                </optgroup>
              ))}
            </select>
            {!item.bancoId && (
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                <svg className="w-3 h-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            )}
            {item.bancoId && !isProc && (
              <button
                onClick={() => onBanco("")}
                title="Limpar seleção"
                className="absolute inset-y-0 right-0 flex items-center pr-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        )}
      </div>

      {/* Ações */}
      <div className="flex items-center gap-1.5 flex-shrink-0">
        {isOk && item.excelId && (
          <button
            onClick={onBaixar}
            data-notheme
            title={item.filenameSugerido}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-700/25 dark:hover:bg-emerald-700/40 text-white dark:text-emerald-300 border border-emerald-600 dark:border-emerald-500/30 rounded-lg text-[11px] font-bold transition-all"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Baixar
          </button>
        )}
        {!isProc && !isOk && (
          <button
            onClick={onRemover}
            title="Remover"
            className="p-1.5 rounded-lg transition-colors text-slate-400 dark:text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
        {isOk && (
          <button
            onClick={onRemover}
            title="Remover"
            className="p-1.5 rounded-lg transition-colors text-slate-300 dark:text-slate-600 hover:text-slate-500 dark:hover:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/50"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
