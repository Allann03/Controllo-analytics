"use client";
import { useCallback, useRef, useState } from "react";
import { useEmpresa } from "@/contexts/EmpresaContext";

// ─── Types ──────────────────────────────────────────────────────────────────

export type ImportSchema = {
  section: string;
  description: string;
  modelFilename: string;
  columns: Array<{ key: string; label: string; tipo: string; exemplo: string; obrigatorio: boolean }>;
  exemplos: Record<string, string | number>[];
  instrucoes?: string[];
};

interface DataImportPanelProps {
  schema: ImportSchema;
  onImport: (file: File, empresaId: number) => Promise<void>;
  /** Extra action button shown alongside "Importar" (e.g. already have data: manage) */
  secondaryAction?: { label: string; onClick: () => void };
}

// ─── Helpers ────────────────────────────────────────────────────────────────

async function gerarModeloXLSX(schema: ImportSchema): Promise<void> {
  // @ts-ignore
  const XLSX = await import("xlsx");
  const wb = XLSX.utils.book_new();

  // Aba Instruções
  const instrRows: Record<string, string>[] = [
    { "": "INSTRUÇÕES DE PREENCHIMENTO" },
    { "": "" },
    { "": `Seção: ${schema.section}` },
    { "": `Descrição: ${schema.description}` },
    { "": "" },
    { "": "COLUNAS OBRIGATÓRIAS (marcadas com *)" },
    ...schema.columns.map(c => ({
      "": `  ${c.obrigatorio ? "* " : "  "}${c.label} [${c.tipo}] — ex: ${c.exemplo}`,
    })),
    { "": "" },
    ...(schema.instrucoes ?? [
      "1. Não altere os nomes das colunas.",
      "2. Datas devem estar no formato YYYY-MM-DD (ex: 2025-01-31).",
      "3. Valores monetários são numéricos sem símbolo de moeda.",
      "4. Percentuais são numéricos (ex: 12.5 para 12,5%).",
      "5. Não deixe linhas em branco entre registros.",
    ]).map(i => ({ "": i })),
  ];
  const wsInstr = XLSX.utils.json_to_sheet(instrRows);
  wsInstr["!cols"] = [{ wch: 80 }];
  XLSX.utils.book_append_sheet(wb, wsInstr, "Instruções");

  // Aba de dados com cabeçalho e exemplos
  const header = schema.columns.map(c => `${c.obrigatorio ? "*" : ""}${c.label}`);
  const rows = schema.exemplos.map(ex =>
    Object.fromEntries(
      schema.columns.map(c => [`${c.obrigatorio ? "*" : ""}${c.label}`, ex[c.key] ?? ""])
    )
  );
  const wsDados = XLSX.utils.json_to_sheet(rows.length ? rows : [Object.fromEntries(schema.columns.map(c => [`${c.obrigatorio ? "*" : ""}${c.label}`, ""]))]);
  wsDados["!cols"] = schema.columns.map(() => ({ wch: 22 }));
  XLSX.utils.book_append_sheet(wb, wsDados, "Dados");

  XLSX.writeFile(wb, schema.modelFilename);
}

function parsePreview(file: File): Promise<Array<Record<string, string>>> {
  return new Promise(resolve => {
    const reader = new FileReader();
    reader.onload = async e => {
      try {
        // @ts-ignore
        const XLSX = await import("xlsx");
        const wb = XLSX.read(e.target?.result, { type: "array" });
        const ws = wb.Sheets[wb.SheetNames[wb.SheetNames.length > 1 ? 1 : 0]];
        const rows: Record<string, string>[] = XLSX.utils.sheet_to_json(ws, { defval: "" });
        resolve(rows.slice(0, 5));
      } catch {
        resolve([]);
      }
    };
    reader.readAsArrayBuffer(file);
  });
}

// ─── Component ──────────────────────────────────────────────────────────────

export function DataImportPanel({ schema, onImport, secondaryAction }: DataImportPanelProps) {
  const { empresaSelecionada } = useEmpresa();
  const empresaId = empresaSelecionada?.id ?? null;
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Array<Record<string, string>>>([]);
  const [importing, setImporting] = useState(false);
  const [erro, setErro] = useState("");

  const handleFile = useCallback(async (f: File) => {
    if (!f.name.match(/\.(xlsx|xls|csv)$/i)) {
      setErro("Formato inválido. Use .xlsx, .xls ou .csv.");
      return;
    }
    setErro("");
    setFile(f);
    const rows = await parsePreview(f);
    setPreview(rows);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const onInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const handleImport = async () => {
    if (!file || !empresaId) return;
    setImporting(true);
    setErro("");
    try {
      await onImport(file, empresaId);
      setFile(null);
      setPreview([]);
    } catch (e: unknown) {
      setErro(e instanceof Error ? e.message : "Erro ao importar. Tente novamente.");
    } finally {
      setImporting(false);
    }
  };

  const previewCols = preview.length > 0 ? Object.keys(preview[0]).slice(0, 6) : [];

  return (
    <div className="max-w-2xl mx-auto px-6 py-16 flex flex-col items-center gap-8">

      {/* Icon + title */}
      <div className="text-center">
        <div className="w-14 h-14 rounded-2xl bg-[#102a43] flex items-center justify-center mx-auto mb-4 shadow-md">
          <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">{schema.section}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-sm">{schema.description}</p>
      </div>

      {/* Action row */}
      <div className="flex flex-col sm:flex-row gap-3 w-full justify-center">
        <button
          onClick={() => gerarModeloXLSX(schema)}
          className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        >
          <svg className="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Baixar Planilha Modelo
        </button>
        {secondaryAction && (
          <button
            onClick={secondaryAction.onClick}
            className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold border border-[#102a43]/20 bg-[#102a43]/5 dark:bg-[#102a43]/20 text-[#102a43] dark:text-blue-300 hover:bg-[#102a43]/10 dark:hover:bg-[#102a43]/30 transition-colors"
          >
            {secondaryAction.label}
          </button>
        )}
      </div>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`
          w-full border-2 border-dashed rounded-2xl p-10 flex flex-col items-center gap-3 cursor-pointer transition-all
          ${drag
            ? "border-[#102a43] bg-[#102a43]/5 dark:bg-[#102a43]/10"
            : "border-slate-300 dark:border-slate-600 hover:border-[#102a43]/50 hover:bg-slate-50 dark:hover:bg-slate-800/40"
          }
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          className="hidden"
          onChange={onInputChange}
        />
        <svg className={`w-10 h-10 transition-colors ${drag ? "text-[#102a43]" : "text-slate-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
        </svg>
        <div className="text-center">
          <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            {file ? file.name : "Arraste o arquivo ou clique para selecionar"}
          </p>
          <p className="text-xs text-slate-400 mt-0.5">Formatos aceitos: .xlsx, .xls, .csv</p>
        </div>
        {file && (
          <span className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold">
            {(file.size / 1024).toFixed(1)} KB — pronto para importar
          </span>
        )}
      </div>

      {/* Preview */}
      {preview.length > 0 && previewCols.length > 0 && (
        <div className="w-full rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="px-4 py-2.5 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Pré-visualização — {preview.length} linha{preview.length !== 1 ? "s" : ""}
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/60">
                  {previewCols.map(col => (
                    <th key={col} className="px-3 py-2 text-left font-semibold text-slate-600 dark:text-slate-400 whitespace-nowrap border-r border-slate-100 dark:border-slate-700 last:border-r-0">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.map((row, i) => (
                  <tr key={i} className="border-t border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/30">
                    {previewCols.map(col => (
                      <td key={col} className="px-3 py-2 text-slate-700 dark:text-slate-300 whitespace-nowrap border-r border-slate-100 dark:border-slate-700 last:border-r-0 font-mono max-w-[160px] truncate">
                        {String(row[col] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Error */}
      {erro && (
        <div className="w-full px-4 py-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 text-sm text-red-700 dark:text-red-400">
          {erro}
        </div>
      )}

      {/* Import button */}
      {file && (
        <button
          onClick={handleImport}
          disabled={importing || !empresaId}
          className="w-full py-3 rounded-xl text-sm font-bold text-white bg-[#102a43] hover:bg-[#1e3a5f] disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
        >
          {importing ? "Importando..." : "Confirmar Importação"}
        </button>
      )}

      {!empresaId && (
        <p className="text-xs text-slate-400 text-center">
          Selecione uma empresa no menu superior antes de importar.
        </p>
      )}
    </div>
  );
}
