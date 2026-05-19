"""
engine.py — Orquestrador da reconciliação bancária.

Detecta o banco a partir das transações do PDF e seleciona
o matcher específico para aquele banco.
"""

from .matchers import (
    NubankMatcher, BradescoMatcher, ItauMatcher, InterMatcher,
    SicrediMatcher, C6BankMatcher, PagBankMatcher, MercadoPagoMatcher,
    CaixaMatcher, SantanderMatcher, StoneMatcher, BBMatcher,
    UniversalMatcher,
)

# Mapeamento banco_key → matcher
# banco_key vem do campo "banco" retornado pelos parsers (ex: "Nubank", "Itaú")
_MATCHERS = {
    "nubank":       NubankMatcher,
    "bradesco":     BradescoMatcher,
    "itau":         ItauMatcher,
    "itaú":         ItauMatcher,
    "inter":        InterMatcher,
    "sicredi":      SicrediMatcher,
    "c6bank":       C6BankMatcher,
    "c6 bank":      C6BankMatcher,
    "pagbank":      PagBankMatcher,
    "mercado_pago": MercadoPagoMatcher,
    "mercado pago": MercadoPagoMatcher,
    "caixa":        CaixaMatcher,
    "santander":    SantanderMatcher,
    "stone":        StoneMatcher,
    "bb":           BBMatcher,
    "banco do brasil": BBMatcher,
}


def _detectar_banco(transacoes_pdf: list[dict]) -> str:
    """
    Detecta o banco dominante nas transações do PDF.
    Usa o campo 'banco' da primeira transação como referência.
    """
    if not transacoes_pdf:
        return ""
    banco = str(transacoes_pdf[0].get("banco", "")).strip().lower()
    return banco


def reconciliar(transacoes_pdf: list[dict], transacoes_excel: list[dict]) -> dict:
    """
    Reconcilia transações do PDF com transações do Excel.

    Detecta o banco automaticamente, seleciona o matcher correto e
    retorna o relatório completo de divergências com linhas Excel.
    """
    banco_key = _detectar_banco(transacoes_pdf)

    # Busca o matcher por correspondência parcial (ex: "Itaú" → "itaú")
    matcher_cls = UniversalMatcher
    for key, cls in _MATCHERS.items():
        if key in banco_key or banco_key in key:
            matcher_cls = cls
            break

    matcher = matcher_cls()
    return matcher.reconciliar(transacoes_pdf, transacoes_excel)
