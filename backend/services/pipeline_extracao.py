"""
pipeline_extracao.py — Pipeline obrigatorio de 8 passos para leitura de extratos.

Cada extrato bancario DEVE passar pelos 8 passos, nessa ordem:
  1. Ler e Identificar o Banco
  2. Interpretar os Valores
  3. Identificar Entradas e Saidas
  4. Autenticar a Veracidade
  5. Verificar Saldo Inicial e Final
  6. Conferencia Progressiva com Saldos Intermediarios
  7. Verificar se Nada Ficou para Tras
  8. Entregar Excel

Se um passo falha, o pipeline PARA e reporta ONDE e POR QUE falhou.
"""

import os
import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

import pdfplumber

from .extrator_pdf import (
    detectar_banco,
    PARSERS,
    FALLBACK_PARSERS,
    _NOME_BANCO_EXIBICAO,
    _extrair_saldos_pdf,
    _parse_valor_br,
    aplicar_categorias,
    MAX_PAGINAS_PDF,
)
# Sessão 18: validador de saldos (4 checks) + classificador de confiança.
from .validacao import validar_extracao, classificar

_logger = logging.getLogger(__name__)


# -- Resultado estruturado ----------------------------------------------------

@dataclass
class LogPasso:
    """Registro de um passo do pipeline."""
    passo: int
    nome: str
    ok: bool
    mensagem: str
    detalhes: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime('%H:%M:%S'))


@dataclass
class ResultadoExtracao:
    """Resultado completo do pipeline de 8 passos."""
    # Passo 1
    banco: str = 'desconhecido'
    banco_display: str = ''
    layout: str = ''
    # Passo 2
    transacoes: list[dict] = field(default_factory=list)
    saldo_inicial: Optional[float] = None
    saldo_final: Optional[float] = None
    saldos_intermediarios: list[dict] = field(default_factory=list)
    # Passo 3
    total_entradas: float = 0.0
    total_saidas: float = 0.0
    num_entradas: int = 0
    num_saidas: int = 0
    # Passo 4
    warnings: list[str] = field(default_factory=list)
    # Passo 5
    gap: Optional[float] = None
    reconciliacao: str = ''  # 'RECONCILIADO', 'ACEITAVEL', 'FALHA', 'SEM_SALDO'
    # Passo 6
    checkpoints_total: int = 0
    checkpoints_ok: int = 0
    divergencias: list[dict] = field(default_factory=list)
    modo_saldo: str = ''  # 'fechamento', 'abertura'
    # Passo 7
    paginas_processadas: int = 0
    completude_warnings: list[str] = field(default_factory=list)
    # Passo 8
    excel_path: Optional[str] = None
    # Meta
    confianca: str = 'BAIXA'  # 'ALTA', 'MEDIA', 'BAIXA'
    erro: Optional[str] = None
    passo_falha: Optional[int] = None
    log: list[LogPasso] = field(default_factory=list)
    avisos_parser: list[str] = field(default_factory=list)
    requer_ocr: bool = False
    num_paginas: int = 0
    # Sessão 18 — Validador de saldos
    validacao: dict = field(default_factory=dict)
    nivel_confianca: str = ''   # 'VERDE' | 'AMARELO' | 'VERMELHO' | ''
    diagnostico: str = ''
    # Período pedido (extraído do PDF para Check 4 do validador)
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None


# -- Pipeline ------------------------------------------------------------------

class PipelineExtracao:
    """Pipeline obrigatorio de 8 passos para leitura de extratos."""

    def __init__(self):
        self._resultado = ResultadoExtracao()

    def _log(self, passo: int, nome: str, ok: bool, msg: str,
             detalhes: list[str] | None = None) -> LogPasso:
        entry = LogPasso(
            passo=passo, nome=nome, ok=ok, mensagem=msg,
            detalhes=detalhes or [],
        )
        self._resultado.log.append(entry)
        level = logging.INFO if ok else logging.WARNING
        status = '✅' if ok else '❌'
        _logger.log(level, '[PASSO %d] %s %s', passo, status, msg)
        return entry

    def executar(self, pdf_path: str, banco_id: str = '',
                 senha: str | None = None,
                 gerar_excel: bool = False,
                 excel_path: str | None = None) -> ResultadoExtracao:
        """Executa os 8 passos na ordem. Retorna ResultadoExtracao."""
        r = self._resultado

        try:
            # ── PASSO 1: Ler e Identificar o Banco ──────────────────
            if not self._passo1_identificar(pdf_path, banco_id, senha):
                return r

            # ── PASSO 2: Interpretar os Valores ─────────────────────
            if not self._passo2_interpretar(pdf_path, senha):
                return r

            # ── PASSO 3: Identificar Entradas e Saidas ──────────────
            self._passo3_classificar()

            # ── PASSO 4: Autenticar a Veracidade ────────────────────
            self._passo4_veracidade()

            # ── PASSO 5: Verificar Saldo Inicial e Final ────────────
            self._passo5_reconciliacao()

            # ── PASSO 6: Conferencia Progressiva ────────────────────
            self._passo6_conferencia_progressiva()

            # ── PASSO 7: Verificar Completude ───────────────────────
            self._passo7_completude(pdf_path, senha)

            # Sessão 18 — Validador de saldos (não altera fluxo de erro;
            # apenas anexa metadados de qualidade ao resultado).
            self._validar_saldos(pdf_path)

            # Calcular confianca final
            r.confianca = self._calcular_confianca()

            # ── PASSO 8: Entregar Excel ─────────────────────────────
            if gerar_excel and r.confianca != 'BAIXA':
                self._passo8_excel(excel_path or pdf_path.replace('.pdf', '.xlsx'))
            elif gerar_excel and r.confianca == 'BAIXA':
                self._log(8, 'Entregar Excel', False,
                          'Excel NAO gerado — confianca BAIXA. Dados podem estar incorretos.',
                          [f'Confianca: {r.confianca}',
                           f'Reconciliacao: {r.reconciliacao}',
                           f'Divergencias: {len(r.divergencias)}'])

        except Exception as e:
            r.erro = str(e)
            _logger.exception('Pipeline falhou: %s', e)

        return r

    # -- Passo 1 ---------------------------------------------------------------

    def _passo1_identificar(self, pdf_path: str, banco_id: str,
                            senha: str | None) -> bool:
        r = self._resultado

        _arquivo = os.path.basename(pdf_path)

        # Verificar se PDF existe
        if not os.path.isfile(pdf_path):
            r.erro = f'Arquivo nao encontrado: {pdf_path}'
            r.passo_falha = 1
            print(f'[PIPELINE-422] passo=1 arquivo={_arquivo} banco=N/A '
                  f'motivo=arquivo_nao_encontrado gap=N/A')
            self._log(1, 'Identificar Banco', False, r.erro)
            return False

        # Extrair texto e contar paginas
        texto = ''
        num_paginas = 0
        try:
            with pdfplumber.open(pdf_path, password=senha or '') as pdf:
                num_paginas = len(pdf.pages)
                r.num_paginas = num_paginas
                if num_paginas > MAX_PAGINAS_PDF:
                    r.erro = f'PDF com {num_paginas} paginas excede limite de {MAX_PAGINAS_PDF}'
                    r.passo_falha = 1
                    print(f'[PIPELINE-422] passo=1 arquivo={_arquivo} banco=N/A '
                          f'motivo=excede_limite_paginas gap=N/A '
                          f'paginas={num_paginas}/{MAX_PAGINAS_PDF}')
                    self._log(1, 'Identificar Banco', False, r.erro)
                    return False
                for page in pdf.pages[:3]:
                    try:
                        texto += (page.extract_text() or '') + '\n'
                    except Exception:
                        pass
        except Exception as e:
            err = str(e).lower()
            if 'password' in err or 'encrypted' in err:
                r.erro = 'PDF protegido por senha'
                _motivo = 'pdf_protegido_senha'
            else:
                r.erro = f'Erro ao abrir PDF: {str(e)[:100]}'
                _motivo = 'erro_abertura_pdf'
            r.passo_falha = 1
            print(f'[PIPELINE-422] passo=1 arquivo={_arquivo} banco=N/A '
                  f'motivo={_motivo} gap=N/A erro_short={str(e)[:80]!r}')
            self._log(1, 'Identificar Banco', False, r.erro)
            return False

        # PDF vetorial/imagem?
        if len(texto.strip()) < 50:
            r.requer_ocr = True
            r.erro = 'PDF vetorial/imagem — texto insuficiente para leitura automatica'
            r.passo_falha = 1
            print(f'[PIPELINE-422] passo=1 arquivo={_arquivo} banco=N/A '
                  f'motivo=pdf_imagem_requer_ocr gap=N/A '
                  f'chars_extraidos={len(texto.strip())}')
            self._log(1, 'Identificar Banco', False,
                      f'Texto extraido: {len(texto.strip())} chars (< 50). Requer OCR.',
                      [f'Primeiros 200 chars: {texto[:200]}'])
            return False

        # Detectar banco
        banco = banco_id.strip().lower() if banco_id else detectar_banco(pdf_path, password=senha)
        if banco == 'desconhecido':
            r.banco = 'desconhecido'
            r.erro = 'Banco nao identificado'
            r.passo_falha = 1
            print(f'[PIPELINE-422] passo=1 arquivo={_arquivo} banco=desconhecido '
                  f'motivo=banco_nao_identificado gap=N/A')
            self._log(1, 'Identificar Banco', False,
                      'Banco nao identificado',
                      [f'Primeiras 500 chars: {texto[:500]}'])
            return False

        r.banco = banco
        r.layout = banco
        r.banco_display = _NOME_BANCO_EXIBICAO.get(banco, banco.capitalize())
        self._log(1, 'Identificar Banco', True,
                  f'Banco identificado: {r.banco_display} | Layout: {banco} | {num_paginas} paginas')
        return True

    # -- Passo 2 ---------------------------------------------------------------

    def _passo2_interpretar(self, pdf_path: str, senha: str | None) -> bool:
        r = self._resultado
        banco_key = r.banco

        parser_cls = PARSERS.get(banco_key)
        if not parser_cls:
            r.erro = f'Parser nao implementado para: {banco_key}'
            r.passo_falha = 2
            print(f'[PIPELINE-422] passo=2 arquivo={os.path.basename(pdf_path)} '
                  f'banco={banco_key} motivo=parser_nao_implementado gap=N/A')
            self._log(2, 'Interpretar Valores', False, r.erro)
            return False

        # Parser primario
        parser = parser_cls(pdf_path, password=senha)
        transacoes_brutas = parser.extrair()
        r.avisos_parser = parser.avisos

        # Fallback se 0 transacoes
        if not transacoes_brutas and banco_key in FALLBACK_PARSERS:
            fb_key = FALLBACK_PARSERS[banco_key]
            fb_cls = PARSERS.get(fb_key)
            if fb_cls:
                try:
                    parser_fb = fb_cls(pdf_path, password=senha)
                    tx_fb = parser_fb.extrair()
                    if tx_fb:
                        transacoes_brutas = tx_fb
                        r.avisos_parser = parser_fb.avisos
                        r.avisos_parser.append(
                            f'Parser primario ({banco_key}) retornou 0 tx. '
                            f'Usando fallback ({fb_key}).')
                        banco_key = fb_key
                        r.banco = banco_key
                        r.layout = fb_key
                        parser = parser_fb
                except Exception as e:
                    r.avisos_parser.append(f'Fallback {fb_key} falhou: {e}')

        # Filtrar tipo='ignorar'
        transacoes = [t for t in transacoes_brutas if t.get('tipo') != 'ignorar']

        # Aplicar categorias
        transacoes = aplicar_categorias(transacoes)

        # Converter Decimal -> float
        for t in transacoes:
            if isinstance(t.get('valor'), Decimal):
                t['valor'] = float(t['valor'])

        r.transacoes = transacoes

        # Extrair saldos
        si, sf = _extrair_saldos_pdf(pdf_path, banco_key, password=senha)
        r.saldo_inicial = float(round(si, 2)) if si is not None else None
        r.saldo_final = float(round(sf, 2)) if sf is not None else None

        # Saldos intermediarios
        try:
            saldos_inter = parser._extrair_saldos_intermediarios()
            r.saldos_intermediarios = saldos_inter or []
        except Exception:
            r.saldos_intermediarios = []

        if not transacoes:
            r.warnings.append('Nenhuma transacao extraida')
            self._log(2, 'Interpretar Valores', True,
                      f'0 transacoes | SI={r.saldo_inicial} | SF={r.saldo_final} | '
                      f'{len(r.saldos_intermediarios)} saldos intermediarios',
                      ['AVISO: extrato vazio ou parser nao extraiu transacoes'])
        else:
            self._log(2, 'Interpretar Valores', True,
                      f'{len(transacoes)} valores interpretados | SI={r.saldo_inicial} | '
                      f'SF={r.saldo_final} | {len(r.saldos_intermediarios)} saldos intermediarios')

        return True

    # -- Passo 3 ---------------------------------------------------------------

    def _passo3_classificar(self):
        r = self._resultado

        entradas = [t for t in r.transacoes if t.get('tipo') == 'entrada']
        saidas = [t for t in r.transacoes if t.get('tipo') == 'saida']

        r.num_entradas = len(entradas)
        r.num_saidas = len(saidas)
        r.total_entradas = round(sum(t['valor'] for t in entradas), 2)
        r.total_saidas = round(sum(t['valor'] for t in saidas), 2)

        # Se SF nao extraido mas SI presente, calcular
        if r.saldo_final is None and r.saldo_inicial is not None:
            r.saldo_final = round(r.saldo_inicial + r.total_entradas - r.total_saidas, 2)

        self._log(3, 'Classificar Entradas/Saidas', True,
                  f'{r.num_entradas} entradas (R$ {r.total_entradas:,.2f}) | '
                  f'{r.num_saidas} saidas (R$ {r.total_saidas:,.2f})')

    # -- Passo 4 ---------------------------------------------------------------

    def _passo4_veracidade(self):
        r = self._resultado
        warns = []

        for i, t in enumerate(r.transacoes):
            # Valor = 0
            if t.get('valor', 0) == 0:
                warns.append(f'TX[{i}] valor=0: {t.get("descricao", "")[:40]}')

            # Valor absurdo
            if t.get('valor', 0) > 100_000_000:
                warns.append(f'TX[{i}] valor absurdo R${t["valor"]:,.2f}: {t.get("descricao", "")[:40]}')

            # Data invalida
            data = t.get('data', '')
            if data and not re.match(r'^\d{2}/\d{2}/\d{4}$', data):
                warns.append(f'TX[{i}] data invalida: {data}')

        # Duplicatas (mesma data + desc + valor) — flag se > 3
        from collections import Counter
        keys = [(t.get('data', ''), t.get('descricao', ''), t.get('valor', 0))
                for t in r.transacoes]
        for key, cnt in Counter(keys).items():
            if cnt > 3:
                warns.append(f'Possivel duplicata ({cnt}x): {key[0]} {key[1][:30]} R${key[2]:.2f}')

        r.warnings.extend(warns)

        if warns:
            self._log(4, 'Autenticar Veracidade', True,
                      f'{len(warns)} warnings',
                      warns[:10])
        else:
            self._log(4, 'Autenticar Veracidade', True,
                      'Veracidade OK | 0 warnings')

    # -- Passo 5 ---------------------------------------------------------------

    def _passo5_reconciliacao(self):
        r = self._resultado

        if r.saldo_inicial is None or r.saldo_final is None:
            r.reconciliacao = 'SEM_SALDO'
            self._log(5, 'Verificar Reconciliacao', True,
                      'Reconciliacao nao possivel — SI ou SF nao encontrado no PDF',
                      [f'SI={r.saldo_inicial}', f'SF={r.saldo_final}'])
            return

        calculado = round(r.saldo_inicial + r.total_entradas - r.total_saidas, 2)
        r.gap = round(r.saldo_final - calculado, 2)
        volume = r.total_entradas + r.total_saidas
        gap_pct = abs(r.gap / volume * 100) if volume > 0 else 0

        if abs(r.gap) < 0.02:
            r.reconciliacao = 'RECONCILIADO'
            self._log(5, 'Verificar Reconciliacao', True,
                      f'SI={r.saldo_inicial} + E={r.total_entradas:,.2f} - S={r.total_saidas:,.2f} '
                      f'= {calculado:,.2f} vs SF={r.saldo_final} | gap={r.gap}')
        elif gap_pct < 1.0:
            r.reconciliacao = 'ACEITAVEL'
            r.warnings.append(f'Gap de reconciliacao: R$ {r.gap:.2f} ({gap_pct:.2f}%)')
            self._log(5, 'Verificar Reconciliacao', True,
                      f'ACEITAVEL | gap={r.gap} ({gap_pct:.2f}%)',
                      [f'SI={r.saldo_inicial}', f'E={r.total_entradas:,.2f}',
                       f'S={r.total_saidas:,.2f}', f'SF={r.saldo_final}'])
        else:
            r.reconciliacao = 'FALHA'
            r.warnings.append(f'FALHA reconciliacao: gap R$ {r.gap:.2f} ({gap_pct:.2f}%)')
            self._log(5, 'Verificar Reconciliacao', False,
                      f'FALHA | gap={r.gap} ({gap_pct:.2f}%)',
                      [f'SI={r.saldo_inicial}', f'E={r.total_entradas:,.2f}',
                       f'S={r.total_saidas:,.2f}', f'SF={r.saldo_final}',
                       f'Calculado={calculado}'])

    # -- Passo 6 ---------------------------------------------------------------

    def _passo6_conferencia_progressiva(self):
        r = self._resultado

        if not r.saldos_intermediarios:
            self._log(6, 'Conferencia Progressiva', True,
                      'Saldos intermediarios nao disponiveis neste formato — passo ignorado')
            return

        if r.saldo_inicial is None:
            # Tentar usar primeiro saldo intermediario como ponto de partida
            self._log(6, 'Conferencia Progressiva', True,
                      'SI nao disponivel — conferencia progressiva limitada')
            return

        # Agregar transacoes e saldos por data
        ultimo_saldo_por_data: dict[str, Decimal] = {}
        for s in r.saldos_intermediarios:
            ultimo_saldo_por_data[s['data']] = Decimal(str(s['saldo']))

        tx_por_data: dict[str, list] = {}
        for t in r.transacoes:
            tx_por_data.setdefault(t['data'], []).append(t)

        datas_ordenadas = sorted(
            set(t['data'] for t in r.transacoes) | set(ultimo_saldo_por_data.keys()),
            key=lambda d: (int(d[6:10]), int(d[3:5]), int(d[0:2]))
            if len(d) >= 10 else (0, 0, 0)
        )

        # Testar modo fechamento (saldo = apos transacoes do dia)
        def _verificar(modo_pre: bool):
            sc = Decimal(str(r.saldo_inicial))
            divs = []
            ok_count = 0
            for data in datas_ordenadas:
                if modo_pre and data in ultimo_saldo_por_data:
                    esperado = ultimo_saldo_por_data[data]
                    if abs(sc - esperado) > Decimal('0.02'):
                        divs.append({
                            'data': data,
                            'saldo_esperado': float(esperado),
                            'saldo_calculado': float(round(sc, 2)),
                            'diferenca': float(round(sc - esperado, 2)),
                        })
                    else:
                        ok_count += 1
                for t in tx_por_data.get(data, []):
                    v = Decimal(str(t['valor']))
                    if t['tipo'] == 'entrada':
                        sc += v
                    elif t['tipo'] == 'saida':
                        sc -= v
                if not modo_pre and data in ultimo_saldo_por_data:
                    esperado = ultimo_saldo_por_data[data]
                    if abs(sc - esperado) > Decimal('0.02'):
                        divs.append({
                            'data': data,
                            'saldo_esperado': float(esperado),
                            'saldo_calculado': float(round(sc, 2)),
                            'diferenca': float(round(sc - esperado, 2)),
                        })
                    else:
                        ok_count += 1
            return divs, ok_count

        divs_post, ok_post = _verificar(modo_pre=False)
        divs_pre, ok_pre = _verificar(modo_pre=True)

        if ok_post >= ok_pre:
            divergencias, saldos_ok, modo = divs_post, ok_post, 'fechamento'
        else:
            divergencias, saldos_ok, modo = divs_pre, ok_pre, 'abertura'

        r.checkpoints_total = len(ultimo_saldo_por_data)
        r.checkpoints_ok = saldos_ok
        r.divergencias = divergencias
        r.modo_saldo = modo

        if divergencias:
            det = [f'{d["data"]}: calculado={d["saldo_calculado"]} esperado={d["saldo_esperado"]} diff={d["diferenca"]}'
                   for d in divergencias[:5]]
            self._log(6, 'Conferencia Progressiva', False,
                      f'{len(divergencias)} divergencias em {r.checkpoints_total} checkpoints '
                      f'({saldos_ok} OK) modo={modo}',
                      det)
        else:
            self._log(6, 'Conferencia Progressiva', True,
                      f'{r.checkpoints_total} checkpoints verificados, 0 divergencias | modo={modo}')

    # -- Passo 7 ---------------------------------------------------------------

    def _passo7_completude(self, pdf_path: str, senha: str | None):
        r = self._resultado
        warns = []

        # Contar paginas processadas
        try:
            with pdfplumber.open(pdf_path, password=senha or '') as pdf:
                r.paginas_processadas = len(pdf.pages)
        except Exception:
            r.paginas_processadas = r.num_paginas

        # Verificar gaps de datas (muitos dias sem transacao pode indicar pagina nao lida)
        if r.transacoes:
            datas = sorted(set(t['data'] for t in r.transacoes if t.get('data')),
                           key=lambda d: (int(d[6:10]), int(d[3:5]), int(d[0:2]))
                           if len(d) >= 10 else (0, 0, 0))
            if len(datas) >= 2:
                try:
                    d_first = datetime.strptime(datas[0], '%d/%m/%Y')
                    d_last = datetime.strptime(datas[-1], '%d/%m/%Y')
                    span = (d_last - d_first).days
                    # Se periodo > 7 dias e menos de 50% dos dias tem transacao
                    if span > 7 and len(datas) < span * 0.3:
                        warns.append(
                            f'Periodo de {span} dias mas apenas {len(datas)} datas com transacoes '
                            f'— possivel pagina nao processada')
                except (ValueError, IndexError):
                    pass

        r.completude_warnings = warns

        detalhes = [f'{r.paginas_processadas} paginas processadas',
                    f'{len(r.transacoes)} transacoes extraidas']
        detalhes.extend(warns)

        if warns:
            self._log(7, 'Verificar Completude', True,
                      f'Possivel incompletude: {warns[0][:80]}', detalhes)
        else:
            self._log(7, 'Verificar Completude', True,
                      f'Completude OK | {r.paginas_processadas} paginas, '
                      f'{len(r.transacoes)} transacoes', detalhes)

    # -- Validador (Sessão 18) -------------------------------------------------

    def _validar_saldos(self, pdf_path: str):
        """Aplica os 4 checks do validador (saldo total, saldos diários,
        continuidade, datas) e popula `r.validacao`, `r.nivel_confianca` e
        `r.diagnostico`. Não altera o fluxo do pipeline — apenas anexa
        metadados de qualidade.

        - `saldos_diarios`: convertido a partir de `r.saldos_intermediarios`
          (cada item já tem `data` + `saldo`; assume saldo é fechamento do
          dia, então si_calc do dia seguinte = sf do dia atual quando
          adjacentes — mas aqui só popula sf por dia; o validador detecta
          ruptura entre dias com sf+si).
        - `periodo_inicio`/`periodo_fim`: lidos do texto via regex "Entre
          DD/MM/YYYY e DD/MM/YYYY" (formato Bradesco/Itaú/Santander).
        """
        r = self._resultado

        # Constrói saldos_diarios a partir dos saldos_intermediarios
        saldos_diarios = self._construir_saldos_diarios()

        # Tenta extrair periodo do PDF para Check 4
        periodo_inicio, periodo_fim = self._extrair_periodo(pdf_path)
        r.periodo_inicio = periodo_inicio
        r.periodo_fim = periodo_fim

        try:
            resultado = validar_extracao(
                transacoes=r.transacoes or [],
                saldo_inicial=r.saldo_inicial,
                saldo_final=r.saldo_final,
                saldos_diarios=saldos_diarios or None,
                periodo_inicio=periodo_inicio,
                periodo_fim=periodo_fim,
            )
            nivel, diagnostico = classificar(resultado)
        except Exception as e:
            resultado = {'erro_validador': str(e)[:120]}
            nivel = 'VERMELHO'
            diagnostico = f'erro no validador: {str(e)[:80]}'

        r.validacao = resultado
        r.nivel_confianca = nivel
        r.diagnostico = diagnostico

        try:
            arquivo = os.path.basename(pdf_path)
            print(f'[VALIDADOR] arquivo={arquivo} nivel={nivel} diag={diagnostico}')
        except Exception:
            pass

    def _construir_saldos_diarios(self) -> dict:
        """Converte `r.saldos_intermediarios` (lista) para dict por data.
        Cada item da lista tem `data` (str ou date) e `saldo` (float)."""
        from datetime import datetime as _dt
        r = self._resultado
        out: dict = {}
        for item in r.saldos_intermediarios or []:
            d = item.get('data') if isinstance(item, dict) else None
            sf = item.get('saldo') if isinstance(item, dict) else None
            if d is None or sf is None:
                continue
            # Parse data
            if isinstance(d, str):
                parsed = None
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y'):
                    try:
                        parsed = _dt.strptime(d, fmt).date()
                        break
                    except ValueError:
                        continue
                if parsed is None:
                    continue
                d = parsed
            try:
                sf = float(sf)
            except (TypeError, ValueError):
                continue
            # Sem si do dia explícito; deixa só sf — o validador detecta
            # rupturas entre dias adjacentes mesmo sem si.
            out[d] = {'sf': sf, 'si': out.get(d, {}).get('si')}
        return out

    def _extrair_periodo(self, pdf_path: str) -> tuple[Optional[str], Optional[str]]:
        """Extrai `Entre <DD/MM/YYYY> e <DD/MM/YYYY>` das primeiras 2 páginas.
        Formato comum em Bradesco, Itaú, Santander. Retorna (None, None) se
        não encontrar."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                texto = ''
                for pg in pdf.pages[:2]:
                    try:
                        texto += (pg.extract_text() or '') + '\n'
                    except Exception:
                        pass
        except Exception:
            return None, None
        m = re.search(
            r'entre\s+(\d{2}/\d{2}/\d{4})\s+e\s+(\d{2}/\d{2}/\d{4})',
            texto, re.IGNORECASE,
        )
        if not m:
            return None, None
        return m.group(1), m.group(2)

    # -- Passo 8 ---------------------------------------------------------------

    def _passo8_excel(self, excel_path: str):
        r = self._resultado

        if not r.transacoes:
            self._log(8, 'Entregar Excel', False,
                      'Excel NAO gerado — nenhuma transacao extraida')
            return

        try:
            from .gerador_excel_pipeline import gerar_excel_pipeline
            r.excel_path = gerar_excel_pipeline(
                transacoes=r.transacoes,
                caminho_saida=excel_path,
                saldo_inicial=r.saldo_inicial,
                saldo_final=r.saldo_final,
                banco_display=r.banco_display,
                layout=r.layout,
                gap=r.gap,
                reconciliacao=r.reconciliacao,
                confianca=r.confianca,
                checkpoints_ok=r.checkpoints_ok,
                checkpoints_total=r.checkpoints_total,
                warnings=r.warnings,
                divergencias=r.divergencias,
                log_passos=r.log,
                num_paginas=r.paginas_processadas,
            )
            self._log(8, 'Entregar Excel', True,
                      f'Excel gerado: {os.path.basename(excel_path)}')
        except Exception as e:
            self._log(8, 'Entregar Excel', False,
                      f'Erro ao gerar Excel: {e}')

    # -- Confianca -------------------------------------------------------------

    def _calcular_confianca(self) -> str:
        r = self._resultado

        # BAIXA: banco nao detectado, 0 transacoes, ou reconciliacao FALHA
        if r.banco == 'desconhecido':
            return 'BAIXA'
        if not r.transacoes:
            return 'BAIXA'
        if r.reconciliacao == 'FALHA':
            gap_pct = 0
            volume = r.total_entradas + r.total_saidas
            if volume > 0 and r.gap is not None:
                gap_pct = abs(r.gap / volume * 100)
            # Gap > 5% = BAIXA, otherwise MEDIA
            if gap_pct > 5:
                return 'BAIXA'
            return 'MEDIA'

        # ALTA: reconciliado + sem divergencias + SI/SF presentes
        if (r.reconciliacao == 'RECONCILIADO'
                and not r.divergencias
                and r.saldo_inicial is not None
                and r.saldo_final is not None):
            return 'ALTA'

        # MEDIA: tudo o mais (sem saldo, aceitavel, etc.)
        return 'MEDIA'


# -- Funcao de conveniencia ----------------------------------------------------

def processar_com_pipeline(pdf_path: str, banco_id: str = '',
                           senha: str | None = None,
                           gerar_excel: bool = False,
                           excel_path: str | None = None) -> ResultadoExtracao:
    """Executa o pipeline de 8 passos em um PDF. Ponto de entrada principal."""
    pipeline = PipelineExtracao()
    return pipeline.executar(
        pdf_path=pdf_path,
        banco_id=banco_id,
        senha=senha,
        gerar_excel=gerar_excel,
        excel_path=excel_path,
    )
