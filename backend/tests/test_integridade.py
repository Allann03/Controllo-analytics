"""
Testes de integridade do pipeline de valores financeiros.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal


class _ConcreteParser:
    """Stub concreto para testar métodos de ParserBase sem instanciar ABC."""
    pass


def _get_parser():
    """Cria instância testável com métodos de ParserBase."""
    from services.parsers.base import ParserBase
    # Create a concrete subclass
    class TestParser(ParserBase):
        def extrair(self):
            return []
    return TestParser("/dev/null")


def test_normalizar_valor_returns_decimal():
    """_normalizar_valor deve retornar Decimal, não float."""
    p = _get_parser()
    result = p._normalizar_valor("1.234,56")
    assert isinstance(result, Decimal), f"Esperado Decimal, recebeu {type(result)}: {result}"
    assert result == Decimal("1234.56")


def test_normalizar_valor_formats():
    """Testa diversos formatos de valor BR."""
    p = _get_parser()
    cases = [
        ("R$ 1.234,56", Decimal("1234.56")),
        ("1234,56", Decimal("1234.56")),
        ("-1.234,56", Decimal("1234.56")),  # _normalizar_valor retorna abs — sinal é pelo tipo
        ("0,01", Decimal("0.01")),
    ]
    for text, expected in cases:
        result = p._normalizar_valor(text)
        assert result == expected, f"Input '{text}': esperado {expected}, recebeu {result}"


def test_sum_precision_decimal():
    """Soma de Decimals mantém precisão exata."""
    valores = [Decimal("0.01")] * 1000
    assert sum(valores) == Decimal("10.00")


def test_decimal_vs_float_precision():
    """Decimal garante precisão que float pode perder em certos cenários."""
    # Cenário clássico: 0.1 + 0.2
    assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")
    # float: 0.1 + 0.2 != 0.3 exatamente
    assert 0.1 + 0.2 != 0.3


def test_transacao_dict_has_decimal_valor():
    """Dict de transação do parser deve ter valor como Decimal."""
    p = _get_parser()
    t = p._transacao(
        data="01/01/2025",
        descricao="Teste",
        valor=Decimal("100.50"),
        tipo="entrada",
        banco="test",
    )
    assert isinstance(t["valor"], Decimal), f"valor deveria ser Decimal, é {type(t['valor'])}"
