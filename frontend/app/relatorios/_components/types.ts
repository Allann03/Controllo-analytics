export interface LancamentoMensal {
  receita_bruta: number;
  deducoes_receita: number;
  custo_servicos: number;
  despesas_adm: number;
  despesas_comerciais: number;
  despesas_financeiras: number;
  outras_despesas: number;
  ir_csll: number;
  entradas_caixa: number;
  saidas_caixa: number;
  saldo_inicial_caixa: number;
  caixa_equivalentes: number;
  contas_receber: number;
  estoques: number;
  outros_ativo_circ: number;
  ativo_nao_circulante: number;
  fornecedores: number;
  emprestimos_cp: number;
  tributos_pagar: number;
  outros_passivo_circ: number;
  passivo_nao_circulante: number;
  capital_social: number;
  reservas: number;
  lucros_acumulados: number;
  folha_pagamento: number;
  depreciacao_amortizacao: number;
  ano: number;
  mes: number;

  // indicadores derivados pelo backend (services/financeiro_service.py:_lanc_to_metricas)
  receita_liquida?: number | null;
  lucro_bruto?: number | null;
  ebit?: number | null;
  lair?: number | null;
  resultado_liquido?: number | null;
  lucro_liquido?: number | null;
  margem_bruta?: number | null;
  margem_liquida?: number | null;
  ebitda?: number | null;
}

export const MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
export const ANOS  = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i);

export const fmt = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v);

export const n = (v: unknown) => (typeof v === "number" ? v : 0);
