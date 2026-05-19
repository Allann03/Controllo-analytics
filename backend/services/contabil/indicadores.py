"""
Indicadores FP&A canonicos — 22 indicadores financeiros.

Funcoes puras tipadas com Decimal. Cada uma retorna ResultadoIndicador
com valor, formula, referencia bibliografica e motivo de indisponibilidade.

Secoes: Liquidez, Rentabilidade, Atividade/Ciclo, Estrutura de Capital, Fleuriet.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from services.contabil.core import money, rate, to_decimal

_ZERO = Decimal("0")
_360 = Decimal("360")


@dataclass
class ResultadoIndicador:
    valor: Optional[Decimal]
    indisponivel_motivo: Optional[str]
    formula: str
    referencia: str


def _ratio(num: Decimal, den: Decimal, formula: str, ref: str,
           motivo_zero: str = "Denominador zero") -> ResultadoIndicador:
    if den == _ZERO:
        return ResultadoIndicador(None, motivo_zero, formula, ref)
    return ResultadoIndicador(money(num / den), None, formula, ref)


def _pct_ratio(num: Decimal, den: Decimal, formula: str, ref: str,
               motivo_zero: str = "Denominador zero") -> ResultadoIndicador:
    if den == _ZERO:
        return ResultadoIndicador(None, motivo_zero, formula, ref)
    return ResultadoIndicador(rate(num / den * Decimal("100")), None, formula, ref)


def _dias(num: Decimal, den: Decimal, formula: str, ref: str) -> ResultadoIndicador:
    if den == _ZERO:
        return ResultadoIndicador(None, "Denominador zero", formula, ref)
    return ResultadoIndicador(money(num / den * _360), None, formula, ref)


# ── LIQUIDEZ ─────────────────────────────────────────────────────────

def liquidez_corrente(ac: Decimal, pc: Decimal) -> ResultadoIndicador:
    """LC = Ativo Circulante / Passivo Circulante. Gitman, 2017 cap. 3."""
    return _ratio(ac, pc, "AC / PC", "Gitman (2017) cap. 3", "Passivo Circulante zero")


def liquidez_seca(ac: Decimal, estoques: Decimal, pc: Decimal) -> ResultadoIndicador:
    """LS = (AC - Estoques) / PC. Gitman, 2017 cap. 3."""
    return _ratio(ac - estoques, pc, "(AC - Estoques) / PC", "Gitman (2017) cap. 3", "PC zero")


def liquidez_imediata(disponibilidades: Decimal, pc: Decimal) -> ResultadoIndicador:
    """LI = Disponibilidades / PC. Assaf Neto (2020) cap. 6."""
    return _ratio(disponibilidades, pc, "Disponibilidades / PC",
                  "Assaf Neto (2020) cap. 6", "PC zero")


def liquidez_geral(ac: Decimal, arlp: Decimal, pc: Decimal, pnc: Decimal) -> ResultadoIndicador:
    """LG = (AC + ARLP) / (PC + PNC). Assaf Neto (2020) cap. 6."""
    den = pc + pnc
    return _ratio(ac + arlp, den, "(AC + ARLP) / (PC + PNC)",
                  "Assaf Neto (2020) cap. 6", "Passivo total zero")


# ── RENTABILIDADE ────────────────────────────────────────────────────

def margem_bruta(lucro_bruto: Decimal, receita_liquida: Decimal) -> ResultadoIndicador:
    """MB = LB / RL × 100. Damodaran (2012) cap. 3."""
    return _pct_ratio(lucro_bruto, receita_liquida, "LB / RL x 100",
                      "Damodaran (2012) cap. 3", "Receita Liquida zero")


def margem_ebit(ebit: Decimal, receita_liquida: Decimal) -> ResultadoIndicador:
    """M.EBIT = EBIT / RL × 100. Damodaran (2012) cap. 3."""
    return _pct_ratio(ebit, receita_liquida, "EBIT / RL x 100",
                      "Damodaran (2012) cap. 3", "RL zero")


def margem_ebitda(ebitda: Decimal, receita_liquida: Decimal) -> ResultadoIndicador:
    """M.EBITDA = EBITDA / RL × 100. Damodaran (2012) cap. 3."""
    return _pct_ratio(ebitda, receita_liquida, "EBITDA / RL x 100",
                      "Damodaran (2012) cap. 3", "RL zero")


def margem_liquida(resultado_liquido: Decimal, receita_liquida: Decimal) -> ResultadoIndicador:
    """ML = RL(resultado) / RL(receita) × 100. Gitman (2017) cap. 3."""
    return _pct_ratio(resultado_liquido, receita_liquida, "Resultado Liq / Receita Liq x 100",
                      "Gitman (2017) cap. 3", "RL zero")


def roe(resultado_liquido: Decimal, patrimonio_liquido: Decimal) -> ResultadoIndicador:
    """ROE = RL / PL × 100. DuPont. Gitman (2017) cap. 3."""
    return _pct_ratio(resultado_liquido, patrimonio_liquido, "RL / PL x 100",
                      "Gitman (2017) cap. 3 — DuPont", "PL zero")


def roa(resultado_liquido: Decimal, ativo_total: Decimal) -> ResultadoIndicador:
    """ROA = RL / AT × 100. Gitman (2017) cap. 3."""
    return _pct_ratio(resultado_liquido, ativo_total, "RL / AT x 100",
                      "Gitman (2017) cap. 3", "AT zero")


def roic(ebit: Decimal, ir_sobre_ebit: Decimal,
         patrimonio_liquido: Decimal, divida_onerosa: Decimal) -> ResultadoIndicador:
    """ROIC = NOPAT / Capital Investido × 100. Damodaran (2012) cap. 4.
    NOPAT = EBIT × (1 - t). Capital Investido = PL + Divida Onerosa."""
    nopat = ebit - ir_sobre_ebit
    capital = patrimonio_liquido + divida_onerosa
    return _pct_ratio(nopat, capital, "NOPAT / (PL + Divida) x 100",
                      "Damodaran (2012) cap. 4", "Capital investido zero")


def giro_ativo(receita_liquida: Decimal, ativo_total: Decimal) -> ResultadoIndicador:
    """GA = RL / AT. Gitman (2017) cap. 3."""
    return _ratio(receita_liquida, ativo_total, "RL / AT",
                  "Gitman (2017) cap. 3", "AT zero")


# ── ATIVIDADE / CICLO ────────────────────────────────────────────────

def pmr(contas_receber: Decimal, receita_bruta: Decimal) -> ResultadoIndicador:
    """PMR = (CR / RB) × 360. Assaf Neto (2020) cap. 7."""
    return _dias(contas_receber, receita_bruta, "(CR / RB) x 360",
                 "Assaf Neto (2020) cap. 7")


def pme(estoques: Decimal, custo_mercadorias: Decimal) -> ResultadoIndicador:
    """PME = (Estoques / CMV) × 360. Assaf Neto (2020) cap. 7."""
    return _dias(estoques, custo_mercadorias, "(Estoques / CMV) x 360",
                 "Assaf Neto (2020) cap. 7")


def pmp(fornecedores: Decimal, compras: Decimal) -> ResultadoIndicador:
    """PMP = (Fornecedores / Compras) × 360. Assaf Neto (2020) cap. 7."""
    return _dias(fornecedores, compras, "(Fornecedores / Compras) x 360",
                 "Assaf Neto (2020) cap. 7")


def ciclo_operacional(pmr_val: Optional[Decimal], pme_val: Optional[Decimal]) -> ResultadoIndicador:
    """CO = PMR + PME. Assaf Neto (2020) cap. 7."""
    if pmr_val is None or pme_val is None:
        return ResultadoIndicador(None, "PMR ou PME indisponivel", "PMR + PME",
                                  "Assaf Neto (2020) cap. 7")
    return ResultadoIndicador(money(pmr_val + pme_val), None, "PMR + PME",
                              "Assaf Neto (2020) cap. 7")


def ciclo_financeiro(pmr_val: Optional[Decimal], pme_val: Optional[Decimal],
                     pmp_val: Optional[Decimal]) -> ResultadoIndicador:
    """CF = PMR + PME - PMP. Assaf Neto (2020) cap. 7."""
    if pmr_val is None or pme_val is None or pmp_val is None:
        return ResultadoIndicador(None, "PMR, PME ou PMP indisponivel",
                                  "PMR + PME - PMP", "Assaf Neto (2020) cap. 7")
    return ResultadoIndicador(money(pmr_val + pme_val - pmp_val), None,
                              "PMR + PME - PMP", "Assaf Neto (2020) cap. 7")


# ── ESTRUTURA DE CAPITAL ─────────────────────────────────────────────

def endividamento_geral(passivo_total: Decimal, ativo_total: Decimal) -> ResultadoIndicador:
    """EG = PT / AT × 100. Gitman (2017) cap. 3."""
    return _pct_ratio(passivo_total, ativo_total, "PT / AT x 100",
                      "Gitman (2017) cap. 3", "AT zero")


def composicao_endividamento(pc: Decimal, passivo_total: Decimal) -> ResultadoIndicador:
    """CE = PC / PT × 100. Assaf Neto (2020) cap. 6."""
    return _pct_ratio(pc, passivo_total, "PC / PT x 100",
                      "Assaf Neto (2020) cap. 6", "PT zero")


def grau_alavancagem(ativo_total: Decimal, patrimonio_liquido: Decimal) -> ResultadoIndicador:
    """GAF = AT / PL. Gitman (2017) cap. 3 — Multiplicador DuPont."""
    return _ratio(ativo_total, patrimonio_liquido, "AT / PL",
                  "Gitman (2017) cap. 3 — DuPont", "PL zero")


def cobertura_juros(ebit: Decimal, despesas_financeiras: Decimal) -> ResultadoIndicador:
    """CJ = EBIT / Despesas Financeiras. Gitman (2017) cap. 3."""
    return _ratio(ebit, despesas_financeiras, "EBIT / Desp.Financeiras",
                  "Gitman (2017) cap. 3", "Despesas Financeiras zero")


# ── FLEURIET ─────────────────────────────────────────────────────────

def ncg(ac_operacional: Decimal, pc_operacional: Decimal) -> ResultadoIndicador:
    """NCG = ACO - PCO. Fleuriet, Kehdy, Blanc (2003) cap. 2."""
    return ResultadoIndicador(money(ac_operacional - pc_operacional), None,
                              "ACO - PCO", "Fleuriet, Kehdy, Blanc (2003) cap. 2")


def cdg(fontes_permanentes: Decimal, aplicacoes_permanentes: Decimal) -> ResultadoIndicador:
    """CDG = Fontes Permanentes - Aplicacoes Permanentes. Fleuriet (2003) cap. 2."""
    return ResultadoIndicador(money(fontes_permanentes - aplicacoes_permanentes), None,
                              "Fontes Perm. - Aplic. Perm.", "Fleuriet (2003) cap. 2")


def saldo_tesouraria(cdg_val: Decimal, ncg_val: Decimal) -> ResultadoIndicador:
    """ST = CDG - NCG. Fleuriet (2003) cap. 2."""
    return ResultadoIndicador(money(cdg_val - ncg_val), None,
                              "CDG - NCG", "Fleuriet (2003) cap. 2")
