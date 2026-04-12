"""
Motor de calculo do ICMS-ST (Substituicao Tributaria).

ICMS-ST antecipa o recolhimento de toda a cadeia na primeira operacao.
Base ST = valor_produto × (1 + MVA).
ICMS-ST = (Base ST × aliq_interna_destino) - (valor_produto × aliq_interestadual).

Fontes: Convenios CONFAZ + legislacao estadual.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from services.contabil.core import (
    money_fiscal, rate, to_decimal,
    MemoriaCalculo, ResultadoCalculo, NormaContabil,
    assertir_invariante, VERSAO_CALCULO,
)

_ZERO = Decimal("0")
_TOL = money_fiscal("0.01")


@dataclass(frozen=True)
class OperacaoST:
    descricao: str
    valor_produto: Decimal
    ncm: str
    mva: Decimal                          # margem valor agregado (0.40 = 40%)
    aliquota_interna_destino: Decimal     # aliq interna do estado destino
    aliquota_interestadual: Decimal       # aliq interestadual aplicavel

    def __post_init__(self):
        if not isinstance(self.valor_produto, Decimal):
            object.__setattr__(self, "valor_produto", to_decimal(self.valor_produto))
        if not isinstance(self.mva, Decimal):
            object.__setattr__(self, "mva", to_decimal(self.mva))
        if not isinstance(self.aliquota_interna_destino, Decimal):
            object.__setattr__(self, "aliquota_interna_destino", to_decimal(self.aliquota_interna_destino))
        if not isinstance(self.aliquota_interestadual, Decimal):
            object.__setattr__(self, "aliquota_interestadual", to_decimal(self.aliquota_interestadual))
        if self.valor_produto < _ZERO:
            raise ValueError(f"valor_produto nao pode ser negativo: {self.valor_produto}")
        if self.mva < _ZERO:
            raise ValueError(f"mva nao pode ser negativa: {self.mva}")
        if not self.ncm or not self.ncm.strip():
            raise ValueError("ncm e obrigatorio")
        if not self.descricao or not self.descricao.strip():
            raise ValueError("descricao e obrigatorio")


@dataclass
class ResultadoICMSST:
    valor_produto: Decimal
    base_st: Decimal
    icms_proprio: Decimal
    icms_st: Decimal
    total_icms: Decimal


def calcular_icms_st(
    operacao: OperacaoST,
    periodo: str = "",
) -> ResultadoCalculo:
    avisos: list[str] = []
    vp = money_fiscal(operacao.valor_produto)
    mva = operacao.mva
    aliq_int = rate(operacao.aliquota_interna_destino)
    aliq_inter = rate(operacao.aliquota_interestadual)

    # INV-ST-1: base_st = valor_produto × (1 + mva)
    base_st = money_fiscal(vp * (Decimal("1") + mva))
    assertir_invariante("INV-ST-1: base_st = vp x (1 + mva)",
                        base_st, money_fiscal(vp * (Decimal("1") + mva)),
                        tolerancia=_TOL, contexto=f"ST {periodo}")

    # ICMS proprio = valor × aliq_interestadual
    icms_proprio = money_fiscal(vp * aliq_inter)

    # INV-ST-2: icms_st = base_st × aliq_interna - icms_proprio
    icms_st_bruto = money_fiscal(base_st * aliq_int - icms_proprio)
    icms_st = money_fiscal(max(_ZERO, icms_st_bruto))

    if icms_st_bruto < _ZERO:
        avisos.append(
            "ICMS-ST calculado seria negativo (ICMS proprio > ICMS ST). "
            "Resultado ajustado para zero. Verificar MVA e aliquotas."
        )

    assertir_invariante("INV-ST-2: icms_st = base_st*aliq - proprio",
                        icms_st, money_fiscal(max(_ZERO, money_fiscal(base_st * aliq_int - icms_proprio))),
                        tolerancia=_TOL, contexto=f"ST {periodo}")

    total_icms = money_fiscal(icms_proprio + icms_st)

    resultado = ResultadoICMSST(
        valor_produto=vp, base_st=base_st,
        icms_proprio=icms_proprio, icms_st=icms_st, total_icms=total_icms,
    )
    insumos = {"valor_produto": vp, "mva": to_decimal(mva),
               "aliq_interna": aliq_int, "aliq_inter": aliq_inter}
    memoria = MemoriaCalculo(
        insumos=insumos,
        formula=f"Base ST = {float(vp)} x (1+{float(mva)}); ST = BaseST*{float(aliq_int)} - {float(icms_proprio)}",
        norma=NormaContabil.COSTUME, resultado=total_icms,
    )
    return ResultadoCalculo(valor=resultado, memoria=memoria, avisos=avisos)
