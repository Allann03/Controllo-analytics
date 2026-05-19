"""
Testes do motor de classificação contábil.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal


class TestClassificarTransacao:
    def test_importa_sem_erro(self):
        from services.motor_classificacao import classificar_transacao
        assert callable(classificar_transacao)

    def test_fallback_despesa(self):
        """Transação de saída sem regra vai para 49901 (A Classificar)."""
        from services.motor_classificacao import classificar_transacao
        result = classificar_transacao(
            descricao="PAGAMENTO XYZABC DESCONHECIDO",
            tipo="saida",
            banco="Nubank",
            conta_banco_codigo="11202",
            regras_usuario=[],
            cadastros=[],
            plano={"11202": "Banco Nubank", "49901": "Despesas a Classificar"},
        )
        assert "debito" in result
        assert "credito" in result
        assert result["credito"] == "11202"  # saída: crédito na conta banco
        assert result["status"] in ("automatico", "pendente")

    def test_fallback_receita(self):
        """Transação de entrada sem regra vai para 39901 (A Classificar)."""
        from services.motor_classificacao import classificar_transacao
        result = classificar_transacao(
            descricao="PIX RECEBIDO XYZABC DESCONHECIDO",
            tipo="entrada",
            banco="Nubank",
            conta_banco_codigo="11202",
            regras_usuario=[],
            cadastros=[],
            plano={"11202": "Banco Nubank", "39901": "Receitas a Classificar"},
        )
        assert result["debito"] == "11202"  # entrada: débito na conta banco


class TestClassificarLote:
    def test_importa_sem_erro(self):
        from services.motor_classificacao import classificar_lote
        assert callable(classificar_lote)

    def test_lote_vazio(self):
        from services.motor_classificacao import classificar_lote
        result = classificar_lote(
            transacoes=[],
            conta_banco_map={"Nubank": "11202"},
            regras_usuario=[],
            cadastros=[],
            plano={},
        )
        assert result == []

    def test_lote_retorna_lancamentos(self):
        from services.motor_classificacao import classificar_lote
        transacoes = [
            {"data": "01/01/2025", "descricao": "PIX", "valor": Decimal("100"), "tipo": "entrada", "banco": "Nubank"},
            {"data": "02/01/2025", "descricao": "PAG", "valor": Decimal("50"), "tipo": "saida", "banco": "Nubank"},
        ]
        result = classificar_lote(
            transacoes=transacoes,
            conta_banco_map={"Nubank": "11202"},
            regras_usuario=[],
            cadastros=[],
            plano={"11202": "Banco", "49901": "Desp", "39901": "Rec"},
        )
        assert len(result) == 2
        for lanc in result:
            assert "debito" in lanc
            assert "credito" in lanc
            assert "valor" in lanc
            assert "lancamento" in lanc
