"""
Score de Saude Financeira — nota de 0 a 100.

9 componentes pesados conforme Adendo A.5.3:
  Liquidez Corrente (15), Liquidez Seca (10), Endividamento Geral (15),
  Margem Liquida (15), ROE (10), Ciclo Financeiro (10),
  Tendencia Receita (10), Regularidade Fiscal (10), Cobertura Juros (5).
Total = 100.

Correcoes sobre o legado:
  - MEDIO-1: branch inalcancavel corrigido
  - ALTO-SCORE-1: float -> Decimal
  - MEDIO-SCORE-2: pesos documentados
  - MEDIO-SCORE-3: Cobertura de Juros adicionada
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from services.contabil.core import money, to_decimal, MemoriaCalculo, ResultadoCalculo, NormaContabil, VERSAO_CALCULO
from services.contabil import indicadores as ind

_ZERO = Decimal("0")

# Pesos documentados (Adendo A.5.3) — total = 100
PESOS: dict[str, int] = {
    "liquidez_corrente": 15,
    "liquidez_seca": 10,
    "endividamento_geral": 15,
    "margem_liquida": 15,
    "roe": 10,
    "ciclo_financeiro": 10,
    "tendencia_receita": 10,
    "regularidade_fiscal": 10,
    "cobertura_juros": 5,
}
assert sum(PESOS.values()) == 100, "Pesos devem somar 100"


@dataclass
class ResultadoScore:
    total: int
    classificacao: str
    componentes: dict[str, int]
    detalhes: dict[str, str]


# -- Funcoes de normalizacao (0-100 por componente) ----------------------------

def _score_liquidez_corrente(val: Optional[Decimal]) -> int:
    if val is None or val < Decimal("0.5"):
        return 0
    if val < Decimal("1"):
        return 30
    if val < Decimal("1.5"):
        return 60
    if val < Decimal("2.5"):
        return 85
    return 100


def _score_liquidez_seca(val: Optional[Decimal]) -> int:
    if val is None or val < Decimal("0.3"):
        return 0
    if val < Decimal("0.7"):
        return 30
    if val < Decimal("1"):
        return 60
    if val < Decimal("1.5"):
        return 85
    return 100


def _score_endividamento(val: Optional[Decimal]) -> int:
    """Endividamento em %: menor e melhor."""
    if val is None:
        return 50
    if val > Decimal("80"):
        return 0
    if val > Decimal("60"):
        return 30
    if val > Decimal("40"):
        return 60
    if val > Decimal("20"):
        return 80
    return 100


def _score_margem_liquida(val: Optional[Decimal]) -> int:
    if val is None or val < _ZERO:
        return 0
    if val < Decimal("5"):
        return 30
    if val < Decimal("10"):
        return 60
    if val < Decimal("20"):
        return 80
    return 100


def _score_roe(val: Optional[Decimal]) -> int:
    if val is None or val < _ZERO:
        return 0
    if val < Decimal("5"):
        return 30
    if val < Decimal("10"):
        return 60
    if val < Decimal("20"):
        return 80
    return 100


def _score_ciclo_financeiro(val: Optional[Decimal]) -> int:
    """Ciclo em dias: menor e melhor."""
    if val is None:
        return 50
    if val > Decimal("120"):
        return 0
    if val > Decimal("90"):
        return 30
    if val > Decimal("60"):
        return 60
    if val > Decimal("30"):
        return 80
    return 100


def _score_tendencia_receita(receitas: list) -> int:
    """Avalia tendencia de crescimento/queda nos ultimos meses.
    Corrige MEDIO-1: usa ate 6 meses para permitir quedas >= 3."""
    if not receitas or len(receitas) < 2:
        return 50  # sem dados suficientes = neutro

    ultimos = receitas[-6:] if len(receitas) >= 6 else receitas
    quedas = 0
    for i in range(1, len(ultimos)):
        if to_decimal(ultimos[i]) < to_decimal(ultimos[i - 1]):
            quedas += 1

    if quedas >= 4:
        return 0
    if quedas >= 3:
        return 20
    if quedas >= 2:
        return 40
    if quedas >= 1:
        return 70
    return 100


def _score_regularidade_fiscal(tributos_em_dia: bool = True) -> int:
    """Indicador binario: tributos em dia = 100, inadimplente = 0."""
    return 100 if tributos_em_dia else 0


def _score_cobertura_juros(val: Optional[Decimal]) -> int:
    """Cobertura = EBIT / Desp.Financeiras. Maior e melhor."""
    if val is None:
        return 50  # sem desp financeiras = neutro
    if val < Decimal("1"):
        return 0
    if val < Decimal("1.5"):
        return 30
    if val < Decimal("3"):
        return 60
    if val < Decimal("5"):
        return 80
    return 100


# -- Classificacao -------------------------------------------------------------

def _classificar(total: int) -> str:
    if total >= 80:
        return "Excelente"
    if total >= 60:
        return "Bom"
    if total >= 40:
        return "Regular"
    return "Critico"


# -- Motor principal -----------------------------------------------------------

def calcular_score(
    dados: dict[str, Any],
    historico_receitas: Optional[list] = None,
    tributos_em_dia: bool = True,
    periodo: str = "",
) -> ResultadoCalculo:
    """
    Calcula score de saude financeira 0-100.

    Parametros:
      dados: dict com campos de _lanc_to_metricas ou equivalente.
      historico_receitas: lista de receitas brutas dos ultimos meses.
      tributos_em_dia: indicador de regularidade fiscal.
      periodo: string descritiva.
    """
    _get = lambda k: to_decimal(dados.get(k, 0) or 0)

    # Calcular indicadores usando motores canonicos
    lc = ind.liquidez_corrente(_get("ativo_circulante"), _get("passivo_circulante"))
    ls = ind.liquidez_seca(_get("ativo_circulante"), _get("estoques"), _get("passivo_circulante"))
    eg = ind.endividamento_geral(_get("passivo_total"), _get("ativo_total"))
    ml = ind.margem_liquida(_get("resultado_liquido") or _get("lucro_liquido"), _get("receita_liquida"))
    r = ind.roe(_get("resultado_liquido") or _get("lucro_liquido"), _get("patrimonio_liquido"))

    pmr_v = ind.pmr(_get("contas_receber"), _get("receita_bruta"))
    pme_v = ind.pme(_get("estoques"), _get("custo_servicos"))
    pmp_v = ind.pmp(_get("fornecedores"), _get("custo_servicos"))
    cf = ind.ciclo_financeiro(pmr_v.valor, pme_v.valor, pmp_v.valor)
    cj = ind.cobertura_juros(_get("ebit"), _get("despesas_financeiras"))

    # Scores por componente
    componentes: dict[str, int] = {}
    detalhes: dict[str, str] = {}

    componentes["liquidez_corrente"] = _score_liquidez_corrente(lc.valor)
    detalhes["liquidez_corrente"] = f"LC={lc.valor}" if lc.valor else "Indisponivel"

    componentes["liquidez_seca"] = _score_liquidez_seca(ls.valor)
    detalhes["liquidez_seca"] = f"LS={ls.valor}" if ls.valor else "Indisponivel"

    componentes["endividamento_geral"] = _score_endividamento(eg.valor)
    detalhes["endividamento_geral"] = f"EG={eg.valor}%" if eg.valor else "Indisponivel"

    componentes["margem_liquida"] = _score_margem_liquida(ml.valor)
    detalhes["margem_liquida"] = f"ML={ml.valor}%" if ml.valor else "Indisponivel"

    componentes["roe"] = _score_roe(r.valor)
    detalhes["roe"] = f"ROE={r.valor}%" if r.valor else "Indisponivel"

    componentes["ciclo_financeiro"] = _score_ciclo_financeiro(cf.valor)
    detalhes["ciclo_financeiro"] = f"CF={cf.valor} dias" if cf.valor else "Indisponivel"

    componentes["tendencia_receita"] = _score_tendencia_receita(historico_receitas or [])
    detalhes["tendencia_receita"] = f"{len(historico_receitas or [])} meses analisados"

    componentes["regularidade_fiscal"] = _score_regularidade_fiscal(tributos_em_dia)
    detalhes["regularidade_fiscal"] = "Em dia" if tributos_em_dia else "Inadimplente"

    componentes["cobertura_juros"] = _score_cobertura_juros(cj.valor)
    detalhes["cobertura_juros"] = f"CJ={cj.valor}x" if cj.valor else "Sem desp. financeiras"

    # Score ponderado
    total_ponderado = sum(
        componentes[k] * PESOS[k] for k in PESOS
    )
    total = max(0, min(100, round(total_ponderado / 100)))

    classificacao = _classificar(total)

    resultado = ResultadoScore(
        total=total, classificacao=classificacao,
        componentes=componentes, detalhes=detalhes,
    )

    memoria = MemoriaCalculo(
        insumos={k: to_decimal(v) for k, v in componentes.items()},
        formula="Score = sum(componente_i * peso_i) / 100, clamped [0,100]",
        norma=NormaContabil.COSTUME,
        resultado=to_decimal(total),
    )

    return ResultadoCalculo(valor=resultado, memoria=memoria, avisos=[])
