"""
Testes do motor de categorização de transações.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAplicarCategorias:
    def test_importa_sem_erro(self):
        from services.categorias import aplicar_categorias
        assert callable(aplicar_categorias)

    def test_transacao_desconhecida_retorna_outros(self):
        from services.categorias import aplicar_categorias
        result = aplicar_categorias("XYZABC123NAOEXISTE")
        assert result == "Outros"

    def test_pix_recebido(self):
        from services.categorias import aplicar_categorias
        result = aplicar_categorias("PIX RECEBIDO DE JOAO")
        assert result != "Outros"

    def test_imposto(self):
        from services.categorias import aplicar_categorias
        result = aplicar_categorias("DARF IMPOSTO DE RENDA")
        assert result != "Outros"

    def test_tarifa_bancaria(self):
        from services.categorias import aplicar_categorias
        result = aplicar_categorias("TARIFA MANUTENCAO CONTA")
        assert result != "Outros"

    def test_retorna_string(self):
        from services.categorias import aplicar_categorias
        result = aplicar_categorias("COMPRA CARTAO SUPERMERCADO")
        assert isinstance(result, str)
        assert len(result) > 0
