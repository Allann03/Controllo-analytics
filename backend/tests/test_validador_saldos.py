"""
Sessão 18 — Testes do validador de saldos.

Cobre os 4 checks (saldo total, saldos diários, continuidade, datas) e a
classificação (VERDE/AMARELO/VERMELHO).
"""
from __future__ import annotations

from datetime import date

import pytest

from services.validacao.validador_saldos import validar_extracao
from services.validacao.classificador_confianca import classificar


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def tx(data, valor, tipo):
    return {'data': data, 'valor': valor, 'tipo': tipo, 'descricao': 'x'}


# ─────────────────────────────────────────────────────────────────────────────
# Testes do validador
# ─────────────────────────────────────────────────────────────────────────────

def test_extrato_perfeito_verde():
    """SI + entradas - saídas = SF, sem saldos diários, datas no período → VERDE."""
    transacoes = [
        tx('05/01/2026', 1000.00, 'entrada'),
        tx('06/01/2026',  300.00, 'saida'),
    ]
    r = validar_extracao(
        transacoes=transacoes,
        saldo_inicial=500.00,
        saldo_final=1200.00,
        periodo_inicio='01/01/2026',
        periodo_fim='31/01/2026',
    )
    assert r['saldo_total_ok'] is True
    assert r['saldo_total_gap'] == 0.00
    assert r['datas_ok'] is True
    nivel, diag = classificar(r)
    assert nivel == 'VERDE'
    assert 'reconciliada' in diag.lower()


def test_saldo_total_falha_vermelho():
    """SI + tx ≠ SF → VERMELHO."""
    transacoes = [tx('05/01/2026', 1000.00, 'entrada')]
    r = validar_extracao(
        transacoes=transacoes,
        saldo_inicial=500.00,
        saldo_final=999.99,  # devia ser 1500 — gap=-499.99
    )
    assert r['saldo_total_ok'] is False
    assert abs(r['saldo_total_gap'] - 500.01) < 0.01
    nivel, _ = classificar(r)
    assert nivel == 'VERMELHO'


def test_um_dia_divergente_amarelo():
    """Saldo total OK, 1 dia com gap > 0.01 → AMARELO."""
    transacoes = [
        tx('05/01/2026',  100.00, 'entrada'),
        tx('06/01/2026',   50.00, 'saida'),
    ]
    saldos_diarios = {
        date(2026, 1, 5): {'si': 0.00,    'sf': 100.00},
        # bug "intencional": SF do dia 6 não bate com 100 - 50 = 50 (deveria ser 50, mas vem 60)
        date(2026, 1, 6): {'si': 100.00,  'sf':  60.00},
    }
    r = validar_extracao(
        transacoes=transacoes,
        saldo_inicial=0.00,
        saldo_final=50.00,  # SF total bate (0 + 100 - 50 = 50)
        saldos_diarios=saldos_diarios,
    )
    assert r['saldo_total_ok'] is True
    assert r['saldos_diarios_ok'] is False
    assert len(r['dias_suspeitos']) == 1
    assert r['dias_suspeitos'][0]['data'] == date(2026, 1, 6)
    nivel, _ = classificar(r)
    assert nivel == 'AMARELO'


def test_multiplos_dias_divergentes_amarelo():
    """Saldo total OK, ≥2 dias divergentes → AMARELO + lista com tamanho > 1."""
    transacoes = []
    saldos_diarios = {
        date(2026, 1, 5): {'si': 0.00, 'sf':  10.00},   # bug: sem tx, sf devia=0
        date(2026, 1, 6): {'si': 10.00, 'sf':  20.00},  # bug: sem tx, sf devia=10
    }
    r = validar_extracao(
        transacoes=transacoes,
        saldo_inicial=0.00,
        saldo_final=0.00,
        saldos_diarios=saldos_diarios,
    )
    assert r['saldo_total_ok'] is True
    assert r['saldos_diarios_ok'] is False
    assert len(r['dias_suspeitos']) >= 2
    nivel, _ = classificar(r)
    assert nivel == 'AMARELO'


def test_ruptura_continuidade_amarelo():
    """SF do dia A ≠ SI do dia B → ruptura → AMARELO."""
    transacoes = []
    saldos_diarios = {
        date(2026, 1, 5): {'si': 0.00, 'sf': 0.00},
        # bug intencional: saldo da abertura do dia 6 (10) não bate com fechamento do 5 (0)
        date(2026, 1, 6): {'si': 10.00, 'sf': 10.00},
    }
    r = validar_extracao(
        transacoes=transacoes,
        saldo_inicial=0.00,
        saldo_final=10.00,  # vou ajustar: 0 + 0 (sem tx) ≠ 10 — ainda assim teríamos saldo_total falhando
        saldos_diarios=saldos_diarios,
    )
    # Para isolar a ruptura: ajustar saldo_total para que o Check 1 passe
    # (com saldo_final=0, 0+0=0=0 OK).
    r = validar_extracao(
        transacoes=transacoes,
        saldo_inicial=0.00,
        saldo_final=0.00,
        saldos_diarios=saldos_diarios,
    )
    # Saldos diários: dia 5 sem tx, sf calc=0=sf, OK; dia 6 sem tx, sf calc=10=sf, OK
    # Continuidade: sf[5]=0 ≠ si[6]=10 → ruptura
    assert r['saldo_total_ok'] is True
    assert r['saldos_diarios_ok'] is True
    assert r['continuidade_ok'] is False
    assert len(r['rupturas_continuidade']) == 1
    nivel, _ = classificar(r)
    assert nivel == 'AMARELO'


def test_data_fora_do_periodo_vermelho():
    """Tx com data < periodo_inicio → VERMELHO (Check 4)."""
    transacoes = [
        tx('15/12/2025', 100.00, 'entrada'),  # ANTES de 01/01/2026
    ]
    r = validar_extracao(
        transacoes=transacoes,
        saldo_inicial=0.00,
        saldo_final=100.00,
        periodo_inicio='01/01/2026',
        periodo_fim='31/01/2026',
    )
    assert r['saldo_total_ok'] is True
    assert r['datas_ok'] is False
    assert any(dp['motivo'] == 'antes_periodo' for dp in r['datas_problematicas'])
    nivel, _ = classificar(r)
    assert nivel == 'VERMELHO'


def test_sem_saldos_diarios_e_total_ok_verde():
    """Sem saldos_diarios e total OK → VERDE (Checks 2/3 pulados)."""
    transacoes = [tx('05/01/2026', 100.00, 'entrada')]
    r = validar_extracao(
        transacoes=transacoes,
        saldo_inicial=0.00,
        saldo_final=100.00,
    )
    assert r['saldo_total_ok'] is True
    assert r['saldos_diarios_ok'] is True   # check pulado
    assert r['continuidade_ok'] is True     # check pulado
    nivel, _ = classificar(r)
    assert nivel == 'VERDE'


def test_tolerancia_continuidade_fim_de_semana():
    """Diferença ≤ 0.50 (rendimento overnight de fim de semana) NÃO deve
    disparar ruptura."""
    transacoes = []
    saldos_diarios = {
        # sexta para segunda: rendimento de R$ 0.42 não conta como ruptura
        date(2026, 1, 9):  {'si': 1000.00, 'sf': 1000.00},
        date(2026, 1, 12): {'si': 1000.42, 'sf': 1000.42},
    }
    r = validar_extracao(
        transacoes=transacoes,
        saldo_inicial=1000.00,
        saldo_final=1000.42,
        saldos_diarios=saldos_diarios,
        # Ajusta para Check 1 passar — soma das tx=0, então sf_calc=1000 mas sf=1000.42, gap=0.42
        # Vamos relaxar o Check 1 com tolerância maior só pra isolar Check 3:
        tolerancia_saldo=0.50,
    )
    # Dia 9: sem tx, sf_calc=1000=sf OK
    # Dia 12: sem tx, sf_calc=1000.42=sf OK
    # Continuidade: sf[9]=1000.00, si[12]=1000.42, gap=+0.42 ≤ tolerancia 0.50 → OK
    assert r['continuidade_ok'] is True
    assert r['rupturas_continuidade'] == []


def test_classificador_resultado_invalido():
    """classificar com input não-dict deve retornar VERMELHO defensivamente."""
    nivel, diag = classificar(None)  # type: ignore[arg-type]
    assert nivel == 'VERMELHO'


def test_valor_assinado_sem_tipo_usa_sinal_aparente():
    """Tx sem campo 'tipo' usa o sinal numérico do 'valor' (defesa)."""
    transacoes = [
        {'data': '05/01/2026', 'valor':  100.00, 'descricao': 'sem tipo'},
        {'data': '06/01/2026', 'valor': -50.00, 'descricao': 'sem tipo, valor neg'},
    ]
    r = validar_extracao(
        transacoes=transacoes,
        saldo_inicial=0.00,
        saldo_final=50.00,
    )
    assert r['saldo_total_ok'] is True
