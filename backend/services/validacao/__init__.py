# Sessão 18: módulo de validação de extrações.
#
# Expõe `validar_extracao` (4 checks: saldo total, saldos diários,
# continuidade, datas) e `classificar` (VERDE/AMARELO/VERMELHO + diagnóstico).
from .validador_saldos import validar_extracao
from .classificador_confianca import classificar

__all__ = ['validar_extracao', 'classificar']
