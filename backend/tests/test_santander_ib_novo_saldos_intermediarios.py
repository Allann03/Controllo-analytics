"""Sessão 19, Iter 1 — método novo `_extrair_saldos_intermediarios()`
no `ParserSantanderIBNovo`.

Útil para o validador da Sessão 18 fazer Check 2 (saldos diários) e
Check 3 (continuidade SF→SI). Retorna `[{data, saldo}]` em ordem
cronológica ascendente, com dedup por data.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from services.parsers.santander_ib_novo import ParserSantanderIBNovo

PDFS_DIR = Path(__file__).parent / "fixtures" / "pdfs_reais"


def _pdf_or_skip(nome: str):
    p = PDFS_DIR / nome
    if not p.exists():
        pytest.skip(f"PDF real {nome} ausente em {PDFS_DIR}")
    return p


def test_iter1_ib_n2_saldos_diarios_22_dias():
    """VILA PET IB N2 — 22 dias com saldo diário (quase todos 0,00 por
    causa do padrão contamax). Garante que o método retorna a quantidade
    correta de dias e que está em ordem cronológica ASC."""
    pdf = _pdf_or_skip("Santander Internet Banking N2.pdf")
    parser = ParserSantanderIBNovo(str(pdf), password=None)
    saldos = parser._extrair_saldos_intermediarios()
    assert len(saldos) == 22
    # Maioria absoluta dos dias zerados (>= 90%)
    zerados = sum(1 for s in saldos if abs(s["saldo"]) < 0.01)
    assert zerados >= len(saldos) * 0.9, f"esperava >= 90% zerados, obteve {zerados}/{len(saldos)}"
    # Ordem ASC cronologica
    datas = [s["data"] for s in saldos]
    assert datas[0] == "02/01/2025"
    assert datas[-1] == "31/01/2025"


def test_iter1_ib_n3_saldos_diarios_20_dias():
    """VILA PET IB N3 — 20 dias com saldo, um deles (24/02) tem 70,00."""
    pdf = _pdf_or_skip("Santander Internet Banking N3.pdf")
    parser = ParserSantanderIBNovo(str(pdf), password=None)
    saldos = parser._extrair_saldos_intermediarios()
    assert len(saldos) == 20
    # Encontra dia 24/02 com saldo 70,00
    s_24 = next((s for s in saldos if s["data"] == "24/02/2025"), None)
    assert s_24 is not None
    assert abs(s_24["saldo"] - 70.0) < 0.01
    # Restante todos zerados
    for s in saldos:
        if s["data"] != "24/02/2025":
            assert abs(s["saldo"] - 0.0) < 0.01
