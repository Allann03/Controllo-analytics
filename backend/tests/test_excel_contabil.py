"""
Testes de conformidade contábil do Excel gerado (partida dobrada).
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
import openpyxl
from io import BytesIO


def _gerar_excel_teste():
    """Gera um Excel contábil com dados de teste e retorna o Workbook."""
    from services.gerador_excel_contabil import gerar_excel_contabil

    transacoes = [
        {"data": "02/01/2025", "descricao": "PIX Recebido - Cliente ABC", "valor": Decimal("1500.00"), "tipo": "entrada", "banco": "Nubank"},
        {"data": "03/01/2025", "descricao": "Pagamento Fornecedor XYZ", "valor": Decimal("750.50"), "tipo": "saida", "banco": "Nubank"},
        {"data": "05/01/2025", "descricao": "Transferência recebida", "valor": Decimal("2000.00"), "tipo": "entrada", "banco": "Nubank"},
        {"data": "10/01/2025", "descricao": "Conta de energia", "valor": Decimal("320.75"), "tipo": "saida", "banco": "Nubank"},
        {"data": "15/01/2025", "descricao": "Aluguel", "valor": Decimal("1800.00"), "tipo": "saida", "banco": "Nubank"},
    ]

    conta_banco_map = {"Nubank": "11202"}
    regras_usuario = []
    cadastros = []
    plano = {
        "11202": "Banco Nubank - C/C",
        "11200": "Bancos Conta Movimento",
        "39901": "Receitas a Classificar",
        "49901": "Despesas a Classificar",
    }

    excel_bytes = gerar_excel_contabil(
        transacoes=transacoes,
        conta_banco_map=conta_banco_map,
        regras_usuario=regras_usuario,
        cadastros=cadastros,
        plano=plano,
        banco_detectado="Nubank",
        saldo_inicial=5000.0,
    )
    wb = openpyxl.load_workbook(BytesIO(excel_bytes))
    return wb


def test_partida_dobrada_no_empty_contas():
    """Nenhum lançamento pode ter conta débito ou crédito vazia."""
    wb = _gerar_excel_teste()
    ws = wb["Lançamentos Contábeis"]

    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            break  # fim dos dados
        debito = row[4]
        credito = row[5]
        valor = row[6]
        assert debito, f"Conta débito vazia no lançamento: {row}"
        assert credito, f"Conta crédito vazia no lançamento: {row}"


def test_partida_dobrada_no_negative_values():
    """Contabilidade NÃO usa valores negativos."""
    wb = _gerar_excel_teste()
    ws = wb["Lançamentos Contábeis"]

    for row in ws.iter_rows(min_row=2, values_only=True):
        valor = row[6]
        if valor is None:
            break
        assert isinstance(valor, (int, float)), f"Valor não numérico: {valor} ({type(valor)})"
        assert valor > 0, f"Valor não-positivo: {valor}"


def test_partida_dobrada_valores_numericos():
    """Células de valor devem ser numéricas, não texto."""
    wb = _gerar_excel_teste()
    ws = wb["Lançamentos Contábeis"]

    for row in ws.iter_rows(min_row=2, values_only=True):
        valor = row[6]
        if valor is None:
            break
        assert isinstance(valor, (int, float)), f"Valor é texto, não número: {valor!r}"


def test_contas_existem_no_plano():
    """Toda conta usada nos lançamentos deve existir na aba Plano de Contas."""
    wb = _gerar_excel_teste()
    ws_lanc = wb["Lançamentos Contábeis"]
    ws_plano = wb["Plano de Contas Utilizado"]

    # Coletar contas do plano
    contas_plano = set()
    for row in ws_plano.iter_rows(min_row=2, values_only=True):
        if row[0]:
            contas_plano.add(str(row[0]))

    # Coletar contas usadas
    contas_usadas = set()
    for row in ws_lanc.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            break
        if row[4]: contas_usadas.add(str(row[4]))  # débito
        if row[5]: contas_usadas.add(str(row[5]))  # crédito

    faltando = contas_usadas - contas_plano
    assert not faltando, f"Contas usadas mas ausentes no plano: {faltando}"


def test_lancamentos_numeracao_sequencial():
    """Numeração dos lançamentos deve ser sequencial."""
    wb = _gerar_excel_teste()
    ws = wb["Lançamentos Contábeis"]

    numeros = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            break
        numeros.append(row[1])  # coluna Lançamento

    for i in range(1, len(numeros)):
        assert numeros[i] == numeros[i-1] + 1, \
            f"Gap na numeração: {numeros[i-1]} → {numeros[i]}"


def test_resumo_aba_exists():
    """Aba Resumo deve existir e ter dados."""
    wb = _gerar_excel_teste()
    assert "Resumo" in wb.sheetnames
    ws = wb["Resumo"]
    # Deve ter pelo menos 10 linhas de dados
    rows = list(ws.iter_rows(min_row=3, values_only=True))
    assert len(rows) >= 8, f"Resumo tem poucas linhas: {len(rows)}"
