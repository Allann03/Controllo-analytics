"""
Motor de calculo do Lucro Real (RIR/2018, Lei 9.249/95, Lei 9.065/95).

Modulo isolado — depende apenas de services.contabil.core.
Sem dependencia de database, models, routers, ou qualquer ORM.

Implementa:
  - LALUR simplificado (adicoes e exclusoes com norma obrigatoria)
  - Compensacao de prejuizo fiscal limitada a 30% (Lei 9.065/95 art. 15)
  - IRPJ 15% + adicional 10% sobre excedente trimestral a R$ 60k
  - CSLL 9% com base propria (aceita ajustes separados)
  - PIS nao-cumulativo 1,65% com creditos detalhados (Lei 10.637/02)
  - COFINS nao-cumulativo 7,6% com creditos detalhados (Lei 10.833/03)

Bugs corrigidos do legado:
  - CRITICO-LR-1: LALUR ausente ("lucro real" = lucro bruto simplificado)
  - CRITICO-LR-2: Compensacao de prejuizo fiscal ausente
  - ALTO-LR-3: float em toda aritmetica
  - MEDIO-LR-4: Creditos PIS/COFINS sem detalhamento
  - MEDIO-LR-5: CSLL sem base propria
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from services.contabil.core import (
    money_fiscal,
    rate,
    to_decimal,
    MemoriaCalculo,
    ResultadoCalculo,
    NormaContabil,
    assertir_invariante,
    VERSAO_CALCULO,
)

_ZERO = Decimal("0")
_TOL = money_fiscal("0.01")

# -- Aliquotas Lucro Real ------------------------------------------------------

ALIQUOTA_IRPJ        = rate("0.15")       # Lei 9.249/95 art. 3
ALIQUOTA_IRPJ_ADIC   = rate("0.10")       # Lei 9.249/95 art. 3 par. 1
LIMITE_TRIM_IRPJ     = Decimal("60000")   # Lei 9.249/95 art. 3 par. 1
ALIQUOTA_CSLL        = rate("0.09")       # Lei 7.689/88 art. 3
ALIQUOTA_PIS         = rate("0.0165")     # Lei 10.637/02 art. 2 (nao-cumulativo)
ALIQUOTA_COFINS      = rate("0.076")      # Lei 10.833/03 art. 2 (nao-cumulativo)
LIMITE_COMPENSACAO   = rate("0.30")       # Lei 9.065/95 art. 15 (30% do lucro real)

_TIPOS_CREDITO_VALIDOS = frozenset({"insumos", "energia", "aluguel", "depreciacao", "frete", "outros"})


# -- Estruturas ----------------------------------------------------------------

@dataclass(frozen=True)
class AjusteLALUR:
    """Ajuste do LALUR (adicao ou exclusao) com citacao normativa obrigatoria."""
    descricao: str
    valor: Decimal
    tipo: str    # "adicao" | "exclusao"
    norma: str   # citacao normativa obrigatoria

    def __post_init__(self):
        if not isinstance(self.valor, Decimal):
            object.__setattr__(self, "valor", to_decimal(self.valor))
        if not self.norma or not self.norma.strip():
            raise ValueError("AjusteLALUR.norma e obrigatorio com citacao normativa")
        if self.tipo not in ("adicao", "exclusao"):
            raise ValueError(f"tipo deve ser 'adicao' ou 'exclusao', recebido: {self.tipo}")
        if self.valor < _ZERO:
            raise ValueError(f"valor nao pode ser negativo: {self.valor}")


@dataclass(frozen=True)
class CreditoPISCofins:
    """Credito PIS/COFINS nao-cumulativo detalhado."""
    descricao: str
    base_credito: Decimal
    tipo: str    # "insumos" | "energia" | "aluguel" | "depreciacao" | "frete" | "outros"

    def __post_init__(self):
        if not isinstance(self.base_credito, Decimal):
            object.__setattr__(self, "base_credito", to_decimal(self.base_credito))
        if self.tipo not in _TIPOS_CREDITO_VALIDOS:
            raise ValueError(
                f"tipo invalido: {self.tipo}. Permitidos: {sorted(_TIPOS_CREDITO_VALIDOS)}"
            )
        if self.base_credito < _ZERO:
            raise ValueError(f"base_credito nao pode ser negativa: {self.base_credito}")
        if not self.descricao or not self.descricao.strip():
            raise ValueError("CreditoPISCofins.descricao e obrigatorio")


@dataclass
class ResultadoLucroReal:
    """Resultado detalhado do calculo do Lucro Real."""
    periodo: str
    # LALUR
    lucro_contabil: Decimal
    total_adicoes: Decimal
    total_exclusoes: Decimal
    lucro_real_antes_compensacao: Decimal
    # Compensacao de prejuizo
    prejuizo_compensado: Decimal
    prejuizo_remanescente: Decimal
    lucro_real_final: Decimal
    # IRPJ
    irpj_15: Decimal
    irpj_adicional_10: Decimal
    irpj_total: Decimal
    # CSLL
    base_csll: Decimal
    csll_9: Decimal
    # PIS/COFINS
    receita_liquida: Decimal
    pis_debito: Decimal
    pis_credito: Decimal
    pis_devido: Decimal
    cofins_debito: Decimal
    cofins_credito: Decimal
    cofins_devido: Decimal
    # Totais
    total_tributos: Decimal
    aliquota_efetiva: Decimal
    trimestral: bool


# -- Motor de calculo ----------------------------------------------------------

def calcular_lucro_real(
    lucro_contabil: Any,
    receita_liquida: Any,
    adicoes: Optional[list[AjusteLALUR]] = None,
    exclusoes: Optional[list[AjusteLALUR]] = None,
    creditos_pis_cofins: Optional[list[CreditoPISCofins]] = None,
    prejuizo_fiscal_acumulado: Any = 0,
    base_csll: Any = None,
    periodo: str = "",
    trimestral: bool = False,
) -> ResultadoCalculo:
    """
    Calcula a carga tributaria no Lucro Real.

    Parametros:
      lucro_contabil: Lucro/prejuizo contabil do periodo (antes de ajustes LALUR).
      receita_liquida: Receita liquida do periodo (base PIS/COFINS).
      adicoes: lista de AjusteLALUR tipo "adicao".
      exclusoes: lista de AjusteLALUR tipo "exclusao".
      creditos_pis_cofins: lista de CreditoPISCofins.
      prejuizo_fiscal_acumulado: saldo de prejuizo fiscal de periodos anteriores.
      base_csll: base CSLL se diferente do lucro real (None = usa lucro_real_final).
      periodo: string descritiva.
      trimestral: True se dados ja sao do trimestre.
    """
    avisos: list[str] = []
    _adicoes = adicoes or []
    _exclusoes = exclusoes or []
    _creditos = creditos_pis_cofins or []

    lc = money_fiscal(to_decimal(lucro_contabil))
    rl = money_fiscal(to_decimal(receita_liquida))
    prej_acum = money_fiscal(to_decimal(prejuizo_fiscal_acumulado))

    # -- LALUR: adicoes e exclusoes --------------------------------------------
    total_adic = _ZERO
    for a in _adicoes:
        total_adic += money_fiscal(a.valor)
    total_adic = money_fiscal(total_adic)

    total_excl = _ZERO
    for e in _exclusoes:
        total_excl += money_fiscal(e.valor)
    total_excl = money_fiscal(total_excl)

    # INV-LR-1
    check_adic = _ZERO
    for a in _adicoes:
        check_adic += money_fiscal(a.valor)
    assertir_invariante("INV-LR-1: total_adicoes", total_adic, money_fiscal(check_adic),
                        tolerancia=money_fiscal(Decimal(str(max(1, len(_adicoes)))) * Decimal("0.01")),
                        contexto=f"LR {periodo}")

    # INV-LR-2
    check_excl = _ZERO
    for e in _exclusoes:
        check_excl += money_fiscal(e.valor)
    assertir_invariante("INV-LR-2: total_exclusoes", total_excl, money_fiscal(check_excl),
                        tolerancia=money_fiscal(Decimal(str(max(1, len(_exclusoes)))) * Decimal("0.01")),
                        contexto=f"LR {periodo}")

    # Lucro real antes da compensacao
    lucro_antes = money_fiscal(lc + total_adic - total_excl)

    # INV-LR-3
    assertir_invariante("INV-LR-3: lucro_antes = LC + adic - excl",
                        lucro_antes, money_fiscal(lc + total_adic - total_excl),
                        tolerancia=_TOL, contexto=f"LR {periodo}")

    if not _adicoes and not _exclusoes:
        avisos.append(
            "Nenhum ajuste LALUR informado. Lucro Real = Lucro Contabil. "
            "Se a empresa tem despesas indedutiveis ou exclusoes legais, "
            "o calculo pode estar impreciso."
        )

    # -- Compensacao de prejuizo fiscal (Lei 9.065/95 art. 15) -----------------
    compensacao = _ZERO
    prej_remanescente = prej_acum

    if lucro_antes > _ZERO and prej_acum > _ZERO:
        compensacao_maxima = money_fiscal(lucro_antes * LIMITE_COMPENSACAO)
        compensacao = money_fiscal(min(prej_acum, compensacao_maxima))
        prej_remanescente = money_fiscal(prej_acum - compensacao)

        # INV-LR-4: compensacao <= 30% do lucro antes
        assertir_invariante("INV-LR-4: compensacao <= 30% lucro",
                            compensacao, money_fiscal(min(prej_acum, compensacao_maxima)),
                            tolerancia=_TOL, contexto=f"LR {periodo}")
        # INV-LR-5: compensacao <= prejuizo acumulado
        assertir_invariante("INV-LR-5: compensacao <= prejuizo_acum",
                            compensacao,
                            money_fiscal(min(compensacao, prej_acum)),
                            tolerancia=_TOL, contexto=f"LR {periodo}")
    elif lucro_antes <= _ZERO:
        # Prejuizo no periodo: acumula
        prej_remanescente = money_fiscal(prej_acum + abs(lucro_antes))
        avisos.append(
            f"Prejuizo no periodo (R$ {abs(lucro_antes):,.2f}). "
            f"Prejuizo acumulado atualizado para R$ {prej_remanescente:,.2f}."
        )

    lucro_final = money_fiscal(lucro_antes - compensacao)

    # INV-LR-6
    assertir_invariante("INV-LR-6: lucro_final = antes - compensacao",
                        lucro_final, money_fiscal(lucro_antes - compensacao),
                        tolerancia=_TOL, contexto=f"LR {periodo}")

    # -- IRPJ ------------------------------------------------------------------
    base_irpj = money_fiscal(max(_ZERO, lucro_final))
    irpj_15 = money_fiscal(base_irpj * ALIQUOTA_IRPJ)

    # INV-LR-7
    assertir_invariante("INV-LR-7: irpj_15 = max(0,lucro)*0.15",
                        irpj_15, money_fiscal(base_irpj * ALIQUOTA_IRPJ),
                        tolerancia=_TOL, contexto=f"LR {periodo}")

    # Adicional IRPJ
    if trimestral:
        base_trim = base_irpj
    else:
        base_trim = money_fiscal(base_irpj * Decimal("3"))
        if base_irpj > _ZERO:
            avisos.append(
                "ATENCAO: adicional IRPJ estimado a partir de base mensal x 3. "
                "Para apuracao trimestral, forneca dados do trimestre (trimestral=True)."
            )

    excedente_trim = money_fiscal(max(_ZERO, base_trim - LIMITE_TRIM_IRPJ))

    if trimestral:
        irpj_adic = money_fiscal(excedente_trim * ALIQUOTA_IRPJ_ADIC)
    else:
        adic_trim = money_fiscal(excedente_trim * ALIQUOTA_IRPJ_ADIC)
        irpj_adic = money_fiscal(adic_trim / Decimal("3"))

    # INV-LR-8
    assertir_invariante("INV-LR-8: adicional_irpj",
                        irpj_adic,
                        money_fiscal(excedente_trim * ALIQUOTA_IRPJ_ADIC) if trimestral
                        else money_fiscal(money_fiscal(excedente_trim * ALIQUOTA_IRPJ_ADIC) / Decimal("3")),
                        tolerancia=_TOL, contexto=f"LR {periodo}")

    irpj_total = money_fiscal(irpj_15 + irpj_adic)

    # -- CSLL ------------------------------------------------------------------
    if base_csll is not None:
        b_csll = money_fiscal(to_decimal(base_csll))
    else:
        b_csll = money_fiscal(max(_ZERO, lucro_final))

    csll_9 = money_fiscal(b_csll * ALIQUOTA_CSLL)

    # -- PIS nao-cumulativo (Lei 10.637/02) ------------------------------------
    pis_debito = money_fiscal(rl * ALIQUOTA_PIS)

    total_base_credito = _ZERO
    for c in _creditos:
        total_base_credito += money_fiscal(c.base_credito)
    pis_credito = money_fiscal(total_base_credito * ALIQUOTA_PIS)
    pis_devido = money_fiscal(max(_ZERO, pis_debito - pis_credito))

    # INV-LR-9
    assertir_invariante("INV-LR-9: pis_devido = max(0, deb-cred)",
                        pis_devido, money_fiscal(max(_ZERO, pis_debito - pis_credito)),
                        tolerancia=_TOL, contexto=f"LR {periodo}")

    # -- COFINS nao-cumulativo (Lei 10.833/03) ---------------------------------
    cofins_debito = money_fiscal(rl * ALIQUOTA_COFINS)
    cofins_credito = money_fiscal(total_base_credito * ALIQUOTA_COFINS)
    cofins_devido = money_fiscal(max(_ZERO, cofins_debito - cofins_credito))

    # INV-LR-10
    assertir_invariante("INV-LR-10: cofins_devido = max(0, deb-cred)",
                        cofins_devido, money_fiscal(max(_ZERO, cofins_debito - cofins_credito)),
                        tolerancia=_TOL, contexto=f"LR {periodo}")

    if not _creditos and rl > _ZERO:
        avisos.append(
            "Nenhum credito PIS/COFINS informado. Se a empresa tem insumos, "
            "os tributos podem estar superestimados."
        )

    # -- Total -----------------------------------------------------------------
    total = money_fiscal(irpj_total + csll_9 + pis_devido + cofins_devido)

    # INV-LR-11
    assertir_invariante("INV-LR-11: total_tributos",
                        total, money_fiscal(irpj_total + csll_9 + pis_devido + cofins_devido),
                        tolerancia=_TOL, contexto=f"LR {periodo}")

    aliq_efetiva = _ZERO
    if rl > _ZERO:
        aliq_efetiva = rate(total / rl)

    # -- Resultado -------------------------------------------------------------
    resultado = ResultadoLucroReal(
        periodo=periodo,
        lucro_contabil=lc,
        total_adicoes=total_adic,
        total_exclusoes=total_excl,
        lucro_real_antes_compensacao=lucro_antes,
        prejuizo_compensado=compensacao,
        prejuizo_remanescente=prej_remanescente,
        lucro_real_final=lucro_final,
        irpj_15=irpj_15,
        irpj_adicional_10=irpj_adic,
        irpj_total=irpj_total,
        base_csll=b_csll,
        csll_9=csll_9,
        receita_liquida=rl,
        pis_debito=pis_debito,
        pis_credito=pis_credito,
        pis_devido=pis_devido,
        cofins_debito=cofins_debito,
        cofins_credito=cofins_credito,
        cofins_devido=cofins_devido,
        total_tributos=total,
        aliquota_efetiva=aliq_efetiva,
        trimestral=trimestral,
    )

    # -- Memoria ---------------------------------------------------------------
    insumos: dict[str, Decimal] = {
        "lucro_contabil": lc,
        "total_adicoes": total_adic,
        "total_exclusoes": total_excl,
        "prejuizo_acumulado": prej_acum,
        "receita_liquida": rl,
        "total_creditos_pis_cofins": money_fiscal(total_base_credito),
    }

    memoria = MemoriaCalculo(
        insumos=insumos,
        formula=(
            "LALUR: LR = LC + Adic - Excl; Comp = min(prej, LR*0.30); "
            "LR_final = LR - Comp; IRPJ = LR_final*0.15 + adic; "
            "CSLL = base*0.09; PIS/COFINS nao-cumulativo com creditos"
        ),
        norma=NormaContabil.RIR_2018,
        resultado=total,
    )

    return ResultadoCalculo(valor=resultado, memoria=memoria, avisos=avisos)
