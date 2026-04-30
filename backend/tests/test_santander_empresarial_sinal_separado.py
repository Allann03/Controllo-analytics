"""Sessão 19, Iter 3 — fix do `ParserSantanderEmpresas._processar_linha`
para detectar sinal `- R$` separado por espaço.

Antes do fix: 'Transferencia ... - R$ 50,00' classificava como ENTRADA
(porque o `-` não estava colado ao número). Depois: classifica como SAÍDA.
Mantém comportamento existente para hífen colado (`-300,00` continua saída).
"""
from __future__ import annotations

from services.parsers.santander_empresarial import ParserSantanderEmpresas


class _ParserStub(ParserSantanderEmpresas):
    """Subclasse que evita chamar o construtor `pdfplumber.open`."""

    def __init__(self):
        self.avisos = []
        self.password = None
        self.pdf_path = None


def _process(linha: str):
    return _ParserStub()._processar_linha(linha)


# ─── Sinal `- R$` separado (caso KKS — Iter 3) ──────────────────────────────


def test_iter3_sinal_separado_pix_enviado_eh_saida():
    tx = _process("27/01/2026 Transferencia Programada PARA: 3875.60.005670-9 - R$ 50,00")
    assert tx is not None
    assert tx["tipo"] == "saida"
    assert abs(float(tx["valor"]) - 50.0) < 0.01
    # Descricao limpa do " - R$" residual
    assert "Transferencia Programada PARA: 3875.60.005670-9" == tx["descricao"]


def test_iter3_sinal_separado_pagamento_boleto_eh_saida():
    tx = _process("19/01/2026 Pagamento De Boleto Outros Bancos CONTROLLO BPO - R$ 705,72")
    assert tx is not None
    assert tx["tipo"] == "saida"
    assert abs(float(tx["valor"]) - 705.72) < 0.01


def test_iter3_sinal_separado_aplicacao_eh_saida():
    tx = _process("21/01/2026 Aplicacao Cdb/rdb - R$ 15.000,00")
    assert tx is not None
    assert tx["tipo"] == "saida"
    assert abs(float(tx["valor"]) - 15000.0) < 0.01


# ─── Sinal POSITIVO sem hífen (entrada) ─────────────────────────────────────


def test_iter3_sem_hifen_eh_entrada():
    tx = _process("20/01/2026 Operacao De Cambio-credito Reserva R$ 46.712,24")
    assert tx is not None
    assert tx["tipo"] == "entrada"
    assert abs(float(tx["valor"]) - 46712.24) < 0.01


def test_iter3_rendimento_eh_entrada():
    tx = _process("12/01/2026 Rendimento Liquido De Contamax 7000 R$ 0,05")
    assert tx is not None
    assert tx["tipo"] == "entrada"
    assert abs(float(tx["valor"]) - 0.05) < 0.01


# ─── Sinal hífen COLADO ao número (regressão Iter 3) ────────────────────────


def test_regressao_hifen_colado_eh_saida():
    """MARTINS Aplicativo Santander Empresas: '-300,00 1,07' (valor com saldo)."""
    tx = _process(
        "16/12/2025 Pagamento Cartao Credito Bce 0000210401 -300,00 1,07"
    )
    assert tx is not None
    assert tx["tipo"] == "saida"
    assert abs(float(tx["valor"]) - 300.0) < 0.01


def test_regressao_hifen_colado_pix_envio():
    """Padrão antigo: '-1.234,56' colado."""
    tx = _process("15/12/2025 Pix Enviado -10,00")
    assert tx is not None
    assert tx["tipo"] == "saida"
    assert abs(float(tx["valor"]) - 10.0) < 0.01
