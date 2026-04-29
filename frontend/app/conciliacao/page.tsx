"use client";

import { useState, useRef, useCallback } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";
import { CopyCheck, Layers, Building2 } from "lucide-react";

function exportarCSV(transacoes: Transacao[], nomeEmpresa: string) {
  const cabecalho = ["Data", "Descrição PDF", "Descrição Excel", "Valor PDF", "Valor Excel", "Tipo", "Banco", "Status"];
  const linhas = transacoes.map(t => [
    t.data,
    `"${(t.descricao_pdf ?? "").replace(/"/g, '""')}"`,
    `"${(t.descricao_excel ?? "").replace(/"/g, '""')}"`,
    t.valor_pdf != null ? t.valor_pdf.toFixed(2).replace(".", ",") : "",
    t.valor_excel != null ? t.valor_excel.toFixed(2).replace(".", ",") : "",
    t.tipo === "entrada" ? "Entrada" : "Saída",
    t.banco,
    t.status === "conciliado" ? "Conciliado" : t.status === "apenas_pdf" ? "Só PDF" : "Só Excel",
  ]);
  const bom = "\uFEFF";
  const csv = bom + [cabecalho.join(";"), ...linhas.map(l => l.join(";"))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `conciliacao_${nomeEmpresa.replace(/\s+/g, "_")}_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

const _rawApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = _rawApi.replace(/\/api\/?$/, "").replace(/\/$/, "");

const fmt = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 2 }).format(v);

// ─────────────────────────────────────────────────────────────────
//  Tipos
// ─────────────────────────────────────────────────────────────────

type StatusTx = "conciliado" | "apenas_pdf" | "apenas_excel";

interface Transacao {
  status:          StatusTx;
  linha_excel:     number | null;
  data:            string;
  descricao_pdf:   string | null;
  descricao_excel: string | null;
  valor_pdf:       number | null;
  valor_excel:     number | null;
  diff_valor:      number | null;
  tipo:            string;
  banco:           string;
  categoria:       string;
}

interface Totais {
  entradas:      number;
  saidas:        number;
  saldo:         number;
  total:         number;
  saldo_inicial?: number | null;
  saldo_final?:   number | null;
}

interface Diferenca {
  entradas: number;
  saidas:   number;
  saldo:    number;
}

interface Resultado {
  totais_pdf:   Totais;
  totais_excel: Totais | null;
  diferenca:    Diferenca | null;
  conciliados:  number;
  apenas_pdf:   number;
  apenas_excel: number;
  transacoes:   Transacao[];
  avisos:       string[];
}

// ─────────────────────────────────────────────────────────────────
//  Upload zone simples
// ─────────────────────────────────────────────────────────────────

function UploadZone({
  label, accept, files, onChange, cor,
}: {
  label: string; accept: string; files: File[];
  onChange: (f: File[]) => void; cor: "indigo" | "emerald";
}) {
  const ref  = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  const styles = {
    indigo:  {
      border: drag ? "border-blue-700 dark:border-[#102a43]" : "border-slate-300 dark:border-slate-700 hover:border-blue-700/60 dark:hover:border-[#102a43]/60",
      icon: "text-blue-800 dark:text-[#102a43]",
      tag: "bg-blue-50 dark:bg-[#102a43]/10 text-blue-800 dark:text-[#9BB3FF] border border-blue-200 dark:border-[#102a43]/20",
      glow: drag ? "shadow-[0_0_20px_rgba(79,106,255,0.12)]" : "",
    },
    emerald: {
      border: drag ? "border-emerald-700 dark:border-emerald-500" : "border-slate-300 dark:border-slate-700 hover:border-emerald-700/60 dark:hover:border-emerald-500/60",
      icon: "text-emerald-700 dark:text-emerald-400",
      tag: "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20",
      glow: drag ? "shadow-[0_0_20px_rgba(52,211,153,0.12)]" : "",
    },
  }[cor];

  function add(newFiles: FileList | null) {
    if (newFiles) onChange([...files, ...Array.from(newFiles)]);
  }

  return (
    <div className="flex flex-col gap-2">
      <p className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest">{label}</p>
      <div
        className={`upload-zone border-2 border-dashed rounded-2xl p-6 cursor-pointer transition-all duration-200 ${styles.border} ${styles.glow} ${drag ? `bg-slate-100 dark:bg-slate-800/70 ${cor === "indigo" ? "drag-active-indigo" : "drag-active-emerald"}` : "bg-slate-50 dark:bg-slate-800/20 hover:bg-slate-100 dark:hover:bg-slate-800/40"}`}
        onDragOver={e => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={e => { e.preventDefault(); setDrag(false); add(e.dataTransfer.files); }}
        onClick={() => ref.current?.click()}
      >
        <input ref={ref} type="file" accept={accept} multiple className="hidden"
          onChange={e => { add(e.target.files); e.target.value = ""; }} />
        <div className="flex flex-col items-center gap-2 pointer-events-none select-none">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${cor === "indigo" ? "bg-blue-50 dark:bg-[#102a43]/10 border border-blue-200 dark:border-[#102a43]/20" : "bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20"}`}>
            <svg className={`w-5 h-5 ${styles.icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">
            {files.length === 0 ? "Arraste ou clique para enviar" : `${files.length} arquivo(s) selecionado(s)`}
          </p>
          {files.length === 0 && <p className="text-[11px] text-slate-400 dark:text-slate-600">{accept.toUpperCase().replace(/\./g, "").replace(/,/g, " / ")}</p>}
        </div>
      </div>
      {files.map((f, i) => (
        <div key={i} className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs ${styles.tag}`}>
          <div className="flex items-center gap-2 truncate">
            <svg className="w-3.5 h-3.5 flex-shrink-0 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="truncate max-w-[180px] font-medium">{f.name}</span>
          </div>
          <button onClick={e => { e.stopPropagation(); onChange(files.filter((_, j) => j !== i)); }}
            className="ml-2 opacity-50 hover:opacity-100 hover:text-rose-400 text-base leading-none transition-opacity">×</button>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
//  Linha de totais lado a lado
// ─────────────────────────────────────────────────────────────────

function TotaisCard({ titulo, t, cor }: { titulo: string; t: Totais; cor: string }) {
  const temSaldoInicial = t.saldo_inicial != null;
  const saldoFinal = t.saldo_final != null
    ? t.saldo_final
    : temSaldoInicial ? (t.saldo_inicial! + t.saldo) : null;

  return (
    <div className={`flex-1 rounded-2xl border p-5 space-y-2.5 ${cor}`}
      style={{ boxShadow: "0 2px 8px rgba(0,0,0,0.08)" }}>
      <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 opacity-80">{titulo}</p>
      {temSaldoInicial && (
        <div className="flex justify-between text-sm border-b border-slate-200 dark:border-slate-700/50 pb-2.5">
          <span className="text-slate-500 dark:text-slate-400">Saldo Inicial</span>
          <span className="text-slate-700 dark:text-slate-300 font-mono font-bold">{fmt(t.saldo_inicial!)}</span>
        </div>
      )}
      <div className="flex justify-between text-sm">
        <span className="text-slate-500 dark:text-slate-400">Entradas</span>
        <span className="text-emerald-600 dark:text-emerald-400 font-mono font-bold">{fmt(t.entradas)}</span>
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-slate-500 dark:text-slate-400">Saídas</span>
        <span className="text-rose-600 dark:text-rose-400 font-mono font-bold">{fmt(t.saidas)}</span>
      </div>
      <div className="flex justify-between text-sm border-t border-slate-200 dark:border-slate-700 pt-2.5">
        <span className="text-slate-700 dark:text-slate-300 font-semibold">{saldoFinal != null ? "Saldo Final" : "Saldo"}</span>
        <span className={`font-mono font-bold ${(saldoFinal ?? t.saldo) >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
          {fmt(saldoFinal ?? t.saldo)}
        </span>
      </div>
      <p className="text-[11px] text-slate-400 dark:text-slate-600">{t.total} transação(ões)</p>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
//  Página
// ─────────────────────────────────────────────────────────────────

export default function ConciliacaoPage() {
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;

  const [pdfs, setPdfs]     = useState<File[]>([]);
  const [excels, setExcels] = useState<File[]>([]);
  const [analisando, setAna]= useState(false);
  const [resultado, setRes] = useState<Resultado | null>(null);
  const [erro, setErro]     = useState("");
  const [filtro, setFiltro] = useState<"" | StatusTx>("");

  const analisar = useCallback(async () => {
    if (!empresaId) { setErro("Selecione uma empresa no menu lateral."); return; }
    if (pdfs.length === 0 && excels.length === 0) { setErro("Adicione ao menos um PDF ou planilha."); return; }
    setAna(true); setErro(""); setRes(null); setFiltro("");
    try {
      const token = localStorage.getItem("controllo_token") ?? "";
      const form  = new FormData();
      form.append("empresa_id", String(empresaId));
      pdfs.forEach(f => form.append("pdfs", f));
      excels.forEach(f => form.append("excels", f));
      const r = await fetch(`${API}/api/conciliacao/analisar`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        setErro(d.detail || `Erro ${r.status}`);
        return;
      }
      setRes(await r.json());
    } catch {
      setErro("Não foi possível conectar ao servidor. Verifique se o backend está rodando.");
    } finally {
      setAna(false);
    }
  }, [empresaId, pdfs, excels]);

  const res = resultado;
  const divergencias = res?.transacoes.filter(t => t.status !== "conciliado") ?? [];
  const exibir = res
    ? (filtro ? res.transacoes.filter(t => t.status === filtro) : res.transacoes)
    : [];
  const total = res ? res.conciliados + res.apenas_pdf + res.apenas_excel : 0;
  const pct   = total > 0 ? Math.round((res!.conciliados / total) * 100) : 0;
  const ok    = pct === 100;

  return (
    <div className="min-h-full" style={{ background: "var(--bg-canvas)", color: "var(--text-primary)" }}>

      {/* Header */}
      <header
        className="px-8 pt-8 pb-6"
        style={{ borderBottom: "1px solid var(--border-subtle)" }}
      >
        <p
          className="text-xs uppercase font-medium mb-2"
          style={{
            color: "var(--text-tertiary)",
            letterSpacing: "var(--tracking-widest)",
          }}
        >
          Ferramenta
        </p>
        <h1 className="text-2xl font-extrabold tracking-tight" style={{ color: "var(--text-primary)" }}>
          Conciliação Bancária
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
          <span style={{ color: "var(--text-primary)" }} className="font-medium">{empresaSelecionada?.nome ?? "Selecione uma empresa"}</span>
          <span className="mx-2" style={{ color: "var(--text-tertiary)" }}>·</span>
          Compare o extrato PDF do banco com a planilha Excel
        </p>
      </header>

      <div className="px-8 py-10 space-y-6 max-w-5xl mx-auto">

        {/* Hero — Upload Section centralizado */}
        <div
          className="mx-auto rounded-2xl p-10 space-y-6"
          style={{
            maxWidth: 880,
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <UploadZone label="Extrato PDF (banco)" accept=".pdf" files={pdfs} onChange={setPdfs} cor="indigo" />
            <UploadZone label="Planilha Excel (leitor de extrato)" accept=".xlsx,.xls" files={excels} onChange={setExcels} cor="emerald" />
          </div>

          <p className="text-[11px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            Arraste um ou mais PDFs + a planilha gerada pelo Leitor de Extrato do mesmo período. O sistema compara
            automaticamente cada transação por data · valor · tipo usando lógica específica de cada banco.
          </p>

          {/* 3 mini-explicações */}
          <div
            className="pt-4"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
              gap: "1rem",
              borderTop: "1px solid var(--border-subtle)",
            }}
          >
            {[
              { Icon: CopyCheck, text: "Detecção automática de duplicidades" },
              { Icon: Layers, text: "Match por data + valor + descrição" },
              { Icon: Building2, text: "Lógica específica por banco" },
            ].map(({ Icon, text }) => (
              <div
                key={text}
                style={{
                  display: "grid",
                  gridTemplateColumns: "20px 1fr",
                  alignItems: "start",
                  gap: "0.625rem",
                }}
              >
                <Icon size={20} strokeWidth={1.75} style={{ color: "var(--text-tertiary)", marginTop: 1 }} />
                <p className="text-sm leading-snug" style={{ color: "var(--text-secondary)" }}>{text}</p>
              </div>
            ))}
          </div>

          {erro && (
            <div
              className="flex items-center gap-2.5 px-4 py-3 rounded-xl"
              style={{
                background: "var(--danger-subtle)",
                border: "1px solid var(--danger-border)",
              }}
            >
              <svg className="w-4 h-4 flex-shrink-0" style={{ color: "var(--danger)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm" style={{ color: "var(--danger)" }}>{erro}</p>
            </div>
          )}

          <button
            onClick={analisar}
            disabled={analisando || (pdfs.length === 0 && excels.length === 0)}
            className="font-semibold px-8 py-3 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-sm"
            style={{
              background: "var(--accent)",
              color: "var(--text-inverse)",
              borderRadius: "var(--radius-md)",
            }}
            onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.background = "var(--accent-hover)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "var(--accent)"; }}
          >
            {analisando ? (
              <>
                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Analisando...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
                Comparar Extratos
              </>
            )}
          </button>
        </div>

        {/* Resultado */}
        {res && (
          <>
            {/* Avisos */}
            {res.avisos.length > 0 && (
              <div className="rounded-2xl border border-amber-200 dark:border-amber-500/20 bg-amber-50 dark:bg-amber-950/20 px-5 py-4 space-y-1.5">
                <p className="text-[11px] font-bold text-amber-600 dark:text-amber-400 uppercase tracking-widest mb-2">Avisos</p>
                {res.avisos.map((a, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <svg className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <p className="text-amber-700 dark:text-amber-300 text-xs">{a}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Status banner */}
            <div className={`rounded-2xl px-6 py-5 flex items-center gap-4 border ${
              ok
                ? "border-emerald-200 dark:border-emerald-500/25 bg-emerald-50 dark:bg-emerald-950/20"
                : "border-amber-200 dark:border-amber-500/25 bg-amber-50 dark:bg-amber-950/20"
            }`}>
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${ok ? "bg-emerald-100 dark:bg-emerald-500/15 border border-emerald-300 dark:border-emerald-500/25" : "bg-amber-100 dark:bg-amber-500/15 border border-amber-300 dark:border-amber-500/25"}`}>
                {ok ? (
                  <svg className="w-5 h-5 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                )}
              </div>
              <div>
                <p className={`font-bold text-base ${ok ? "text-emerald-700 dark:text-emerald-300" : "text-amber-700 dark:text-amber-300"}`}>
                  {ok
                    ? `Totalmente conciliado — ${res.conciliados} transação(ões) verificadas`
                    : `${divergencias.length} divergência(s) encontrada(s) — ${res.conciliados}/${total} conciliadas (${pct}%)`
                  }
                </p>
                {!ok && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    {res.apenas_pdf > 0 && `${res.apenas_pdf} no PDF sem par no Excel`}
                    {res.apenas_pdf > 0 && res.apenas_excel > 0 && <span className="mx-2 opacity-40">·</span>}
                    {res.apenas_excel > 0 && `${res.apenas_excel} no Excel sem par no PDF`}
                  </p>
                )}
              </div>
              {/* Progress pill */}
              {!ok && (
                <div className="ml-auto flex flex-col items-end gap-1">
                  <span className="text-2xl font-black text-amber-600 dark:text-amber-300">{pct}%</span>
                  <div className="w-24 h-1.5 rounded-full bg-slate-200 dark:bg-slate-700">
                    <div className="h-full rounded-full bg-gradient-to-r from-amber-500 to-amber-400 transition-all" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )}
            </div>

            {/* Summary stat cards */}
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "Conciliados", value: res.conciliados, color: "emerald", icon: "M5 13l4 4L19 7" },
                { label: "Só PDF", value: res.apenas_pdf, color: "amber", icon: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" },
                { label: "Só Excel", value: res.apenas_excel, color: "rose", icon: "M6 18L18 6M6 6l12 12" },
              ].map(({ label, value, color, icon }) => (
                <div key={label} className="rounded-2xl border p-4 flex flex-col gap-1"
                  style={{
                    background: `linear-gradient(135deg, rgba(${color === "emerald" ? "52,211,153" : color === "amber" ? "251,191,36" : "251,113,133"},0.08) 0%, transparent 100%)`,
                    borderColor: `rgba(${color === "emerald" ? "52,211,153" : color === "amber" ? "251,191,36" : "251,113,133"},0.2)`,
                    boxShadow: "0 4px 16px rgba(0,0,0,0.15)"
                  }}>
                  <p className={`text-[11px] font-bold uppercase tracking-widest ${color === "emerald" ? "text-emerald-600 dark:text-emerald-500" : color === "amber" ? "text-amber-600 dark:text-amber-500" : "text-rose-600 dark:text-rose-500"}`}>{label}</p>
                  <p className={`text-3xl font-black ${color === "emerald" ? "text-emerald-600 dark:text-emerald-400" : color === "amber" ? "text-amber-600 dark:text-amber-400" : "text-rose-600 dark:text-rose-400"}`}>{value}</p>
                </div>
              ))}
            </div>

            {/* Totais lado a lado */}
            <div className="flex gap-4 flex-wrap">
              <TotaisCard titulo="Totais do PDF" t={res.totais_pdf}
                cor="bg-white dark:bg-slate-800/40 border-[#E2E8F0] dark:border-slate-700/60" />
              {res.totais_excel && (
                <TotaisCard titulo="Totais do Excel" t={res.totais_excel}
                  cor="bg-white dark:bg-slate-800/40 border-[#E2E8F0] dark:border-slate-700/60" />
              )}
              {res.diferenca && (
                <div className={`flex-1 rounded-2xl border p-5 space-y-2.5 ${
                  Math.abs(res.diferenca.saldo) < 0.02
                    ? "border-emerald-200 dark:border-emerald-500/20 bg-emerald-50 dark:bg-emerald-950/20"
                    : "border-amber-200 dark:border-amber-500/20 bg-amber-50 dark:bg-amber-950/20"
                }`} style={{ boxShadow: "0 2px 8px rgba(0,0,0,0.08)" }}>
                  <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 opacity-80">Diferença (PDF − Excel)</p>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 dark:text-slate-400">Entradas</span>
                    <span className={`font-mono font-bold ${Math.abs(res.diferenca.entradas) < 0.02 ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                      {res.diferenca.entradas >= 0 ? "+" : ""}{fmt(res.diferenca.entradas)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500 dark:text-slate-400">Saídas</span>
                    <span className={`font-mono font-bold ${Math.abs(res.diferenca.saidas) < 0.02 ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                      {res.diferenca.saidas >= 0 ? "+" : ""}{fmt(res.diferenca.saidas)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm border-t border-slate-200 dark:border-slate-700/60 pt-2.5">
                    <span className="text-slate-700 dark:text-slate-300 font-semibold">Saldo</span>
                    <span className={`font-mono font-bold ${Math.abs(res.diferenca.saldo) < 0.02 ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                      {Math.abs(res.diferenca.saldo) < 0.02 ? "✓ OK" : (res.diferenca.saldo >= 0 ? "+" : "") + fmt(res.diferenca.saldo)}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Divergências em destaque */}
            {divergencias.length > 0 && (
              <div className="rounded-2xl border border-amber-200 dark:border-amber-500/20 overflow-hidden"
                style={{ boxShadow: "0 2px 8px rgba(0,0,0,0.08)" }}>
                <div className="px-5 py-3.5 border-b border-amber-100 dark:border-amber-500/15 flex items-center gap-2 bg-amber-50 dark:bg-amber-950/30">
                  <svg className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <p className="text-[11px] font-bold text-amber-700 dark:text-amber-400 uppercase tracking-widest">
                    Divergências ({divergencias.length})
                  </p>
                </div>
                <div className="divide-y divide-slate-100 dark:divide-slate-800/60 bg-white dark:bg-slate-900/50">
                  {divergencias.map((t, i) => (
                    <div key={i} className={`px-5 py-4 flex flex-col sm:flex-row sm:items-start gap-3 border-l-2 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/20 ${
                      t.status === "apenas_pdf" ? "border-l-amber-500" : "border-l-rose-500"
                    }`}>
                      <div className="flex items-center gap-2 min-w-[120px]">
                        <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full ${
                          t.status === "apenas_pdf"
                            ? "bg-amber-100 dark:bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-300 dark:border-amber-500/30"
                            : "bg-rose-100 dark:bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-300 dark:border-rose-500/30"
                        }`}>
                          {t.status === "apenas_pdf" ? "Só PDF" : "Só Excel"}
                        </span>
                        {t.linha_excel && (
                          <span className="text-xs text-slate-500 font-mono">Linha {t.linha_excel}</span>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-slate-500 font-mono">{t.data}</p>
                        <p className="text-sm text-slate-700 dark:text-slate-300 truncate font-medium">
                          {t.descricao_pdf ?? t.descricao_excel}
                        </p>
                        {t.descricao_excel && t.descricao_pdf && t.descricao_excel !== t.descricao_pdf && (
                          <p className="text-xs text-slate-500 dark:text-slate-600">Excel: {t.descricao_excel}</p>
                        )}
                      </div>
                      <div className="text-right whitespace-nowrap">
                        <p className={`font-mono text-sm font-bold ${t.tipo === "entrada" ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
                          {t.tipo === "entrada" ? "+" : "−"}{fmt(t.valor_pdf ?? t.valor_excel ?? 0)}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-600 mt-0.5">{t.tipo === "entrada" ? "Entrada" : "Saída"} · {t.banco}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tabela completa */}
            <div className="rounded-2xl border border-[#E2E8F0] dark:border-slate-700/60 overflow-hidden"
              style={{ boxShadow: "0 2px 8px rgba(0,0,0,0.08)" }}>
              {/* Toolbar */}
              <div className="flex gap-1.5 p-4 border-b border-[#E2E8F0] dark:border-slate-700/60 flex-wrap items-center justify-between bg-[#F8FAFC] dark:bg-slate-800/50">
                <div className="flex gap-1 flex-wrap">
                  {(["", "conciliado", "apenas_pdf", "apenas_excel"] as const).map(f => {
                    const labels: Record<string, string> = {
                      "":           `Todos (${total})`,
                      conciliado:   `Conciliados (${res.conciliados})`,
                      apenas_pdf:   `Só PDF (${res.apenas_pdf})`,
                      apenas_excel: `Só Excel (${res.apenas_excel})`,
                    };
                    return (
                      <button key={f} onClick={() => setFiltro(f as "" | StatusTx)}
                        data-notheme={filtro === f ? true : undefined}
                        className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all duration-150 ${
                          filtro === f
                            ? "text-white shadow-sm"
                            : "text-slate-500 hover:text-[#1E293B] dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/50"
                        }`}
                        style={filtro === f ? { background: "linear-gradient(135deg, #102a43 0%, #3b6ea5 100%)", boxShadow: "0 2px 8px rgba(79,106,255,0.35)" } : {}}>
                        {labels[f]}
                      </button>
                    );
                  })}
                </div>
                <button
                  onClick={() => exportarCSV(exibir, empresaSelecionada?.nome ?? "empresa")}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-semibold text-[#64748B] dark:text-slate-400 hover:text-[#1E293B] dark:hover:text-white border border-[#CBD5E1] dark:border-slate-700 hover:border-[#94A3B8] dark:hover:border-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-all duration-150 whitespace-nowrap flex items-center gap-1.5"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Exportar CSV
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-[10px] text-slate-500 uppercase tracking-widest border-b border-[#E2E8F0] dark:border-slate-700/60 bg-[#F8FAFC] dark:bg-slate-900/50">
                      <th className="px-4 py-3 text-left font-bold">Linha Excel</th>
                      <th className="px-4 py-3 text-left font-bold">Data</th>
                      <th className="px-4 py-3 text-left font-bold">Descrição</th>
                      <th className="px-4 py-3 text-right font-bold">Valor PDF</th>
                      <th className="px-4 py-3 text-right font-bold">Valor Excel</th>
                      <th className="px-4 py-3 text-center font-bold">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exibir.length === 0 && (
                      <tr><td colSpan={6} className="px-4 py-12 text-center text-slate-600 text-sm">Nenhuma transação.</td></tr>
                    )}
                    {exibir.map((t, i) => (
                      <tr key={i} className={`border-b border-[#F1F5F9] dark:border-slate-800/50 transition-colors border-l-2 ${
                        t.status === "conciliado"
                          ? "border-l-emerald-400 hover:bg-emerald-50/50 dark:hover:bg-emerald-950/10"
                          : t.status === "apenas_pdf"
                          ? "border-l-amber-400 bg-amber-50/50 dark:bg-amber-950/5 hover:bg-amber-50 dark:hover:bg-amber-950/15"
                          : "border-l-rose-400 bg-rose-50/50 dark:bg-rose-950/5 hover:bg-rose-50 dark:hover:bg-rose-950/15"
                      }`}>
                        <td className="px-4 py-2.5 text-slate-400 dark:text-slate-500 font-mono text-xs">
                          {t.linha_excel ? `L${t.linha_excel}` : "—"}
                        </td>
                        <td className="px-4 py-2.5 text-slate-500 font-mono text-xs whitespace-nowrap">{t.data}</td>
                        <td className="px-4 py-2.5 text-slate-700 dark:text-slate-300 max-w-[280px]">
                          <span className="line-clamp-1 block text-xs font-medium">{t.descricao_pdf ?? t.descricao_excel}</span>
                          {t.descricao_excel && t.descricao_pdf && t.descricao_excel !== t.descricao_pdf && (
                            <span className="text-[10px] text-slate-400 dark:text-slate-600 block">Excel: {t.descricao_excel}</span>
                          )}
                        </td>
                        <td className={`px-4 py-2.5 text-right font-mono text-xs font-bold ${
                          t.tipo === "entrada" ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
                        }`}>
                          {t.valor_pdf != null ? fmt(t.valor_pdf) : "—"}
                        </td>
                        <td className={`px-4 py-2.5 text-right font-mono text-xs font-bold ${
                          t.diff_valor !== null && Math.abs(t.diff_valor) >= 0.02
                            ? "text-amber-600 dark:text-amber-400"
                            : t.tipo === "entrada" ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
                        }`}>
                          {t.valor_excel != null ? (
                            <>
                              {fmt(t.valor_excel)}
                              {t.diff_valor !== null && Math.abs(t.diff_valor) >= 0.02 && (
                                <span className="text-amber-600 dark:text-amber-400 text-[10px] ml-1">
                                  (Δ {t.diff_valor > 0 ? "+" : ""}{fmt(t.diff_valor)})
                                </span>
                              )}
                            </>
                          ) : "—"}
                        </td>
                        <td className="px-4 py-2.5 text-center">
                          <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full ${
                            t.status === "conciliado"
                              ? "bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-500/30"
                              : t.status === "apenas_pdf"
                              ? "bg-amber-100 dark:bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-300 dark:border-amber-500/30"
                              : "bg-rose-100 dark:bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-300 dark:border-rose-500/30"
                          }`}>
                            {t.status === "conciliado" ? "✓" : t.status === "apenas_pdf" ? "Só PDF" : "Só Excel"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
