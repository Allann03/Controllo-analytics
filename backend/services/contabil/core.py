"""
Infraestrutura de calculo contabil-fiscal -- Controllo BPO Analytics.

Modulo de dependencia ZERO: nao importa models, database, routers, nem
qualquer outro modulo da aplicacao. Pode ser testado em isolamento total.

Convencoes:
  - money()        -> Decimal quantizado a 0.01 (ROUND_HALF_EVEN)
  - money_fiscal() -> Decimal quantizado a 0.01 (ROUND_HALF_UP -- RFB)
  - rate()         -> Decimal quantizado a 0.000001 (6 casas)
  - pct()          -> Decimal para percentuais 0-100, 6 casas
  - to_decimal()   -> conversor defensivo (aceita int, float, str, Decimal)
"""

import logging
import math
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP, getcontext, localcontext
from enum import Enum
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)

# -- Versao do calculo (semver) -----------------------------------------------
# Incrementar quando formulas mudarem nos sub-blocos 3B--3K.
VERSAO_CALCULO = "3.0.0"

# -----------------------------------------------------------------
# QUANDO USAR money() vs money_fiscal()
# -----------------------------------------------------------------
# money()          -- Contabilidade pura (sem impacto fiscal direto)
#   . DRE, BP, DFC, indicadores FP&A
#   . Lancamentos contabeis internos
#   . Analise de variancia, orcamento vs realizado
#   . Conciliacao bancaria
#
# money_fiscal()   -- Apuracao de tributo a recolher
#   . IRPJ, CSLL, PIS, COFINS, ISS, ICMS, IPI
#   . DAS (Simples Nacional)
#   . CBS, IBS, IS (Reforma Tributaria)
#   . Retencoes na fonte (IRRF, CSRF, INSS-retido)
#   . Base de calculo -> aliquota -> tributo devido
#
# REGRA DE OURO: se o valor vai para uma guia de recolhimento
# (DARF, DAS, GPS, GNRE), use money_fiscal. Caso contrario, money.
# -----------------------------------------------------------------


# -- Contexto Decimal ----------------------------------------------------------
# Contexto base configurado uma unica vez. Como o modulo decimal do Python
# mantem contexto por thread, cada quantizador chama _aplicar_contexto()
# para garantir prec=28 e ROUND_HALF_EVEN independente da thread.

_CONTEXTO_BASE = getcontext().copy()
_CONTEXTO_BASE.prec = 28
_CONTEXTO_BASE.rounding = ROUND_HALF_EVEN

_Q_MONEY = Decimal("0.01")
_Q_RATE  = Decimal("0.000001")
_Q_PCT   = Decimal("0.000001")
_ZERO    = Decimal("0")


def _aplicar_contexto() -> None:
    """Garante contexto Decimal correto na thread atual.

    Overhead desprezivel (nanossegundos), garantia absoluta de que
    prec=28 e rounding=ROUND_HALF_EVEN estao ativos mesmo em
    worker threads do uvicorn/FastAPI.
    """
    ctx = getcontext()
    ctx.prec = 28
    ctx.rounding = ROUND_HALF_EVEN


# -- Quantizadores -------------------------------------------------------------

def money(valor: Any) -> Decimal:
    """Quantiza a 2 casas decimais com ROUND_HALF_EVEN (padrao contabil)."""
    _aplicar_contexto()
    return to_decimal(valor).quantize(_Q_MONEY, rounding=ROUND_HALF_EVEN)


def money_fiscal(valor: Any) -> Decimal:
    """Quantiza a 2 casas decimais com ROUND_HALF_UP (padrao RFB).

    Usar em calculos fiscais onde a Receita Federal exige arredondamento
    para cima em .005: IRPJ, CSLL, PIS, COFINS, DAS, ISS.
    Referencia: IN RFB 1.700/2017 Art. 7, par. 2.
    """
    _aplicar_contexto()
    return to_decimal(valor).quantize(_Q_MONEY, rounding=ROUND_HALF_UP)


def rate(valor: Any) -> Decimal:
    """Quantiza aliquota a 6 casas decimais (ex: 0.153000)."""
    _aplicar_contexto()
    return to_decimal(valor).quantize(_Q_RATE, rounding=ROUND_HALF_EVEN)


def pct(valor: Any) -> Decimal:
    """Quantiza percentual (0-100) a 6 casas decimais."""
    _aplicar_contexto()
    return to_decimal(valor).quantize(_Q_PCT, rounding=ROUND_HALF_EVEN)


# -- Conversor defensivo -------------------------------------------------------

def to_decimal(valor: Any) -> Decimal:
    """Converte int, float, str ou Decimal para Decimal.

    Rejeita None, bool, list, dict, NaN e Infinity com TypeError explicito.
    float e convertido via str() para evitar artefatos binarios
    (ex: float(0.1) -> '0.1' -> Decimal('0.1'), nao Decimal(0.1...00001)).
    """
    if valor is None:
        raise TypeError("to_decimal: None nao e um valor numerico valido.")
    if isinstance(valor, bool):
        raise TypeError("to_decimal: bool nao e um valor numerico valido.")
    if isinstance(valor, Decimal):
        if not valor.is_finite():
            raise TypeError(f"to_decimal: Decimal nao-finito ({valor}) nao e um valor contabil.")
        return valor
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, float):
        if math.isnan(valor) or math.isinf(valor):
            raise TypeError(f"to_decimal: float invalido ({valor}) nao e um valor contabil.")
        return Decimal(str(valor))
    if isinstance(valor, str):
        valor = valor.strip()
        if not valor:
            raise TypeError("to_decimal: string vazia nao e um valor numerico valido.")
        resultado = Decimal(valor)
        if not resultado.is_finite():
            raise TypeError(f"to_decimal: string '{valor}' produz Decimal nao-finito.")
        return resultado
    raise TypeError(f"to_decimal: tipo {type(valor).__name__} nao suportado.")


# -- Normas --------------------------------------------------------------------

class NormaContabil(str, Enum):
    """Normas contabeis e fiscais suportadas."""
    CPC_26     = "CPC 26 (R2) -- DRE"
    CPC_03     = "CPC 03 (R2) -- DFC"
    CPC_26_BP  = "CPC 26 (R2) -- Balanco Patrimonial"
    NBC_TG_26  = "NBC TG 26 (R5)"
    RIR_2018   = "RIR/2018"
    IN_1700    = "IN RFB 1.700/2017"
    LC_123     = "LC 123/2006 -- Simples Nacional"
    LC_214     = "LC 214/2025 -- Reforma Tributaria"
    LEI_9718   = "Lei 9.718/1998 -- PIS/COFINS cumulativo"
    LEI_10637  = "Lei 10.637/2002 -- PIS nao-cumulativo"
    LEI_10833  = "Lei 10.833/2003 -- COFINS nao-cumulativo"
    COSTUME    = "Pratica contabil usual"

# Union permite strings livres para normas nao catalogadas
Norma = Union[NormaContabil, str]


# -- Memoria de Calculo --------------------------------------------------------

@dataclass
class MemoriaCalculo:
    """Rastreabilidade completa de um calculo contabil-fiscal."""
    insumos: dict[str, Decimal]
    formula: str
    norma: Norma
    resultado: Decimal
    versao: str = field(default_factory=lambda: VERSAO_CALCULO)
    calculado_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Valida e converte insumos e resultado para Decimal (defesa contra float)."""
        self.insumos = {k: to_decimal(v) for k, v in self.insumos.items()}
        if not isinstance(self.resultado, Decimal):
            self.resultado = to_decimal(self.resultado)

    def to_dict(self) -> dict:
        """Serializa para JSON (Decimal -> str, datetime -> ISO)."""
        return {
            "insumos": {k: str(v) for k, v in self.insumos.items()},
            "formula": self.formula,
            "norma": str(self.norma.value) if isinstance(self.norma, NormaContabil) else self.norma,
            "resultado": str(self.resultado),
            "versao": self.versao,
            "calculado_em": self.calculado_em.isoformat(),
        }


@dataclass
class ResultadoCalculo:
    """Retorno padrao de funcoes top-level de calculo fiscal."""
    valor: Decimal
    memoria: MemoriaCalculo
    avisos: list[str] = field(default_factory=list)


# -- Integridade Contabil ------------------------------------------------------

class IntegridadeContabilError(Exception):
    """Violacao de invariante contabil (ex: Ativo != Passivo + PL)."""
    def __init__(self, mensagem: str, esperado: Decimal, obtido: Decimal,
                 diferenca: Decimal, contexto: str = ""):
        self.esperado = esperado
        self.obtido = obtido
        self.diferenca = diferenca
        self.contexto = contexto
        super().__init__(
            f"{mensagem} | esperado={esperado} obtido={obtido} "
            f"diferenca={diferenca} contexto={contexto}"
        )


def assertir_invariante(
    nome: str,
    esperado: Decimal,
    obtido: Decimal,
    tolerancia: Decimal = _ZERO,
    contexto: str = "",
) -> None:
    """Levanta IntegridadeContabilError se |esperado - obtido| > tolerancia.

    Emite log estruturado ANTES do raise para garantir trilha de auditoria
    mesmo quando a excecao e capturada em camadas superiores.
    """
    diferenca = abs(esperado - obtido)
    if diferenca > tolerancia:
        logger.error(
            "INVARIANTE_CONTABIL_VIOLADA",
            extra={
                "invariante": nome,
                "esperado": str(esperado),
                "obtido": str(obtido),
                "diferenca": str(diferenca),
                "tolerancia": str(tolerancia),
                "contexto": contexto,
            },
        )
        raise IntegridadeContabilError(
            mensagem=f"Invariante '{nome}' violada",
            esperado=esperado,
            obtido=obtido,
            diferenca=diferenca,
            contexto=contexto,
        )
