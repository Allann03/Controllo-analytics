"""
Motor de calculo do Simples Nacional (LC 123/2006).

Modulo isolado — depende apenas de services.contabil.core e constantes legadas.
Sem dependencia de database, models, routers, ou qualquer ORM.

Correcoes sobre o motor legado:
  - Decimal + money_fiscal em toda aritmetica (R3)
  - Fator R automatico: folha_12m / rbt12 >= 0.28 -> Anexo III (LC 123/2006 par. 5-J)
  - Sublimite estadual/municipal: ISS/ICMS zerados quando RBT12 > R$3.6M (par. 20)
  - ResultadoCalculo com MemoriaCalculo auditavel
  - Tabelas versionadas em Decimal (convertidas uma unica vez na inicializacao)
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
from services.tributario.constantes import (
    SIMPLES_ANEXOS,
    SIMPLES_ANEXOS_DESC,
)

_ZERO = Decimal("0")
_TETO_SIMPLES = Decimal("4800000")
_SUBLIMITE = Decimal("3600000")
_FATOR_R_THRESHOLD = Decimal("0.28")  # >= 0.28 redireciona V -> III (LC 123/2006 par. 5-J)
_TOL_RATE = rate("0.000001")
_TOL_MONEY = money_fiscal("0.01")


# -- Tabelas convertidas para Decimal (uma unica vez na inicializacao) ---------

@dataclass(frozen=True)
class FaixaSimples:
    limite: Decimal
    aliquota_nominal: Decimal
    deducao: Decimal
    label: str


def _converter_tabela(tabela_float: list) -> list[FaixaSimples]:
    """Converte tabela legada (float) para FaixaSimples (Decimal)."""
    return [
        FaixaSimples(
            limite=to_decimal(limite),
            aliquota_nominal=rate(nominal),
            deducao=to_decimal(deducao),
            label=label,
        )
        for limite, nominal, deducao, label in tabela_float
    ]


# Tabelas Decimal — inicializadas uma unica vez no import do modulo
TABELAS: dict[str, list[FaixaSimples]] = {
    anexo: _converter_tabela(faixas)
    for anexo, faixas in SIMPLES_ANEXOS.items()
}

# Distribuicao do DAS por tributo (percentuais sobre o total do DAS)
# Fonte: LC 123/2006 Tabelas I-V (distribuicao media ponderada por faixa)
_DISTRIBUICAO: dict[str, dict[str, Decimal]] = {
    "I": {"IRPJ": rate("0.055"), "CSLL": rate("0.035"), "COFINS": rate("0.1274"),
           "PIS": rate("0.0276"), "CPP": rate("0.4150"), "ICMS": rate("0.3400")},
    "II": {"IRPJ": rate("0.050"), "CSLL": rate("0.035"), "COFINS": rate("0.275"),
            "PIS": rate("0.059"), "CPP": rate("0.430"), "IPI": rate("0.025"), "ICMS": rate("0.126")},
    "III": {"IRPJ": rate("0.045"), "CSLL": rate("0.090"), "COFINS": rate("0.287"),
             "PIS": rate("0.062"), "CPP": rate("0.434"), "ISS": rate("0.082")},
    "IV": {"IRPJ": rate("0.180"), "CSLL": rate("0.150"), "COFINS": rate("0.347"),
            "PIS": rate("0.075"), "ISS": rate("0.248")},
    "V": {"IRPJ": rate("0.150"), "CSLL": rate("0.090"), "COFINS": rate("0.287"),
           "PIS": rate("0.062"), "CPP": rate("0.257"), "ISS": rate("0.154")},
}

# Tributos sujeitos a sublimite (excluidos do DAS quando RBT12 > 3.6M)
_TRIBUTOS_SUBLIMITE = frozenset({"ISS", "ICMS"})


# -- Estruturas ----------------------------------------------------------------

@dataclass
class ResultadoSimples:
    """Resultado detalhado do calculo do Simples Nacional."""
    regime: str                         # "simples"
    anexo: str                          # anexo solicitado
    anexo_efetivo: str                  # pode diferir se Fator R redirecionou
    faixa: str                          # label da faixa
    rbt12: Decimal
    receita_mensal: Decimal
    aliquota_efetiva: Decimal           # decimal (0.060000 = 6%)
    das: Decimal                        # valor do DAS mensal
    fator_r: Optional[Decimal]          # folha/receita se calculado
    fator_r_aplicado: bool              # True se V -> III
    sublimite_aplicado: bool            # True se ISS/ICMS excluidos
    detalhes: list[dict]                # breakdown por tributo


# -- Motor de calculo ----------------------------------------------------------

def calcular_simples(
    receita_mensal: Any,
    rbt12: Any = None,
    anexo: str = "III",
    folha_12m: Any = None,
    periodo: str = "",
) -> ResultadoCalculo:
    """
    Calcula o DAS do Simples Nacional para o mes.

    Parametros:
      receita_mensal: Receita bruta do mes corrente (R$).
      rbt12: Receita Bruta Acumulada 12 meses. Se None, extrapola receita_mensal * 12.
      anexo: Anexo solicitado ('I' a 'V'). Default 'III'.
      folha_12m: Folha de pagamento acumulada 12 meses (para Fator R).
      periodo: string descritiva.

    Retorna ResultadoCalculo com ResultadoSimples.
    """
    avisos: list[str] = []
    rec = money_fiscal(to_decimal(receita_mensal))
    anexo_solicitado = (anexo or "III").upper()

    # -- RBT12 -----------------------------------------------------------------
    rbt12_extrapolada = False
    if rbt12 is not None:
        rbt12_val = to_decimal(rbt12)
    else:
        rbt12_val = rec * Decimal("12")
        rbt12_extrapolada = True
        if rec > _ZERO:
            avisos.append(
                "RBT12 nao informada — extrapolada como receita_mensal * 12. "
                "Para precisao, informe a RBT12 real."
            )

    # -- Fator R (LC 123/2006 par. 5-J) ----------------------------------------
    fator_r: Optional[Decimal] = None
    fator_r_aplicado = False
    anexo_efetivo = anexo_solicitado

    if folha_12m is not None and rbt12_val > _ZERO:
        folha = to_decimal(folha_12m)
        fator_r = rate(folha / rbt12_val) if rbt12_val > _ZERO else _ZERO

        if anexo_solicitado == "V":
            if fator_r >= _FATOR_R_THRESHOLD:
                # Fator R >= 28%: redireciona para Anexo III
                anexo_efetivo = "III"
                fator_r_aplicado = True
                avisos.append(
                    f"Fator R = {float(fator_r * 100):.2f}% (>= 28%). "
                    "Redirecionado de Anexo V para Anexo III conforme LC 123/2006 par. 5-J."
                )
            else:
                avisos.append(
                    f"Fator R = {float(fator_r * 100):.2f}% (< 28%). "
                    "Permanece no Anexo V."
                )
    elif folha_12m is None and anexo_solicitado == "V":
        avisos.append(
            "Fator R nao calculado — folha de pagamento 12 meses nao informada. "
            "Usando Anexo V conforme solicitado. Se folha/receita >= 28%, "
            "o correto seria Anexo III."
        )

    # Fator R nao se aplica a Anexos I, II, III, IV
    if folha_12m is not None and anexo_solicitado not in ("V", "III"):
        # Informativo apenas
        pass

    # -- Acima do teto ---------------------------------------------------------
    if rbt12_val > _TETO_SIMPLES:
        resultado = ResultadoSimples(
            regime="simples", anexo=anexo_solicitado, anexo_efetivo=anexo_efetivo,
            faixa="Acima do limite do Simples Nacional (> R$ 4,8 mi/ano)",
            rbt12=rbt12_val, receita_mensal=rec,
            aliquota_efetiva=_ZERO, das=_ZERO,
            fator_r=fator_r, fator_r_aplicado=fator_r_aplicado,
            sublimite_aplicado=False, detalhes=[],
        )
        avisos.append("RBT12 acima de R$ 4.800.000 — empresa nao optante pelo Simples Nacional.")
        memoria = MemoriaCalculo(
            insumos={"receita_mensal": rec, "rbt12": rbt12_val},
            formula="RBT12 > 4.800.000 -> nao optante",
            norma=NormaContabil.LC_123,
            resultado=_ZERO,
        )
        return ResultadoCalculo(valor=resultado, memoria=memoria, avisos=avisos)

    # -- Receita zero ----------------------------------------------------------
    if rec <= _ZERO:
        resultado = ResultadoSimples(
            regime="simples", anexo=anexo_solicitado, anexo_efetivo=anexo_efetivo,
            faixa="Sem receita", rbt12=rbt12_val, receita_mensal=rec,
            aliquota_efetiva=_ZERO, das=_ZERO,
            fator_r=fator_r, fator_r_aplicado=fator_r_aplicado,
            sublimite_aplicado=False, detalhes=[],
        )
        memoria = MemoriaCalculo(
            insumos={"receita_mensal": rec, "rbt12": rbt12_val},
            formula="receita_mensal <= 0 -> DAS = 0",
            norma=NormaContabil.LC_123,
            resultado=_ZERO,
        )
        return ResultadoCalculo(valor=resultado, memoria=memoria, avisos=avisos)

    # -- Determinar faixa ------------------------------------------------------
    tabela = TABELAS.get(anexo_efetivo, TABELAS["III"])
    faixa_encontrada: Optional[FaixaSimples] = None

    for faixa in tabela:
        if rbt12_val <= faixa.limite:
            faixa_encontrada = faixa
            break

    if faixa_encontrada is None:
        # RBT12 entre 4.8M e algum valor — usar ultima faixa
        faixa_encontrada = tabela[-1]

    # -- Aliquota efetiva ------------------------------------------------------
    # Formula: (RBT12 * aliquota_nominal - deducao) / RBT12
    # Deducao subtrai do NUMERADOR (nao do denominador)
    numerador = rbt12_val * faixa_encontrada.aliquota_nominal - faixa_encontrada.deducao
    aliq_efetiva = rate(numerador / rbt12_val) if rbt12_val > _ZERO else _ZERO
    if aliq_efetiva < _ZERO:
        aliq_efetiva = _ZERO

    # INV-SN-1: aliquota efetiva == formula
    assertir_invariante(
        "INV-SN-1: aliquota_efetiva",
        aliq_efetiva,
        rate(max(_ZERO, numerador / rbt12_val)) if rbt12_val > _ZERO else _ZERO,
        tolerancia=_TOL_RATE,
        contexto=f"Simples {periodo} Anexo {anexo_efetivo}",
    )

    # -- DAS -------------------------------------------------------------------
    das = money_fiscal(rec * aliq_efetiva)

    # INV-SN-2: das == receita * aliquota
    assertir_invariante(
        "INV-SN-2: DAS = receita * aliquota_efetiva",
        das,
        money_fiscal(rec * aliq_efetiva),
        tolerancia=_TOL_MONEY,
        contexto=f"Simples {periodo}",
    )

    # -- Sublimite estadual/municipal (LC 123/2006 par. 20) --------------------
    sublimite_aplicado = False
    if rbt12_val > _SUBLIMITE:
        sublimite_aplicado = True
        avisos.append(
            f"Sublimite aplicado: RBT12 (R$ {float(rbt12_val):,.2f}) > R$ 3.600.000. "
            "ISS e ICMS excluidos do DAS — devem ser recolhidos separadamente."
        )

    # -- Distribuicao do DAS por tributo ---------------------------------------
    dist = _DISTRIBUICAO.get(anexo_efetivo, _DISTRIBUICAO["III"])
    detalhes = []
    soma_detalhes = _ZERO

    for tributo, pct_tributo in dist.items():
        if sublimite_aplicado and tributo in _TRIBUTOS_SUBLIMITE:
            # ISS/ICMS excluidos do DAS quando acima do sublimite
            valor_tributo = _ZERO
        else:
            valor_tributo = money_fiscal(das * pct_tributo)

        soma_detalhes += valor_tributo
        detalhes.append({
            "tributo": tributo,
            "aliquota_pct": float(pct(aliq_efetiva * pct_tributo * Decimal("100"))),
            "percentual_das": float(pct_tributo),
            "base": "receita_bruta",
            "valor": valor_tributo,
            "excluido_sublimite": sublimite_aplicado and tributo in _TRIBUTOS_SUBLIMITE,
        })

    # Quando sublimite aplicado, o DAS efetivo e menor (sem ISS/ICMS)
    das_efetivo = soma_detalhes if sublimite_aplicado else das

    # INV-SN-3: soma detalhes == DAS (sem sublimite)
    # Tolerancia proporcional ao numero de tributos: cada money_fiscal() pode
    # gerar ate 0.005 de arredondamento, com N tributos o acumulado e ate N*0.005.
    # Usamos 0.01 por tributo como margem conservadora.
    if not sublimite_aplicado:
        tol_dist = money_fiscal(Decimal(str(len(detalhes))) * Decimal("0.01"))
        assertir_invariante(
            "INV-SN-3: sum(detalhes) == DAS",
            soma_detalhes, das,
            tolerancia=tol_dist,
            contexto=f"Simples {periodo} ({len(detalhes)} tributos)",
        )

    # -- Resultado -------------------------------------------------------------
    resultado = ResultadoSimples(
        regime="simples",
        anexo=anexo_solicitado,
        anexo_efetivo=anexo_efetivo,
        faixa=faixa_encontrada.label,
        rbt12=rbt12_val,
        receita_mensal=rec,
        aliquota_efetiva=aliq_efetiva,
        das=das_efetivo,
        fator_r=fator_r,
        fator_r_aplicado=fator_r_aplicado,
        sublimite_aplicado=sublimite_aplicado,
        detalhes=detalhes,
    )

    # -- Memoria de calculo ----------------------------------------------------
    insumos: dict[str, Decimal] = {
        "receita_mensal": rec,
        "rbt12": rbt12_val,
        "aliquota_nominal": faixa_encontrada.aliquota_nominal,
        "deducao": faixa_encontrada.deducao,
    }
    if fator_r is not None:
        insumos["fator_r"] = fator_r
        insumos["folha_12m"] = to_decimal(folha_12m)

    formula = (
        f"aliq_efetiva = (RBT12 * {float(faixa_encontrada.aliquota_nominal)} "
        f"- {float(faixa_encontrada.deducao)}) / RBT12; "
        f"DAS = receita_mensal * aliq_efetiva"
    )

    memoria = MemoriaCalculo(
        insumos=insumos,
        formula=formula,
        norma=NormaContabil.LC_123,
        resultado=das_efetivo,
    )

    return ResultadoCalculo(valor=resultado, memoria=memoria, avisos=avisos)
