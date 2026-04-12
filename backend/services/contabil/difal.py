"""
Motor de calculo do DIFAL (Diferencial de Aliquota).

EC 87/2015 + LC 190/2022: operacoes interestaduais destinadas a consumidor
final nao contribuinte do ICMS.

DIFAL = Valor × (aliquota_interna_destino - aliquota_interestadual)
FCP = Valor × aliquota_fcp_destino (Fundo de Combate a Pobreza)
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from services.contabil.core import (
    money_fiscal, rate, to_decimal,
    MemoriaCalculo, ResultadoCalculo, NormaContabil,
    assertir_invariante, VERSAO_CALCULO,
)
from services.contabil.tabelas.aliquotas_icms import (
    UFS_VALIDAS, aliquota_interestadual as _get_aliq_inter,
    ALIQUOTA_INTERNA_PADRAO, FCP_POR_UF,
)

_ZERO = Decimal("0")
_TOL = money_fiscal("0.01")


@dataclass(frozen=True)
class OperacaoInterestadual:
    descricao: str
    valor: Decimal
    uf_origem: str
    uf_destino: str
    consumidor_final: bool
    contribuinte_icms: bool = False
    importado: bool = False

    def __post_init__(self):
        if not isinstance(self.valor, Decimal):
            object.__setattr__(self, "valor", to_decimal(self.valor))
        if self.uf_origem not in UFS_VALIDAS:
            raise ValueError(f"UF origem invalida: {self.uf_origem}")
        if self.uf_destino not in UFS_VALIDAS:
            raise ValueError(f"UF destino invalida: {self.uf_destino}")
        if self.valor < _ZERO:
            raise ValueError(f"valor nao pode ser negativo: {self.valor}")
        if not self.descricao or not self.descricao.strip():
            raise ValueError("descricao e obrigatorio")


@dataclass
class ResultadoDIFAL:
    valor_operacao: Decimal
    aliquota_interestadual: Decimal
    aliquota_interna_destino: Decimal
    difal_valor: Decimal
    fcp: Decimal
    total: Decimal
    aplicavel: bool
    motivo_nao_aplicavel: str


def calcular_difal(
    operacao: OperacaoInterestadual,
    aliquota_interna_override: Any = None,
    periodo: str = "",
) -> ResultadoCalculo:
    avisos: list[str] = []
    v = money_fiscal(operacao.valor)

    # INV-DIFAL-1: aplicado apenas se consumidor_final e UFs diferentes
    aplicavel = True
    motivo = ""

    if not operacao.consumidor_final:
        aplicavel = False
        motivo = "Destinatario nao e consumidor final (B2B)"
    elif operacao.uf_origem == operacao.uf_destino:
        aplicavel = False
        motivo = "Operacao interna (mesma UF)"
    elif operacao.contribuinte_icms:
        aplicavel = False
        motivo = "Destinatario e contribuinte do ICMS (recolhe na apuracao propria)"

    if not aplicavel:
        resultado = ResultadoDIFAL(
            valor_operacao=v,
            aliquota_interestadual=_ZERO, aliquota_interna_destino=_ZERO,
            difal_valor=_ZERO, fcp=_ZERO, total=_ZERO,
            aplicavel=False, motivo_nao_aplicavel=motivo,
        )
        memoria = MemoriaCalculo(
            insumos={"valor": v}, formula=f"DIFAL nao aplicavel: {motivo}",
            norma=NormaContabil.COSTUME, resultado=_ZERO,
        )
        return ResultadoCalculo(valor=resultado, memoria=memoria, avisos=avisos)

    # Aliquotas
    aliq_inter = _get_aliq_inter(operacao.uf_origem, operacao.uf_destino, operacao.importado)

    if aliquota_interna_override is not None:
        aliq_interna = rate(to_decimal(aliquota_interna_override))
    else:
        aliq_interna = ALIQUOTA_INTERNA_PADRAO.get(operacao.uf_destino, rate("0.18"))

    fcp_rate = FCP_POR_UF.get(operacao.uf_destino, _ZERO)

    # INV-DIFAL-2: difal = valor × (aliq_interna - aliq_inter)
    diff_aliq = rate(aliq_interna - aliq_inter)
    if diff_aliq < _ZERO:
        diff_aliq = _ZERO
        avisos.append("Aliquota interestadual >= aliquota interna destino. DIFAL = 0.")

    difal_valor = money_fiscal(v * diff_aliq)
    fcp_valor = money_fiscal(v * fcp_rate)
    total = money_fiscal(difal_valor + fcp_valor)

    assertir_invariante("INV-DIFAL-2: difal = valor x (interna - inter)",
                        difal_valor, money_fiscal(v * diff_aliq),
                        tolerancia=_TOL, contexto=f"DIFAL {periodo}")

    resultado = ResultadoDIFAL(
        valor_operacao=v,
        aliquota_interestadual=aliq_inter,
        aliquota_interna_destino=aliq_interna,
        difal_valor=difal_valor, fcp=fcp_valor, total=total,
        aplicavel=True, motivo_nao_aplicavel="",
    )
    insumos = {"valor": v, "aliq_inter": aliq_inter, "aliq_interna": aliq_interna, "fcp_rate": fcp_rate}
    memoria = MemoriaCalculo(
        insumos=insumos,
        formula=f"DIFAL = {float(v)} x ({float(aliq_interna)} - {float(aliq_inter)}) + FCP",
        norma=NormaContabil.COSTUME, resultado=total,
    )
    return ResultadoCalculo(valor=resultado, memoria=memoria, avisos=avisos)
