"use client";

import { TIPO_INFO } from "./types";
import type { CampoDestino, Etapa } from "./types";

interface Props {
  empresaId: number | null;
  etapa: Etapa;
  tipoDado: string;
  setTipoDado: (t: string) => void;
  arquivo: File | null;
  setArquivo: (f: File | null) => void;
  dragging: boolean;
  setDragging: (d: boolean) => void;
  tiposDisponiveis: string[];
  camposDestino: Record<string, CampoDestino[]>;
  colunasArquivo: string[];
  mapeamento: Record<string, string>;
  setMapeamento: (fn: (prev: Record<string, string>) => Record<string, string>) => void;
  carregandoPreview: boolean;
  erro: string;
  processando: boolean;
  buscarPreview: () => void;
  processarAvancado: () => void;
  setEtapa: (e: Etapa) => void;
  reiniciar: () => void;
}

export default function ModoAvancado({
  empresaId, etapa, tipoDado, setTipoDado, arquivo, setArquivo, dragging, setDragging,
  tiposDisponiveis, camposDestino, colunasArquivo, mapeamento, setMapeamento,
  carregandoPreview, erro, processando, buscarPreview, processarAvancado, setEtapa, reiniciar,
}: Props) {
  if (etapa === "upload") {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <button onClick={reiniciar} className="text-[#64748B] dark:text-slate-500 hover:text-[#0F2D4A] dark:hover:text-slate-300 transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <p className="font-bold text-[#0F2D4A] dark:text-slate-200">Planilha própria — Passo 1: Upload</p>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {(tiposDisponiveis.length > 0 ? tiposDisponiveis : Object.keys(TIPO_INFO)).map((tipo) => (
            <button key={tipo} onClick={() => setTipoDado(tipo)}
              className={`p-3 rounded-xl border text-left transition-all text-sm ${tipoDado === tipo ? "border-[#1E4976] bg-[#1E4976]/10 text-[#0F2D4A] dark:text-[#9BB3FF]" : "border-[#E2E8F0] dark:border-slate-700 text-[#475569] dark:text-slate-400 hover:border-[#CBD5E1] dark:hover:border-slate-600"}`}>
              {TIPO_INFO[tipo]?.label ?? tipo}
            </button>
          ))}
        </div>
        <div
          onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) setArquivo(f); }}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onClick={() => document.getElementById("file-adv")?.click()}
          className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all ${dragging ? "border-[#1E4976] bg-[#1E4976]/5" : arquivo ? "border-emerald-400 dark:border-emerald-500/50 bg-emerald-50 dark:bg-emerald-950/20" : "border-[#CBD5E1] dark:border-slate-700 hover:border-[#94A3B8] dark:hover:border-slate-600 hover:bg-[#F8FAFC] dark:hover:bg-slate-800/30"}`}
        >
          <input id="file-adv" type="file" accept=".xlsx,.xls,.csv" className="hidden"
            onChange={(e) => { if (e.target.files?.[0]) setArquivo(e.target.files[0]); }} />
          {arquivo
            ? <div className="flex flex-col items-center gap-2">
                <p className="font-semibold text-emerald-700 dark:text-emerald-300 text-sm">{arquivo.name}</p>
                <p className="text-xs text-[#64748B] dark:text-slate-500">{(arquivo.size / 1024).toFixed(1)} KB</p>
                <button onClick={(e) => { e.stopPropagation(); setArquivo(null); }} className="text-xs text-[#64748B] dark:text-slate-500 hover:text-red-600 dark:hover:text-red-400">Remover</button>
              </div>
            : <div className="flex flex-col items-center gap-2">
                <p className="font-semibold text-[#2C3E50] dark:text-slate-300 text-sm">Arraste o arquivo aqui</p>
                <p className="text-xs text-[#64748B] dark:text-slate-500">ou clique · .xlsx, .xls, .csv · Máx. 20 MB</p>
              </div>
          }
        </div>
        {erro && <div className="px-4 py-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-500/20 text-red-700 dark:text-red-400 text-sm">{erro}</div>}
        <button
          disabled={!arquivo || !empresaId || carregandoPreview}
          onClick={() => { setEtapa("classificar"); buscarPreview(); }}
          className="w-full py-3 rounded-xl font-semibold text-sm bg-[#1E4976] text-white hover:bg-[#0F2D4A] disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {carregandoPreview ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Analisando...</> : "Analisar colunas →"}
        </button>
      </div>
    );
  }

  // etapa === "classificar" (mapeamento)
  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <button onClick={() => setEtapa("upload")} className="text-[#64748B] dark:text-slate-500 hover:text-[#0F2D4A] dark:hover:text-slate-300 transition-colors">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <p className="font-bold text-[#0F2D4A] dark:text-slate-200">Passo 2: Mapear colunas</p>
      </div>
      <p className="text-sm text-[#64748B] dark:text-slate-400">
        Associe cada coluna do arquivo ao campo correspondente. Os campos com
        <span className="text-[#1E4976] dark:text-[#3b6ea5]"> *</span> são obrigatórios (<strong>ano</strong> e <strong>mês</strong>).
      </p>
      {carregandoPreview ? (
        <div className="flex justify-center py-10">
          <div className="w-6 h-6 border-2 border-[#102a43]/30 border-t-[#102a43] rounded-full animate-spin" />
        </div>
      ) : (
        <>
          <div className="space-y-2">
            {colunasArquivo.map((col) => (
              <div key={col} className="flex items-center gap-3 bg-[#F8FAFC] dark:bg-slate-800/40 border border-[#E2E8F0] dark:border-slate-700 rounded-xl px-4 py-3">
                <p className="text-sm font-medium text-[#0F172A] dark:text-slate-200 flex-1 truncate">{col}</p>
                <svg className="w-4 h-4 text-[#94A3B8] dark:text-slate-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
                <select
                  value={mapeamento[col] ?? ""}
                  onChange={(e) => setMapeamento((prev) => { const n = { ...prev }; e.target.value ? (n[col] = e.target.value) : delete n[col]; return n; })}
                  className="bg-white dark:bg-slate-900 border border-[#CBD5E1] dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm text-[#0F172A] dark:text-slate-300 focus:outline-none focus:border-[#1E4976] min-w-[180px]"
                >
                  <option value="">Ignorar coluna</option>
                  {(camposDestino[tipoDado] ?? []).map((c) => (
                    <option key={c.campo} value={c.campo}>{c.label}{c.obrigatorio ? " *" : ""}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          {(!Object.values(mapeamento).includes("ano") || !Object.values(mapeamento).includes("mes")) && (
            <div className="px-4 py-2 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-500/20 text-amber-700 dark:text-amber-400 text-xs">
              Mapeie as colunas <strong>Ano</strong> e <strong>Mês</strong> para continuar.
            </div>
          )}
          {erro && <div className="px-4 py-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-500/20 text-red-700 dark:text-red-400 text-sm">{erro}</div>}
          <button
            onClick={processarAvancado}
            disabled={
              processando ||
              !Object.values(mapeamento).includes("ano") ||
              !Object.values(mapeamento).includes("mes")
            }
            className="w-full py-3 rounded-xl font-semibold text-sm bg-[#1E4976] text-white hover:bg-[#0F2D4A] disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {processando ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Importando...</> : "Importar dados →"}
          </button>
        </>
      )}
    </div>
  );
}
