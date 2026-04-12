"""
Testes do módulo tributário — Simples Nacional, Presumido, Real, Reforma.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_simples_anexo_i_distribution_sums_to_100():
    """Bug #8 corrigido: Anexo I somava 120%. Deve somar 100%."""
    from services.tributario.simples_nacional import _distribuicao_das
    for anexo in ['I', 'II', 'III', 'IV', 'V']:
        dist = _distribuicao_das(0.10, anexo)
        total = sum(dist.values())
        assert abs(total - 1.0) < 0.01, f"Anexo {anexo}: soma = {total}, esperado 1.0"


def test_simples_calculo_basico():
    """Cálculo básico do Simples Nacional."""
    from services.tributario.simples_nacional import calcular
    resultado = calcular(receita_mensal=50000, rbt12=600000, anexo='III')
    assert resultado['regime'] == 'simples'
    assert resultado['das'] > 0
    assert resultado['aliquota_efetiva_pct'] > 0
    assert resultado['total'] == resultado['das']


def test_presumido_calculo_basico():
    """Cálculo básico do Lucro Presumido."""
    from services.tributario.lucro_presumido import calcular
    resultado = calcular(receita_bruta=50000, custo_servicos=20000)
    assert resultado['regime'] == 'presumido'
    assert resultado['total'] > 0
    assert resultado['pct_receita'] > 0


def test_real_calculo_basico():
    """Cálculo básico do Lucro Real."""
    from services.tributario.lucro_real import calcular
    resultado = calcular(receita_bruta=50000, custo_servicos=20000)
    assert resultado['regime'] == 'real'
    assert resultado['total'] > 0
    assert resultado['lucro_real'] == 30000  # 50000 - 20000


def test_reforma_calculo_basico():
    """Cálculo básico da Reforma Tributária."""
    from services.tributario.reforma import calcular
    resultado = calcular(receita_bruta=50000, custo_servicos=20000)
    assert resultado['regime'] == 'reforma_tributaria'
    assert resultado['total'] > 0
