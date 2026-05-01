"""Sessão 21 — ContaMax NÃO é mais filtrado nos parsers Santander.

Sistema é Excel contábil; movimentações ContaMax (resgate/aplicação automática)
afetam saldo da conta-corrente e devem aparecer na conciliação. Filtrar aqui
causava VERMELHO honesto nos PDFs DLS, DLS_1 e IB N1 da S19 (gap = exatamente
o líquido ContaMax filtrado).

Cobre os 3 sites onde havia o filtro:
- santander_empresarial._IGNORAR
- santander_empresas/santander_empresas_v1._SKIP_DESC_LOWER
- santander_consolidado._IGNORAR_CONTEM
"""
from __future__ import annotations

from services.parsers import santander_consolidado
from services.parsers.santander_empresarial import ParserSantanderEmpresas
from services.parsers.santander_empresas.santander_empresas_v1 import (
    _desc_deve_ignorar,
)


class _ParserStubEmpresarial(ParserSantanderEmpresas):
    def __init__(self):
        self.avisos = []
        self.password = None
        self.pdf_path = None


# ─── santander_empresarial ──────────────────────────────────────────────────


def test_contamax_resgate_nao_filtrado_empresarial():
    """Linha de resgate ContaMax vira transação, não é descartada."""
    parser = _ParserStubEmpresarial()
    tx = parser._processar_linha(
        "15/04/2025 Resgate Contamax Automatico 1.234,56 5.678,90"
    )
    assert tx is not None, "ContaMax deve passar — não é mais filtrado em S21"
    assert abs(float(tx["valor"]) - 1234.56) < 0.01


def test_contamax_aplicacao_nao_filtrada_empresarial():
    parser = _ParserStubEmpresarial()
    tx = parser._processar_linha(
        "16/04/2025 Aplicacao Contamax Automatica -2.000,00 3.678,90"
    )
    assert tx is not None
    assert tx["tipo"] == "saida"
    assert abs(float(tx["valor"]) - 2000.0) < 0.01


# ─── santander_empresas_v1 ───────────────────────────────────────────────────


def test_contamax_resgate_nao_filtrado_v1():
    assert _desc_deve_ignorar("RESGATE CONTAMAX AUTOMATICO") is False
    assert _desc_deve_ignorar("Resgate Contamax") is False


def test_contamax_aplicacao_nao_filtrada_v1():
    assert _desc_deve_ignorar("APLICACAO CONTAMAX") is False
    assert _desc_deve_ignorar("Aplicação Contamax Automatica") is False


def test_v1_saldo_anterior_continua_filtrado():
    """Sanidade: outros filtros do _SKIP_DESC_LOWER permanecem ativos."""
    assert _desc_deve_ignorar("SALDO ANTERIOR") is True


# ─── santander_consolidado ───────────────────────────────────────────────────


def test_contamax_consolidado_nao_filtrado():
    """`_IGNORAR_CONTEM` não pode mais conter substring de ContaMax — caso
    contrário descrições contendo 'CONTAMAX EMPRESARIAL' são descartadas como
    cabeçalho de seção auxiliar.
    """
    for padrao in santander_consolidado._IGNORAR_CONTEM:
        assert "contamax" not in padrao.lower(), (
            f"Padrão {padrao!r} ainda filtra ContaMax — S21 removeu este filtro"
        )
