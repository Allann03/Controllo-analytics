export interface Empresa { id: number; nome: string; }

export interface CampoDestino { campo: string; label: string; obrigatorio: boolean; }

export interface HistoricoItem {
  id: number;
  nome_arquivo: string;
  tipo_dado: string;
  status: string;
  linhas_processadas: number;
  linhas_com_erro: number;
  criado_em: string;
}

export type Modo = "inicio" | "template" | "avancado";
export type Etapa = "upload" | "classificar" | "mapear" | "resultado";

export const TIPO_INFO: Record<string, { label: string; descricao: string }> = {
  faturamento: {
    label: "Faturamento",
    descricao: "Receitas, notas fiscais e vendas mensais.",
  },
  despesas: {
    label: "Despesas e Custos",
    descricao: "Custos operacionais, despesas administrativas e comerciais.",
  },
  impostos: {
    label: "Impostos e Tributos",
    descricao: "Guias de impostos pagos (IRPJ, CSLL, PIS, COFINS, ISS).",
  },
  folha: {
    label: "Folha de Pagamento",
    descricao: "Gastos com pessoal, encargos e benefícios.",
  },
  fluxo: {
    label: "Fluxo de Caixa",
    descricao: "Entradas, saídas e saldo de caixa por período.",
  },
  balanco: {
    label: "Balanço Patrimonial",
    descricao: "Ativo, passivo e patrimônio líquido mensais.",
  },
  dre: {
    label: "DRE Completa",
    descricao: "Demonstração de resultado com todos os componentes.",
  },
  generico: {
    label: "Dados Gerais",
    descricao: "Formato flexível para dados variados.",
  },
};
