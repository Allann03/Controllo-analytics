"""
tributario/__init__.py — Módulo de cálculo tributário.

Exporta funções públicas de cada regime:
  - simples_nacional.calcular(receita_mensal, rbt12)
  - lucro_presumido.calcular(receita_bruta, custo_servicos, aliquota_iss)
  - lucro_real.calcular(receita_bruta, custo_servicos, aliquota_iss)
  - reforma.calcular(receita_bruta, custo_servicos)
  - reforma.comparar_com_regime_atual(regime_resultado, receita_bruta, custo_servicos)
"""

from .simples_nacional import calcular as calcular_simples
from .lucro_presumido import calcular as calcular_presumido
from .lucro_real import calcular as calcular_real
from .reforma import calcular as calcular_reforma, comparar_com_regime_atual
from .constantes import LABEL_REGIME, REFORMA_ALIQUOTA_TOTAL, SIMPLES_ANEXOS, SIMPLES_ANEXOS_DESC

__all__ = [
    "calcular_simples",
    "calcular_presumido",
    "calcular_real",
    "calcular_reforma",
    "comparar_com_regime_atual",
    "LABEL_REGIME",
    "REFORMA_ALIQUOTA_TOTAL",
    "SIMPLES_ANEXOS",
    "SIMPLES_ANEXOS_DESC",
]
