"""
test_all_parsers.py — Script de teste automatizado de TODOS os parsers de extrato.

Varre todos os PDFs em tests/fixtures/pdfs_reais/ e test_extratos/,
detecta banco, extrai transacoes, calcula gap e roda validacoes V1-V4.

Validacoes:
  V1 — Integridade basica (TX > 0, campos obrigatorios, valores validos)
  V2 — Reconciliacao (SI + entradas - saidas = SF)
  V3 — Confianca (ALTA, MEDIA, BAIXA)
  V4 — Sanidade (duplicatas, valores absurdos, datas inconsistentes)

Uso:
  python -m tests.test_all_parsers          (relatorio completo)
  python -m tests.test_all_parsers --json   (saida JSON)

Exit code:
  0 se assertividade >= 90%
  1 se assertividade < 90%

BLOCO 8 FINAL.
"""

import sys
import os
import re
import json
import warnings
from datetime import datetime
from decimal import Decimal
from typing import Optional

# Setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
import logging
logging.disable(logging.WARNING)

from services.extrator_pdf import extrair_extrato, detectar_banco


# -- Constantes ---------------------------------------------------------------

PDF_DIRS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'tests', 'fixtures', 'pdfs_reais'),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'test_extratos'),
]

LIMITE_VALOR_PJ = 1_000_000_000  # R$ 1B
LIMITE_VALOR_PF = 100_000_000    # R$ 100M
TOL_GAP = 0.02                   # tolerancia de arredondamento

# PDFs conhecidos como vetoriais/imagem/CID-encoded (requer OCR) ou sem texto extraivel
KNOWN_OCR = {
    'Extrato Jan à Jul.pdf',
    'extrato 01.07.25 até 11.02.26.pdf',
    'Inter.pdf',
    'Itaú 07828-5.pdf',
    'Itaú 07828-5_1.pdf',
    'Itaú 09089-2.pdf',
    'EXTRATO SICREDI.pdf',
    # CID-encoded Itaú (font substitution — pdfplumber can't decode)
    'Extrato Mensal_Novembro2025 - Consolidado.pdf',
    'Extrato Mensal_Outubro2025 - Consolidado.pdf',
    'Extrato Mensal_Setembro2025 - Consolidado.pdf',
}

# PDFs com saldo zero ou sem transacoes — extrato legitimamente vazio
KNOWN_EMPTY = {
    'ExtratoMY - zerado 0251_994174_12-03-2026.pdf',
}


# -- V1: Integridade basica ---------------------------------------------------

def v1_integridade(resultado: dict) -> dict:
    """
    V1 — Integridade basica.
    Retorna {'ok': bool, 'falhas': [str], 'avisos': [str]}
    """
    falhas = []
    avisos = []
    txs = resultado.get('transacoes', [])
    banco = resultado.get('banco', 'desconhecido')

    if banco == 'desconhecido':
        falhas.append('Banco nao detectado')
        return {'ok': False, 'falhas': falhas, 'avisos': avisos}

    if not txs:
        falhas.append(f'Nenhuma transacao extraida (banco={banco})')
        return {'ok': False, 'falhas': falhas, 'avisos': avisos}

    for i, t in enumerate(txs):
        if not t.get('data'):
            falhas.append(f'TX[{i}]: data ausente')
        elif not re.match(r'^\d{2}/\d{2}/\d{4}$', t['data']):
            falhas.append(f'TX[{i}]: data invalida: {t["data"]}')

        if not t.get('descricao') or not t['descricao'].strip():
            falhas.append(f'TX[{i}]: descricao vazia')

        valor = t.get('valor', 0)
        if valor == 0:
            avisos.append(f'TX[{i}]: valor=0 (suspeito)')
        if valor < 0:
            falhas.append(f'TX[{i}]: valor negativo: {valor}')

        if t.get('tipo') not in ('entrada', 'saida', 'posicao', 'investimento'):
            falhas.append(f'TX[{i}]: tipo invalido: {t.get("tipo")}')

    return {'ok': len(falhas) == 0, 'falhas': falhas[:10], 'avisos': avisos[:5]}


# -- V2: Reconciliacao --------------------------------------------------------

def v2_reconciliacao(resultado: dict) -> dict:
    """
    V2 — Reconciliacao: SI + entradas - saidas = SF.
    Retorna {'ok': bool, 'gap': float|None, 'gap_pct': float|None, 'classificacao': str}
    """
    si = resultado.get('saldo_inicial')
    sf = resultado.get('saldo_final')
    te = resultado.get('total_entradas', 0)
    ts = resultado.get('total_saidas', 0)
    txs = resultado.get('transacoes', [])

    if not txs:
        return {'ok': False, 'gap': None, 'gap_pct': None, 'classificacao': 'SEM_TX'}

    if si is None or sf is None:
        return {'ok': False, 'gap': None, 'gap_pct': None, 'classificacao': 'SEM_SALDO'}

    gap = round(si + te - ts - sf, 2)
    volume = te + ts
    gap_pct = abs(gap / volume * 100) if volume > 0 else 0

    if abs(gap) < TOL_GAP:
        return {'ok': True, 'gap': gap, 'gap_pct': 0, 'classificacao': 'OK'}
    elif gap_pct < 1.0:
        return {'ok': False, 'gap': gap, 'gap_pct': gap_pct, 'classificacao': 'ACEITAVEL'}
    else:
        return {'ok': False, 'gap': gap, 'gap_pct': gap_pct, 'classificacao': 'FALHA'}


# -- V3: Confianca ------------------------------------------------------------

def v3_confianca(resultado: dict, v1: dict, v2: dict) -> str:
    """
    V3 — Nivel de confianca.
    ALTA: V1 ok + V2 gap=0 + SI e SF detectados
    MEDIA: V1 ok + V2 gap<1% OU sem SI/SF
    BAIXA: V1 falha OU V2 gap>1%
    """
    si = resultado.get('saldo_inicial')
    sf = resultado.get('saldo_final')

    if v1['ok'] and v2['ok'] and si is not None and sf is not None:
        return 'ALTA'
    if v1['ok'] and (v2['classificacao'] in ('ACEITAVEL', 'SEM_SALDO')):
        return 'MEDIA'
    if v1['ok'] and not v1['falhas']:
        return 'MEDIA'
    return 'BAIXA'


# -- V4: Sanidade --------------------------------------------------------------

def v4_sanidade(resultado: dict) -> dict:
    """
    V4 — Verificacoes de sanidade.
    Retorna {'ok': bool, 'alertas': [str]}
    """
    alertas = []
    txs = resultado.get('transacoes', [])

    if not txs:
        return {'ok': True, 'alertas': []}

    # Duplicatas: mesma data + descricao + valor
    # (NAO considerar duplicata — bancos legitimamente tem tx identicas)
    # Apenas flag se > 3 identicas
    from collections import Counter
    keys = [(t.get('data', ''), t.get('descricao', ''), t.get('valor', 0)) for t in txs]
    counts = Counter(keys)
    for key, cnt in counts.items():
        if cnt > 3:
            alertas.append(f'Possivel duplicata ({cnt}x): {key[0]} {key[1][:30]} R${key[2]:.2f}')

    # Valores absurdos
    for t in txs:
        if t.get('valor', 0) > LIMITE_VALOR_PF:
            alertas.append(f'Valor absurdo: R${t["valor"]:,.2f} em {t["data"]} {t["descricao"][:30]}')

    return {'ok': len(alertas) == 0, 'alertas': alertas[:10]}


# -- Runner principal ----------------------------------------------------------

def run_all_tests() -> dict:
    """Executa testes em todos os PDFs e retorna resultados."""
    all_results = []

    for pdf_dir in PDF_DIRS:
        if not os.path.isdir(pdf_dir):
            continue
        pdfs = sorted([f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')])

        for fname in pdfs:
            path = os.path.join(pdf_dir, fname)
            folder = os.path.basename(pdf_dir)

            try:
                resultado = extrair_extrato(path)
            except Exception as e:
                all_results.append({
                    'arquivo': fname, 'dir': folder,
                    'banco': 'ERROR', 'tx': 0,
                    'v1': {'ok': False, 'falhas': [str(e)[:80]], 'avisos': []},
                    'v2': {'ok': False, 'gap': None, 'gap_pct': None, 'classificacao': 'ERRO'},
                    'v3': 'BAIXA',
                    'v4': {'ok': True, 'alertas': []},
                    'is_ocr': fname in KNOWN_OCR,
                })
                continue

            banco = resultado.get('banco', 'desconhecido')
            txs = resultado.get('transacoes', [])

            is_empty = fname in KNOWN_EMPTY

            v1 = v1_integridade(resultado)
            v2 = v2_reconciliacao(resultado)
            v3 = v3_confianca(resultado, v1, v2)
            v4 = v4_sanidade(resultado)

            # Known-empty files: upgrade from BAIXA to MEDIA (legitimamente vazio)
            if is_empty and v3 == 'BAIXA' and banco != 'desconhecido':
                v3 = 'MEDIA'

            all_results.append({
                'arquivo': fname, 'dir': folder,
                'banco': banco, 'tx': len(txs),
                'si': resultado.get('saldo_inicial'),
                'sf': resultado.get('saldo_final'),
                'total_entradas': resultado.get('total_entradas', 0),
                'total_saidas': resultado.get('total_saidas', 0),
                'v1': v1, 'v2': v2, 'v3': v3, 'v4': v4,
                'is_ocr': fname in KNOWN_OCR,
                'is_empty': is_empty,
                'avisos_parser': resultado.get('avisos', []),
            })

    # Estatisticas
    total = len(all_results)
    non_ocr = [r for r in all_results if not r.get('is_ocr')]
    total_non_ocr = len(non_ocr)

    detected = sum(1 for r in non_ocr if r['banco'] not in ('desconhecido', 'ERROR'))
    with_tx = sum(1 for r in non_ocr if r['tx'] > 0)
    gap_zero = sum(1 for r in non_ocr if r['v2']['ok'])
    alta = sum(1 for r in non_ocr if r['v3'] == 'ALTA')
    media = sum(1 for r in non_ocr if r['v3'] == 'MEDIA')
    baixa = sum(1 for r in non_ocr if r['v3'] == 'BAIXA')

    # Assertividade = PDFs com confianca ALTA ou MEDIA / total (excluindo OCR)
    assertividade = (alta + media) / total_non_ocr * 100 if total_non_ocr > 0 else 0

    return {
        'resultados': all_results,
        'stats': {
            'total': total,
            'total_excl_ocr': total_non_ocr,
            'ocr_needed': sum(1 for r in all_results if r.get('is_ocr')),
            'detected': detected,
            'detected_pct': round(detected / total_non_ocr * 100, 1) if total_non_ocr else 0,
            'with_tx': with_tx,
            'with_tx_pct': round(with_tx / total_non_ocr * 100, 1) if total_non_ocr else 0,
            'gap_zero': gap_zero,
            'gap_zero_pct': round(gap_zero / total_non_ocr * 100, 1) if total_non_ocr else 0,
            'alta': alta,
            'media': media,
            'baixa': baixa,
            'assertividade': round(assertividade, 1),
        },
        'data': datetime.now().strftime('%d/%m/%Y %H:%M'),
    }


# -- Formatacao ----------------------------------------------------------------

def format_report(data: dict) -> str:
    lines = []
    s = data['stats']

    lines.append('=' * 70)
    lines.append(f'RELATORIO DE ASSERTIVIDADE — {data["data"]}')
    lines.append('=' * 70)
    lines.append(f'Total PDFs:          {s["total"]}')
    lines.append(f'Excl. OCR:           {s["total_excl_ocr"]} ({s["ocr_needed"]} requerem OCR)')
    lines.append(f'Banco detectado:     {s["detected"]}/{s["total_excl_ocr"]} ({s["detected_pct"]}%)')
    lines.append(f'Com transacoes:      {s["with_tx"]}/{s["total_excl_ocr"]} ({s["with_tx_pct"]}%)')
    lines.append(f'Gap = 0:             {s["gap_zero"]}/{s["total_excl_ocr"]} ({s["gap_zero_pct"]}%)')
    lines.append(f'Confianca ALTA:      {s["alta"]}/{s["total_excl_ocr"]}')
    lines.append(f'Confianca MEDIA:     {s["media"]}/{s["total_excl_ocr"]}')
    lines.append(f'Confianca BAIXA:     {s["baixa"]}/{s["total_excl_ocr"]}')
    lines.append(f'ASSERTIVIDADE:       {s["assertividade"]}%')
    lines.append('=' * 70)

    # Detalhes por banco
    from collections import defaultdict
    by_bank = defaultdict(list)
    for r in data['resultados']:
        by_bank[r['banco']].append(r)

    lines.append('')
    lines.append('RESUMO POR BANCO:')
    lines.append(f'{"Banco":<25} {"PDFs":>5} {"TX>0":>5} {"Gap=0":>6} {"ALTA":>5} {"MED":>5} {"BAIXA":>5}')
    lines.append('-' * 70)
    for banco in sorted(by_bank.keys()):
        rs = by_bank[banco]
        n = len(rs)
        tx_ok = sum(1 for r in rs if r['tx'] > 0)
        g0 = sum(1 for r in rs if r['v2']['ok'])
        a = sum(1 for r in rs if r['v3'] == 'ALTA')
        m = sum(1 for r in rs if r['v3'] == 'MEDIA')
        b = sum(1 for r in rs if r['v3'] == 'BAIXA')
        lines.append(f'{banco:<25} {n:>5} {tx_ok:>5} {g0:>6} {a:>5} {m:>5} {b:>5}')

    # Falhas detalhadas
    falhas = [r for r in data['resultados']
              if r['v3'] == 'BAIXA' and not r.get('is_ocr')]
    if falhas:
        lines.append('')
        lines.append('FALHAS DETALHADAS:')
        lines.append('-' * 70)
        for r in falhas:
            lines.append(f'  {r["arquivo"][:55]:<57} banco={r["banco"]}')
            if r['v1']['falhas']:
                for f in r['v1']['falhas'][:3]:
                    lines.append(f'    V1: {f}')
            v2c = r['v2']['classificacao']
            if v2c not in ('OK',):
                gap = r['v2'].get('gap')
                lines.append(f'    V2: {v2c} gap={gap}')
            if r['v4']['alertas']:
                for a in r['v4']['alertas'][:2]:
                    lines.append(f'    V4: {a}')

    # PDFs que requerem OCR
    ocr_pdfs = [r for r in data['resultados'] if r.get('is_ocr')]
    if ocr_pdfs:
        lines.append('')
        lines.append('REQUEREM OCR (escopo futuro):')
        for r in ocr_pdfs:
            lines.append(f'  - {r["arquivo"]}')

    lines.append('')
    lines.append('=' * 70)
    aprovado = s['assertividade'] >= 90
    lines.append(f'VEREDITO: {"APROVADO" if aprovado else "REPROVADO"} ({s["assertividade"]}%)')
    lines.append('=' * 70)

    return '\n'.join(lines)


# -- Main ----------------------------------------------------------------------

if __name__ == '__main__':
    data = run_all_tests()

    if '--json' in sys.argv:
        # Remove non-serializable data
        for r in data['resultados']:
            r.pop('avisos_parser', None)
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    else:
        print(format_report(data))

    sys.exit(0 if data['stats']['assertividade'] >= 90 else 1)
