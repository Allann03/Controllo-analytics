"""
Teste de INTEGRACAO end-to-end do PagBank.
Roda o pipeline COMPLETO (extrair_extrato do extrator_pdf.py)
e valida que verificacao_saldos.conferencia_ok == True e que NAO HA
divergencias na verificacao progressiva.

Esse e o teste que reproduz exatamente o que a UI faz, e que faltou
na implementacao anterior - resultando no bug em producao.
"""
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from services.extrator_pdf import extrair_extrato, detectar_banco

PDF_JUN = os.environ.get('PAGBANK_JUN',
    r'C:\Users\Allan\Downloads\Extrato da Conta - Junho.2025 (1).pdf')
PDF_JUL = os.environ.get('PAGBANK_JUL',
    r'C:\Users\Allan\Downloads\Extrato da Conta - Julho.2025.pdf')


def testar_integracao(pdf_path: str, label: str):
    print(f'\n{"=" * 60}\nINTEGRACAO - PagBank {label.upper()}\n{"=" * 60}')

    if not os.path.exists(pdf_path):
        print(f'ERRO: PDF nao encontrado: {pdf_path}')
        sys.exit(1)

    # 1. Detecao automatica
    banco = detectar_banco(pdf_path)
    print(f'Detectado: {banco}')
    assert banco == 'pagbank', f'detectou {banco}, esperado pagbank'

    # 2. Pipeline completo (mesma funcao que o router chama)
    resultado = extrair_extrato(pdf_path, banco_id='pagbank')
    print(f'Tipo de retorno: {type(resultado).__name__}')

    assert isinstance(resultado, dict), 'extrair_extrato deve retornar dict'
    assert 'erro' not in resultado or not resultado['erro'], \
        f'Pipeline retornou erro: {resultado.get("erro")}'

    txs = resultado.get('transacoes', [])
    n_tx = len(txs)
    print(f'Total transacoes: {n_tx}')
    assert n_tx > 0, 'Nenhuma transacao extraida'

    # 3. Validar verificacao_saldos
    vs = resultado.get('verificacao_saldos')
    assert vs is not None, 'verificacao_saldos esta ausente do retorno'
    print(f'verificacao_saldos:')
    print(f'  saldo_inicial: {vs.get("saldo_inicial")}')
    print(f'  saldo_inicial_encontrado: {vs.get("saldo_inicial_encontrado")}')
    print(f'  saldo_final_informado: {vs.get("saldo_final_informado")}')
    print(f'  saldo_final_calculado: {vs.get("saldo_final_calculado")}')
    print(f'  conferencia_ok: {vs.get("conferencia_ok")}')
    print(f'  saldos_intermediarios_ok: {vs.get("saldos_intermediarios_ok")}/{vs.get("saldos_intermediarios_verificados")}')
    print(f'  modo_saldo: {vs.get("modo_saldo")}')
    print(f'  divergencias: {len(vs.get("divergencias", []))}')

    # *** O ASSERT CRITICO ***
    assert vs.get('conferencia_ok') is True, (
        f'CONFERENCIA FALHOU em {label}. '
        f'divergencias: {vs.get("divergencias")}, '
        f'saldo_final_calculado: {vs.get("saldo_final_calculado")}, '
        f'saldo_final_informado: {vs.get("saldo_final_informado")}'
    )

    div = vs.get('divergencias') or []
    assert len(div) == 0, f'{len(div)} divergencias inesperadas: {div[:5]}'

    sf_calc = vs.get('saldo_final_calculado')
    sf_inf = vs.get('saldo_final_informado')
    if sf_calc is not None and sf_inf is not None:
        diff = abs(Decimal(str(sf_calc)) - Decimal(str(sf_inf)))
        print(f'Saldo final: calc={sf_calc}, informado={sf_inf}, diff={diff}')
        assert diff < Decimal('0.01'), f'Diferenca de saldo final: {diff}'

    print(f'OK - {label} sem divergencias no pipeline real')


def main():
    testar_integracao(PDF_JUN, 'junho')
    testar_integracao(PDF_JUL, 'julho')
    print('\n=== TESTES DE INTEGRACAO PASSARAM ===')
    print('\nEsse e o teste que reproduz o que a UI faz.')
    print('Se ele passa, o bug do screenshot esta corrigido.')


if __name__ == '__main__':
    main()
