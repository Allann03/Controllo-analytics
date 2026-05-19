"""
test_parsers.py – Script de teste dos parsers de extrato bancário.

Modo resumo (padrão):
    python test_parsers.py

Modo verbose — imprime TODAS as transações de cada arquivo:
    python test_parsers.py --verbose
    python test_parsers.py -v

Modo de banco específico:
    python test_parsers.py --banco nubank
    python test_parsers.py --banco itau -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.extrator_pdf import extrair_extrato

PASTA = os.path.join(os.path.dirname(__file__), 'test_extratos')
SEP = '-' * 105
SEP_CURTO = '-' * 65


def formatar_brl(valor: float) -> str:
    return f'R$ {valor:>14,.2f}'


def formatar_brl_linha(valor: float, tipo: str) -> str:
    """Formata valor com sinal: + para entrada, - para saída."""
    if tipo == 'entrada':
        return f'  + R$ {valor:>12,.2f}'
    elif tipo == 'saida':
        return f'  - R$ {valor:>12,.2f}'
    else:
        return f'    R$ {valor:>12,.2f}'


def main() -> None:
    # Analisa argumentos
    args = sys.argv[1:]
    verbose = '--verbose' in args or '-v' in args
    banco_filtro = ''
    if '--banco' in args:
        idx = args.index('--banco')
        if idx + 1 < len(args):
            banco_filtro = args[idx + 1].lower()

    if not os.path.isdir(PASTA):
        print(f'Pasta não encontrada: {PASTA}')
        print('Crie a pasta backend/test_extratos/ e coloque PDFs de extrato lá.')
        sys.exit(1)

    pdfs = sorted(f for f in os.listdir(PASTA) if f.lower().endswith('.pdf'))

    if not pdfs:
        print(f'Nenhum PDF encontrado em: {PASTA}')
        sys.exit(0)

    # Cabeçalho da tabela
    print(SEP)
    print(f'{"Arquivo":<40} {"Banco":<18} {"Tx":>6} {"Entradas":>18} {"Saídas":>18}')
    print(SEP)

    falhas: list[str] = []
    bancos_encontrados: set[str] = set()

    for nome in pdfs:
        caminho = os.path.join(PASTA, nome)
        try:
            resultado = extrair_extrato(caminho)
            banco = resultado.get('banco', 'desconhecido')
            transacoes = resultado.get('transacoes', [])
            entradas = resultado.get('total_entradas', 0.0)
            saidas = resultado.get('total_saidas', 0.0)
            erro = resultado.get('erro')
            avisos = resultado.get('avisos', [])

            bancos_encontrados.add(banco)

            # Filtro de banco específico
            if banco_filtro and banco_filtro not in banco.lower():
                continue

            saldo_zero = any(
                'saldo zero' in av.lower() or 'nenhuma transação' in av.lower()
                for av in avisos
            )

            nome_curto = nome[:39]

            if erro or banco == 'desconhecido':
                falhas.append(f'  {nome}: {erro or "banco nao reconhecido"}')
                status = '[!] ' + (erro or 'banco nao reconhecido')[:60]
                print(f'{nome_curto:<40} {status}')

            elif len(transacoes) == 0 and not saldo_zero:
                falhas.append(f'  {nome}: banco={banco}, 0 transacoes extraidas')
                print(f'{nome_curto:<40} {banco:<18} {"0":>6} '
                      f'{"R$ 0,00":>18} {"R$ 0,00":>18}  [!] zero transacoes')

            elif len(transacoes) == 0 and saldo_zero:
                print(f'{nome_curto:<40} {banco:<18} {"0":>6} '
                      f'{formatar_brl(0):>18} {formatar_brl(0):>18}  (saldo zero)')

            else:
                print(f'{nome_curto:<40} {banco:<18} {len(transacoes):>6} '
                      f'{formatar_brl(entradas):>18} {formatar_brl(saidas):>18}')

            # Avisos (máx. 3 por arquivo)
            if avisos:
                for av in avisos[:3]:
                    print(f'   aviso: {av}')

            # ── Modo VERBOSE: lista todas as transações ───────────────
            if verbose and transacoes:
                print(f'   {SEP_CURTO}')
                print(f'   {"Data":<12} {"Tipo":<8} {"Valor":>18}  Descrição')
                print(f'   {SEP_CURTO}')
                for t in transacoes:
                    data = t.get('data', '')
                    tipo = t.get('tipo', '')
                    valor = float(t.get('valor', 0))
                    desc = str(t.get('descricao', ''))[:60]
                    valor_fmt = formatar_brl_linha(valor, tipo)
                    print(f'   {data:<12} {tipo:<8} {valor_fmt}  {desc}')
                print(f'   {SEP_CURTO}')
                print(f'   TOTAL  ENTRADAS: {formatar_brl(entradas)}')
                print(f'   TOTAL  SAÍDAS  : {formatar_brl(saidas)}')
                saldo = entradas - saidas
                sinal = '+' if saldo >= 0 else ''
                print(f'   SALDO DO PERÍODO: {sinal}{formatar_brl(saldo)}')
                print()

        except Exception as e:
            falhas.append(f'  {nome}: exceção – {e}')
            print(f'{nome[:39]:<40} ERRO: {e}')

    print(SEP)
    print(f'Total: {len(pdfs)} arquivo(s) | {len(falhas)} falha(s)')

    # Aviso se Nubank não foi encontrado
    nubank_detectado = any('nubank' in b.lower() for b in bancos_encontrados)
    if not nubank_detectado and not banco_filtro:
        print()
        print('[!] Extrato do Nubank NÃO encontrado em test_extratos/')
        print('    Para testar: adicione um PDF do Nubank na pasta test_extratos/')
        print('    Nomes típicos: "extrato-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX.pdf"')
        print('    ou "Extrato Nubank [Mês] [Ano].pdf"')

    if falhas:
        print('\nFalhas detectadas:')
        for f in falhas:
            print(f)

    print()


if __name__ == '__main__':
    main()
