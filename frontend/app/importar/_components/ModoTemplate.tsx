"use client";

import { TIPO_INFO } from "./types";
import type { CampoDestino } from "./types";

interface Props {
  empresaId: number | null;
  tipoDado: string;
  setTipoDado: (t: string) => void;
  arquivo: File | null;
  setArquivo: (f: File | null) => void;
  dragging: boolean;
  setDragging: (d: boolean) => void;
  tiposDisponiveis: string[];
  camposDestino: Record<string, CampoDestino[]>;
  erro: string;
  processando: boolean;
  baixarTemplate: (tipo: string) => void;
  processarTemplate: (tipo: string) => void;
  reiniciar: () => void;
}

export default function ModoTemplate({
  empresaId, tipoDado, setTipoDado, arquivo, setArquivo, dragging, setDragging,
  tiposDisponiveis, erro, processando, baixarTemplate, processarTemplate, reiniciar,
}: Props) {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={reiniciar} className="text-[#64748B] dark:text-slate-500 hover:text-[#0F2D4A] dark:hover:text-slate-300 transition-colors">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <p className="font-bold text-[#0F2D4A] dark:text-slate-200">Selecione o tipo de dado e carregue o arquivo</p>
      </div>

      {/* Selecionar tipo */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {(tiposDisponiveis.length > 0 ? tiposDisponiveis : Object.keys(TIPO_INFO))
          .filter((t) => t !== "generico")
          .map((tipo) => (
            <button
              key={tipo}
              onClick={() => setTipoDado(tipo)}
              className={`p-3.5 rounded-xl border text-left transition-all ${
                tipoDado === tipo
                  ? "border-[#1E4976] bg-[#1E4976]/10 text-[#0F2D4A] dark:text-[#9BB3FF]"
                  : "border-[#E2E8F0] dark:border-slate-700 text-[#475569] dark:text-slate-400 hover:border-[#CBD5E1] dark:hover:border-slate-600 hover:bg-[#F8FAFC] dark:hover:bg-slate-800"
              }`}
            >
              <p className="font-semibold text-sm">{TIPO_INFO[tipo]?.label ?? tipo}</p>
              <p className="text-[11px] text-[#94A3B8] dark:text-slate-500 mt-0.5 leading-snug">{TIPO_INFO[tipo]?.descricao ?? ""}</p>
            </button>
          ))}
      </div>

      {/* Baixar modelo */}
      <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-[#F8FAFC] dark:bg-slate-800/40 border border-[#E2E8F0] dark:border-slate-700 text-sm">
        <svg className="w-4 h-4 text-[#1E4976] dark:text-[#3b6ea5] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-[#64748B] dark:text-slate-400">Ainda não tem o modelo?</span>
        <button onClick={() => baixarTemplate(tipoDado)} className="text-[#1E4976] dark:text-[#3b6ea5] hover:text-[#0F2D4A] dark:hover:text-[#9BB3FF] font-semibold underline underline-offset-2 transition-colors">
          Baixar modelo_{tipoDado}.xlsx
        </button>
      </div>

      {/* Upload */}
      <div
        onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) setArquivo(f); }}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onClick={() => document.getElementById("file-tpl")?.click()}
        className={`relative border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all ${
          dragging ? "border-[#1E4976] bg-[#1E4976]/5"
          : arquivo ? "border-emerald-400 dark:border-emerald-500/50 bg-emerald-50 dark:bg-emerald-950/20"
          : "border-[#CBD5E1] dark:border-slate-700 hover:border-[#94A3B8] dark:hover:border-slate-600 hover:bg-[#F8FAFC] dark:hover:bg-slate-800/30"
        }`}
      >
        <input id="file-tpl" type="file" accept=".xlsx,.xls,.csv" className="hidden"
          onChange={(e) => { if (e.target.files?.[0]) setArquivo(e.target.files[0]); }} />
        {arquivo ? (
          <div className="flex flex-col items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-500/15 border border-emerald-200 dark:border-emerald-500/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="font-semibold text-emerald-700 dark:text-emerald-300 text-sm">{arquivo.name}</p>
            <p className="text-xs text-[#64748B] dark:text-slate-500">{(arquivo.size / 1024).toFixed(1)} KB</p>
            <button onClick={(e) => { e.stopPropagation(); setArquivo(null); }}
              className="text-xs text-[#64748B] dark:text-slate-500 hover:text-red-600 dark:hover:text-red-400 transition-colors mt-1">
              Remover arquivo
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div className="w-12 h-12 rounded-2xl bg-[#F1F5F9] dark:bg-slate-800 border border-[#CBD5E1] dark:border-slate-700 flex items-center justify-center">
              <svg className="w-6 h-6 text-[#64748B] dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <p className="font-semibold text-[#2C3E50] dark:text-slate-300 text-sm">Arraste o arquivo preenchido aqui</p>
            <p className="text-xs text-[#64748B] dark:text-slate-500">ou clique para selecionar · .xlsx, .xls, .csv · Máx. 20 MB</p>
          </div>
        )}
      </div>

      {erro && <div className="px-4 py-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-500/20 text-red-700 dark:text-red-400 text-sm">{erro}</div>}

      <button
        onClick={() => processarTemplate(tipoDado)}
        disabled={!arquivo || !empresaId || processando}
        className="w-full py-3.5 rounded-xl font-semibold text-sm bg-[#1E4976] text-white hover:bg-[#0F2D4A] disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {processando ? (
          <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Processando...</>
        ) : "Importar dados"}
      </button>
    </div>
  );
}
