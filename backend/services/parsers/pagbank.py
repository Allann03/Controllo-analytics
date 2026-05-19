"""
pagbank.py – Parser PagBank (PagSeguro Internet S/A) — Extrato da Conta PJ.

Estrategia: usa extract_tables() do pdfplumber porque o extrato do PagBank
tem celulas que podem conter quebras de linha (\n) quando a descricao
e muito longa. Isso e mais robusto que extract_text() linha por linha.

Formato do extrato:
- Tabela onde cada celula = "DD/MM/YYYY descricao [-]R$ X,XX"
- Saidas: prefixo -R$, entradas: R$ sem sinal
- Linhas "Saldo do dia" sao saldos diarios (NAO sao transacoes)
- Datas ja vem com ano completo (DD/MM/YYYY)
- Algumas tx tem descricao multilinha (separada por \n na celula)

Correcao critica: injeta saldo intermediario fantasma no dia ANTERIOR
ao primeiro dia do extrato, com SI inferido recalculando para tras a
partir do primeiro saldo de fechamento. Isso corrige o bug onde o
orquestrador usa o primeiro saldo intermediario como SI (fallback),
que no PagBank e saldo de FECHAMENTO, nao abertura.
"""

import re
from decimal import Decimal
from datetime import datetime, timedelta
import pdfplumber

from .base import ParserBase

BANCO = 'PagBank'

# ---------- Regex ----------

# Sub-linha com data + valor sozinhos (linha do meio em celulas multilinha)
_RE_DATA_VALOR_SOLO = re.compile(
    r'^(\d{2}/\d{2}/\d{4})\s+(-?)R\$\s*([\d.]+,\d{2})\s*$'
)

# Linha completa: data + descricao + valor (caso simples, mais comum)
_RE_TX_INLINE = re.compile(
    r'^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?)R\$\s*([\d.]+,\d{2})\s*$'
)

# Periodo na capa
_RE_PERIODO = re.compile(
    r'Per[ií]odo:\s*(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})'
)

# Prefixos de celula a ignorar (cabecalhos, metadados)
_IGNORAR_PREFIX = (
    'data',
    '290 -',
    'extrato da conta',
    'emitido em',
    'periodo:',
    'período:',
    'cnpj:',
    'agência',
    'agencia',
    'conta ',
)


class ParserPagBank(ParserBase):
    """Parser para extratos PJ do PagBank (PagSeguro)."""

    def __init__(self, pdf_path: str, password: str | None = None):
        super().__init__(pdf_path, password)
        self._tx_cache: list[dict] | None = None
        self._saldos_cache: list[dict] | None = None
        self._periodo_inicio: str | None = None
        self._periodo_fim: str | None = None

    def extrair(self) -> list[dict]:
        """Extrai transacoes. Tambem popula o cache de saldos."""
        if self._tx_cache is not None:
            return list(self._tx_cache)
        self._processar_pdf()
        return list(self._tx_cache)

    def _extrair_saldos_intermediarios(self) -> list[dict]:
        """Saldos intermediarios INCLUINDO o saldo fantasma do dia anterior."""
        if self._saldos_cache is None:
            self._processar_pdf()
        return list(self._saldos_cache)

    def _processar_pdf(self) -> None:
        """Processa o PDF uma unica vez. Idempotente via cache."""
        transacoes: list[dict] = []
        saldos: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password) as pdf:
            # Periodo (metadata)
            texto_p1 = pdf.pages[0].extract_text() or ''
            m = _RE_PERIODO.search(texto_p1)
            if m:
                self._periodo_inicio, self._periodo_fim = m.groups()

            for page in pdf.pages:
                tabelas = page.extract_tables() or []
                for tab in tabelas:
                    for row in tab:
                        if not row:
                            continue
                        # A tabela PagBank pode ter 1 ou 3 colunas;
                        # juntamos tudo em uma string unica
                        partes = [c for c in row if c]
                        if not partes:
                            continue
                        celula = ' '.join(partes) if len(partes) > 1 else partes[0]
                        if not celula:
                            continue

                        parsed = self._parse_celula(celula)
                        if parsed is None:
                            continue

                        if parsed['tipo_parsed'] == 'saldo':
                            saldos.append({
                                'data': parsed['data'],
                                'saldo': parsed['valor'],
                            })
                        else:
                            tipo = 'saida' if parsed['sinal'] == '-' else 'entrada'
                            transacoes.append(self._transacao(
                                data=parsed['data'],
                                descricao=parsed['desc'],
                                valor=parsed['valor'],
                                tipo=tipo,
                                banco=BANCO,
                                raw=celula.replace('\n', ' | '),
                            ))

        # Pos-processamento das tx (validacao estrutural + data)
        transacoes = self._post_processar(transacoes)

        # CORRECAO CRITICA: injetar saldo fantasma do dia anterior
        if saldos:
            primeiro = saldos[0]
            ent_pd = sum(t['valor'] for t in transacoes
                         if t['data'] == primeiro['data'] and t['tipo'] == 'entrada')
            sai_pd = sum(t['valor'] for t in transacoes
                         if t['data'] == primeiro['data'] and t['tipo'] == 'saida')
            saldo_inicial_inferido = primeiro['saldo'] - (ent_pd - sai_pd)
            data_anterior_str = self._data_anterior(primeiro['data'])
            saldos = [{
                'data': data_anterior_str,
                'saldo': saldo_inicial_inferido,
            }] + saldos

        self._tx_cache = transacoes
        self._saldos_cache = saldos

    def _parse_celula(self, celula: str) -> dict | None:
        """
        Parseia uma celula da tabela. Retorna:
        - {'tipo_parsed': 'tx', 'data', 'desc', 'valor', 'sinal'}
        - {'tipo_parsed': 'saldo', 'data', 'valor'}
        - None se nao reconhecer ou for cabecalho
        """
        s = celula.strip()
        if not s:
            return None

        # Cabecalhos e metadados
        low = s.lower()
        if any(low.startswith(p) for p in _IGNORAR_PREFIX):
            return None

        # Caso multilinha (celula com \n — descricao longa quebrou)
        if '\n' in s:
            sub_linhas = [ln.strip() for ln in s.split('\n')]
            data = None
            sinal = ''
            valor = None
            idx_dv = -1

            for i, ln in enumerate(sub_linhas):
                m = _RE_DATA_VALOR_SOLO.match(ln)
                if m:
                    data, sinal, val_txt = m.groups()
                    valor = self._parse_valor_br(val_txt)
                    idx_dv = i
                    break

            if data is None or idx_dv < 0:
                return None

            # Concatena as outras sub-linhas como descricao
            partes = [ln for i, ln in enumerate(sub_linhas) if i != idx_dv and ln]
            desc = ' '.join(partes).strip()
            if not desc:
                return None

            if 'saldo do dia' in desc.lower():
                return {'tipo_parsed': 'saldo', 'data': data, 'valor': valor}

            return {'tipo_parsed': 'tx', 'data': data, 'desc': desc,
                    'valor': valor, 'sinal': sinal}

        # Caso linha simples (mais comum)
        m = _RE_TX_INLINE.match(s)
        if m:
            data, desc, sinal, val_txt = m.groups()
            valor = self._parse_valor_br(val_txt)
            desc = desc.strip()

            if 'saldo do dia' in desc.lower():
                return {'tipo_parsed': 'saldo', 'data': data, 'valor': valor}

            return {'tipo_parsed': 'tx', 'data': data, 'desc': desc,
                    'valor': valor, 'sinal': sinal}

        return None

    @staticmethod
    def _parse_valor_br(s: str) -> Decimal:
        """'1.234,56' -> Decimal('1234.56'). Sempre positivo."""
        return Decimal(s.replace('.', '').replace(',', '.'))

    @staticmethod
    def _data_anterior(data_str: str) -> str:
        """'01/06/2025' -> '31/05/2025'. Lida com viradas de mes/ano."""
        dt = datetime.strptime(data_str, '%d/%m/%Y')
        return (dt - timedelta(days=1)).strftime('%d/%m/%Y')
