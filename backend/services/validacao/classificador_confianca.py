"""
Sessão 18 — Classificador de confiança da extração.

Decide nível final (VERDE/AMARELO/VERMELHO) com base no `ResultadoValidacao`
produzido por `validador_saldos.validar_extracao`.

Regras (ordem importa):
  - VERMELHO se Check 1 (saldo total) falhar
  - VERMELHO se Check 4 (datas) falhar
  - AMARELO se Check 2 (saldos diários) falhar com Check 1 OK
  - AMARELO se Check 3 (continuidade) falhar com Check 1 OK
  - VERDE caso contrário
"""
from __future__ import annotations


def classificar(resultado_validacao: dict) -> tuple[str, str]:
    """Retorna (nivel, diagnostico) para uso no log e no JSON do endpoint.

    `nivel` em {'VERDE', 'AMARELO', 'VERMELHO'}.
    `diagnostico` é a frase curta vinda do validador (PT-BR).
    """
    if not isinstance(resultado_validacao, dict):
        return 'VERMELHO', 'resultado_validacao ausente.'

    saldo_total_ok = bool(resultado_validacao.get('saldo_total_ok', False))
    datas_ok = bool(resultado_validacao.get('datas_ok', True))
    saldos_diarios_ok = bool(resultado_validacao.get('saldos_diarios_ok', True))
    continuidade_ok = bool(resultado_validacao.get('continuidade_ok', True))

    diagnostico = str(resultado_validacao.get('diagnostico', '')) or 'sem diagnóstico'

    if not saldo_total_ok:
        return 'VERMELHO', diagnostico
    if not datas_ok:
        return 'VERMELHO', diagnostico
    if not saldos_diarios_ok:
        return 'AMARELO', diagnostico
    if not continuidade_ok:
        return 'AMARELO', diagnostico
    return 'VERDE', diagnostico
