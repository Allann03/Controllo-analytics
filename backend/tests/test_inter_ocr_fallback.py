"""Sessão 20 — OCR fallback para PDFs vetoriais (Inter via Microsoft Print To PDF).

Testes do parser Inter consumindo texto OCR pré-extraído (fixture). Evita
depender do binário Tesseract no CI (testes rodam em qualquer ambiente).

Cobertura:
- Normalizacao de aspas curvas / espaços nao-quebraveis.
- Conversao "DD de Mes de YYYY" -> "DD/MM/YYYY".
- Parser Inter extrai transacoes do texto OCR (via monkey-patch de
  `_obter_paginas_texto`).
- Pipeline E2E em extrato ABRIL.pdf (so se Tesseract estiver disponivel).
"""
from __future__ import annotations

import os
import re
import pytest

from services.ocr_fallback import (
    normalizar_texto_ocr,
    tesseract_disponivel,
)
from services.parsers.inter import ParserInter, _MESES, _RE_DATA_HEADER


FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'fixtures'
)
FIXTURE_OCR = os.path.join(FIXTURE_DIR, 'extrato_abril_ocr_raw.txt')
PDF_REAL = os.path.join(
    FIXTURE_DIR, 'pdfs_reais', 'extrato ABRIL.pdf'
)


# ─── Normalizacao de ruido OCR ──────────────────────────────────────────────


def test_normaliza_aspas_curvas_para_retas():
    txt = '"Cp :60746948-VALE RIO" e "ALLOILS S A”'
    out = normalizar_texto_ocr(txt)
    assert '“' not in out and '”' not in out
    assert out.count('"') == 4


def test_normaliza_apostrofes():
    txt = "Pix recebido ‘teste’ e ’outro’"
    out = normalizar_texto_ocr(txt)
    assert '‘' not in out and '’' not in out


def test_normaliza_espaco_nao_quebravel():
    txt = "R$ 9.903,89"  # NBSP entre R$ e número
    out = normalizar_texto_ocr(txt)
    assert ' ' not in out


# ─── Conversao de data extensa ──────────────────────────────────────────────


def _data_extensa_para_iso(linha: str) -> str | None:
    """Helper espelhando o caminho do parser (DD de Mes de AAAA → DD/MM/AAAA)."""
    m = _RE_DATA_HEADER.match(linha.strip())
    if not m:
        return None
    dia, mes_nome, ano = m.group(1), m.group(2).lower(), m.group(3)
    mes = _MESES.get(mes_nome)
    if not mes:
        return None
    return f'{int(dia):02d}/{mes}/{ano}'


@pytest.mark.parametrize('linha,esperado', [
    ('16 de Janeiro de 2026 Saldo do dia: R$ 0,00', '16/01/2026'),
    ('1 de Dezembro de 2025', '01/12/2025'),
    ('10 de Março de 2026 Saldo do dia: R$ 1.203,24', '10/03/2026'),
    ('5 de Setembro de 2025', '05/09/2025'),
])
def test_data_extensa_para_iso(linha, esperado):
    assert _data_extensa_para_iso(linha) == esperado


def test_data_extensa_invalida_retorna_none():
    assert _data_extensa_para_iso('linha qualquer sem data') is None
    assert _data_extensa_para_iso('15 de Fevreiro de 2026') is None  # tipo erro


# ─── Parser Inter consumindo texto OCR pre-extraido (sem depender de PDF) ───


@pytest.fixture
def texto_ocr_extrato_abril():
    """Carrega a fixture do OCR pre-gerado em FASE 1/2."""
    with open(FIXTURE_OCR, encoding='utf-8') as f:
        return f.read()


class _ParserInterStub(ParserInter):
    """Subclasse que injeta o texto OCR direto, evitando abrir PDF."""

    def __init__(self, texto_ocr: str):
        self.avisos = []
        self.password = None
        self.pdf_path = None
        self._texto_injetado = texto_ocr

    def _obter_paginas_texto(self) -> list[str]:
        return [normalizar_texto_ocr(self._texto_injetado)]


def test_parser_inter_extrai_transacoes_do_texto_ocr(texto_ocr_extrato_abril):
    parser = _ParserInterStub(texto_ocr_extrato_abril)
    txs = parser.extrair()
    assert len(txs) >= 18, f'esperava >=18 tx, veio {len(txs)}'
    assert len(txs) <= 25, f'esperava <=25 tx, veio {len(txs)}'

    # Deve detectar a Pix entrada de 9.508,55 do dia 16/01/2026
    pix_jan = [t for t in txs if t.get('data') == '16/01/2026'
               and t.get('tipo') == 'entrada'
               and abs(float(t.get('valor', 0)) - 9508.55) < 0.01]
    assert len(pix_jan) == 1

    # Deve detectar a tx final do dia 13/04 (Transferencia 9.903,89 entrada)
    final = [t for t in txs if t.get('data') == '13/04/2026'
             and abs(float(t.get('valor', 0)) - 9903.89) < 0.01]
    assert len(final) == 1


def test_parser_inter_rejeita_pseudo_tx_do_header_de_saldo(texto_ocr_extrato_abril):
    """Garante que a linha 'R$ 9.903,89 R$ 9.903,89 R$ 0,00' (header de
    Saldo total/disponivel/bloqueado) NAO vira tx fantasma."""
    parser = _ParserInterStub(texto_ocr_extrato_abril)
    txs = parser.extrair()
    # Tx fantasma teria data='' e descricao tipo 'R$ 9.903,89'
    fantasma = [t for t in txs
                if not t.get('data')
                or re.fullmatch(r'-?R\$\s*[\d.,]+',
                                str(t.get('descricao') or ''),
                                flags=re.IGNORECASE)]
    assert fantasma == [], f'tx fantasma capturada: {fantasma}'


def test_parser_inter_extrai_saldos_intermediarios(texto_ocr_extrato_abril):
    parser = _ParserInterStub(texto_ocr_extrato_abril)
    saldos = parser._extrair_saldos_intermediarios()
    assert len(saldos) >= 10
    datas = {s['data'] for s in saldos}
    assert '16/01/2026' in datas
    assert '13/04/2026' in datas

    saldo_ultimo_dia = next(s for s in saldos if s['data'] == '13/04/2026')
    assert abs(float(saldo_ultimo_dia['saldo']) - 9903.89) < 0.01


# ─── Smoke E2E (so roda se Tesseract instalado) ─────────────────────────────


@pytest.mark.skipif(
    not tesseract_disponivel(),
    reason='Tesseract nao disponivel no ambiente — smoke E2E pulado'
)
def test_pipeline_e2e_extrato_abril():
    """Rota completa pipeline → OCR → parser. Critério Allan: gap < R$ 1,00."""
    from services.pipeline_extracao import processar_com_pipeline

    r = processar_com_pipeline(PDF_REAL)
    assert r.banco in ('inter', 'inter_n2'), f'banco={r.banco}'
    assert r.requer_ocr is True, 'flag requer_ocr deveria estar True'
    assert len(r.transacoes) >= 18
    assert r.saldo_inicial is not None
    assert r.saldo_final is not None
    assert abs(r.saldo_final - 9903.89) < 0.01, f'SF={r.saldo_final}'
    assert r.gap is not None and abs(r.gap) < 1.0, f'gap={r.gap}'
