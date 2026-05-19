"use client";

import { LancamentoMensal, MESES, fmt, n } from "./types";

interface Props {
  dados: LancamentoMensal;
  empresaNome: string;
  empresaCnpj: string;
  mes: number;
  ano: number;
}

function LinhaRelatorio({
  label,
  valor,
  destaque = false,
}: {
  label: string;
  valor: number;
  destaque?: boolean;
}) {
  return (
    <div
      className={`flex items-end py-1.5 gap-2 ${
        destaque
          ? "border-b-2 border-slate-300 print:border-slate-700 mb-0.5"
          : "border-b border-dotted border-slate-200 print:border-gray-200"
      } last:border-0`}
    >
      <span
        className={`text-sm flex-1 font-sans ${
          destaque
            ? "font-semibold text-slate-900 dark:text-slate-100 print:text-black"
            : "text-slate-600 dark:text-slate-400 print:text-gray-600"
        }`}
      >
        {label}
      </span>
      <span
        className={`text-sm font-mono tabular-nums text-right flex-shrink-0 ${
          destaque
            ? "font-bold text-slate-900 dark:text-slate-100 print:text-black"
            : "text-slate-700 dark:text-slate-300 print:text-gray-800"
        } ${valor < 0 ? "text-red-600 dark:text-red-400 print:text-red-700" : ""}`}
      >
        {fmt(valor)}
      </span>
    </div>
  );
}

export default function RelatorioView({ dados: d, empresaNome, empresaCnpj, mes, ano }: Props) {
  // PROIBIDO recalcular indicadores financeiros no frontend.
  // Consuma do JSON do backend. Violacoes serao tratadas como bug.
  // Referencia: BLOCO 3B.2, mandato R3, correcao do ALTO-1.
  const rl     = n(d.receita_liquida);
  const lb     = n(d.lucro_bruto);
  const ebit   = n(d.ebit);
  const lair   = n(d.lair ?? d.ebit);
  const ll     = n(d.resultado_liquido ?? d.lucro_liquido);
  const saldoFC = n(d.saldo_inicial_caixa) + n(d.entradas_caixa) - n(d.saidas_caixa);
  const atCirc  = n(d.caixa_equivalentes) + n(d.contas_receber) + n(d.estoques) + n(d.outros_ativo_circ);
  const atTotal = atCirc + n(d.ativo_nao_circulante);
  const paCirc  = n(d.fornecedores) + n(d.emprestimos_cp) + n(d.tributos_pagar) + n(d.outros_passivo_circ);
  const paTotal = paCirc + n(d.passivo_nao_circulante);
  const pl      = n(d.capital_social) + n(d.reservas) + n(d.lucros_acumulados);
  const margemBruta   = n(d.margem_bruta);
  const margemLiquida = n(d.margem_liquida);

  return (
    <div className="bg-white dark:bg-slate-800/80 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-lg dark:shadow-2xl overflow-hidden print:shadow-none print:border-0 print:bg-white">
      <div className="p-8 space-y-6">
      {/* Cabeçalho */}
      <div className="text-center pb-5 border-b-2 border-slate-200 dark:border-slate-700 print:border-gray-400">
        {/* Logo placeholder */}
        <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
          <svg className="w-6 h-6 text-slate-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
        </div>
        <h2 className="text-xl font-black text-slate-900 dark:text-slate-100 print:text-black">RELATÓRIO FINANCEIRO GERENCIAL</h2>
        <p className="text-slate-500 dark:text-slate-400 print:text-gray-600 mt-1">
          {empresaNome} {empresaCnpj ? `· ${empresaCnpj}` : ""}
        </p>
        <p className="text-slate-400 dark:text-slate-500 print:text-gray-500 text-sm">
          {MESES[mes - 1]}/{ano}
        </p>
        <p className="text-[10px] text-slate-300 dark:text-slate-600 print:text-gray-400 mt-1">
          Gerado em {new Date().toLocaleDateString("pt-BR")} às {new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>

      {/* Métricas chave */}
      <div className="grid grid-cols-3 gap-4 print-section">
        {[
          { label: "Receita Líquida", valor: rl,      cor: "text-[#1E4976] dark:text-blue-400 print:text-blue-700" },
          { label: "Lucro Líquido",   valor: ll,      cor: ll >= 0 ? "text-emerald-700 dark:text-emerald-400 print:text-green-700" : "text-rose-700 dark:text-rose-400 print:text-red-700" },
          { label: "Saldo de Caixa",  valor: saldoFC, cor: saldoFC >= 0 ? "text-emerald-700 dark:text-emerald-400 print:text-green-700" : "text-rose-700 dark:text-rose-400 print:text-red-700" },
        ].map(({ label, valor, cor }) => (
          <div key={label} className="bg-white dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-2xl p-4 text-center print:border-gray-300 print:bg-white">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 print:text-gray-500 uppercase tracking-widest">{label}</p>
            <p className={`text-2xl font-black font-mono mt-1 ${cor}`}>{fmt(valor)}</p>
          </div>
        ))}
      </div>

      {/* Grid de relatórios */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* DRE */}
        <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 overflow-hidden print:border-gray-300 print-section">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 print:text-gray-600 bg-slate-50 dark:bg-slate-800/60 -mx-5 px-5 py-2 mb-4 print:bg-gray-100">
            Demonstração de Resultado
          </p>
          <LinhaRelatorio label="Receita Bruta"          valor={n(d.receita_bruta)} />
          <LinhaRelatorio label="(–) Deduções da Receita" valor={-n(d.deducoes_receita)} />
          <LinhaRelatorio label="= Receita Líquida"       valor={rl}   destaque />
          <LinhaRelatorio label="(–) Custo dos Serviços"  valor={-n(d.custo_servicos)} />
          <LinhaRelatorio label="= Lucro Bruto"           valor={lb}   destaque />
          <LinhaRelatorio label="(–) Desp. Administrativas" valor={-n(d.despesas_adm)} />
          <LinhaRelatorio label="(–) Desp. Comerciais"    valor={-n(d.despesas_comerciais)} />
          <LinhaRelatorio label="(–) Outras Despesas"     valor={-n(d.outras_despesas)} />
          <LinhaRelatorio label="(–) Deprec./Amortiz."    valor={-n(d.depreciacao_amortizacao)} />
          <LinhaRelatorio label="= EBIT"                  valor={ebit} destaque />
          <LinhaRelatorio label="(–) Desp. Financeiras"   valor={-n(d.despesas_financeiras)} />
          <LinhaRelatorio label="= LAIR"                  valor={lair} destaque />
          <LinhaRelatorio label="(–) IR + CSLL"           valor={-n(d.ir_csll)} />
          <LinhaRelatorio label="= Resultado Líquido"     valor={ll}   destaque />
          <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700/30 flex justify-between text-xs text-slate-500 print:text-gray-500">
            <span>Margem Bruta: <span className="font-mono font-bold">{margemBruta.toFixed(1)}%</span></span>
            <span>Margem Líquida: <span className="font-mono font-bold">{margemLiquida.toFixed(1)}%</span></span>
          </div>
        </div>

        {/* Fluxo de Caixa */}
        <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 overflow-hidden print:border-gray-300 print-section">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 print:text-gray-600 bg-slate-50 dark:bg-slate-800/60 -mx-5 px-5 py-2 mb-4 print:bg-gray-100">
            Fluxo de Caixa
          </p>
          <LinhaRelatorio label="Saldo Inicial"  valor={n(d.saldo_inicial_caixa)} />
          <LinhaRelatorio label="(+) Entradas"   valor={n(d.entradas_caixa)} />
          <LinhaRelatorio label="(–) Saídas"     valor={-n(d.saidas_caixa)} />
          <LinhaRelatorio label="= Saldo Final"  valor={saldoFC} destaque />
        </div>

        {/* Balanço Patrimonial */}
        <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 overflow-hidden print:border-gray-300 print-section">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 print:text-gray-600 bg-slate-50 dark:bg-slate-800/60 -mx-5 px-5 py-2 mb-4 print:bg-gray-100">
            Balanço Patrimonial
          </p>
          <p className="text-xs font-semibold text-slate-500 mb-2 uppercase">Ativo</p>
          <LinhaRelatorio label="Caixa e Equivalentes" valor={n(d.caixa_equivalentes)} />
          <LinhaRelatorio label="Contas a Receber"      valor={n(d.contas_receber)} />
          <LinhaRelatorio label="Estoques"              valor={n(d.estoques)} />
          <LinhaRelatorio label="Outros Ativo Circ."    valor={n(d.outros_ativo_circ)} />
          <LinhaRelatorio label="Ativo Circulante"      valor={atCirc}   destaque />
          <LinhaRelatorio label="Ativo Não Circulante"  valor={n(d.ativo_nao_circulante)} />
          <LinhaRelatorio label="ATIVO TOTAL"           valor={atTotal}  destaque />
          <p className="text-xs font-semibold text-slate-500 mt-3 mb-2 uppercase">Passivo + PL</p>
          <LinhaRelatorio label="Passivo Circulante"    valor={paCirc}   destaque />
          <LinhaRelatorio label="Passivo Não Circ."     valor={n(d.passivo_nao_circulante)} />
          <LinhaRelatorio label="Patrimônio Líquido"    valor={pl}       destaque />
          <LinhaRelatorio label="PASSIVO + PL"          valor={paTotal + pl} destaque />
        </div>

        {/* RH */}
        <div className="bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 overflow-hidden print:border-gray-300 print-section">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 print:text-gray-600 bg-slate-50 dark:bg-slate-800/60 -mx-5 px-5 py-2 mb-4 print:bg-gray-100">
            Recursos Humanos &amp; EBITDA
          </p>
          <LinhaRelatorio label="Folha de Pagamento"        valor={n(d.folha_pagamento)} />
          <LinhaRelatorio label="Depreciação / Amortização" valor={n(d.depreciacao_amortizacao)} />
          <LinhaRelatorio label="EBITDA"                    valor={n(d.ebitda ?? (ebit + n(d.depreciacao_amortizacao)))} destaque />
        </div>
      </div>
      </div>
    </div>
  );
}
