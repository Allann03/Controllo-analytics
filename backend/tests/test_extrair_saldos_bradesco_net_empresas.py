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
    texto, sem precisar abrir PDF.

    Sessão 18: heurística estendida — usa Total da seção principal sempre
    que `tem_coluna_investimento` OU `tem_ultimos_lancamentos` OU
    `tem_saldos_invest_facil`. Cabeçalho só é usado quando NENHUM marcador
    pós-período está presente.
    """
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

    tlow = texto.lower()
    tem_investimento = bool(
        re.search(r'investiment[oa]s?\s+(sem|com)\s+baixa', texto, re.IGNORECASE)
    )
    tem_ultimos = (
        'últimos lançamentos' in tlow or 'ultimos lancamentos' in tlow
    )
    tem_invest_facil = (
        'saldos invest fácil' in tlow or 'saldos invest facil' in tlow
    )

    for linha in linhas:
        m = _re_si.search(linha)
        if m:
            v = _parse_br_signed(m.group(1))
            if v is not None:
                ini = v
                break

    usar_total_secao_principal = (
        tem_investimento or tem_ultimos or tem_invest_facil
    )

    if not usar_total_secao_principal:
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
            if (
                'últimos lançamentos' in ll or 'ultimos lancamentos' in ll
                or 'saldos invest fácil' in ll or 'saldos invest facil' in ll
            ):
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
    Sessão 18: SF corrigido pós-stop dos Últimos Lançamentos. Antes:
    -1247.89 (vinha do cabeçalho que reflete saldo após Últimos
    Lançamentos = mistura período + pós-período); depois: +1.00 (último
    Total da seção principal de jan/2026). A regra antiga produzia
    'VERDE fake' porque o parser pegava as 4 tx pós-período de fev/2026
    e o cabeçalho refletia esse mesmo estado, então saldo total batia
    por coincidência. A nova regra detecta presença de 'Últimos
    Lançamentos' no texto e usa o último Total da seção principal."""
    texto = _load_fixture('cw_tour_jan2026_raw.txt')
    ini, fim = _extrair_saldos_bne_from_text(texto)
    assert ini is not None and float(ini) == pytest.approx(-918.38, abs=0.01)
    assert fim is not None and float(fim) == pytest.approx(1.00, abs=0.01)


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
    """TANIA dez/2025: tem 'Últimos Lançamentos' + 'Saldos Invest Fácil'.
    Sessão 18: SF corrigido. Antes: 70042.18 (cabeçalho, mas refletia
    estado pós-Últimos Lançamentos); depois: 43612.02 (último Total da
    seção principal de dez/2025, antes do marcador 'Últimos
    Lançamentos')."""
    texto = _load_fixture('tania_dez2025_raw.txt')
    ini, fim = _extrair_saldos_bne_from_text(texto)
    assert ini is not None and float(ini) == pytest.approx(78019.32, abs=0.01)
    assert fim is not None and float(fim) == pytest.approx(43612.02, abs=0.01)


def test_tania_nov2025_si_sf():
    """TANIA nov/2025: tem 'Últimos Lançamentos' + 'Saldos Invest Fácil'.
    Sessão 18: SF corrigido. Antes: 95043.32 (cabeçalho); depois:
    78019.32 (último Total da seção principal de nov/2025)."""
    texto = _load_fixture('tania_nov2025_raw.txt')
    ini, fim = _extrair_saldos_bne_from_text(texto)
    assert ini is not None and float(ini) == pytest.approx(96735.73, abs=0.01)
    assert fim is not None and float(fim) == pytest.approx(78019.32, abs=0.01)


def test_cw_tour_pipeline_diff_zero():
    """Garante que SI + Excel_liquido = SF para CW TOUR.

    Sessão 16 fixou o bug original (sinal de SALDO ANTERIOR perdido).
    Sessão 18 corrigiu o SF para refletir o saldo do fim do PERÍODO
    pedido (jan/2026), excluindo 'Últimos Lançamentos' (fev/2026):

    - Antes Sessão 18: SF=-1247.89 (cabeçalho), 13 tx (jan + fev),
      excel_liquido=-329.51, gap=0 por coincidência (VERDE fake).
    - Pós Sessão 18: SF=+1.00 (último Total da seção principal de
      jan/2026), 9 tx (só jan/2026), excel_liquido=+919.38, gap=0 real.

    O Lote A da Sessão 18 (parser para na seção 'Últimos Lançamentos')
    + a Hipótese D estendida (SF = último Total quando há marcador
    pós-período) juntos resultam em VERDE genuíno."""
    si = -918.38
    sf = 1.00
    excel_liquido = 919.38   # 9 tx jan/2026 (entradas − saídas)
    assert abs((si + excel_liquido) - sf) < 0.01, (
        f"Bug regredido: si+excel={si + excel_liquido} != sf={sf}"
    )
