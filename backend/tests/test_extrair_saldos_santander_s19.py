"""Sessão 19 — testes para `_extrair_saldos_pdf` nas 3 variantes Santander.

- Iter 1: branch `santander_ib_novo` (Saldo do dia mais antigo/recente).
- Iter 3: fallback A (saldo_do_dia_por_dia, com ajuste SI = saldo - net_tx_d_min).
- Iter 3: fallback B (tabela_aplicativo_saldo_coluna, MARTINS).
- Iter 4: fallback B com `fim is None` preserva SI extraído por SALDO ANTERIOR.

Os testes usam PDFs reais em `tests/fixtures/pdfs_reais/` (gitignored). Se a
pasta não estiver presente, os testes são pulados.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from services.extrator_pdf import _extrair_saldos_pdf

PDFS_DIR = Path(__file__).parent / "fixtures" / "pdfs_reais"


def _pdf_or_skip(nome: str) -> Path:
    p = PDFS_DIR / nome
    if not p.exists():
        pytest.skip(f"PDF real {nome} ausente em {PDFS_DIR}")
    return p


# ─── Iter 1 — santander_ib_novo ─────────────────────────────────────────────


def test_iter1_ib_n2_si_sf_zero():
    """VILA PET IB N2 — todos 'Saldo do dia' são 0,00, SI=SF=0,00."""
    pdf = _pdf_or_skip("Santander Internet Banking N2.pdf")
    si, sf = _extrair_saldos_pdf(str(pdf), banco_key="santander_ib_novo")
    assert si is not None and abs(float(si) - 0.0) < 0.01
    assert sf is not None and abs(float(sf) - 0.0) < 0.01


def test_iter1_ib_n3_si_sf_zero():
    """VILA PET IB N3 — mesmo padrão de IB N2."""
    pdf = _pdf_or_skip("Santander Internet Banking N3.pdf")
    si, sf = _extrair_saldos_pdf(str(pdf), banco_key="santander_ib_novo")
    assert si is not None and abs(float(si) - 0.0) < 0.01
    assert sf is not None and abs(float(sf) - 0.0) < 0.01


# ─── Iter 3 — fallback A (saldo_do_dia_por_dia) ─────────────────────────────


def test_iter3_fallback_a_kks_si_ajustado():
    """KKS PROMOCOES (santander problema.pdf) — fallback A com ajuste de SI.
    SI = saldo_dia(D_min) - net_tx(D_min) = 9260,22 - (-1999,79) = 11260,01.
    SF = saldo_dia(D_max) = 7961,52.
    """
    pdf = _pdf_or_skip("santander problema.pdf")
    si, sf = _extrair_saldos_pdf(str(pdf), banco_key="santander")
    assert si is not None and abs(float(si) - 11260.01) < 0.02
    assert sf is not None and abs(float(sf) - 7961.52) < 0.02


# ─── Iter 3 — fallback B (tabela_aplicativo_saldo_coluna) ───────────────────


def test_iter3_fallback_b_martins_si_sf():
    """MARTINS (Santander empresas 2.pdf) — Aplicativo Santander Empresas
    com tabela 'Data Histórico Documento Valor (R$) Saldo (R$)'.
    SI = saldo da última linha do PDF onde data == D_min, MENOS valor:
       SI = 39,61 - (-353,35) = 392,96.
    SF = saldo da primeira linha do PDF onde data == D_max:
       SF = 1,07 (16/12/2025 Pagamento Cartao -300,00 1,07).
    """
    pdf = _pdf_or_skip("Santander empresas 2.pdf")
    si, sf = _extrair_saldos_pdf(str(pdf), banco_key="santander")
    assert si is not None and abs(float(si) - 392.96) < 0.02
    assert sf is not None and abs(float(sf) - 1.07) < 0.02


# ─── Iter 4 — fallback B com `fim is None` preservando SI ──────────────────


def test_iter4_dls_preserva_si_saldo_anterior_e_extrai_sf_zero():
    """DLS AGENCIA dez/25 — SALDO ANTERIOR=0,00 (extraído pelo branch
    principal). Fallback B agora dispara mesmo com `ini` extraído (porque
    `fim is None`) e calcula SF=0,00 (saldo da última linha do 31/12,
    `RESGATE CONTAMAX 2.000,00 0,00`). Antes da Iter 4 SF era calculado
    pelo pipeline como -919,52 (VERDE FAKE)."""
    pdf = _pdf_or_skip("Santander DLS 13006797-5.pdf")
    si, sf = _extrair_saldos_pdf(str(pdf), banco_key="santander")
    # SI preservado do "SALDO ANTERIOR"
    assert si is not None and abs(float(si) - 0.0) < 0.01
    # SF = saldo da última linha do PDF data 31/12/2025 = 0,00
    assert sf is not None and abs(float(sf) - 0.0) < 0.01


def test_iter4_ib_n1_cw_tour_preserva_si_5084_e_extrai_sf_zero():
    """IB N1 CW TOUR fev/26 — SALDO ANTERIOR=50,84. SF real = 0,00 (saldo
    da última linha do 20/02 'APLICACAO CONTAMAX -230,33 0,00'). Antes da
    Iter 4 SF era 271.580,33 (VERDE FAKE matemático)."""
    pdf = _pdf_or_skip("Santander Internet Banking N1.pdf")
    si, sf = _extrair_saldos_pdf(str(pdf), banco_key="santander")
    assert si is not None and abs(float(si) - 50.84) < 0.02
    assert sf is not None and abs(float(sf) - 0.0) < 0.01
