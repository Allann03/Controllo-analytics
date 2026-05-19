"""
Teste unitario do parser PagBank (nivel isolado).
Roda o parser fora do pipeline e valida transacoes + saldos
intermediarios COM o saldo fantasma injetado.
"""
import sys
import os
from decimal import Decimal
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from services.parsers.pagbank import ParserPagBank

PDF_JUN = os.environ.get('PAGBANK_JUN',
    r'C:\Users\Allan\Downloads\Extrato da Conta - Junho.2025 (1).pdf')
PDF_JUL = os.environ.get('PAGBANK_JUL',
    r'C:\Users\Allan\Downloads\Extrato da Conta - Julho.2025.pdf')

EXPECTED = {
    'junho': {
        'total_tx': 218,
        'total_saldos_com_fantasma': 29,  # 28 reais + 1 fantasma
        'data_fantasma': '31/05/2025',
        'saldo_fantasma': Decimal('117.39'),
        'saldo_final': Decimal('141.45'),
    },
    'julho': {
        'total_tx': 217,
        'total_saldos_com_fantasma': 29,
        'data_fantasma': '30/06/2025',
        'saldo_fantasma': Decimal('141.45'),
        'saldo_final': Decimal('188.01'),
    },
}


def testar_pdf(path: str, label: str, esperado: dict):
    print(f'\n{"=" * 60}\nUNIT - PagBank {label.upper()}\n{"=" * 60}')

    if not os.path.exists(path):
        print(f'ERRO: PDF nao encontrado: {path}')
        sys.exit(1)

    parser = ParserPagBank(path)
    txs = parser.extrair()
    saldos = parser._extrair_saldos_intermediarios()

    print(f'Tx: {len(txs)} (esperado {esperado["total_tx"]})')
    print(f'Saldos (incluindo fantasma): {len(saldos)} (esperado {esperado["total_saldos_com_fantasma"]})')

    assert len(txs) == esperado['total_tx'], \
        f'tx count {len(txs)} != {esperado["total_tx"]}'
    assert len(saldos) == esperado['total_saldos_com_fantasma'], \
        f'saldos count {len(saldos)} != {esperado["total_saldos_com_fantasma"]}'

    # Primeiro saldo deve ser o fantasma
    primeiro = saldos[0]
    print(f'Primeiro saldo (fantasma): {primeiro}')
    assert primeiro['data'] == esperado['data_fantasma'], \
        f'data fantasma {primeiro["data"]} != {esperado["data_fantasma"]}'
    assert primeiro['saldo'] == esperado['saldo_fantasma'], \
        f'saldo fantasma {primeiro["saldo"]} != {esperado["saldo_fantasma"]}'

    # Verificacao incremental usando o fantasma como SI (igual o orquestrador faz)
    mov = defaultdict(lambda: {'e': Decimal(0), 's': Decimal(0)})
    for t in txs:
        if t['tipo'] == 'entrada':
            mov[t['data']]['e'] += t['valor']
        else:
            mov[t['data']]['s'] += t['valor']

    saldo_calc = saldos[0]['saldo']
    ok = 1
    div = []
    for s in saldos[1:]:
        d = s['data']
        m = mov[d]
        saldo_calc += m['e'] - m['s']
        if abs(saldo_calc - s['saldo']) < Decimal('0.01'):
            ok += 1
        else:
            div.append((d, saldo_calc, s['saldo']))

    print(f'Verif progressiva (orquestrador-like): {ok}/{len(saldos)}')
    assert ok == len(saldos), f'{len(div)} divergencias: {div[:3]}'

    print(f'Saldo final calculado: R$ {saldo_calc}')
    assert saldo_calc == esperado['saldo_final']

    # Idempotencia: chamar de novo nao duplica nem altera
    saldos2 = parser._extrair_saldos_intermediarios()
    assert len(saldos2) == len(saldos), 'idempotencia quebrada (saldos duplicados)'
    txs2 = parser.extrair()
    assert len(txs2) == len(txs), 'idempotencia quebrada (tx duplicadas)'

    # Sanity
    assert all(t['banco'] == 'PagBank' for t in txs)
    assert all(t['tipo'] in ('entrada', 'saida') for t in txs)
    assert all(t['valor'] > 0 for t in txs)
    assert not any('saldo do dia' in t['descricao'].lower() for t in txs)


def main():
    testar_pdf(PDF_JUN, 'junho', EXPECTED['junho'])
    testar_pdf(PDF_JUL, 'julho', EXPECTED['julho'])

    # Continuidade entre meses
    parser_jun = ParserPagBank(PDF_JUN)
    parser_jun.extrair()
    saldo_final_jun = parser_jun._extrair_saldos_intermediarios()[-1]['saldo']

    parser_jul = ParserPagBank(PDF_JUL)
    parser_jul.extrair()
    saldo_fantasma_jul = parser_jul._extrair_saldos_intermediarios()[0]['saldo']

    print(f'\nContinuidade: saldo final junho ({saldo_final_jun}) '
          f'== saldo fantasma julho ({saldo_fantasma_jul})?')
    assert saldo_final_jun == saldo_fantasma_jul

    # Multilinha em junho
    parser = ParserPagBank(PDF_JUN)
    txs = parser.extrair()
    multi = [t for t in txs if 'PAGSEGURO INTERNET' in t['descricao']]
    print(f'Multilinha em junho: {len(multi)} (esperado 2)')
    assert len(multi) == 2
    assert sorted(t['valor'] for t in multi) == [Decimal('6.90'), Decimal('7.90')]

    print('\n=== TESTES UNITARIOS PASSARAM ===')


if __name__ == '__main__':
    main()
