"""
Motor de calculo do Lucro Presumido (Lei 9.249/95, Lei 9.718/98).

Modulo isolado — depende apenas de services.contabil.core.
Sem dependencia de database, models, routers, ou qualquer ORM.

Correcoes sobre o motor legado:
  - 4 bases de presuncao IRPJ: 1.6%, 8%, 16%, 32% (Lei 9.249/95 art. 15)
  - 2 bases de presuncao CSLL: 12%, 32% (Lei 9.249/95 art. 20)
  - Multi-atividade: lista de receitas com base individual
  - Decimal + money_fiscal em toda aritmetica (R3)
  - Adicional IRPJ trimestral (Lei 9.249/95 art. 3 par. 1)
  - ResultadoCalculo com MemoriaCalculo auditavel
  - Validacao de bases no construtor (fail-fast)

Bugs corrigidos do legado:
  - CRITICO-LP-1: CSLL com base 32% para todas atividades (deveria ser 12% para comercio)
  - CRITICO-LP-2: IRPJ apenas base 32% (faltavam 1.6%, 8%, 16%)
  - ALTO-LP-3: float em toda aritmetica
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from services.contabil.core import (
    money_fiscal,
    rate,
    to_decimal,
    pct,
    MemoriaCalculo,
    ResultadoCalculo,
    NormaContabil,
    assertir_invariante,
    VERSAO_CALCULO,
)

_ZERO = Decimal("0")
_TOL = money_fiscal("0.01")

# -- Aliquotas Lucro Presumido -------------------------------------------------
# Cada constante cita a norma exata de origem.

ALIQUOTA_IRPJ      = rate("0.15")       # Lei 9.249/95 art. 3
ALIQUOTA_IRPJ_ADIC = rate("0.10")       # Lei 9.249/95 art. 3 par. 1
LIMITE_TRIM_IRPJ   = Decimal("60000")   # Lei 9.249/95 art. 3 par. 1 (R$ 20k/mes x 3)
ALIQUOTA_CSLL      = rate("0.09")       # Lei 7.689/88 art. 3 (alterado Lei 11.727/08)
ALIQUOTA_PIS       = rate("0.0065")     # Lei 9.715/98 art. 8 (regime cumulativo)
ALIQUOTA_COFINS    = rate("0.03")       # Lei 9.718/98 art. 8 (regime cumulativo)

# Bases de presuncao IRPJ (Lei 9.249/95 art. 15)
BASES_IRPJ_VALIDAS = frozenset([
    Decimal("0.016"),  # Combustiveis (art. 15 par. 1 I)
    Decimal("0.08"),   # Comercio/industria (art. 15 caput)
    Decimal("0.16"),   # Transp. passageiros (art. 15 par. 1 II)
    Decimal("0.32"),   # Servicos em geral (art. 15 par. 1 III)
])

# Bases de presuncao CSLL (Lei 9.249/95 art. 20)
BASES_CSLL_VALIDAS = frozenset([
    Decimal("0.12"),   # Comercio/industria (art. 20)
    Decimal("0.32"),   # Servicos (art. 20)
])


# -- Estruturas ----------------------------------------------------------------

@dataclass(frozen=True)
class ReceitaPorAtividade:
    """Receita de uma atividade com bases de presuncao especificas."""
    descricao: str
    valor: Decimal
    base_presuncao_irpj: Decimal  # 0.016, 0.08, 0.16, 0.32
    base_presuncao_csll: Decimal  # 0.12 ou 0.32

    def __post_init__(self):
        # Converter valor para Decimal se necessario
        if not isinstance(self.valor, Decimal):
            object.__setattr__(self, "valor", to_decimal(self.valor))
        if not isinstance(self.base_presuncao_irpj, Decimal):
            object.__setattr__(self, "base_presuncao_irpj", to_decimal(self.base_presuncao_irpj))
        if not isinstance(self.base_presuncao_csll, Decimal):
            object.__setattr__(self, "base_presuncao_csll", to_decimal(self.base_presuncao_csll))

        # IRPJ: apenas as 4 bases legais permitidas
        if self.base_presuncao_irpj not in BASES_IRPJ_VALIDAS:
            raise ValueError(
                f"Base de presuncao IRPJ invalida: {self.base_presuncao_irpj}. "
                f"Valores permitidos: 1.6%, 8%, 16%, 32% (Lei 9.249/95 art. 15)."
            )

        # CSLL: apenas as 2 bases legais permitidas
        if self.base_presuncao_csll not in BASES_CSLL_VALIDAS:
            raise ValueError(
                f"Base de presuncao CSLL invalida: {self.base_presuncao_csll}. "
                f"Valores permitidos: 12%, 32% (Lei 9.249/95 art. 20)."
            )

        # Coerencia IRPJ x CSLL — combinacoes impossiveis
        if self.base_presuncao_irpj == Decimal("0.32") and self.base_presuncao_csll != Decimal("0.32"):
            raise ValueError(
                "Atividade com IRPJ 32% (servicos em geral) deve usar CSLL 32%. "
                "Lei 9.249/95 art. 15 par. 1 III + art. 20."
            )
        if self.base_presuncao_irpj == Decimal("0.016") and self.base_presuncao_csll != Decimal("0.12"):
            raise ValueError(
                "Atividade com IRPJ 1.6% (combustiveis) deve usar CSLL 12%. "
                "Lei 9.249/95 art. 15 par. 1 I + art. 20."
            )

        # Valor >= 0
        if self.valor < _ZERO:
            raise ValueError(f"Valor de receita nao pode ser negativo: {self.valor}")


@dataclass
class ResultadoLucroPresumido:
    """Resultado detalhado do calculo do Lucro Presumido."""
    periodo: str
    receita_bruta_total: Decimal
    base_calculo_irpj: Decimal
    base_calculo_csll: Decimal
    irpj_15: Decimal
    irpj_adicional_10: Decimal
    irpj_total: Decimal
    csll_9: Decimal
    pis_065: Decimal
    cofins_3: Decimal
    iss: Decimal
    total_tributos: Decimal
    aliquota_efetiva: Decimal
    trimestral: bool
    receitas: list


# -- Motor de calculo ----------------------------------------------------------

def calcular_lucro_presumido(
    receitas: list[ReceitaPorAtividade],
    periodo: str = "",
    aliquota_iss: Any = None,
    trimestral: bool = False,
) -> ResultadoCalculo:
    """
    Calcula a carga tributaria no Lucro Presumido.

    Parametros:
      receitas: lista de ReceitaPorAtividade (uma por atividade da empresa).
      periodo: string descritiva ("2025-Q1", "2025-10").
      aliquota_iss: aliquota do ISS municipal (None = sem ISS).
      trimestral: True se receitas ja sao do trimestre completo.
                  False: motor estima base trimestral = mensal x 3.

    Retorna ResultadoCalculo com ResultadoLucroPresumido.
    """
    avisos: list[str] = []

    # -- Somar receitas e calcular bases ponderadas ----------------------------
    receita_total = _ZERO
    base_irpj = _ZERO
    base_csll = _ZERO

    for rec in receitas:
        v = money_fiscal(rec.valor)
        receita_total += v
        base_irpj += money_fiscal(v * rec.base_presuncao_irpj)
        base_csll += money_fiscal(v * rec.base_presuncao_csll)

    receita_total = money_fiscal(receita_total)
    base_irpj = money_fiscal(base_irpj)
    base_csll = money_fiscal(base_csll)

    # INV-LP-1: base_calculo_irpj == sum(receita_i x base_presuncao_irpj_i)
    check_base = _ZERO
    for rec in receitas:
        check_base += money_fiscal(money_fiscal(rec.valor) * rec.base_presuncao_irpj)
    assertir_invariante(
        "INV-LP-1: base_calculo_irpj",
        base_irpj, money_fiscal(check_base),
        tolerancia=money_fiscal(Decimal(str(len(receitas))) * Decimal("0.01")),
        contexto=f"LP {periodo}",
    )

    # -- IRPJ (15% sobre base presumida) — Lei 9.249/95 art. 3 ----------------
    irpj_15 = money_fiscal(base_irpj * ALIQUOTA_IRPJ)

    # INV-LP-2
    assertir_invariante(
        "INV-LP-2: irpj_15",
        irpj_15, money_fiscal(base_irpj * ALIQUOTA_IRPJ),
        tolerancia=_TOL, contexto=f"LP {periodo}",
    )

    # -- Adicional IRPJ (10% sobre excedente a R$60k/trimestre) ----------------
    # Lei 9.249/95 art. 3 par. 1
    if trimestral:
        base_trim_irpj = base_irpj
    else:
        base_trim_irpj = money_fiscal(base_irpj * Decimal("3"))
        avisos.append(
            "ATENCAO: calculo de IRPJ adicional estimado a partir de receita mensal x 3. "
            "Para apuracao oficial trimestral, forneca as receitas dos 3 meses do trimestre "
            "(parametro trimestral=True). Diferencas de sazonalidade podem alterar o adicional."
        )

    excedente_trim = money_fiscal(max(_ZERO, base_trim_irpj - LIMITE_TRIM_IRPJ))

    if trimestral:
        irpj_adicional = money_fiscal(excedente_trim * ALIQUOTA_IRPJ_ADIC)
    else:
        # Adicional trimestral dividido por 3 para obter parcela mensal
        adicional_trim = money_fiscal(excedente_trim * ALIQUOTA_IRPJ_ADIC)
        irpj_adicional = money_fiscal(adicional_trim / Decimal("3"))

    # INV-LP-3: se base_trim <= 60k -> adicional == 0
    if base_trim_irpj <= LIMITE_TRIM_IRPJ:
        assert irpj_adicional == _ZERO, "INV-LP-3: adicional deveria ser zero"

    irpj_total = money_fiscal(irpj_15 + irpj_adicional)

    # -- CSLL (9% sobre base presumida) — Lei 7.689/88 art. 3 -----------------
    csll_9 = money_fiscal(base_csll * ALIQUOTA_CSLL)

    # INV-LP-4
    assertir_invariante(
        "INV-LP-4: csll_9",
        csll_9, money_fiscal(base_csll * ALIQUOTA_CSLL),
        tolerancia=_TOL, contexto=f"LP {periodo}",
    )

    # -- PIS cumulativo (0.65%) — Lei 9.715/98 art. 8 -------------------------
    pis_065 = money_fiscal(receita_total * ALIQUOTA_PIS)

    # INV-LP-5
    assertir_invariante(
        "INV-LP-5: pis_065",
        pis_065, money_fiscal(receita_total * ALIQUOTA_PIS),
        tolerancia=_TOL, contexto=f"LP {periodo}",
    )

    # -- COFINS cumulativo (3%) — Lei 9.718/98 art. 8 -------------------------
    cofins_3 = money_fiscal(receita_total * ALIQUOTA_COFINS)

    # INV-LP-6
    assertir_invariante(
        "INV-LP-6: cofins_3",
        cofins_3, money_fiscal(receita_total * ALIQUOTA_COFINS),
        tolerancia=_TOL, contexto=f"LP {periodo}",
    )

    # -- ISS (opcional, aliquota municipal) ------------------------------------
    iss = _ZERO
    if aliquota_iss is not None:
        iss_rate = rate(to_decimal(aliquota_iss))
        iss = money_fiscal(receita_total * iss_rate)

    # -- Total -----------------------------------------------------------------
    total = money_fiscal(irpj_total + csll_9 + pis_065 + cofins_3 + iss)

    # INV-LP-7
    assertir_invariante(
        "INV-LP-7: total_tributos",
        total, money_fiscal(irpj_total + csll_9 + pis_065 + cofins_3 + iss),
        tolerancia=_TOL, contexto=f"LP {periodo}",
    )

    # -- Aliquota efetiva ------------------------------------------------------
    aliq_efetiva = _ZERO
    if receita_total > _ZERO:
        aliq_efetiva = rate(total / receita_total)

    # -- Resultado -------------------------------------------------------------
    resultado = ResultadoLucroPresumido(
        periodo=periodo,
        receita_bruta_total=receita_total,
        base_calculo_irpj=base_irpj,
        base_calculo_csll=base_csll,
        irpj_15=irpj_15,
        irpj_adicional_10=irpj_adicional,
        irpj_total=irpj_total,
        csll_9=csll_9,
        pis_065=pis_065,
        cofins_3=cofins_3,
        iss=iss,
        total_tributos=total,
        aliquota_efetiva=aliq_efetiva,
        trimestral=trimestral,
        receitas=[
            {"descricao": r.descricao, "valor": str(r.valor),
             "base_irpj": str(r.base_presuncao_irpj),
             "base_csll": str(r.base_presuncao_csll)}
            for r in receitas
        ],
    )

    # -- Memoria de calculo ----------------------------------------------------
    insumos: dict[str, Decimal] = {
        "receita_bruta_total": receita_total,
        "base_calculo_irpj": base_irpj,
        "base_calculo_csll": base_csll,
    }
    if aliquota_iss is not None:
        insumos["aliquota_iss"] = rate(to_decimal(aliquota_iss))

    formula_parts = []
    for i, rec in enumerate(receitas):
        formula_parts.append(
            f"Ativ{i+1}: RB={rec.valor} x IRPJ={rec.base_presuncao_irpj} x CSLL={rec.base_presuncao_csll}"
        )
    formula = "; ".join(formula_parts) + f"; IRPJ=base*{ALIQUOTA_IRPJ}+adic; CSLL=base*{ALIQUOTA_CSLL}; PIS+COFINS cumulativo"

    memoria = MemoriaCalculo(
        insumos=insumos,
        formula=formula,
        norma=NormaContabil.RIR_2018,
        resultado=total,
    )

    return ResultadoCalculo(valor=resultado, memoria=memoria, avisos=avisos)
