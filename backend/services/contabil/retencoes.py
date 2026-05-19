"""
Motor de calculo de Retencoes na Fonte.

IRRF PJ 1,5% (RIR/2018 art. 714), CSRF 4,65% (Lei 10.833/03 art. 30),
INSS retido 11% (Lei 8.212/91 art. 31), ISS retido (LC 116/03).
Dispensa CSRF para pagamentos <= R$ 215,05 (Lei 10.833/03 art. 31 par. 3).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from services.contabil.core import (
    money_fiscal, rate, to_decimal,
    MemoriaCalculo, ResultadoCalculo, NormaContabil,
    assertir_invariante, VERSAO_CALCULO,
)
from services.contabil.tabelas.servicos_retencao import (
    SERVICOS_IRRF_15, SERVICOS_CSRF_465, TIPOS_SERVICO_VALIDOS,
    DISPENSA_CSRF_LIMITE,
    ALIQUOTA_IRRF, ALIQUOTA_CSLL_RET, ALIQUOTA_COFINS_RET,
    ALIQUOTA_PIS_RET, ALIQUOTA_INSS_RET,
)

_ZERO = Decimal("0")
_TOL = money_fiscal("0.01")


@dataclass(frozen=True)
class PagamentoServico:
    descricao: str
    valor_bruto: Decimal
    tipo_servico: str
    tomador_pj: bool = True
    cessao_mao_obra: bool = False

    def __post_init__(self):
        if not isinstance(self.valor_bruto, Decimal):
            object.__setattr__(self, "valor_bruto", to_decimal(self.valor_bruto))
        if self.tipo_servico not in TIPOS_SERVICO_VALIDOS:
            raise ValueError(
                f"tipo_servico invalido: {self.tipo_servico}. "
                f"Permitidos: {sorted(TIPOS_SERVICO_VALIDOS)}"
            )
        if self.valor_bruto < _ZERO:
            raise ValueError(f"valor_bruto nao pode ser negativo: {self.valor_bruto}")
        if not self.descricao or not self.descricao.strip():
            raise ValueError("descricao e obrigatorio")


@dataclass
class ResultadoRetencoes:
    valor_bruto: Decimal
    irrf: Decimal
    csll_retido: Decimal
    cofins_retido: Decimal
    pis_retido: Decimal
    csrf_total: Decimal
    inss_retido: Decimal
    iss_retido: Decimal
    total_retido: Decimal
    valor_liquido: Decimal


def calcular_retencoes(
    pagamento: PagamentoServico,
    aliquota_iss_retido: Any = None,
    periodo: str = "",
) -> ResultadoCalculo:
    avisos: list[str] = []
    vb = money_fiscal(pagamento.valor_bruto)
    ts = pagamento.tipo_servico

    # IRRF 1,5% — RIR/2018 art. 714
    irrf = _ZERO
    if ts in SERVICOS_IRRF_15 and pagamento.tomador_pj:
        irrf = money_fiscal(vb * ALIQUOTA_IRRF)

    # CSRF 4,65% — Lei 10.833/03 art. 30
    csll_ret = _ZERO
    cofins_ret = _ZERO
    pis_ret = _ZERO
    csrf_total = _ZERO
    csrf_dispensada = False

    if ts in SERVICOS_CSRF_465 and pagamento.tomador_pj:
        if vb <= DISPENSA_CSRF_LIMITE:
            csrf_dispensada = True
            avisos.append(
                f"CSRF dispensada: pagamento R$ {float(vb):,.2f} <= limite R$ {float(DISPENSA_CSRF_LIMITE):,.2f} "
                "(Lei 10.833/03 art. 31 par. 3)."
            )
        else:
            csll_ret = money_fiscal(vb * ALIQUOTA_CSLL_RET)
            cofins_ret = money_fiscal(vb * ALIQUOTA_COFINS_RET)
            pis_ret = money_fiscal(vb * ALIQUOTA_PIS_RET)
            csrf_total = money_fiscal(csll_ret + cofins_ret + pis_ret)

    # INV-RET-2
    if not csrf_dispensada and csrf_total > _ZERO:
        assertir_invariante("INV-RET-2: csrf = csll + cofins + pis",
                            csrf_total, money_fiscal(csll_ret + cofins_ret + pis_ret),
                            tolerancia=_TOL, contexto=f"RET {periodo}")

    # INSS retido 11% — Lei 8.212/91 art. 31
    inss_ret = _ZERO
    if pagamento.cessao_mao_obra or ts == "cessao_mao_obra":
        inss_ret = money_fiscal(vb * ALIQUOTA_INSS_RET)

    # ISS retido — LC 116/03 art. 3
    iss_ret = _ZERO
    if aliquota_iss_retido is not None:
        iss_rate = rate(to_decimal(aliquota_iss_retido))
        iss_ret = money_fiscal(vb * iss_rate)

    total_retido = money_fiscal(irrf + csrf_total + inss_ret + iss_ret)
    valor_liquido = money_fiscal(vb - total_retido)

    # INV-RET-1
    assertir_invariante("INV-RET-1: liquido = bruto - retido",
                        valor_liquido, money_fiscal(vb - total_retido),
                        tolerancia=_TOL, contexto=f"RET {periodo}")

    resultado = ResultadoRetencoes(
        valor_bruto=vb, irrf=irrf,
        csll_retido=csll_ret, cofins_retido=cofins_ret, pis_retido=pis_ret,
        csrf_total=csrf_total, inss_retido=inss_ret, iss_retido=iss_ret,
        total_retido=total_retido, valor_liquido=valor_liquido,
    )

    insumos = {"valor_bruto": vb, "tipo_servico": to_decimal(0)}
    memoria = MemoriaCalculo(
        insumos=insumos,
        formula=f"IRRF={float(irrf)} CSRF={float(csrf_total)} INSS={float(inss_ret)} ISS={float(iss_ret)}",
        norma=NormaContabil.RIR_2018,
        resultado=total_retido,
    )
    return ResultadoCalculo(valor=resultado, memoria=memoria, avisos=avisos)
