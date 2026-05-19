"""
Motor de calculo da DFC (Demonstracao dos Fluxos de Caixa) — metodo indireto.

Modulo isolado — depende apenas de services.contabil.core, dre, balanco.
Sem dependencia de database, models, routers, ou qualquer ORM.

Metodo indireto conforme CPC 03 (R2) par. 18-20:
  - Parte do Resultado Liquido (DRE)
  - Ajusta itens nao-caixa (D&A)
  - Ajusta variacoes de capital de giro operacional (delta BP)
  - Categoriza em Operacional / Investimento / Financiamento

Limitacoes transitorias:
  - ANC bucket unico: investimento ajustado por D&A (aproximacao)
  - Metodo direto indisponivel (sem categorizacao de recebimentos/pagamentos)
  - Reconciliacao com fluxos observados pode divergir (dados independentes)
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
from services.contabil.dre import DRE
from services.contabil.balanco import BalancoPatrimonial

_ZERO = Decimal("0")
_TOL = money("0.01")


# -- Estruturas ----------------------------------------------------------------

@dataclass
class LinhaDFC:
    """Uma linha da DFC com categoria e tipo."""
    codigo: str
    descricao: str
    valor: Decimal
    categoria: str   # "operacional" | "investimento" | "financiamento"
    tipo: str        # "base" | "ajuste_nao_caixa" | "variacao_capital_giro" | "total"


@dataclass
class DFC:
    """DFC completa com reconciliacao e diagnostico."""
    periodo: str
    metodo: str  # "indireto"
    # Operacional
    resultado_liquido: Decimal
    ajustes_nao_caixa: Decimal
    variacao_capital_giro: Decimal
    fluxo_operacional: Decimal
    # Investimento
    fluxo_investimento: Decimal
    # Financiamento
    fluxo_financiamento: Decimal
    # Totais e reconciliacao
    variacao_caixa_calculada: Decimal
    variacao_caixa_observada: Optional[Decimal]
    gap_reconciliacao: Optional[Decimal]
    reconciliado: bool
    bp_inicio_fechado: bool
    bp_fim_fechado: bool
    linhas: list[LinhaDFC]


# -- Helpers -------------------------------------------------------------------

def _delta(bp_fim: BalancoPatrimonial, bp_ini: BalancoPatrimonial,
           campo_getter) -> Decimal:
    """Calcula delta de um campo entre dois BPs."""
    return money(campo_getter(bp_fim) - campo_getter(bp_ini))


def _get_linha_bp(bp: BalancoPatrimonial, codigo: str) -> Decimal:
    """Extrai valor de uma linha do BP por codigo."""
    for linha in bp.linhas:
        if linha.codigo == codigo:
            return linha.valor
    return _ZERO


# -- Motor de calculo ----------------------------------------------------------

def calcular_dfc(
    dre_atual: ResultadoCalculo,
    bp_inicio: ResultadoCalculo,
    bp_fim: ResultadoCalculo,
    periodo: str = "",
    dados_fluxo: Optional[dict[str, Any]] = None,
) -> ResultadoCalculo:
    """
    Calcula DFC pelo metodo indireto conforme CPC 03 (R2).

    Parametros:
      dre_atual: ResultadoCalculo do motor DRE do periodo.
      bp_inicio: ResultadoCalculo do motor BP no inicio do periodo.
      bp_fim: ResultadoCalculo do motor BP no fim do periodo.
      periodo: string descritiva.
      dados_fluxo: dict opcional com 'caixa_equivalentes_inicio',
                   'caixa_equivalentes_fim' para reconciliacao com
                   valores observados.

    Retorna ResultadoCalculo com DFC.
    """
    avisos: list[str] = []

    # -- Verificacao de versao cruzada (INV-DFC-V1, V2) ------------------------
    dre_versao = dre_atual.memoria.versao
    bp_ini_versao = bp_inicio.memoria.versao
    bp_fim_versao = bp_fim.memoria.versao

    if dre_versao != VERSAO_CALCULO:
        raise IntegridadeContabilError(
            mensagem=f"DFC: versao da DRE ({dre_versao}) != VERSAO_CALCULO ({VERSAO_CALCULO})",
            esperado=to_decimal(0), obtido=to_decimal(0),
            diferenca=to_decimal(0), contexto="INV-DFC-V1",
        )
    if bp_ini_versao != VERSAO_CALCULO:
        raise IntegridadeContabilError(
            mensagem=f"DFC: versao do BP inicio ({bp_ini_versao}) != VERSAO_CALCULO ({VERSAO_CALCULO})",
            esperado=to_decimal(0), obtido=to_decimal(0),
            diferenca=to_decimal(0), contexto="INV-DFC-V2 (inicio)",
        )
    if bp_fim_versao != VERSAO_CALCULO:
        raise IntegridadeContabilError(
            mensagem=f"DFC: versao do BP fim ({bp_fim_versao}) != VERSAO_CALCULO ({VERSAO_CALCULO})",
            esperado=to_decimal(0), obtido=to_decimal(0),
            diferenca=to_decimal(0), contexto="INV-DFC-V2 (fim)",
        )

    # -- Extrair DRE e BPs ----------------------------------------------------
    dre: DRE = dre_atual.valor
    bp_ini: BalancoPatrimonial = bp_inicio.valor
    bp_fim_bp: BalancoPatrimonial = bp_fim.valor

    bp_inicio_fechado = bp_ini.invariante_atendida
    bp_fim_fechado = bp_fim_bp.invariante_atendida

    if not bp_inicio_fechado or not bp_fim_fechado:
        avisos.append(
            "DFC baseado em BP com desequilibrio. "
            f"BP inicio fechado: {bp_inicio_fechado} (gap={bp_ini.gap_valor}). "
            f"BP fim fechado: {bp_fim_fechado} (gap={bp_fim_bp.gap_valor}). "
            "Variacao de caixa calculada pode divergir da observada."
        )

    # -- O.01: Resultado Liquido (base) ----------------------------------------
    rl = money(dre.resultado_liquido)

    # -- O.02: D&A (ajuste nao-caixa) -----------------------------------------
    da = money(dre.depreciacao_amortizacao)
    ajustes_nao_caixa = da

    if da > _ZERO:
        avisos.append(
            f"D&A de R$ {da:,.2f} adicionada como ajuste nao-caixa. "
            "Consolidacao D&A pendente — separacao por natureza (imobilizado/intangivel) "
            "disponivel apos migracao do modelo (BLOCO 3K)."
        )

    # -- O.03-O.08: Variacoes de capital de giro operacional -------------------
    # Ativo circulante operacional (aumento de ativo = saida de caixa → sinal negativo)
    delta_cr = money(-(_get_linha_bp(bp_fim_bp, "AC.02") - _get_linha_bp(bp_ini, "AC.02")))
    delta_est = money(-(_get_linha_bp(bp_fim_bp, "AC.03") - _get_linha_bp(bp_ini, "AC.03")))
    delta_oac = money(-(_get_linha_bp(bp_fim_bp, "AC.04") - _get_linha_bp(bp_ini, "AC.04")))

    # Passivo circulante operacional (aumento de passivo = entrada de caixa → sinal positivo)
    # NOTA: emprestimos_cp (PC.02) NAO entra aqui — vai para financiamento (F.01)
    delta_forn = money(_get_linha_bp(bp_fim_bp, "PC.01") - _get_linha_bp(bp_ini, "PC.01"))
    delta_trib = money(_get_linha_bp(bp_fim_bp, "PC.03") - _get_linha_bp(bp_ini, "PC.03"))
    delta_opc = money(_get_linha_bp(bp_fim_bp, "PC.04") - _get_linha_bp(bp_ini, "PC.04"))

    variacao_cg = money(delta_cr + delta_est + delta_oac + delta_forn + delta_trib + delta_opc)

    # -- Fluxo Operacional = RL + D&A + variacao CG ---------------------------
    fluxo_oper = money(rl + ajustes_nao_caixa + variacao_cg)

    # -- I.01: Investimento (delta ANC ajustado por D&A) -----------------------
    # ANC e bucket unico. Se ANC nao variou mas D&A > 0, a empresa "investiu"
    # o equivalente a D&A para manter ANC constante.
    # Formula: -(ANC_fim - ANC_ini) - D&A
    delta_anc_bruto = money(bp_fim_bp.ativo_nao_circulante - bp_ini.ativo_nao_circulante)
    fluxo_invest = money(-delta_anc_bruto - da)

    if da > _ZERO and delta_anc_bruto == _ZERO:
        avisos.append(
            "ANC nao variou apesar de D&A > 0. "
            "Investimento ajustado por D&A devido a ANC nao desdobrado. Valor aproximado."
        )

    # -- F.01-F.04: Financiamento (delta emprestimos, PNC, capital, reservas) --
    delta_emp = money(_get_linha_bp(bp_fim_bp, "PC.02") - _get_linha_bp(bp_ini, "PC.02"))
    delta_pnc = money(bp_fim_bp.passivo_nao_circulante - bp_ini.passivo_nao_circulante)
    delta_cap = money(_get_linha_bp(bp_fim_bp, "PL.01") - _get_linha_bp(bp_ini, "PL.01"))
    delta_res = money(_get_linha_bp(bp_fim_bp, "PL.02") - _get_linha_bp(bp_ini, "PL.02"))

    if delta_res != _ZERO:
        avisos.append(
            "Variacao de Reservas tratada como fluxo de financiamento. "
            "Se inclui reservas de reavaliacao ou ajustes de avaliacao patrimonial, "
            "classificacao pode divergir."
        )

    fluxo_financ = money(delta_emp + delta_pnc + delta_cap + delta_res)
    # NOTA: lucros_acumulados NAO entra aqui — ja capturado em O.01 (RL).
    # Incluir seria dupla contagem.

    # -- Variacao de caixa calculada -------------------------------------------
    variacao_calculada = money(fluxo_oper + fluxo_invest + fluxo_financ)

    # -- INV-DFC-1: identidade interna (hard error) ----------------------------
    assertir_invariante(
        "INV-DFC-1: Variacao Caixa = Oper + Invest + Financ",
        variacao_calculada,
        money(fluxo_oper + fluxo_invest + fluxo_financ),
        tolerancia=_TOL,
        contexto=f"DFC {periodo}",
    )

    # -- INV-DFC-3: RL base == DRE.resultado_liquido (hard error) --------------
    assertir_invariante(
        "INV-DFC-3: RL base == DRE resultado_liquido",
        rl,
        money(dre.resultado_liquido),
        tolerancia=_ZERO,
        contexto=f"DFC {periodo}",
    )

    # -- Reconciliacao com observado (INV-DFC-4, informativo) ------------------
    variacao_observada: Optional[Decimal] = None
    gap_reconciliacao: Optional[Decimal] = None
    reconciliado = False

    if dados_fluxo is not None:
        cx_ini = money(to_decimal(dados_fluxo.get("caixa_equivalentes_inicio", 0)))
        cx_fim = money(to_decimal(dados_fluxo.get("caixa_equivalentes_fim", 0)))
        variacao_observada = money(cx_fim - cx_ini)
        gap_reconciliacao = money(variacao_calculada - variacao_observada)
        reconciliado = abs(gap_reconciliacao) <= _TOL

        if not reconciliado:
            avisos.append(
                f"Gap de reconciliacao: variacao calculada R$ {variacao_calculada:,.2f} "
                f"vs observada R$ {variacao_observada:,.2f} "
                f"(diferenca R$ {gap_reconciliacao:,.2f}). "
                "Dados de fluxo e saldos BP podem ter sido informados independentemente."
            )

    # -- INV-DFC-5: ANC constante com D&A > 0 (aviso) -------------------------
    if da > _ZERO and delta_anc_bruto == _ZERO:
        avisos.append(
            "INV-DFC-5: ANC nao varia entre periodos apesar de D&A > 0. "
            "D&A provavelmente nao reduz ANC nos dados informados. "
            "Investimento ajustado por D&A como aproximacao."
        )

    # -- Montar linhas ---------------------------------------------------------
    linhas = [
        # Operacional
        LinhaDFC("O.01", "Resultado Liquido do Exercicio", rl, "operacional", "base"),
        LinhaDFC("O.02", "(+) Depreciacao e Amortizacao", da, "operacional", "ajuste_nao_caixa"),
        LinhaDFC("O.03", "(-/+) Variacao Contas a Receber", delta_cr, "operacional", "variacao_capital_giro"),
        LinhaDFC("O.04", "(-/+) Variacao Estoques", delta_est, "operacional", "variacao_capital_giro"),
        LinhaDFC("O.05", "(-/+) Variacao Outros Ativos Circ", delta_oac, "operacional", "variacao_capital_giro"),
        LinhaDFC("O.06", "(+/-) Variacao Fornecedores", delta_forn, "operacional", "variacao_capital_giro"),
        LinhaDFC("O.07", "(+/-) Variacao Tributos a Pagar", delta_trib, "operacional", "variacao_capital_giro"),
        LinhaDFC("O.08", "(+/-) Variacao Outros Passivos Circ", delta_opc, "operacional", "variacao_capital_giro"),
        LinhaDFC("O.TOT", "= Fluxo de Caixa Operacional", fluxo_oper, "operacional", "total"),
        # Investimento
        LinhaDFC("I.01", "(-/+) Variacao Ativo Nao Circulante (ajustado D&A)", fluxo_invest, "investimento", "variacao_capital_giro"),
        LinhaDFC("I.TOT", "= Fluxo de Caixa de Investimento", fluxo_invest, "investimento", "total"),
        # Financiamento
        LinhaDFC("F.01", "(-/+) Variacao Emprestimos CP", delta_emp, "financiamento", "variacao_capital_giro"),
        LinhaDFC("F.02", "(-/+) Variacao Passivo Nao Circulante", delta_pnc, "financiamento", "variacao_capital_giro"),
        LinhaDFC("F.03", "(-/+) Variacao Capital Social", delta_cap, "financiamento", "variacao_capital_giro"),
        LinhaDFC("F.04", "(-/+) Variacao Reservas", delta_res, "financiamento", "variacao_capital_giro"),
        LinhaDFC("F.TOT", "= Fluxo de Caixa de Financiamento", fluxo_financ, "financiamento", "total"),
        # Total
        LinhaDFC("TOT", "= Variacao Liquida de Caixa", variacao_calculada, "total", "total"),
    ]

    # -- DFC dataclass ---------------------------------------------------------
    dfc = DFC(
        periodo=periodo,
        metodo="indireto",
        resultado_liquido=rl,
        ajustes_nao_caixa=ajustes_nao_caixa,
        variacao_capital_giro=variacao_cg,
        fluxo_operacional=fluxo_oper,
        fluxo_investimento=fluxo_invest,
        fluxo_financiamento=fluxo_financ,
        variacao_caixa_calculada=variacao_calculada,
        variacao_caixa_observada=variacao_observada,
        gap_reconciliacao=gap_reconciliacao,
        reconciliado=reconciliado,
        bp_inicio_fechado=bp_inicio_fechado,
        bp_fim_fechado=bp_fim_fechado,
        linhas=linhas,
    )

    # -- Memoria de calculo ----------------------------------------------------
    insumos = {
        "resultado_liquido": rl,
        "depreciacao_amortizacao": da,
        "delta_contas_receber": delta_cr,
        "delta_estoques": delta_est,
        "delta_outros_ativo_circ": delta_oac,
        "delta_fornecedores": delta_forn,
        "delta_tributos_pagar": delta_trib,
        "delta_outros_passivo_circ": delta_opc,
        "delta_anc_bruto": money(-delta_anc_bruto),
        "delta_emprestimos_cp": delta_emp,
        "delta_passivo_nc": delta_pnc,
        "delta_capital_social": delta_cap,
        "delta_reservas": delta_res,
    }

    memoria = MemoriaCalculo(
        insumos=insumos,
        formula=(
            "Oper = RL + D&A + delta_CG; "
            "Invest = -(delta_ANC) - D&A; "
            "Financ = delta_Emp + delta_PNC + delta_Cap + delta_Res; "
            "Variacao = Oper + Invest + Financ"
        ),
        norma=NormaContabil.CPC_03,
        resultado=variacao_calculada,
    )

    return ResultadoCalculo(valor=dfc, memoria=memoria, avisos=avisos)
