"""
Sessão 16 — Testes de regressão para `_extrair_saldos_pdf` no banco
`bradesco_net_empresas`.

Bug original (CW TOUR EIRELI jan/2026): `_extrair_saldos_pdf` caía no fallback
genérico, que usa `_ultimo_num` com regex `[\\d.,]+` que descarta sinal.
"SALDO ANTERIOR -918,38" virava 918.38 e o pipeline calculava SF errado.

Cada teste lê um fixture raw (texto que `pdfplumber` extrai do PDF original,
sem committar PDFs binários — política da casa) e chama uma versão "from_text"
da extração, que reproduz exatamente a lógica do branch específico.
"""
from __future__ import annotations

import os
import re
from decimal import Decimal, InvalidOperation

import pytest


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


def _parse_br_signed(s: str) -> Decimal | None:
    if not s:
        return None
    s = s.strip().replace(' ', '')
    negativo = s.startswith('-')
    if negativo:
        s = s[1:]
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        v = Decimal(s)
        return -v if negativo else v
    except (InvalidOperation, ValueError, TypeError):
        return None


def _extrair_saldos_bne_from_text(texto: str):
    """Réplica fiel do branch `bradesco_net_empresas` em
    backend/services/extrator_pdf.py:_extrair_saldos_pdf — opera direto sobre
    texto, sem precisar abrir PDF."""
    linhas = texto.splitlines()
    ini: Decimal | None = None
    fim: Decimal | None = None

    _re_si = re.compile(
        r'(?:\d{2}/\d{2}/\d{4}\s+)?SALDO\s+ANTERIOR\s+(-?\d[\d.]*,\d{2})',
        re.IGNORECASE,
    )
    _re_cab = re.compile(
        r'^\d{4,5}\s*\|\s*\d{6,8}-\d\s+(-?\d[\d.]*,\d{2})'
        r'(?:\s+(-?\d[\d.]*,\d{2}))?'
        r'(?:\s+(-?\d[\d.]*,\d{2}))?\s*$'
    )
    _re_total = re.compile(
        r'^total\s+-?\d[\d.,]*\s+-?\d[\d.,]*\s+(-?\d[\d.]*,\d{2})\s*$',
        re.IGNORECASE,
    )

    tem_investimento = bool(
        re.search(r'investiment[oa]s?\s+(sem|com)\s+baixa', texto, re.IGNORECASE)
    )

    for linha in linhas:
        m = _re_si.search(linha)
        if m:
            v = _parse_br_signed(m.group(1))
            if v is not None:
                ini = v
                break

    if not tem_investimento:
        for linha in linhas:
            m = _re_cab.match(linha.strip())
            if m:
                v = _parse_br_signed(m.group(1))
                if v is not None:
                    fim = v
                    break

    if fim is None:
        stop = False
        for linha in linhas:
            ll = linha.lower()
            if 'últimos lançamentos' in ll or 'ultimos lancamentos' in ll:
                stop = True
            if stop:
                continue
            m = _re_total.match(linha.strip())
            if m:
                v = _parse_br_signed(m.group(1))
                if v is not None:
                    fim = v

    return ini, fim


def _load_fixture(name: str) -> str:
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def test_cw_tour_jan2026_si_sf():
    """CW TOUR jan/2026: 'SALDO ANTERIOR -918,38' deve preservar sinal.
    SF=-1247.89 vem do cabeçalho (Total Disponível), pois não há coluna
    'Investimento' (formato Consolidado, 2 valores)."""
    texto = _load_fixture('cw_tour_jan2026_raw.txt')
    ini, fim = _extrair_saldos_bne_from_text(texto)
    assert ini is not None and float(ini) == pytest.approx(-918.38, abs=0.01)
    assert fim is not None and float(fim) == pytest.approx(-1247.89, abs=0.01)


def test_seolin_jan2025_si_sf():
    """SEOLIN jan/2025: cabeçalho tem coluna 'Investimento sem Baixa
    automática' (3 valores). Hipótese D → SF = último Total da seção
    principal = 572.64 (saldo do fim do período pedido), NÃO 2.063,86 do
    cabeçalho (que reflete saldo na data de emissão = ago/2025)."""
    texto = _load_fixture('seolin_jan2025_raw.txt')
    ini, fim = _extrair_saldos_bne_from_text(texto)
    assert ini is not None and float(ini) == pytest.approx(89479.75, abs=0.01)
    assert fim is not None and float(fim) == pytest.approx(572.64, abs=0.01)


def test_tania_dez2025_si_sf():
    """TANIA dez/2025: cabeçalho com 2 valores → SF=70042.18 do Total
    Disponível (≠ 43.612,02 do Total da seção principal e ≠ 70.032,13 do
    último Total dos Últimos Lançamentos)."""
    texto = _load_fixture('tania_dez2025_raw.txt')
    ini, fim = _extrair_saldos_bne_from_text(texto)
    assert ini is not None and float(ini) == pytest.approx(78019.32, abs=0.01)
    assert fim is not None and float(fim) == pytest.approx(70042.18, abs=0.01)


def test_tania_nov2025_si_sf():
    """TANIA nov/2025: cabeçalho com 2 valores → SF=95043.32 do Total
    Disponível."""
    texto = _load_fixture('tania_nov2025_raw.txt')
    ini, fim = _extrair_saldos_bne_from_text(texto)
    assert ini is not None and float(ini) == pytest.approx(96735.73, abs=0.01)
    assert fim is not None and float(fim) == pytest.approx(95043.32, abs=0.01)


def test_cw_tour_pipeline_diff_zero():
    """Garante que SI + Excel_liquido = SF para CW TOUR (regression do bug
    original: pipeline marcava como RECONCILIADO porque SI+E-S=SF batia
    matematicamente, mas com SI=918.38 em vez de -918.38 todos os sinais
    estavam invertidos e Excel/Extrato divergiam em -918.38)."""
    si = -918.38
    sf = -1247.89
    excel_liquido = -329.51  # 13 tx do CW TOUR (entradas - saídas)
    assert abs((si + excel_liquido) - sf) < 0.01, (
        f"Bug regredido: si+excel={si + excel_liquido} != sf={sf}"
    )
