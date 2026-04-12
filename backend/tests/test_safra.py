"""
Teste manual do parser Safra.
Roda contra o PDF de referencia e valida:
1. Numero esperado de transacoes
2. Saldos intermediarios capturados
3. Verificacao progressiva (saldo final bate)
4. Detalhe da divergencia conhecida em 12/03/2025
"""
import sys
import os
from decimal import Decimal
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from services.parsers.safra import ParserSafra

# AJUSTE O PATH se necessario
PDF = os.environ.get('SAFRA_PDF',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                 'test_extratos',
                 'Safra_PJ_-_Extrato_de_Movimentac_a_o_Janeiro_a_Julho_2025.pdf'))

EXPECTED = {
    'total_tx': 721,
    'total_saldos': 142,
    'saldo_inicial': Decimal('71.39'),
    'saldo_final_calc': Decimal('69.19'),
    'saldo_final_extrato': Decimal('69.19'),
    'saldos_ok': 141,
    'saldos_total': 142,
    'divergencias_count': 1,
    'divergencia_data': '12/03/2025',
}

def main():
    if not os.path.exists(PDF):
        print(f'ERRO: PDF nao encontrado em {PDF}')
        print('Defina SAFRA_PDF=/path/to/file.pdf')
        sys.exit(1)

    parser = ParserSafra(PDF)
    txs = parser.extrair()
    saldos = parser._extrair_saldos_intermediarios()

    print(f'Transacoes extraidas: {len(txs)} (esperado {EXPECTED["total_tx"]})')
    print(f'Saldos intermediarios: {len(saldos)} (esperado {EXPECTED["total_saldos"]})')

    assert len(txs) == EXPECTED['total_tx'], f'FALHA: tx count {len(txs)} != {EXPECTED["total_tx"]}'
    assert len(saldos) == EXPECTED['total_saldos'], f'FALHA: saldos count {len(saldos)} != {EXPECTED["total_saldos"]}'

    # Inferir saldo inicial
    primeiro = saldos[0]
    ent_d = sum(t['valor'] for t in txs if t['data'] == primeiro['data'] and t['tipo'] == 'entrada')
    sai_d = sum(t['valor'] for t in txs if t['data'] == primeiro['data'] and t['tipo'] == 'saida')
    SI = primeiro['saldo'] - (ent_d - sai_d)
    print(f'Saldo inicial inferido: R$ {SI} (esperado R$ {EXPECTED["saldo_inicial"]})')
    assert SI == EXPECTED['saldo_inicial'], f'FALHA: SI {SI} != {EXPECTED["saldo_inicial"]}'

    # Reconstruir dia a dia
    mov_dia = defaultdict(lambda: {'ent': Decimal(0), 'sai': Decimal(0)})
    for t in txs:
        if t['tipo'] == 'entrada':
            mov_dia[t['data']]['ent'] += t['valor']
        else:
            mov_dia[t['data']]['sai'] += t['valor']

    saldo_calc = SI
    ok = 0
    divergencias = []
    for s in saldos:
        d = s['data']
        m = mov_dia[d]
        saldo_calc += m['ent'] - m['sai']
        if abs(saldo_calc - s['saldo']) < Decimal('0.01'):
            ok += 1
        else:
            divergencias.append((d, saldo_calc, s['saldo'], saldo_calc - s['saldo']))

    print(f'Saldos verificados OK: {ok}/{len(saldos)} (esperado {EXPECTED["saldos_ok"]}/{EXPECTED["saldos_total"]})')
    print(f'Divergencias: {len(divergencias)}')
    for d in divergencias:
        print(f'  {d[0]}: calc={d[1]} esperado={d[2]} diff={d[3]}')

    assert ok == EXPECTED['saldos_ok'], f'FALHA: saldos OK {ok} != {EXPECTED["saldos_ok"]}'
    assert len(divergencias) == EXPECTED['divergencias_count']
    assert divergencias[0][0] == EXPECTED['divergencia_data']

    print(f'\nSaldo final calculado: R$ {saldo_calc}')
    print(f'Saldo final esperado:  R$ {EXPECTED["saldo_final_calc"]}')
    assert saldo_calc == EXPECTED['saldo_final_calc']

    # Validar saldo final do extrato (ultimo CONTA CORRENTE)
    sf = saldos[-1]['saldo']
    print(f'Saldo final do extrato (ultimo CONTA CORRENTE): R$ {sf}')
    assert sf == EXPECTED['saldo_final_extrato']

    # Sanity checks adicionais
    assert all(t['banco'] == 'Safra' for t in txs)
    assert all(t['tipo'] in ('entrada', 'saida') for t in txs)
    assert all(t['valor'] > 0 for t in txs)  # valores sempre positivos
    assert all(t['descricao'] for t in txs)  # descricao nao-vazia
    # Nao deve ter "CONTA CORRENTE" como descricao em nenhuma tx
    assert not any('CONTA CORRENTE' in t['descricao'].upper() for t in txs)

    # Tipos de lancamento esperados
    pix_recebidos = sum(1 for t in txs if 'PIX RECEBIDO' in t['descricao'])
    pix_enviados = sum(1 for t in txs if 'PIX ENVIADO' in t['descricao'])
    print(f'\nPIX recebidos: {pix_recebidos} (esperado ~515)')
    print(f'PIX enviados:  {pix_enviados} (esperado ~82)')
    assert pix_recebidos >= 510, f'PIX recebidos abaixo do esperado: {pix_recebidos}'
    assert pix_enviados >= 80, f'PIX enviados abaixo do esperado: {pix_enviados}'

    print('\n=== TODOS OS TESTES PASSARAM ===')

if __name__ == '__main__':
    main()
