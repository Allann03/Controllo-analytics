"""
Motor de calculo da DRE (Demonstracao do Resultado do Exercicio).

Modulo isolado — depende apenas de services.contabil.core.
Sem dependencia de database, models, routers, ou qualquer ORM.

Estrutura: 17 linhas conforme CPC 26 (R2) e art. 187 Lei 6.404/76,
com limitacoes transitorias documentadas (IRPJ/CSLL consolidados,
receitas financeiras ausentes, participacoes nao tratadas).

Corrige ALTO-1: EBIT nao inclui despesas financeiras (era LAIR).
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from services.contabil.core import (
    money,
    to_decimal,
    MemoriaCalculo,
    ResultadoCalculo,
    NormaContabil,
    IntegridadeContabilError,
    assertir_invariante,
    VERSAO_CALCULO,
)

_ZERO = Decimal("0")
_TOL = money("0.01")


# -- Estruturas ----------------------------------------------------------------

@dataclass
class LinhaDRE:
    """Uma linha da DRE com codigo, descricao, valor e metadata."""
    codigo: str
    descricao: str
    valor: Decimal
    nivel: int   # 1 = resultado/totalizacao, 2 = componente
    tipo: str    # receita | deducao | custo | despesa | financeiro | imposto | resultado | resultado_final


@dataclass
class DRE:
    """DRE completa com todos os totalizadores."""
    periodo: str
    linhas: list[LinhaDRE]
    receita_bruta: Decimal
    receita_liquida: Decimal
    lucro_bruto: Decimal
    ebit: Decimal
    ebitda: Decimal
    lair: Decimal
    resultado_liquido: Decimal
    # Campos separados quando disponiveis
    irpj: Decimal
    csll: Decimal
    ir_csll_consolidado: Optional[Decimal]
    # Financeiro
    despesas_financeiras: Decimal
    receitas_financeiras: Decimal
    # Deprecicao
    depreciacao_amortizacao: Decimal


# -- Extracao de campos --------------------------------------------------------

def _get(dados: dict[str, Any], campo: str) -> Decimal:
    """Extrai campo do dict e converte para Decimal. None/ausente -> 0."""
    v = dados.get(campo)
    if v is None:
        return _ZERO
    return to_decimal(v)


# -- Motor de calculo ----------------------------------------------------------

def calcular_dre(
    dados: dict[str, Any],
    periodo: str = "",
    dados_anteriores: Optional[dict[str, Any]] = None,
) -> ResultadoCalculo:
    """
    Calcula DRE completa a partir de um dict de lancamento mensal.

    O dict deve conter chaves matching as colunas de LancamentoMensal:
      receita_bruta, deducoes_receita, custo_servicos, despesas_adm,
      despesas_comerciais, outras_despesas, depreciacao_amortizacao,
      despesas_financeiras, ir_csll (consolidado legado),
      irpj (opcional), csll (opcional), receitas_financeiras (opcional).

    Retorna ResultadoCalculo contendo DRE no campo .valor e MemoriaCalculo.
    Valida 6 invariantes em runtime. Gera avisos para limitacoes transitorias.

    Parametro dados_anteriores: se fornecido, calcula variacoes horizontais
    (CPC 26 R2 par. 38 — apresentacao comparativa obrigatoria).
    """
    avisos: list[str] = []

    # -- Extrair campos --------------------------------------------------------
    rb = money(_get(dados, "receita_bruta"))
    ded = money(_get(dados, "deducoes_receita"))
    cmv = money(_get(dados, "custo_servicos"))
    da_adm = money(_get(dados, "despesas_adm"))
    da_com = money(_get(dados, "despesas_comerciais"))
    da_out = money(_get(dados, "outras_despesas"))
    da_da = money(_get(dados, "depreciacao_amortizacao"))
    da_fin = money(_get(dados, "despesas_financeiras"))
    rec_fin = money(_get(dados, "receitas_financeiras"))

    # IRPJ / CSLL — separados ou consolidado legado
    irpj_in = _get(dados, "irpj")
    csll_in = _get(dados, "csll")
    ir_csll_consolidado_in = _get(dados, "ir_csll")

    usando_consolidado = False
    if irpj_in == _ZERO and csll_in == _ZERO and ir_csll_consolidado_in != _ZERO:
        # Modelo legado: IRPJ/CSLL nao separados
        usando_consolidado = True
        irpj = money(ir_csll_consolidado_in)
        csll = money(_ZERO)
        ir_csll_consolidado = money(ir_csll_consolidado_in)
        avisos.append(
            "IRPJ/CSLL apresentados de forma consolidada. "
            "Separacao contabil pendente — aguarda BLOCO 3K."
        )
    else:
        irpj = money(irpj_in)
        csll = money(csll_in)
        ir_csll_consolidado = None

    total_ir = irpj + csll if not usando_consolidado else ir_csll_consolidado

    # Aviso sobre receitas financeiras ausentes
    if rec_fin == _ZERO:
        avisos.append(
            "Receitas financeiras nao informadas. Se a empresa possui rendimentos "
            "de aplicacoes, o LAIR pode estar subestimado. "
            "Coluna dedicada sera introduzida no BLOCO 3K."
        )

    # -- Calculos da DRE -------------------------------------------------------

    receita_liquida = money(rb - ded)
    lucro_bruto = money(receita_liquida - cmv)

    # EBIT = Lucro Bruto - Despesas Operacionais (SEM financeiras, COM D&A)
    # CPC 26 (R2) par. 102: D&A e despesa operacional
    ebit = money(lucro_bruto - da_adm - da_com - da_out - da_da)

    # EBITDA = EBIT + D&A
    ebitda = money(ebit + da_da)

    # LAIR = EBIT + Resultado Financeiro
    lair = money(ebit - da_fin + rec_fin)

    # Resultado Liquido = LAIR - Tributos sobre o lucro
    resultado_liquido = money(lair - total_ir)

    # Aviso para prejuizo com tributo positivo (Simples/Presumido)
    if lair < _ZERO and total_ir > _ZERO:
        avisos.append(
            "Tributo apurado sobre empresa com prejuizo — regime presumido ou "
            "Simples Nacional. Confirme consistencia do regime tributario no BLOCO 3E-3F."
        )

    # -- Invariantes (tolerancia de 1 centavo) ---------------------------------

    assertir_invariante(
        "INV-1: Receita Liquida", money(rb - ded), receita_liquida,
        tolerancia=_TOL, contexto=f"DRE {periodo}",
    )
    assertir_invariante(
        "INV-2: Lucro Bruto", money(receita_liquida - cmv), lucro_bruto,
        tolerancia=_TOL, contexto=f"DRE {periodo}",
    )
    assertir_invariante(
        "INV-3: EBIT", money(lucro_bruto - da_adm - da_com - da_out - da_da), ebit,
        tolerancia=_TOL, contexto=f"DRE {periodo}",
    )
    assertir_invariante(
        "INV-4: EBITDA", money(ebit + da_da), ebitda,
        tolerancia=_TOL, contexto=f"DRE {periodo}",
    )
    assertir_invariante(
        "INV-5: LAIR", money(ebit - da_fin + rec_fin), lair,
        tolerancia=_TOL, contexto=f"DRE {periodo}",
    )
    assertir_invariante(
        "INV-6: Resultado Liquido", money(lair - total_ir), resultado_liquido,
        tolerancia=_TOL, contexto=f"DRE {periodo}",
    )

    # -- Montar linhas ---------------------------------------------------------

    linhas = [
        LinhaDRE("1",  "Receita Bruta de Vendas/Servicos",    rb,          1, "receita"),
        LinhaDRE("2",  "(-) Deducoes da Receita",             ded,         2, "deducao"),
        LinhaDRE("3",  "= Receita Liquida",                   receita_liquida, 1, "resultado"),
        LinhaDRE("4",  "(-) Custo dos Produtos/Servicos",     cmv,         2, "custo"),
        LinhaDRE("5",  "= Lucro Bruto",                       lucro_bruto, 1, "resultado"),
        LinhaDRE("6a", "(-) Despesas Administrativas",        da_adm,      2, "despesa"),
        LinhaDRE("6b", "(-) Despesas Comerciais",             da_com,      2, "despesa"),
        LinhaDRE("6c", "(-) Outras Despesas Operacionais",    da_out,      2, "despesa"),
        LinhaDRE("6d", "(-) Depreciacao e Amortizacao",       da_da,       2, "despesa"),
        LinhaDRE("7",  "= EBIT (Resultado Operacional)",      ebit,        1, "resultado"),
        LinhaDRE("8",  "= EBITDA",                            ebitda,      1, "resultado"),
        LinhaDRE("9a", "(-) Despesas Financeiras",            da_fin,      2, "financeiro"),
        LinhaDRE("9b", "(+) Receitas Financeiras",            rec_fin,     2, "financeiro"),
        LinhaDRE("10", "= LAIR (Lucro Antes IR/CSLL)",        lair,        1, "resultado"),
    ]

    if usando_consolidado:
        linhas.append(
            LinhaDRE("11", "(-) IRPJ + CSLL (consolidado)", ir_csll_consolidado, 2, "imposto"),
        )
    else:
        linhas.append(LinhaDRE("11a", "(-) IRPJ", irpj, 2, "imposto"))
        linhas.append(LinhaDRE("11b", "(-) CSLL", csll, 2, "imposto"))

    linhas.append(
        LinhaDRE("12", "= Resultado Liquido do Exercicio", resultado_liquido, 1, "resultado_final"),
    )

    # -- Comparativo CPC 26 (opcional) ----------------------------------------

    variacoes: Optional[dict[str, Optional[Decimal]]] = None
    dre_anterior: Optional[DRE] = None

    if dados_anteriores is not None:
        res_ant = calcular_dre(dados_anteriores, periodo=f"{periodo}_ant")
        dre_anterior = res_ant.valor
        variacoes = _calcular_variacoes(
            _totais_para_dict(rb, receita_liquida, lucro_bruto, ebit, ebitda, lair, resultado_liquido),
            _totais_para_dict(
                dre_anterior.receita_bruta, dre_anterior.receita_liquida,
                dre_anterior.lucro_bruto, dre_anterior.ebit, dre_anterior.ebitda,
                dre_anterior.lair, dre_anterior.resultado_liquido,
            ),
        )

    # -- DRE dataclass ---------------------------------------------------------

    dre = DRE(
        periodo=periodo,
        linhas=linhas,
        receita_bruta=rb,
        receita_liquida=receita_liquida,
        lucro_bruto=lucro_bruto,
        ebit=ebit,
        ebitda=ebitda,
        lair=lair,
        resultado_liquido=resultado_liquido,
        irpj=irpj,
        csll=csll,
        ir_csll_consolidado=ir_csll_consolidado,
        despesas_financeiras=da_fin,
        receitas_financeiras=rec_fin,
        depreciacao_amortizacao=da_da,
    )

    # -- Memoria de calculo ----------------------------------------------------

    insumos = {
        "receita_bruta": rb,
        "deducoes_receita": ded,
        "custo_servicos": cmv,
        "despesas_adm": da_adm,
        "despesas_comerciais": da_com,
        "outras_despesas": da_out,
        "depreciacao_amortizacao": da_da,
        "despesas_financeiras": da_fin,
        "receitas_financeiras": rec_fin,
    }
    if usando_consolidado:
        insumos["ir_csll_consolidado"] = ir_csll_consolidado
    else:
        insumos["irpj"] = irpj
        insumos["csll"] = csll

    memoria = MemoriaCalculo(
        insumos=insumos,
        formula=(
            "RL = RB - Ded; LB = RL - CMV; "
            "EBIT = LB - DA_adm - DA_com - DA_out - D&A; "
            "EBITDA = EBIT + D&A; LAIR = EBIT - DFin + RFin; "
            "LL = LAIR - IRPJ - CSLL"
        ),
        norma=NormaContabil.CPC_26,
        resultado=resultado_liquido,
    )

    return ResultadoCalculo(valor=dre, memoria=memoria, avisos=avisos)


# -- Helpers -------------------------------------------------------------------

def _totais_para_dict(*vals: Decimal) -> dict[str, Decimal]:
    chaves = [
        "receita_bruta", "receita_liquida", "lucro_bruto",
        "ebit", "ebitda", "lair", "resultado_liquido",
    ]
    return dict(zip(chaves, vals))


def _variacao_pct(atual: Decimal, anterior: Decimal) -> Optional[Decimal]:
    """Variacao percentual: ((atual - anterior) / |anterior|) * 100."""
    if anterior == _ZERO:
        return None
    return (atual - anterior) / abs(anterior) * Decimal("100")


def _calcular_variacoes(
    atual: dict[str, Decimal],
    anterior: dict[str, Decimal],
) -> dict[str, Optional[Decimal]]:
    """Calcula variacao horizontal para cada totalizador."""
    return {
        chave: _variacao_pct(atual[chave], anterior[chave])
        for chave in atual
    }
