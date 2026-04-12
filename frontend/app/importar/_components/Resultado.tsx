"use client";

interface Props {
  resultado: Record<string, unknown>;
  reiniciar: () => void;
}

export default function Resultado({ resultado, reiniciar }: Props) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center gap-3 py-6">
        <div className="w-14 h-14 rounded-full bg-emerald-500/15 border border-emerald-500/20 flex items-center justify-center">
          <svg className="w-7 h-7 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold">Importação Concluída</h2>
        <p className="text-slate-400 text-sm">Os painéis financeiros já refletem os novos dados.</p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="bg-emerald-950/40 border border-emerald-500/20 rounded-xl p-4 text-center">
          <p className="text-2xl font-mono font-bold text-emerald-400">{String(resultado.linhas_ok ?? 0)}</p>
          <p className="text-xs text-emerald-600 mt-1 font-medium">Linhas importadas</p>
        </div>
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 text-center">
          <p className="text-2xl font-mono font-bold text-slate-300">
            {Array.isArray(resultado.meses_atualizados) ? (resultado.meses_atualizados as unknown[]).length : 0}
          </p>
          <p className="text-xs text-slate-500 mt-1 font-medium">Períodos atualizados</p>
        </div>
        <div className={`border rounded-xl p-4 text-center ${Number(resultado.linhas_erro ?? 0) > 0 ? "bg-red-950/40 border-red-500/20" : "bg-slate-800/50 border-slate-700"}`}>
          <p className={`text-2xl font-mono font-bold ${Number(resultado.linhas_erro ?? 0) > 0 ? "text-red-400" : "text-slate-400"}`}>
            {String(resultado.linhas_erro ?? 0)}
          </p>
          <p className="text-xs text-slate-500 mt-1 font-medium">Erros</p>
        </div>
      </div>

      {Array.isArray(resultado.erros) && (resultado.erros as string[]).length > 0 && (
        <div className="bg-red-950/20 border border-red-500/20 rounded-xl p-4 space-y-1">
          <p className="text-xs font-bold text-red-400 uppercase tracking-wider mb-2">Linhas com erro</p>
          {(resultado.erros as string[]).map((err, i) => <p key={i} className="text-xs text-red-300/80">{err}</p>)}
        </div>
      )}

      <div className="flex gap-3">
        <button onClick={reiniciar}
          className="flex-1 py-3 rounded-xl font-semibold text-sm border border-slate-700 text-slate-400 hover:bg-slate-800 transition-colors">
          Nova importação
        </button>
        <a href="/dashboard-geral"
          className="flex-1 py-3 rounded-xl font-semibold text-sm bg-[#2D2B4B] text-white hover:bg-[#3D3A63] transition-colors text-center">
          Ver Dashboard
        </a>
      </div>
    </div>
  );
}
