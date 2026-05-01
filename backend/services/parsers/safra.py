"""
safra.py – Parser do Banco Safra — Extrato de Conta Corrente PJ.

Formato do extrato:
- Tabela: Data | Lancamento | Complemento | N Documento | Valor (R$)
- Datas no formato DD/MM (ano vem do periodo na capa)
- Valores BR (1.234,56), saidas com sinal negativo
- Linhas "CONTA CORRENTE" sao saldos do dia (NAO sao transacoes)
- Descricao pode quebrar em linha de continuacao (sem data, sem valor)
"""

import re
from decimal import Decimal
import pdfplumber

from .base import ParserBase

BANCO = 'Safra'

# ---------- Linhas a ignorar (cabecalhos, rodapes, info da capa) ----------
_IGNORAR_PREFIX = (
    'banco safra', 'cnpj:', 'extrato de conta corrente', 'periodo de',
    'período de', 'saldo + limite', 'r$ ', 'lançamentos realizados',
    'lancamentos realizados', 'data lançamento', 'data lancamento',
    'central de suporte', 'sac e deficientes', '(11) 3175', '0300 015',
    '0800 772', '0800 770', 'atendimento', 'personalizado',
    'a 6ª feira', '19h, exceto', '18h, exceto', 'por semana',
    'saldo bloqueado', 'limite cheque', 'cobrança d0', 'cobranca d0',
    'nº documento', 'n° documento', 'valor (r$)', 'complemento',
    # S21: filtros de "razão social na capa" foram removidos — nomes de cliente
    # hardcoded (ex.: 'nina pet') é antipattern. Se aparecer regressão de
    # cabeçalho com nome de cliente sendo confundido com transação, resolver
    # via regex de header (não substring).
)

_IGNORAR_CONTAINS = ('página', 'pagina',)

# ---------- Regex ----------

# Linha de transacao: DD/MM + descricao + N documento (6+ digitos) + valor
_RE_TX = re.compile(
    r'^(\d{2}/\d{2})\s+'        # data DD/MM
    r'(.+?)\s+'                  # descricao (lazy)
    r'(\d{6,})\s+'               # numero documento (6+ digitos)
    r'(-?[\d.]+,\d{2})\s*$'     # valor BR com sinal opcional
)

# Linha CONTA CORRENTE (saldo do dia)
_RE_SALDO_DIA = re.compile(
    r'^(\d{2}/\d{2})\s+CONTA\s+CORRENTE\s+(-?[\d.]+,\d{2})\s*$'
)

# Periodo na capa
_RE_PERIODO = re.compile(
    r'Per[ií]odo\s+de\s+(\d{2})/(\d{2})/(\d{4})\s+a\s+(\d{2})/(\d{2})/(\d{4})'
)

# Detecta valor BR no final de linha (para identificar se é continuation ou não)
_RE_TEM_VALOR = re.compile(r'-?[\d.]+,\d{2}\s*$')

# Detecta se linha começa com data DD/MM
_RE_COMECA_DATA = re.compile(r'^\d{2}/\d{2}\s')

# Data hora da emissão (ex: "01/09/2025 12:23") — ignorar
_RE_DATA_EMISSAO = re.compile(r'^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}')


class ParserSafra(ParserBase):
    """Parser para extratos PJ do Banco Safra."""

    def __init__(self, pdf_path: str, password: str | None = None):
        super().__init__(pdf_path, password)
        self._saldos_intermediarios_cache: list[dict] = []
        self._periodo_inicio: str | None = None
        self._periodo_fim: str | None = None

    def extrair(self) -> list[dict]:
        transacoes: list[dict] = []
        self._saldos_intermediarios_cache = []

        with pdfplumber.open(self.pdf_path, password=self.password) as pdf:
            ano_inicio, ano_fim = self._extrair_periodo(pdf.pages[0])
            ultimo_mes: int | None = None

            for page in pdf.pages:
                texto = page.extract_text() or ''
                linhas = texto.splitlines()
                i = 0
                while i < len(linhas):
                    linha = linhas[i].strip()
                    low = linha.lower()

                    # Pular linhas vazias e ignoráveis
                    if not linha or self._is_ignoravel(linha, low):
                        i += 1
                        continue

                    # Data/hora de emissão do PDF (ex: "01/09/2025 12:23") — ignorar
                    if _RE_DATA_EMISSAO.match(linha):
                        i += 1
                        continue

                    # 1. Saldo do dia (CONTA CORRENTE)
                    m_saldo = _RE_SALDO_DIA.match(linha)
                    if m_saldo:
                        dm, valor_txt = m_saldo.groups()
                        ano, ultimo_mes = self._resolver_ano(
                            dm, ultimo_mes, ano_inicio, ano_fim
                        )
                        # Preservar sinal para saldos (pode ser negativo)
                        saldo_val = self._parse_saldo_com_sinal(valor_txt)
                        self._saldos_intermediarios_cache.append({
                            'data': f'{dm}/{ano}',
                            'saldo': saldo_val,
                        })
                        i += 1
                        continue

                    # 2. Transação com Nº Documento
                    m_tx = _RE_TX.match(linha)
                    if m_tx:
                        dm, desc, ndoc, valor_txt = m_tx.groups()

                        # Olhar continuation line
                        if i + 1 < len(linhas):
                            prox = linhas[i + 1].strip()
                            prox_low = prox.lower()
                            if (prox
                                    and not _RE_COMECA_DATA.match(prox)
                                    and not self._is_ignoravel(prox, prox_low)
                                    and not _RE_TEM_VALOR.search(prox)
                                    and not _RE_DATA_EMISSAO.match(prox)):
                                desc = f'{desc} {prox}'
                                i += 1  # consome continuation

                        # _normalizar_valor retorna abs() — detectar sinal pelo raw
                        valor = self._normalizar_valor(valor_txt)
                        is_saida = valor_txt.strip().startswith('-')
                        tipo = 'saida' if is_saida else 'entrada'

                        ano, ultimo_mes = self._resolver_ano(
                            dm, ultimo_mes, ano_inicio, ano_fim
                        )

                        transacoes.append(self._transacao(
                            data=f'{dm}/{ano}',
                            descricao=desc.strip(),
                            valor=valor,
                            tipo=tipo,
                            banco=BANCO,
                            raw=linha,
                        ))
                        i += 1
                        continue

                    i += 1

        # Verificação progressiva e avisos
        self._verificar_saldos(transacoes)

        return self._post_processar(transacoes)

    # ── Saldos intermediários ────────────────────────────────────────────

    def _extrair_saldos_intermediarios(self) -> list[dict]:
        """Retorna saldos do dia capturados durante extrair()."""
        if not self._saldos_intermediarios_cache:
            self.extrair()
        return list(self._saldos_intermediarios_cache)

    # ── Helpers internos ─────────────────────────────────────────────────

    def _parse_saldo_com_sinal(self, texto: str) -> Decimal:
        """Converte valor BR preservando sinal (para saldos que podem ser negativos)."""
        if not texto:
            return Decimal('0')
        texto = texto.strip()
        negativo = texto.startswith('-')
        valor = self._normalizar_valor(texto)  # retorna abs
        return -valor if negativo else valor

    def _extrair_periodo(self, page) -> tuple[int, int]:
        """Extrai (ano_inicio, ano_fim) da capa."""
        texto = page.extract_text() or ''
        m = _RE_PERIODO.search(texto)
        if m:
            self._periodo_inicio = f'{m.group(1)}/{m.group(2)}/{m.group(3)}'
            self._periodo_fim = f'{m.group(4)}/{m.group(5)}/{m.group(6)}'
            return int(m.group(3)), int(m.group(6))
        from datetime import datetime
        ano = datetime.now().year
        return ano, ano

    def _resolver_ano(
        self, dm: str, ultimo_mes: int | None,
        ano_inicio: int, ano_fim: int,
    ) -> tuple[int, int]:
        """Resolve ano para data DD/MM, detectando virada de ano."""
        mes = int(dm.split('/')[1])
        if ultimo_mes is not None and mes < ultimo_mes and ano_inicio != ano_fim:
            return ano_fim, mes
        return ano_inicio, mes

    def _is_ignoravel(self, linha: str, low: str) -> bool:
        """Verifica se a linha é cabeçalho/rodapé que deve ser ignorado."""
        if any(low.startswith(p) for p in _IGNORAR_PREFIX):
            return True
        if any(c in low for c in _IGNORAR_CONTAINS):
            return True
        return False

    # ── Verificação progressiva de saldo ─────────────────────────────────

    def _verificar_saldos(self, transacoes: list[dict]) -> None:
        """
        Verificação progressiva dia a dia usando saldos intermediários.
        Registra divergências em self.avisos mas nunca bloqueia a extração.
        """
        saldos = self._saldos_intermediarios_cache
        if not saldos or not transacoes:
            return

        from collections import defaultdict

        # Calcular movimento por dia
        mov_dia: dict[str, dict] = defaultdict(
            lambda: {'ent': Decimal('0'), 'sai': Decimal('0')}
        )
        for t in transacoes:
            if t['tipo'] == 'entrada':
                mov_dia[t['data']]['ent'] += t['valor']
            elif t['tipo'] == 'saida':
                mov_dia[t['data']]['sai'] += t['valor']

        # Inferir saldo inicial
        primeiro = saldos[0]
        ent_d1 = mov_dia[primeiro['data']]['ent']
        sai_d1 = mov_dia[primeiro['data']]['sai']
        saldo_inicial = primeiro['saldo'] - (ent_d1 - sai_d1)

        # Verificar dia a dia
        saldo_calc = saldo_inicial
        divergencias: list[str] = []

        for s in saldos:
            d = s['data']
            m = mov_dia[d]
            saldo_calc += m['ent'] - m['sai']
            diff = saldo_calc - s['saldo']
            if abs(diff) >= Decimal('0.01'):
                divergencias.append(
                    f"{d}: calculado R$ {saldo_calc:.2f}, "
                    f"esperado R$ {s['saldo']:.2f}, "
                    f"diff R$ {diff:.2f}"
                )

        # Registrar avisos
        saldo_final_extrato = saldos[-1]['saldo']
        diff_final = abs(saldo_calc - saldo_final_extrato)

        if divergencias:
            self.avisos.append(
                f"Saldo final com diferença de R$ {diff_final:.2f}. "
                f"Possível divergência em {len(divergencias)} dia(s): "
                + '; '.join(divergencias)
            )
        else:
            self.avisos.append(
                f"Verificação de saldo OK. "
                f"Saldo inicial inferido: R$ {saldo_inicial:.2f}, "
                f"saldo final: R$ {saldo_final_extrato:.2f}."
            )
