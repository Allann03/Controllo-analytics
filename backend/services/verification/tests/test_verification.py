"""
test_verification.py — Testes unitários para a camada de verificação contábil.

Testes cobrem:
  - Verificação OK (saldo batendo)
  - Verificação DIVERGENT (saldo não batendo)
  - Validação progressiva com saldos intermediários
  - Releitura automática
  - Uso de Decimal (nunca float nos cálculos)
  - Linhas de saldo NÃO computadas como transação
  - Edge cases: extrato sem saldo intermediário, transação única,
    sem saldo anterior, valores negativos, valores zero
  - Verificação cruzada com Excel
  - Cada verificador de banco instanciável
"""

import unittest
from decimal import Decimal
from datetime import datetime

from services.verification.models import (
    VerificationResult,
    DivergencePoint,
    TransactionRecord,
)
from services.verification.base import BankVerifier, _to_decimal
from services.verification.verifiers import (
    VERIFIERS,
    ItauVerifier,
    BradescoVerifier,
    BancoDoBrasilVerifier,
    SantanderVerifier,
    CaixaVerifier,
    NubankVerifier,
    InterVerifier,
    SicrediVerifier,
    StoneVerifier,
    C6BankVerifier,
    PagBankVerifier,
    MercadoPagoVerifier,
    CoraVerifier,
    BS2Verifier,
    _parse_valor_br_decimal,
)
from services.verification.orchestrator import executar_verificacao


class TestToDecimal(unittest.TestCase):
    """Testa a conversão segura para Decimal."""

    def test_float_to_decimal(self):
        result = _to_decimal(1234.56)
        self.assertIsInstance(result, Decimal)
        self.assertEqual(result, Decimal('1234.56'))

    def test_int_to_decimal(self):
        self.assertEqual(_to_decimal(100), Decimal('100'))

    def test_str_to_decimal(self):
        self.assertEqual(_to_decimal('999.99'), Decimal('999.99'))

    def test_none_to_decimal(self):
        self.assertEqual(_to_decimal(None), Decimal('0'))

    def test_invalid_to_decimal(self):
        self.assertEqual(_to_decimal('abc'), Decimal('0'))

    def test_decimal_passthrough(self):
        d = Decimal('42.00')
        self.assertIs(_to_decimal(d), d)


class TestParseValorBrDecimal(unittest.TestCase):
    """Testa parsing de valores monetários brasileiros para Decimal."""

    def test_valor_simples(self):
        self.assertEqual(_parse_valor_br_decimal('1.234,56'), Decimal('1234.56'))

    def test_valor_sem_milhar(self):
        self.assertEqual(_parse_valor_br_decimal('234,56'), Decimal('234.56'))

    def test_valor_com_r_cifrao(self):
        self.assertEqual(_parse_valor_br_decimal('R$ 1.234,56'), Decimal('1234.56'))

    def test_valor_negativo(self):
        result = _parse_valor_br_decimal('-1.234,56')
        self.assertEqual(result, Decimal('1234.56'))  # Abs — sinal tratado externamente

    def test_valor_vazio(self):
        self.assertIsNone(_parse_valor_br_decimal(''))

    def test_valor_invalido(self):
        self.assertIsNone(_parse_valor_br_decimal('abc'))

    def test_valor_muito_grande(self):
        self.assertIsNone(_parse_valor_br_decimal('999.999.999,99'))

    def test_nunca_retorna_float(self):
        result = _parse_valor_br_decimal('100,00')
        self.assertIsInstance(result, Decimal)
        self.assertNotIsInstance(result, float)


class TestVerificationResultOK(unittest.TestCase):
    """Testa verificação com saldo batendo → status OK."""

    def setUp(self):
        self.transacoes = [
            {'data': '01/01/2026', 'descricao': 'PIX Recebido', 'valor': 1000.0,
             'tipo': 'entrada', 'banco': 'Itau', 'raw': '', 'categoria': ''},
            {'data': '02/01/2026', 'descricao': 'Pagamento Boleto', 'valor': 300.0,
             'tipo': 'saida', 'banco': 'Itau', 'raw': '', 'categoria': ''},
            {'data': '03/01/2026', 'descricao': 'TED Recebida', 'valor': 500.0,
             'tipo': 'entrada', 'banco': 'Itau', 'raw': '', 'categoria': ''},
        ]
        # saldo_inicial=1000, +1000 -300 +500 = 2200 (saldo_final)
        self.saldo_inicial = 1000.0
        self.saldo_final = 2200.0

    def test_verificacao_ok(self):
        verifier = ItauVerifier()
        result = verifier.verify(
            transacoes_parser=self.transacoes,
            saldo_inicial=self.saldo_inicial,
            saldo_final=self.saldo_final,
            file_name='teste_itau.pdf',
        )
        self.assertEqual(result.status, 'OK')
        self.assertEqual(result.total_credits, Decimal('1500'))
        self.assertEqual(result.total_debits, Decimal('300'))
        self.assertEqual(result.transaction_count, 3)
        self.assertEqual(result.credit_count, 2)
        self.assertEqual(result.debit_count, 1)
        self.assertEqual(result.opening_balance, Decimal('1000'))
        self.assertEqual(result.calculated_closing_balance, Decimal('2200'))
        self.assertEqual(result.expected_closing_balance, Decimal('2200'))
        self.assertEqual(len(result.divergence_points), 0)

    def test_resultado_to_dict(self):
        verifier = ItauVerifier()
        result = verifier.verify(
            transacoes_parser=self.transacoes,
            saldo_inicial=self.saldo_inicial,
            saldo_final=self.saldo_final,
            file_name='teste.pdf',
        )
        d = result.to_dict()
        self.assertEqual(d['status'], 'OK')
        self.assertIsInstance(d['total_credits'], str)
        self.assertIsInstance(d['timestamp'], str)

    def test_format_message_ok(self):
        verifier = ItauVerifier()
        result = verifier.verify(
            transacoes_parser=self.transacoes,
            saldo_inicial=self.saldo_inicial,
            saldo_final=self.saldo_final,
            file_name='teste.pdf',
        )
        msg = result.format_message()
        self.assertIn('OK', msg)
        self.assertIn('Itau', msg)


class TestVerificationResultDivergent(unittest.TestCase):
    """Testa verificação com saldo NÃO batendo → status DIVERGENT."""

    def test_saldo_divergente(self):
        transacoes = [
            {'data': '01/01/2026', 'descricao': 'PIX Recebido', 'valor': 1000.0,
             'tipo': 'entrada', 'banco': 'Itau', 'raw': '', 'categoria': ''},
        ]
        # saldo_inicial=500, +1000 = 1500, mas banco diz 1600 → divergência de 100
        verifier = ItauVerifier()
        result = verifier.verify(
            transacoes_parser=transacoes,
            saldo_inicial=500.0,
            saldo_final=1600.0,
            file_name='teste_div.pdf',
        )
        self.assertEqual(result.status, 'DIVERGENT')
        self.assertEqual(result.difference, Decimal('100'))
        self.assertEqual(result.calculated_closing_balance, Decimal('1500'))
        self.assertEqual(result.expected_closing_balance, Decimal('1600'))
        self.assertTrue(len(result.divergence_points) > 0)

    def test_format_message_divergent(self):
        transacoes = [
            {'data': '01/01/2026', 'descricao': 'PIX', 'valor': 100.0,
             'tipo': 'entrada', 'banco': 'Itau', 'raw': '', 'categoria': ''},
        ]
        verifier = ItauVerifier()
        result = verifier.verify(
            transacoes_parser=transacoes,
            saldo_inicial=0.0,
            saldo_final=200.0,
            file_name='div.pdf',
        )
        msg = result.format_message()
        self.assertIn('DIVERGENCIA', msg)
        self.assertIn('Itau', msg)
        self.assertIn('Diferenca', msg)


class TestIntermediateBalanceValidation(unittest.TestCase):
    """Testa validação progressiva com saldos intermediários."""

    def test_divergencia_intermediaria(self):
        verifier = ItauVerifier()
        transacoes = [
            TransactionRecord(0, '01/01/2026', 'PIX', Decimal('100'), 'entrada'),
            TransactionRecord(1, '02/01/2026', 'Boleto', Decimal('50'), 'saida'),
            TransactionRecord(2, '03/01/2026', 'TED', Decimal('200'), 'entrada'),
        ]
        saldo_inicial = Decimal('1000')
        # Após 01/01: 1000 + 100 = 1100
        # Após 02/01: 1100 - 50 = 1050
        # Saldo intermediário informado: 1100 (correto p/ 01/01) e 999 (errado p/ 02/01)
        saldos_intermediarios = [
            ('01/01/2026', Decimal('1100')),
            ('02/01/2026', Decimal('999')),  # Deveria ser 1050
        ]
        divergencias = verifier._validacao_progressiva(
            saldo_inicial, transacoes, saldos_intermediarios
        )
        self.assertEqual(len(divergencias), 1)
        dp = divergencias[0]
        self.assertEqual(dp.date, '02/01/2026')
        self.assertEqual(dp.expected_balance, Decimal('999'))
        self.assertEqual(dp.calculated_balance, Decimal('1050'))
        self.assertEqual(dp.difference, Decimal('-51'))

    def test_sem_saldos_intermediarios(self):
        verifier = ItauVerifier()
        transacoes = [
            TransactionRecord(0, '01/01/2026', 'PIX', Decimal('100'), 'entrada'),
        ]
        divergencias = verifier._validacao_progressiva(
            Decimal('1000'), transacoes, []
        )
        self.assertEqual(len(divergencias), 0)


class TestSaldoLinesNotCounted(unittest.TestCase):
    """Testa que linhas de saldo NÃO são computadas como transação."""

    def test_saldo_lines_ignored(self):
        transacoes = [
            {'data': '01/01/2026', 'descricao': 'PIX Recebido', 'valor': 1000.0,
             'tipo': 'entrada', 'banco': 'BB', 'raw': '', 'categoria': ''},
            # Esta transação tem tipo 'ignorar' — deve ser filtrada
            {'data': '01/01/2026', 'descricao': 'SALDO ANTERIOR', 'valor': 5000.0,
             'tipo': 'ignorar', 'banco': 'BB', 'raw': '', 'categoria': ''},
            {'data': '02/01/2026', 'descricao': 'Compra Débito', 'valor': 200.0,
             'tipo': 'saida', 'banco': 'BB', 'raw': '', 'categoria': ''},
        ]
        verifier = BancoDoBrasilVerifier()
        result = verifier.verify(
            transacoes_parser=transacoes,
            saldo_inicial=5000.0,
            saldo_final=5800.0,
            file_name='teste_bb.pdf',
        )
        # Apenas 2 transações devem ser contadas (PIX + Compra), não o SALDO
        self.assertEqual(result.transaction_count, 2)
        self.assertEqual(result.credit_count, 1)
        self.assertEqual(result.debit_count, 1)
        self.assertEqual(result.status, 'OK')

    def test_classify_line_saldo(self):
        verifier = BancoDoBrasilVerifier()
        self.assertEqual(verifier.classify_line('SALDO ANTERIOR 5.000,00'), 'SALDO_INFORMATIVO')
        self.assertEqual(verifier.classify_line('SALDO DO DIA 5.800,00'), 'SALDO_INFORMATIVO')
        self.assertEqual(verifier.classify_line('SALDO FINAL 5.800,00'), 'SALDO_INFORMATIVO')
        self.assertEqual(verifier.classify_line('PIX Recebido 1.000,00'), 'TRANSACAO')
        self.assertEqual(verifier.classify_line(''), 'IGNORAR')


class TestFloatNeverUsed(unittest.TestCase):
    """Testa que float NÃO é usado em nenhum cálculo de verificação."""

    def test_all_decimal_in_result(self):
        transacoes = [
            {'data': '01/01/2026', 'descricao': 'PIX', 'valor': 1000.0,
             'tipo': 'entrada', 'banco': 'Inter', 'raw': '', 'categoria': ''},
        ]
        verifier = InterVerifier()
        result = verifier.verify(
            transacoes_parser=transacoes,
            saldo_inicial=500.0,
            saldo_final=1500.0,
            file_name='teste.pdf',
        )
        # Todos os campos monetários devem ser Decimal
        self.assertIsInstance(result.total_credits, Decimal)
        self.assertIsInstance(result.total_debits, Decimal)
        self.assertIsInstance(result.difference, Decimal)
        self.assertIsInstance(result.opening_balance, Decimal)
        self.assertIsInstance(result.calculated_closing_balance, Decimal)
        self.assertIsInstance(result.expected_closing_balance, Decimal)

    def test_transaction_record_uses_decimal(self):
        verifier = InterVerifier()
        records = verifier._converter_transacoes([
            {'data': '01/01/2026', 'descricao': 'PIX', 'valor': 100.50,
             'tipo': 'entrada', 'banco': 'Inter', 'raw': '', 'categoria': ''},
        ])
        self.assertEqual(len(records), 1)
        self.assertIsInstance(records[0].value, Decimal)
        self.assertEqual(records[0].value, Decimal('100.5'))


class TestEdgeCases(unittest.TestCase):
    """Testa edge cases diversos."""

    def test_extrato_transacao_unica(self):
        transacoes = [
            {'data': '15/03/2026', 'descricao': 'TED Recebida', 'valor': 5000.0,
             'tipo': 'entrada', 'banco': 'Caixa', 'raw': '', 'categoria': ''},
        ]
        verifier = CaixaVerifier()
        result = verifier.verify(
            transacoes_parser=transacoes,
            saldo_inicial=0.0,
            saldo_final=5000.0,
            file_name='unica.pdf',
        )
        self.assertEqual(result.status, 'OK')
        self.assertEqual(result.transaction_count, 1)

    def test_sem_saldo_anterior(self):
        transacoes = [
            {'data': '01/01/2026', 'descricao': 'PIX', 'valor': 100.0,
             'tipo': 'entrada', 'banco': 'Nubank', 'raw': '', 'categoria': ''},
        ]
        verifier = NubankVerifier()
        result = verifier.verify(
            transacoes_parser=transacoes,
            saldo_inicial=None,
            saldo_final=100.0,
            file_name='sem_anterior.pdf',
        )
        # Sem saldo inicial, usa 0; 0 + 100 = 100 = saldo_final → OK
        self.assertEqual(result.status, 'OK')

    def test_sem_nenhum_saldo(self):
        transacoes = [
            {'data': '01/01/2026', 'descricao': 'PIX', 'valor': 100.0,
             'tipo': 'entrada', 'banco': 'Santander', 'raw': '', 'categoria': ''},
        ]
        verifier = SantanderVerifier()
        result = verifier.verify(
            transacoes_parser=transacoes,
            saldo_inicial=None,
            saldo_final=None,
            file_name='sem_saldo.pdf',
        )
        self.assertEqual(result.status, 'SKIPPED')
        self.assertIn('nao disponiveis', result.skip_reason)

    def test_valor_zero(self):
        transacoes = [
            {'data': '01/01/2026', 'descricao': 'Estorno', 'valor': 0.0,
             'tipo': 'entrada', 'banco': 'Stone', 'raw': '', 'categoria': ''},
        ]
        verifier = StoneVerifier()
        result = verifier.verify(
            transacoes_parser=transacoes,
            saldo_inicial=1000.0,
            saldo_final=1000.0,
            file_name='zero.pdf',
        )
        # Transação com valor 0 é filtrada → nenhuma transação → SKIPPED
        self.assertEqual(result.status, 'SKIPPED')

    def test_transacoes_vazias(self):
        verifier = C6BankVerifier()
        result = verifier.verify(
            transacoes_parser=[],
            saldo_inicial=1000.0,
            saldo_final=1000.0,
            file_name='vazio.pdf',
        )
        self.assertEqual(result.status, 'SKIPPED')

    def test_tolerancia_arredondamento(self):
        """Diferença de R$ 0.01 deve ser tolerada (arredondamento)."""
        transacoes = [
            {'data': '01/01/2026', 'descricao': 'PIX', 'valor': 100.0,
             'tipo': 'entrada', 'banco': 'Itau', 'raw': '', 'categoria': ''},
        ]
        verifier = ItauVerifier()
        result = verifier.verify(
            transacoes_parser=transacoes,
            saldo_inicial=1000.0,
            saldo_final=1100.01,  # Diferença de 0.01
            file_name='arredond.pdf',
        )
        self.assertEqual(result.status, 'OK')


class TestExcelCrossValidation(unittest.TestCase):
    """Testa validação cruzada com Excel."""

    def test_excel_saldo_correto(self):
        transacoes = [
            {'data': '01/01/2026', 'descricao': 'PIX', 'valor': 1000.0,
             'tipo': 'entrada', 'banco': 'Bradesco', 'raw': '', 'categoria': ''},
            {'data': '02/01/2026', 'descricao': 'Boleto', 'valor': 300.0,
             'tipo': 'saida', 'banco': 'Bradesco', 'raw': '', 'categoria': ''},
        ]
        verifier = BradescoVerifier()
        result = verifier.verify(
            transacoes_parser=transacoes,
            saldo_inicial=500.0,
            saldo_final=1200.0,
            file_name='excel_ok.pdf',
            excel_saldo=700.0,  # entradas - saidas = 1000 - 300 = 700
        )
        self.assertEqual(result.status, 'OK')
        self.assertEqual(result.excel_closing_balance, Decimal('700'))


class TestOrchestrator(unittest.TestCase):
    """Testa o orquestrador de verificação."""

    def test_banco_desconhecido(self):
        result = executar_verificacao(
            banco_key='banco_fantasma',
            transacoes=[],
            saldo_inicial=None,
            saldo_final=None,
            file_name='fantasma.pdf',
        )
        self.assertEqual(result.status, 'SKIPPED')
        self.assertIn('nao implementado', result.skip_reason)

    def test_verificacao_ok_via_orquestrador(self):
        transacoes = [
            {'data': '01/01/2026', 'descricao': 'PIX Recebido', 'valor': 500.0,
             'tipo': 'entrada', 'banco': 'Nubank', 'raw': '', 'categoria': ''},
        ]
        result = executar_verificacao(
            banco_key='nubank',
            transacoes=transacoes,
            saldo_inicial=1000.0,
            saldo_final=1500.0,
            file_name='nubank_ok.pdf',
        )
        self.assertEqual(result.status, 'OK')
        self.assertEqual(result.bank_name, 'Nubank')

    def test_verificacao_divergente_via_orquestrador(self):
        transacoes = [
            {'data': '01/01/2026', 'descricao': 'PIX', 'valor': 100.0,
             'tipo': 'entrada', 'banco': 'Cora', 'raw': '', 'categoria': ''},
        ]
        result = executar_verificacao(
            banco_key='cora',
            transacoes=transacoes,
            saldo_inicial=0.0,
            saldo_final=999.0,  # Deveria ser 100
            file_name='cora_div.pdf',
        )
        # Será REPROCESSED_FAIL pois a releitura não resolve divergência de dados
        self.assertIn(result.status, ('DIVERGENT', 'REPROCESSED_FAIL'))
        self.assertTrue(result.was_reprocessed)


class TestAllVerifiersExist(unittest.TestCase):
    """Testa que existe um verificador para cada banco do sistema."""

    BANCOS_ESPERADOS = [
        'itau', 'itau_empresas', 'bradesco', 'bradesco_empresas',
        'bradesco_net_empresas', 'santander', 'santander_empresas',
        'santander_consolidado', 'santander_empresas_v1', 'santander_empresas_v2',
        'bb', 'caixa', 'nubank', 'inter', 'inter_n2', 'sicredi',
        'stone', 'c6bank', 'pagbank', 'mercado_pago', 'cora', 'bs2',
        'sumup', 'xp_extrato', 'xp_posicao',
        'itau_n2', 'itau_empresas_n2',
    ]

    def test_todos_bancos_tem_verificador(self):
        for banco in self.BANCOS_ESPERADOS:
            self.assertIn(
                banco, VERIFIERS,
                f'Verificador ausente para banco: {banco}'
            )

    def test_verificadores_instanciaveis(self):
        for banco, cls in VERIFIERS.items():
            instance = cls()
            self.assertIsInstance(instance, BankVerifier)
            self.assertTrue(len(instance.bank_name) > 0, f'{banco} sem bank_name')


class TestIntermediateBalanceExtraction(unittest.TestCase):
    """Testa extração de saldos intermediários de texto PDF por banco."""

    def test_itau_saldo_total_disponivel(self):
        texto = 'SALDO TOTAL DISPONÍVEL DIA 15/01 1.234,56\nOutra linha'
        verifier = ItauVerifier()
        saldos = verifier.extract_intermediate_balances(texto)
        self.assertEqual(len(saldos), 1)
        self.assertEqual(saldos[0][1], Decimal('1234.56'))

    def test_bb_saldo_do_dia(self):
        texto = '01/03/2026 SALDO DO DIA 15.432,10 C'
        verifier = BancoDoBrasilVerifier()
        saldos = verifier.extract_intermediate_balances(texto)
        self.assertEqual(len(saldos), 1)
        self.assertEqual(saldos[0][1], Decimal('15432.10'))

    def test_inter_saldo_do_dia(self):
        texto = '1 de Março de 2026 Saldo do dia: R$ 5.678,90 Valor Saldo por transação'
        verifier = InterVerifier()
        saldos = verifier.extract_intermediate_balances(texto)
        self.assertEqual(len(saldos), 1)
        self.assertEqual(saldos[0][0], '01/03/2026')
        self.assertEqual(saldos[0][1], Decimal('5678.90'))

    def test_c6bank_saldo_do_dia(self):
        texto = 'Saldo do dia 15/01/2026 R$ 3.456,78\nOutra linha'
        verifier = C6BankVerifier()
        saldos = verifier.extract_intermediate_balances(texto)
        self.assertEqual(len(saldos), 1)
        self.assertEqual(saldos[0][1], Decimal('3456.78'))

    def test_c6bank_ignora_bullet(self):
        texto = 'Saldo do dia \u2022 3 de janeiro de 2026 \u2022 R$ 4.813,94'
        verifier = C6BankVerifier()
        saldos = verifier.extract_intermediate_balances(texto)
        self.assertEqual(len(saldos), 0)  # Linha com bullet deve ser ignorada

    def test_pagbank_saldo_do_dia(self):
        texto = '15/01/2026 Saldo do dia R$ 2.345,67'
        verifier = PagBankVerifier()
        saldos = verifier.extract_intermediate_balances(texto)
        self.assertEqual(len(saldos), 1)
        self.assertEqual(saldos[0][0], '15/01/2026')
        self.assertEqual(saldos[0][1], Decimal('2345.67'))

    def test_caixa_saldo_dia(self):
        texto = 'SALDO DIA R$ 8.765,43'
        verifier = CaixaVerifier()
        saldos = verifier.extract_intermediate_balances(texto)
        self.assertEqual(len(saldos), 1)
        self.assertEqual(saldos[0][1], Decimal('8765.43'))

    def test_caixa_ignora_saldo_anterior(self):
        texto = 'SALDO ANTERIOR R$ 1.000,00\nSALDO DIA R$ 2.000,00'
        verifier = CaixaVerifier()
        saldos = verifier.extract_intermediate_balances(texto)
        self.assertEqual(len(saldos), 1)  # Apenas SALDO DIA, não SALDO ANTERIOR

    def test_bradesco_total_line(self):
        texto = 'Total 1.500,00 -800,00 1.700,00'
        verifier = BradescoVerifier()
        saldos = verifier.extract_intermediate_balances(texto)
        self.assertEqual(len(saldos), 1)
        self.assertEqual(saldos[0][1], Decimal('1700.00'))

    def test_santander_sem_intermediarios(self):
        verifier = SantanderVerifier()
        saldos = verifier.extract_intermediate_balances('Qualquer texto')
        self.assertEqual(len(saldos), 0)

    def test_nubank_sem_intermediarios(self):
        verifier = NubankVerifier()
        saldos = verifier.extract_intermediate_balances('Qualquer texto')
        self.assertEqual(len(saldos), 0)

    def test_sicredi_saldo_do_dia(self):
        texto = '31/01/2026 Saldo do dia 4.567,89'
        verifier = SicrediVerifier()
        saldos = verifier.extract_intermediate_balances(texto)
        self.assertEqual(len(saldos), 1)
        self.assertEqual(saldos[0][1], Decimal('4567.89'))


class TestDataComparison(unittest.TestCase):
    """Testa comparação de datas."""

    def test_mesma_data(self):
        self.assertTrue(BankVerifier._data_menor_ou_igual('01/01/2026', '01/01/2026'))

    def test_data_anterior(self):
        self.assertTrue(BankVerifier._data_menor_ou_igual('01/01/2026', '02/01/2026'))

    def test_data_posterior(self):
        self.assertFalse(BankVerifier._data_menor_ou_igual('03/01/2026', '02/01/2026'))

    def test_meses_diferentes(self):
        self.assertTrue(BankVerifier._data_menor_ou_igual('31/01/2026', '01/02/2026'))

    def test_anos_diferentes(self):
        self.assertTrue(BankVerifier._data_menor_ou_igual('31/12/2025', '01/01/2026'))

    def test_formato_invalido_nao_bloqueia(self):
        self.assertTrue(BankVerifier._data_menor_ou_igual('invalido', '01/01/2026'))


if __name__ == '__main__':
    unittest.main()
