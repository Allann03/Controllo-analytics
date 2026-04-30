"""Sessão 19, Iter 2 — diagnóstico acionável do validador para
`santander_empresas` quando SI/SF estão ausentes (formato App).

Garante:
 1. nivel='VERMELHO' (não muda comportamento)
 2. diagnostico contém 'extrato_sem_si_sf' e mensagem humana acionável
 3. para outros bancos com SI/SF ausentes, mantém diagnóstico genérico
"""
from __future__ import annotations

from services.validacao.validador_saldos import validar_extracao
from services.validacao.classificador_confianca import classificar


def test_iter2_diagnostico_acionavel_santander_empresas():
    res = validar_extracao(
        transacoes=[{"valor": 100.0, "tipo": "entrada", "data": "01/12/2025"}],
        saldo_inicial=None,
        saldo_final=None,
        banco="santander_empresas",
    )
    nivel, diagnostico = classificar(res)
    assert nivel == "VERMELHO"
    assert "extrato_sem_si_sf" in diagnostico
    assert "Santander Empresas" in diagnostico
    assert "Consolidado Inteligente" in diagnostico


def test_iter2_outro_banco_si_sf_ausente_mantem_diag_generico():
    """Banco diferente de santander_empresas: mensagem genérica (sem
    a frase específica)."""
    res = validar_extracao(
        transacoes=[{"valor": 100.0, "tipo": "entrada", "data": "01/12/2025"}],
        saldo_inicial=None,
        saldo_final=None,
        banco="bradesco",
    )
    nivel, diagnostico = classificar(res)
    assert nivel == "VERMELHO"
    assert "extrato_sem_si_sf" not in diagnostico
    # Mensagem genérica padrão
    assert "saldo inicial ou final ausente" in diagnostico


def test_iter2_banco_none_si_sf_ausente_mantem_diag_generico():
    """Sem `banco` informado (compat retroativa): mensagem genérica."""
    res = validar_extracao(
        transacoes=[{"valor": 100.0, "tipo": "entrada", "data": "01/12/2025"}],
        saldo_inicial=None,
        saldo_final=None,
    )
    nivel, diagnostico = classificar(res)
    assert nivel == "VERMELHO"
    assert "extrato_sem_si_sf" not in diagnostico
    assert "saldo inicial ou final ausente" in diagnostico


def test_iter2_santander_empresas_com_saldos_validos_e_verde():
    """Quando SI/SF presentes e equação bate, mesmo com banco=santander_empresas
    o nível continua VERDE (a mensagem específica não aparece)."""
    res = validar_extracao(
        transacoes=[{"valor": 100.0, "tipo": "entrada", "data": "01/12/2025"}],
        saldo_inicial=0.0,
        saldo_final=100.0,
        banco="santander_empresas",
    )
    nivel, diagnostico = classificar(res)
    assert nivel == "VERDE"
    assert "extrato_sem_si_sf" not in diagnostico
