"""
Sessão 18 — Lote A — testes do parser ParserBradescoNetEmpresas.

Cobertura:
- (positivo) PDF COM "Últimos Lançamentos": parser para no marcador e
  ignora as transações pós-período.
- (positivo) PDF COM "Saldos Invest Fácil / Plus": parser para no marcador.
- (regressão R-A) PDF SEM marcadores pós-período: parser lê até o fim.
- Cross-página: marcador detectado em página 2 ainda corta corretamente.

Os testes operam sobre PDFs reais em `pdfs_reais/` quando possível e sobre
texto sintético quando uma variante não tem fixture real.
"""
from __future__ import annotations

import os

import pytest

from services.parsers.bradesco_empresas.bradesco_net_empresas import (
    ParserBradescoNetEmpresas,
    _MARCADORES_FIM_PERIODO,
)

PDFS_REAIS = os.path.join(os.path.dirname(__file__), 'fixtures', 'pdfs_reais')


def _pdf_existe(nome: str) -> bool:
    return os.path.isfile(os.path.join(PDFS_REAIS, nome))


# ─────────────────────────────────────────────────────────────────────────────
# Marcadores e helpers
# ─────────────────────────────────────────────────────────────────────────────

def test_marcadores_fim_periodo_cobrem_variantes_de_encoding():
    """Marcadores devem cobrir 'últimos lançamentos' e 'ultimos lancamentos'
    (encoding) + 'saldos invest fácil' / 'saldos invest facil'."""
    assert 'últimos lançamentos' in _MARCADORES_FIM_PERIODO
    assert 'ultimos lancamentos' in _MARCADORES_FIM_PERIODO
    assert 'saldos invest fácil' in _MARCADORES_FIM_PERIODO
    assert 'saldos invest facil' in _MARCADORES_FIM_PERIODO


def test_e_linha_skip_pula_titulos_pos_periodo():
    """`_e_linha_skip` continua pulando títulos individuais (linha de
    cabeçalho de tabela e similares)."""
    parser = ParserBradescoNetEmpresas('')
    assert parser._e_linha_skip('Últimos Lançamentos')
    assert parser._e_linha_skip('Saldos Invest Fácil / Plus')
    assert parser._e_linha_skip('Saldo Anterior 100,00')
    # Linha de transação real NÃO deve ser pulada
    assert not parser._e_linha_skip('05/01/2026 TRANSFERENCIA PIX')


# ─────────────────────────────────────────────────────────────────────────────
# Testes em PDFs reais (Sessão 18 — verifica que parser para no marcador)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not _pdf_existe('Bradesco Net Empresas (2).pdf'),
    reason='fixture real CW TOUR não está presente neste ambiente',
)
def test_cw_tour_para_em_ultimos_lancamentos():
    """CW TOUR jan/2026 tem 'Últimos Lançamentos' com 4 tx de fev/2026.
    Pós Sessão 18, parser deve extrair 9 tx (só jan/2026) — não 13."""
    p = os.path.join(PDFS_REAIS, 'Bradesco Net Empresas (2).pdf')
    parser = ParserBradescoNetEmpresas(p)
    tx = parser.extrair()
    # Todas as datas devem estar em jan/2026 (período pedido)
    datas_fora_jan = [
        t for t in tx
        if not t.get('data', '').startswith('05/01/')
        and not t.get('data', '').startswith('07/01/')
        and not t.get('data', '').startswith('12/01/')
        and not t.get('data', '').startswith('15/01/')
        and not t.get('data', '').startswith('30/01/')
    ]
    assert datas_fora_jan == [], (
        f'Parser NÃO parou em "Últimos Lançamentos" — '
        f'{len(datas_fora_jan)} tx fora do período pedido: '
        f'{[(t.get("data"), t.get("descricao", "")[:30]) for t in datas_fora_jan[:5]]}'
    )
    # E deve ter pegado as 9 tx de jan/2026
    assert len(tx) == 9, f'Esperava 9 tx (só jan/2026), achei {len(tx)}'


@pytest.mark.skipif(
    not _pdf_existe('Bradesco net.pdf'),
    reason='fixture real TANIA dez não está presente neste ambiente',
)
def test_tania_dez_para_em_ultimos_lancamentos_cross_pagina():
    """TANIA dez/2025 tem 3 páginas. 'Últimos Lançamentos' começa na pg2.
    Parser deve parar mesmo com cross-página (sem ler invest fácil pg3)."""
    p = os.path.join(PDFS_REAIS, 'Bradesco net.pdf')
    parser = ParserBradescoNetEmpresas(p)
    tx = parser.extrair()
    # Datas devem estar todas em 11/12/2025 ou anteriores (período dez/2025);
    # nenhuma de jan/2026 (Últimos Lançamentos) ou linhas "SALDO INVEST FÁCIL"
    # Dec 2025 tem datas DD/12/2025 e SALDO ANTERIOR 28/11/2025 (não conta)
    descricoes_invest = [
        t for t in tx
        if 'invest fácil' in (t.get('descricao', '') or '').lower()
        or 'invest facil' in (t.get('descricao', '') or '').lower()
        and 'saldo' in (t.get('descricao', '') or '').lower()
    ]
    # "RENTAB.INVEST FACILCRED" é tx legítima; "SALDO INVEST FÁCIL" é
    # da seção pós-período. Aceitamos a primeira; rejeitamos a segunda.
    saldos_invest = [
        t for t in tx
        if (t.get('descricao', '') or '').strip().upper().startswith('SALDO INVEST FÁCIL')
        or (t.get('descricao', '') or '').strip().upper().startswith('SALDO INVEST FACIL')
    ]
    assert saldos_invest == [], (
        f'Parser leu "SALDO INVEST FÁCIL" como tx (era pós-período): '
        f'{[(t.get("data"), t.get("descricao", "")[:40]) for t in saldos_invest[:3]]}'
    )
    # Datas de jan/2026 (Últimos Lançamentos da pg2) também não devem aparecer
    datas_jan = [t for t in tx if (t.get('data') or '').endswith('/2026')]
    assert datas_jan == [], (
        f'Parser leu tx de 2026 (Últimos Lançamentos): {len(datas_jan)} tx'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Teste de regressão (R-A): PDF SEM marcadores pós-período lê até o fim
# ─────────────────────────────────────────────────────────────────────────────

class _ParserSemPdfplumber(ParserBradescoNetEmpresas):
    """Subclasse que injeta texto sintético em vez de abrir PDF real.
    Usada apenas para o teste de regressão sem marcadores."""

    def __init__(self, texto_sintetico: str):
        super().__init__(pdf_path='__sintetico__')
        self._texto_sintetico = texto_sintetico

    def extrair(self):
        """Versão simplificada que reusa a lógica de `extrair` do pai
        sem abrir PDF — substitui o conteúdo de `linhas_raw` direto."""
        # Reaproveita a lógica processando o texto sintético.
        # Como o método pai abre PDF via pdfplumber, monkey-patch local:
        from services.parsers.bradesco_empresas import bradesco_net_empresas as _mod
        original = _mod.pdfplumber

        class _FakePdfplumber:
            class _FakePage:
                def __init__(self, txt):
                    self._txt = txt
                def extract_text(self):
                    return self._txt

            class _FakePdf:
                def __init__(self, txt):
                    self.pages = [_FakePdfplumber._FakePage(txt)]
                def __enter__(self):
                    return self
                def __exit__(self, *a):
                    return False

            @staticmethod
            def open(path, password=''):
                # path ignorado — usa texto sintético via closure
                return _FakePdfplumber._FakePdf(_self_texto)

        _self_texto = self._texto_sintetico
        _mod.pdfplumber = _FakePdfplumber
        try:
            return super().extrair()
        finally:
            _mod.pdfplumber = original


def test_pdf_sem_marcadores_pos_periodo_le_ate_o_fim():
    """Regressão R-A do Lote A: se o PDF NÃO tem 'Últimos Lançamentos' nem
    'Saldos Invest Fácil', o parser deve ler até a última transação. O stop
    é OPCIONAL, não obrigatório.

    Texto sintético: 3 transações simples sem nenhuma seção pós-período.
    O parser deve extrair as 3 (não parar antes do fim)."""
    texto = """\
Agência | Conta Total Disponível (R$) Total (R$)
00198 | 0220862-8 100,00 100,00
Extrato de: Ag: 198 | CC: 0220862-8 | Entre 01/01/2026 e 31/01/2026
Data Lançamento Dcto. Crédito (R$) Débito (R$) Saldo (R$)
31/12/2025 SALDO ANTERIOR 50,00
05/01/2026 TRANSFERENCIA PIX 951320 100,00 150,00
REM: TESTE 05/01
12/01/2026 PAGTO ELETRON COBRANCA 105 -30,00 120,00
DESCRICAO TESTE
20/01/2026 TARIFA BANCARIA 20126 -20,00 100,00
CESTA PJ FACIL
Total 100,00 -50,00 100,00
"""
    parser = _ParserSemPdfplumber(texto)
    tx = parser.extrair()
    # Deve ter 3 transações (não parou prematuramente):
    assert len(tx) == 3, (
        f'Parser parou ANTES do fim em PDF sem marcadores: extraiu {len(tx)} '
        f'tx, esperava 3. Datas extraídas: {[t.get("data") for t in tx]}'
    )
    datas = sorted(t.get('data') for t in tx)
    assert datas == ['05/01/2026', '12/01/2026', '20/01/2026']


def test_pdf_com_marcador_apenas_para_apos_marcador():
    """Texto sintético com 2 tx pré-marcador + marcador 'Últimos
    Lançamentos' + 1 tx pós-marcador. Parser deve extrair APENAS as 2
    primeiras."""
    texto = """\
Agência | Conta Total Disponível (R$) Total (R$)
00198 | 0220862-8 100,00 100,00
Data Lançamento Dcto. Crédito (R$) Débito (R$) Saldo (R$)
31/12/2025 SALDO ANTERIOR 50,00
05/01/2026 TRANSFERENCIA PIX 951320 100,00 150,00
REM: PRE-MARCADOR
12/01/2026 PAGTO ELETRON 105 -30,00 120,00
ANTES DO MARCADOR
Total 100,00 -30,00 120,00
Os dados acima têm como base 11/02/2026.
Últimos Lançamentos
Data Lançamento Dcto. Crédito (R$) Débito (R$) Saldo (R$)
05/02/2026 SALDO ANTERIOR 120,00
10/02/2026 RESG.AUTOM 100226 50,00 170,00
DEPOIS DO MARCADOR
Total 50,00 0,00 170,00
"""
    parser = _ParserSemPdfplumber(texto)
    tx = parser.extrair()
    descricoes = [t.get('descricao', '').upper() for t in tx]
    # Deve ter EXATAMENTE 2 tx (as antes do marcador)
    assert len(tx) == 2, (
        f'Parser não parou no marcador: extraiu {len(tx)} tx, esperava 2. '
        f'Descrições: {descricoes}'
    )
    # Nenhuma descrição "DEPOIS DO MARCADOR" deve aparecer
    assert not any('DEPOIS DO MARCADOR' in d for d in descricoes), (
        f'Parser leu transação pós-marcador: {descricoes}'
    )
