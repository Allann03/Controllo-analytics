"""
sumup.py – Parser de extrato da SumUp (Extrato de Depósitos).

Formato da tabela "Resumo da Transação":
  DATA E HORA | CÓDIGO DA TRANSAÇÃO | DESCRIÇÃO | PARCELAS |
  VALOR | SALDO DEVEDOR INICIAL | TAXA EM R$ | VALOR DO DEPÓSITO

Todas as transações são entradas (recebimentos via maquininha SumUp).
"""

import re
import pdfplumber
from .base import ParserBase

BANCO = 'SumUp'

# Data no formato "DD/MM/YYYY" ou "DD/MM/YYYY, HH:MM"
_RE_DATA = re.compile(r'^(\d{2}/\d{2}/\d{4})')

_IGNORAR_DESC = [
    'data e hora', 'data hora', 'código', 'codigo', 'descrição', 'descricao',
    'parcelas', 'valor do depósito', 'valor do deposito', 'saldo devedor',
    'taxa em r$', 'taxa', 'resumo', 'transação', 'transacao',
    'valor', 'saldo', 'depósito', 'deposito',
]

# Linhas de sumário / totais (apenas um código numérico longo, sem descrição)
_RE_CODIGO_NUMERICO = re.compile(r'^\d{15,}$')


class ParserSumUp(ParserBase):
    """Parser para extratos SumUp (Extrato de Depósitos)."""

    def extrair(self) -> list[dict]:
        transacoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    tabelas = pagina.extract_tables()
                    for tabela in tabelas:
                        for linha in tabela:
                            t = self._processar_linha(linha)
                            if t:
                                transacoes.append(t)
                except Exception as e:
                    self.avisos.append(f'SumUp: erro na página {num}: {e}')

        return self._post_processar(transacoes)

    def _processar_linha(self, linha: list) -> dict | None:
        if not linha or len(linha) < 5:
            return None

        # Coluna 0: DATA E HORA — deve começar com DD/MM/YYYY
        data_raw = str(linha[0] or '').strip()
        m = _RE_DATA.match(data_raw)
        if not m:
            return None
        data = self._normalizar_data(m.group(1))

        # Coluna 1: CÓDIGO DA TRANSAÇÃO — pula linhas de sumário (só número)
        codigo = str(linha[1] or '').strip()
        if _RE_CODIGO_NUMERICO.match(codigo):
            return None

        # Coluna 2: DESCRIÇÃO
        desc_raw = str(linha[2] or '').strip() if len(linha) > 2 else ''
        if not desc_raw or any(x in desc_raw.lower() for x in _IGNORAR_DESC):
            desc_raw = 'Venda SumUp'

        # Valor: prefere VALOR DO DEPÓSITO (índice 7 = líquido após taxa),
        # fallback para VALOR (índice 4 = valor bruto da transação)
        valor_raw = ''
        if len(linha) > 7:
            v7 = str(linha[7] or '').strip()
            if v7 and re.search(r'\d', v7):
                valor_raw = v7
        if not valor_raw and len(linha) > 4:
            v4 = str(linha[4] or '').strip()
            if v4 and re.search(r'\d', v4):
                valor_raw = v4
        if not valor_raw:
            return None

        valor = self._normalizar_valor(valor_raw)
        if valor == 0.0:
            return None

        raw = '|'.join(str(c or '') for c in linha)

        return self._transacao(
            data=data,
            descricao=desc_raw,
            valor=valor,
            tipo='entrada',  # SumUp = recebimentos via maquininha
            banco=BANCO,
            raw=raw,
        )
