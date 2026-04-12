"""
Testes de lógica dos parsers — sem precisar de PDFs reais.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal


def _get_parser():
    from services.parsers.base import ParserBase
    class TestParser(ParserBase):
        def extrair(self):
            return []
    return TestParser("/dev/null")


class TestNormalizarValor:
    def test_formato_br(self):
        p = _get_parser()
        assert p._normalizar_valor("1.234,56") == Decimal("1234.56")

    def test_com_cifrao(self):
        p = _get_parser()
        assert p._normalizar_valor("R$ 1.234,56") == Decimal("1234.56")

    def test_centavos(self):
        p = _get_parser()
        assert p._normalizar_valor("0,01") == Decimal("0.01")

    def test_inteiro(self):
        p = _get_parser()
        assert p._normalizar_valor("1234") == Decimal("1234")

    def test_milhoes(self):
        p = _get_parser()
        assert p._normalizar_valor("1.234.567,89") == Decimal("1234567.89")

    def test_retorna_decimal(self):
        p = _get_parser()
        result = p._normalizar_valor("100,00")
        assert isinstance(result, Decimal)


class TestNormalizarData:
    def test_formato_completo(self):
        p = _get_parser()
        assert p._normalizar_data("01/06/2025", 2025) == "01/06/2025"

    def test_ano_dois_digitos(self):
        p = _get_parser()
        assert p._normalizar_data("01/06/25", 2025) == "01/06/2025"

    def test_sem_ano(self):
        p = _get_parser()
        assert p._normalizar_data("01/06", 2025) == "01/06/2025"


class TestIsLinhaSaldo:
    def test_saldo_do_dia(self):
        p = _get_parser()
        assert p._is_linha_saldo("SALDO DO DIA")

    def test_saldo_anterior(self):
        p = _get_parser()
        assert p._is_linha_saldo("Saldo anterior")

    def test_transacao_normal_nao_e_saldo(self):
        p = _get_parser()
        assert not p._is_linha_saldo("PIX RECEBIDO JOAO")

    def test_pagamento_nao_e_saldo(self):
        p = _get_parser()
        assert not p._is_linha_saldo("PAGAMENTO DE BOLETO")


class TestTransacao:
    def test_campos_obrigatorios(self):
        p = _get_parser()
        tx = p._transacao("01/01/2025", "PIX RECEBIDO", Decimal("100.00"), "entrada", "nubank")
        assert tx["data"] == "01/01/2025"
        assert tx["descricao"] == "PIX RECEBIDO"
        assert tx["tipo"] == "entrada"
        assert tx["banco"] == "nubank"

    def test_valor_decimal(self):
        p = _get_parser()
        tx = p._transacao("01/01/2025", "Teste", Decimal("99.99"), "saida", "bb")
        assert isinstance(tx["valor"], Decimal)

    def test_tipo_valido(self):
        p = _get_parser()
        for tipo in ("entrada", "saida"):
            tx = p._transacao("01/01/2025", "Teste", Decimal("10"), tipo, "bb")
            assert tx["tipo"] == tipo
