"""
bradesco.py – Parser de extrato do Bradesco.

Formato: texto misto. Quatro layouts de linha suportados:

  A) DD/MM/YYYY [doc] valores
     Ex: '03/11/2025 7881747 6.953,89 103.689,62'

  B) doc valores  (mesma data do dia anterior; doc 3-10 dígitos)
     Ex: '1046421 2.392,00 106.081,62'

  C) Descrição doc valor saldo  (inline, sem data separada)
     Ex: 'RENTAB.INVEST FACILCRED* 9167372 4,62 103.567,50'
     Ex: 'CARTAO CREDITO ANUIDADE 4740321 -22,00 53.497,84'
     Ex: 'DES: CACHE COMERCIAL CRIAT 17/11 1840561 -973,15 49.320,69'

  D) DD/MM/YYYY Descrição doc valor saldo  (data + tudo na mesma linha)
     Ex: '11/11/2025 RENTAB.INVEST FACILCRED* 1111080 2,39 101.351,57'
     Ex: '02/12/2025 REM: RENATA VELASCO WICHMA 02/12 737365 2.392,00 95.019,66'

Regras de tipo:
  - Valor positivo (coluna Crédito) = entrada (autoritário)
  - Valor negativo (coluna Débito, com '-') = saída (autoritário)
"""

import re
import pdfplumber
from .base import ParserBase


BANCO = 'Bradesco'

_RE_ANO = re.compile(r'\b(20\d{2})\b')

# Formato A: DD/MM/YYYY [doc] valores
_RE_LINHA_DATA = re.compile(
    r'^(\d{2}/\d{2}/\d{4})\s+(?:\d+\s+)?([-\d.,]+(?:\s+[-\d.,]+){0,2})\s*$'
)

# Formato B: doc(3-10 dígitos) valores
_RE_LINHA_DOC = re.compile(
    r'^(\d{3,10})\s+([-\d.,]+(?:\s+[-\d.,]+){1,2})\s*$'
)

# Formato C: descrição + doc(3-10) + valor + saldo (tudo inline, sem data)
_RE_LINHA_INLINE = re.compile(
    r'^([A-ZÀ-Ÿa-zà-ÿ*:].+?)\s+(\d{3,10})\s+([-\d.,]+)\s+[\d.,]+\s*$'
)

# Formato D: DD/MM/YYYY + descrição + doc(3-10) + valor + saldo
_RE_LINHA_DATA_INLINE = re.compile(
    r'^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\d{3,10})\s+([-\d.,]+)\s+[\d.,]+\s*$'
)

_IGNORAR = [
    # Saldos nunca são transações
    'saldo anterior', 'saldo do dia', 'saldo final', 'saldo em',
    'saldo (r$)', 'saldo inicial', 'saldo invest',
    # Cabeçalhos de tabela
    'lançamento', 'lancamento', 'dcto', 'crédito', 'debito',
    'débito', 'banco bradesco', 'ag/conta',
    'extrato', 'período', 'periodo', 'cliente',
    # Campos de identificação
    'cpf', 'cnpj',
    # Aplicações automáticas
    'aplic automatica', 'aplicação automática',
    'res aplic', 'rend aplic',
    # Totalizadores
    'total',
    'os dados acima',
]

# Marcadores que indicam fim da seção principal do período.
# Tudo depois disso (Últimos Lançamentos, Saldos Invest) deve ser ignorado.
_STOP_SECTION = [
    'últimos lançamentos', 'ultimos lancamentos',
    'saldos invest',
]

_ENTRADAS = [
    'ted', 'pix rem', 'pix recebido', 'credito', 'crédito', 'estorno',
    'devolução', 'devolucao', 'deposito', 'depósito', 'rentab.invest',
    'rem:', 'recebimento', 'transferencia recebida', 'transferência recebida',
    'resgate',
]

_SAIDAS = [
    'des:', 'debito', 'débito', 'pagto eletron', 'tarifa', 'taxa',
    'simples nacional', 'correios', 'conta de telefone', 'pix des',
    'pagamento', 'compra', 'saque', 'cheque', 'darf', 'fgts',
]


class ParserBradesco(ParserBase):
    """Parser para extratos do Bradesco (texto com rastreamento de data)."""

    def extrair(self) -> list[dict]:
        """Extrai transações do extrato Bradesco via texto."""
        transacoes: list[dict] = []
        _stop_parsing = False

        with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
            ano_ref = None
            data_atual = ''
            desc_buffer: list[str] = []

            for num, pagina in enumerate(pdf.pages, start=1):
                if _stop_parsing:
                    break
                try:
                    texto = pagina.extract_text() or ''
                    if not texto.strip():
                        continue

                    if ano_ref is None:
                        m = _RE_ANO.search(texto)
                        if m:
                            ano_ref = int(m.group(1))

                    for linha in texto.splitlines():
                        linha = linha.strip()
                        if not linha:
                            continue

                        linha_lower = linha.lower()

                        # Seções pós-período: para completamente
                        if any(x in linha_lower for x in _STOP_SECTION):
                            _stop_parsing = True
                            break

                        # Cabeçalhos, saldos e metadados — limpa buffer e pula
                        if any(x in linha_lower for x in _IGNORAR):
                            desc_buffer.clear()
                            continue

                        # Formato A: DD/MM/YYYY [doc] valores
                        m_data = _RE_LINHA_DATA.match(linha)
                        if m_data:
                            data_raw = m_data.group(1)
                            valores_str = m_data.group(2)
                            data_atual = self._normalizar_data(
                                data_raw, ano_referencia=ano_ref
                            )
                            desc = ' '.join(desc_buffer).strip()
                            desc_buffer.clear()
                            t = self._montar_transacao(
                                data_atual, desc, valores_str, linha
                            )
                            if t:
                                transacoes.append(t)
                            continue

                        # Formato D: DD/MM/YYYY desc doc valor saldo (tudo inline)
                        m_data_inline = _RE_LINHA_DATA_INLINE.match(linha)
                        if m_data_inline:
                            data_raw = m_data_inline.group(1)
                            desc_inline = m_data_inline.group(2).strip()
                            valor_str = m_data_inline.group(4)
                            data_atual = self._normalizar_data(
                                data_raw, ano_referencia=ano_ref
                            )
                            desc_buffer.clear()
                            t = self._montar_transacao_simples(
                                data_atual, desc_inline, valor_str, linha
                            )
                            if t:
                                transacoes.append(t)
                            continue

                        # Formato B: doc(3-10 dígitos) valores (usa data_atual)
                        m_doc = _RE_LINHA_DOC.match(linha)
                        if m_doc and data_atual:
                            valores_str = m_doc.group(2)
                            desc = ' '.join(desc_buffer).strip()
                            desc_buffer.clear()
                            t = self._montar_transacao(
                                data_atual, desc, valores_str, linha
                            )
                            if t:
                                transacoes.append(t)
                            continue

                        # Formato C: desc doc valor saldo (inline, usa data_atual)
                        m_inline = _RE_LINHA_INLINE.match(linha)
                        if m_inline and data_atual:
                            desc_inline = m_inline.group(1).strip()
                            valor_str = m_inline.group(3)
                            desc_buffer.clear()
                            t = self._montar_transacao_simples(
                                data_atual, desc_inline, valor_str, linha
                            )
                            if t:
                                transacoes.append(t)
                            continue

                        # Linha de descrição — acumula
                        # Ignora linhas só com números ou datas
                        if not re.match(r'^[\d\s.,/-]+$', linha):
                            desc_buffer.append(linha)

                except Exception as e:
                    self.avisos.append(f'Bradesco: erro na página {num}: {e}')

        return self._post_processar(transacoes)

    def _montar_transacao(
        self,
        data: str,
        desc: str,
        valores_str: str,
        raw: str,
    ) -> dict | None:
        """Monta transação a partir de data, descrição e string de valores."""
        nums = re.findall(r'-?\d{1,3}(?:\.\d{3})*,\d{2}', valores_str)
        if not nums:
            return None

        desc_lower = desc.lower()

        if any(x in desc_lower for x in _IGNORAR):
            return None

        # Com 3+ números: [crédito/débito, ..., saldo] — ignora o último (saldo)
        # Com 2 números: [valor, saldo]
        if len(nums) >= 2:
            candidatos = nums[:-1]  # exclui saldo (último número = saldo do dia)
        else:
            return None  # só saldo, sem transação

        # ── Verificação 1: prioriza negativos (débito explícito) ──────
        negativos = [n for n in candidatos if n.startswith('-')]
        positivos = [n for n in candidatos if not n.startswith('-')]

        if negativos:
            valor_raw = negativos[0]
            tipo_por_sinal = 'saida'
        elif positivos:
            valor_raw = positivos[0]
            # Bradesco: coluna Crédito (R$) positiva = entrada (autoritário)
            tipo_por_sinal = 'entrada'
        else:
            return None

        valor = self._normalizar_valor(valor_raw)
        if valor == 0.0:
            return None

        # ── Verificação 2: tipo cruzado (sinal + palavras-chave) ──────
        tipo = self._verificar_tipo_cruzado(
            tipo_por_sinal=tipo_por_sinal,
            descricao=desc or 'lançamento',
            palavras_entrada=_ENTRADAS,
            palavras_saida=_SAIDAS,
        )

        return self._transacao(
            data=data,
            descricao=desc or f'Lançamento {data}',
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=raw,
        )

    def _montar_transacao_simples(
        self,
        data: str,
        desc: str,
        valor_str: str,
        raw: str,
    ) -> dict | None:
        """Monta transação a partir de um único valor já identificado na linha."""
        if not desc or not data:
            return None
        desc_lower = desc.lower()
        if any(x in desc_lower for x in _IGNORAR):
            return None

        valor = self._normalizar_valor(valor_str)
        if valor == 0.0:
            return None

        negativo = valor_str.strip().startswith('-')
        tipo_por_sinal = 'saida' if negativo else 'entrada'

        tipo = self._verificar_tipo_cruzado(
            tipo_por_sinal=tipo_por_sinal,
            descricao=desc,
            palavras_entrada=_ENTRADAS,
            palavras_saida=_SAIDAS,
        )

        return self._transacao(
            data=data,
            descricao=desc,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=raw,
        )
