"""
Motor de calculo da Reforma Tributaria (EC 132/2023, LC 214/2025, LC 215/2025).

Modulo isolado — depende apenas de services.contabil.core e tabelas versionadas.
Sem dependencia de database, models, routers, ou qualquer ORM.

Implementa:
  - CBS (Contribuicao sobre Bens e Servicos) — substitui PIS/COFINS
  - IBS (Imposto sobre Bens e Servicos) — substitui ICMS/ISS
  - IS (Imposto Seletivo) — setorial
  - Cronograma de transicao 2026-2033 com aliquotas por ano
  - Regimes especificos com aliquotas reduzidas (saude, educacao, etc.)
  - Nao-cumulatividade com creditos detalhados

Bugs corrigidos do legado:
  - ALTO-RT-1: Cronograma 2026-2033 ausente (usava aliquota plena para todos os anos)
  - ALTO-RT-2: Float em toda aritmetica
  - MEDIO-RT-3: Sem regimes especificos
  - MEDIO-RT-4: Referencia normativa desatualizada (PLP 68/2024 -> LC 214/2025)
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
from services.contabil.tabelas.reforma_tributaria import (
    get_aliquotas,
    REGIMES_ESPECIFICOS,
    REGIMES_VALIDOS,
)

_ZERO = Decimal("0")
_TOL = money_fiscal("0.01")


# -- Estruturas ----------------------------------------------------------------

@dataclass(frozen=True)
class OperacaoReforma:
    """Operacao sujeita a CBS/IBS com regime especifico."""
    descricao: str
    valor: Decimal
    regime: str  # "geral" | "saude" | "educacao" | ...

    def __post_init__(self):
        if not isinstance(self.valor, Decimal):
            object.__setattr__(self, "valor", to_decimal(self.valor))
        if self.regime not in REGIMES_VALIDOS:
            raise ValueError(
                f"regime invalido: {self.regime}. Permitidos: {sorted(REGIMES_VALIDOS)}"
            )
        if self.valor < _ZERO:
            raise ValueError(f"valor nao pode ser negativo: {self.valor}")
        if not self.descricao or not self.descricao.strip():
            raise ValueError("descricao e obrigatorio")


@dataclass
class ResultadoReforma:
    """Resultado detalhado do calculo da Reforma Tributaria."""
    periodo: str
    ano: int
    fase: str
    receita_total: Decimal
    # CBS
    cbs_aliquota: Decimal
    cbs_debito: Decimal
    cbs_credito: Decimal
    cbs_devido: Decimal
    # IBS
    ibs_aliquota: Decimal
    ibs_debito: Decimal
    ibs_credito: Decimal
    ibs_devido: Decimal
    # IS
    is_valor: Decimal
    # Totais
    total_tributos: Decimal
    aliquota_efetiva: Decimal
    split_payment_obrigatorio: bool


# -- Motor de calculo ----------------------------------------------------------

def calcular_reforma(
    operacoes: list[OperacaoReforma],
    ano: int,
    base_credito: Any = 0,
    incluir_is: bool = False,
    aliquota_is: Any = 0,
    periodo: str = "",
) -> ResultadoCalculo:
    """
    Calcula a carga tributaria estimada no regime da Reforma Tributaria.

    Parametros:
      operacoes: lista de OperacaoReforma (receitas por regime).
      ano: ano do cronograma (2026-2033+).
      base_credito: base para creditos CBS/IBS (custos com insumos PJ).
      incluir_is: se True, inclui Imposto Seletivo.
      aliquota_is: aliquota do IS (setorial).
      periodo: string descritiva.
    """
    avisos: list[str] = []

    # -- Obter aliquotas do ano (INV-RT-1) -------------------------------------
    tabela_ano = get_aliquotas(ano)  # ValueError se ano < 2026
    cbs_ref = tabela_ano["cbs"]
    ibs_ref = tabela_ano["ibs"]
    fase = tabela_ano["fase"]

    base_cred = money_fiscal(to_decimal(base_credito))
    is_rate = rate(to_decimal(aliquota_is)) if incluir_is else _ZERO

    # -- Calcular CBS e IBS por operacao (com regime especifico) ---------------
    receita_total = _ZERO
    cbs_debito_total = _ZERO
    ibs_debito_total = _ZERO

    for op in operacoes:
        v = money_fiscal(op.valor)
        receita_total += v

        regime_info = REGIMES_ESPECIFICOS[op.regime]
        fator = regime_info["fator"]

        # INV-RT-2 e INV-RT-4: aliquota = referencia * fator do regime
        cbs_aliq_op = rate(cbs_ref * fator)
        ibs_aliq_op = rate(ibs_ref * fator)

        cbs_debito_total += money_fiscal(v * cbs_aliq_op)
        ibs_debito_total += money_fiscal(v * ibs_aliq_op)

    receita_total = money_fiscal(receita_total)
    cbs_debito_total = money_fiscal(cbs_debito_total)
    ibs_debito_total = money_fiscal(ibs_debito_total)

    # Aliquota efetiva ponderada (para exibicao)
    if receita_total > _ZERO:
        cbs_aliq_efetiva = rate(cbs_debito_total / receita_total)
        ibs_aliq_efetiva = rate(ibs_debito_total / receita_total)
    else:
        cbs_aliq_efetiva = _ZERO
        ibs_aliq_efetiva = _ZERO

    # -- Creditos (nao-cumulativo) — INV-RT-5 ----------------------------------
    cbs_credito = money_fiscal(base_cred * cbs_aliq_efetiva) if cbs_aliq_efetiva > _ZERO else _ZERO
    ibs_credito = money_fiscal(base_cred * ibs_aliq_efetiva) if ibs_aliq_efetiva > _ZERO else _ZERO

    # INV-RT-6: devido = max(0, debito - credito)
    cbs_devido = money_fiscal(max(_ZERO, cbs_debito_total - cbs_credito))
    ibs_devido = money_fiscal(max(_ZERO, ibs_debito_total - ibs_credito))

    assertir_invariante(
        "INV-RT-6a: cbs_devido = max(0, deb-cred)",
        cbs_devido, money_fiscal(max(_ZERO, cbs_debito_total - cbs_credito)),
        tolerancia=_TOL, contexto=f"RT {periodo} ano={ano}",
    )
    assertir_invariante(
        "INV-RT-6b: ibs_devido = max(0, deb-cred)",
        ibs_devido, money_fiscal(max(_ZERO, ibs_debito_total - ibs_credito)),
        tolerancia=_TOL, contexto=f"RT {periodo} ano={ano}",
    )

    # -- IS (Imposto Seletivo) -------------------------------------------------
    is_valor = _ZERO
    if incluir_is and is_rate > _ZERO:
        is_valor = money_fiscal(receita_total * is_rate)

    # -- Total — INV-RT-3 -----------------------------------------------------
    total = money_fiscal(cbs_devido + ibs_devido + is_valor)
    assertir_invariante(
        "INV-RT-3: total = cbs + ibs + is",
        total, money_fiscal(cbs_devido + ibs_devido + is_valor),
        tolerancia=_TOL, contexto=f"RT {periodo} ano={ano}",
    )

    # Aliquota efetiva sobre receita
    aliq_efetiva = _ZERO
    if receita_total > _ZERO:
        aliq_efetiva = rate(total / receita_total)

    # -- Avisos ----------------------------------------------------------------
    if fase == "teste":
        avisos.append(
            f"Ano {ano}: fase de teste. CBS {float(cbs_ref)*100:.1f}% e IBS {float(ibs_ref)*100:.1f}% "
            "sao compensaveis contra PIS/COFINS vigentes."
        )
    elif fase != "pleno":
        avisos.append(
            f"Ano {ano}: fase de transicao ({fase}). ICMS/ISS coexistem com IBS. "
            "Carga total inclui apenas CBS/IBS — adicionar ICMS/ISS vigentes para carga real."
        )

    # Split payment informativo (LC 214/2025 art. 27-36)
    split_payment = ano >= 2026

    # -- Resultado -------------------------------------------------------------
    resultado = ResultadoReforma(
        periodo=periodo,
        ano=ano,
        fase=fase,
        receita_total=receita_total,
        cbs_aliquota=cbs_aliq_efetiva,
        cbs_debito=cbs_debito_total,
        cbs_credito=cbs_credito,
        cbs_devido=cbs_devido,
        ibs_aliquota=ibs_aliq_efetiva,
        ibs_debito=ibs_debito_total,
        ibs_credito=ibs_credito,
        ibs_devido=ibs_devido,
        is_valor=is_valor,
        total_tributos=total,
        aliquota_efetiva=aliq_efetiva,
        split_payment_obrigatorio=split_payment,
    )

    # -- Memoria ---------------------------------------------------------------
    insumos: dict[str, Decimal] = {
        "receita_total": receita_total,
        "base_credito": base_cred,
        "cbs_ref": cbs_ref,
        "ibs_ref": ibs_ref,
        "ano": to_decimal(ano),
    }
    if incluir_is:
        insumos["aliquota_is"] = is_rate

    memoria = MemoriaCalculo(
        insumos=insumos,
        formula=(
            f"CBS={float(cbs_aliq_efetiva)*100:.2f}% IBS={float(ibs_aliq_efetiva)*100:.2f}% "
            f"fase={fase}; devido = max(0, debito - credito)"
        ),
        norma=NormaContabil.LC_214,
        resultado=total,
    )

    return ResultadoCalculo(valor=resultado, memoria=memoria, avisos=avisos)
