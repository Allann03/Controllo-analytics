"""
caixa.py – Parser de extrato da Caixa Econômica Federal.

Formato: texto por linha (extração de texto, NÃO tabela).

Cada entrada bancária ocupa uma "linha de doc" com o padrão:
  6-dígitos [descrição] [- ]R$ valor R$ saldo [C|D]

Casos especiais:
  - Descrição pode vir em linha separada ANTES da linha de data
  - Data pode aparecer junto com descrição: 'DD/MM/YYYY CRED PIX CHAVE'
  - Em algumas entradas, o sinal '-' aparece na linha de data (ex: '19/12/2025 -')
    e o valor real aparece na linha de timestamp: 'DD/MM HH:MM R$ valor'

Sinal de tipo:
  - '- R$' antes do valor na linha de doc → saída
  - Sem '-' → entrada
  - Linha de data termina com ' -' → próxima transação é saída (valor split)
  - D no final do saldo → débito (saída); C → crédito (entrada)
"""

import re
import pdfplumber
from .base import ParserBase


BANCO = 'Caixa'

# Linha de data: DD/MM/YYYY [texto opcional]
_RE_DATA = re.compile(r'^(\d{2}/\d{2}/\d{4})(.*)')

# Linha de doc com DOIS ou mais R$ (entrada completa)
# Ex: '041129 SAQUE BANCO 24H - R$ 400,00 R$ 21,93 D'
# Ex: '041247 R$ 3.000,00 R$ 2.978,07 C'
# Ex: '221037 - R$ 966,29 R$ 63,34 C'
_RE_DOC_FULL = re.compile(
    r'^(\d{6})\s*(.*?)\s*(-\s*R\$\s*[\d.,]+|R\$\s*[\d.,]+)\s+R\$\s*[\d.,]+\s*[CD]?\s*$'
)

# Linha de doc com UM R$ (valor split — valor real na linha de timestamp)
# Ex: '191053 CAIXA CARTOES ELO PJ INTERNACIONAL R$ 2.794,41 C'
_RE_DOC_SPLIT = re.compile(
    r'^(\d{6})\s+(.*?)\s+R\$\s*[\d.,]+\s*[CD]?\s*$'
)

# Linha de timestamp com valor: DD/MM HH:MM [texto] R$ valor
_RE_TIMESTAMP_VALOR = re.compile(
    r'^\d{2}/\d{2}\s+\d{2}:\d{2}.*?R\$\s*([\d.,]+)'
)

_IGNORAR = [
    'saldo do dia', 'saldo anterior', 'saldo dia',
    'saldo final', 'saldo inicial', 'saldo em',
    'data', 'histórico', 'historico', 'valor', 'documento', 'data efetiva',
    'sac caixa', 'ouvidoria', 'pessoas com defici',
    'cnpj:', 'agência:', 'agencia:',
    'extrato no período', 'extrato no periodo', 'extrato',
]


class ParserCaixa(ParserBase):
    """Parser para extratos da Caixa Econômica Federal (texto por linha)."""

    def _extrair_saldos_intermediarios(self) -> list[dict]:
        """Extrai 'DD/MM/YYYY SALDO DIA R$ X.XXX,XX C' do extrato Caixa."""
        saldos = []
        _re_saldo = re.compile(
            r'(\d{2}/\d{2}/\d{4})\s+SALDO\s+DIA\s+R\$\s*([\d.,]+)',
            re.IGNORECASE
        )
        try:
            with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
                for page in pdf.pages:
                    texto = page.extract_text() or ''
                    for linha in texto.split('\n'):
                        m = _re_saldo.search(linha)
                        if m:
                            data = m.group(1)
                            valor = self._normalizar_valor(m.group(2))
                            saldos.append({'data': data, 'saldo': valor})
        except Exception:
            pass
        return saldos

    def extrair(self) -> list[dict]:
        """Extrai transações do extrato Caixa via texto."""
        transacoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
            data_atual = ''
            desc_buffer: list[str] = []
            desc_data = ''
            negativo_split = False
            pending_split: tuple | None = None  # (desc, data)

            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    texto = pagina.extract_text() or ''
                    for linha in texto.splitlines():
                        linha = linha.strip()
                        if not linha:
                            continue

                        linha_lower = linha.lower()

                        # Filtra cabeçalhos, saldos e metadados
                        if any(x in linha_lower for x in _IGNORAR):
                            desc_buffer.clear()
                            desc_data = ''
                            pending_split = None
                            negativo_split = False
                            continue

                        # Linha de timestamp: DD/MM HH:MM [R$ valor]
                        if re.match(r'^\d{2}/\d{2}\s+\d{2}:\d{2}', linha):
                            m_ts = _RE_TIMESTAMP_VALOR.match(linha)
                            if m_ts and pending_split:
                                valor = self._normalizar_valor(m_ts.group(1))
                                if valor > 0:
                                    desc, data = pending_split
                                    tipo = 'saida' if negativo_split else 'entrada'
                                    transacoes.append(self._transacao(
                                        data=data, descricao=desc, valor=valor,
                                        tipo=tipo, banco=BANCO, raw=linha,
                                    ))
                                pending_split = None
                                negativo_split = False
                            # Timestamps sem valor pendente são ignorados
                            continue

                        # Linha de data: DD/MM/YYYY [texto]
                        m_data = _RE_DATA.match(linha)
                        if m_data:
                            data_atual = self._normalizar_data(m_data.group(1))
                            after_date = (m_data.group(2) or '').strip()
                            # Data termina com ' -' → próxima transação é saída (split)
                            if re.search(r'\s*-\s*$', after_date) or linha.rstrip() == m_data.group(1) + ' -':
                                negativo_split = True
                                desc_data = re.sub(r'\s*-\s*$', '', after_date).strip()
                            else:
                                negativo_split = False
                                desc_data = after_date
                            # Não limpa desc_buffer aqui (pode ser desc de transação)
                            continue

                        # CNPJ / CPF / número puro → ignora
                        if re.match(r'^\d{2}[./]\d{3}[./]', linha):
                            continue
                        if re.match(r'^\*{3}\.\d{3}', linha):
                            continue

                        # Linha de doc (começa com 6 dígitos)
                        if re.match(r'^\d{6}\s', linha):
                            n_rs = linha.count('R$')

                            if n_rs >= 2:
                                # Entrada completa: dois R$ na linha
                                m_full = _RE_DOC_FULL.match(linha)
                                if m_full and data_atual:
                                    desc_doc = (m_full.group(2) or '').strip()
                                    valor_raw = m_full.group(3)
                                    negativo = '-' in valor_raw
                                    valor = self._normalizar_valor(valor_raw)
                                    if valor > 0:
                                        desc = desc_doc or desc_data or ' '.join(desc_buffer)
                                        desc = desc.strip() or f'Lançamento {data_atual}'
                                        tipo = 'saida' if negativo else 'entrada'
                                        transacoes.append(self._transacao(
                                            data=data_atual, descricao=desc,
                                            valor=valor, tipo=tipo, banco=BANCO, raw=linha,
                                        ))
                                desc_buffer.clear()
                                desc_data = ''
                                negativo_split = False
                                pending_split = None

                            elif n_rs == 1:
                                # Entrada split: valor vem na linha de timestamp
                                m_split = _RE_DOC_SPLIT.match(linha)
                                if m_split and data_atual:
                                    desc_doc = (m_split.group(2) or '').strip()
                                    desc = desc_doc or desc_data or ' '.join(desc_buffer)
                                    desc = desc.strip() or f'Lançamento {data_atual}'
                                    pending_split = (desc, data_atual)
                                desc_buffer.clear()
                                desc_data = ''
                            continue

                        # Linha de texto puro → acumula como descrição
                        # Ignora linhas que são só números/pontuação
                        if not re.match(r'^[\d\s.,/:@*-]+$', linha):
                            desc_buffer.append(linha)

                except Exception as e:
                    self.avisos.append(f'Caixa: erro na página {num}: {e}')

        return self._post_processar(transacoes)
