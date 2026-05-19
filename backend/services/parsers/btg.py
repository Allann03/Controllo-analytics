"""
btg.py -- Parser para extratos BTG Pactual (Conta corrente PJ).

Layout:
  - Cabecalho: "Conta corrente - PJ"
  - Saldo de abertura e fechamento na secao 01
  - Secao 02. Lancamentos:
    Data lancamento | Descricao do lancamento | Entradas / Saidas (R$) | Saldo (R$)
  - Valores negativos = saida, positivos = entrada
  - Descricoes podem quebrar em multiplas linhas
  - Linhas de detalhe bancario (Banco XXX | Ag XX | Conta XXX) sao continuacao
  - Linhas de chave Pix (QRCode, hash, 01001000...) sao continuacao
  - Aplicacao/Resgate Conta Remunerada = movimentacao interna (excluir)
  - Credito/Debito na Conta Corrente = movimentacao interna (excluir)
  - Ordem cronologica invertida (mais recente primeiro)

BLOCO 8.
"""

import re
from decimal import Decimal, InvalidOperation
from .base import ParserBase

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# Data no inicio da linha: DD/MM/YYYY
_RE_DATA = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.*)')

# Valor monetario BR com sinal
_RE_VALOR = re.compile(r'-?\d{1,3}(?:\.\d{3})*,\d{2}')

# Linha de detalhe bancario (nao e transacao)
_RE_DETALHE_BANCO = re.compile(r'^\s*Banco\s+\d+\s*\|', re.IGNORECASE)

# Chave Pix / QRCode / hash (nao e transacao)
_RE_CHAVE_PIX = re.compile(r'^[A-Za-z0-9]{20,}$|^QRCode|^01001|^CIELO|^00000')

# Movimentacoes internas (excluir)
_SKIP_LOWER = [
    'aplicação conta remunerada',
    'aplicacao conta remunerada',
    'resgate conta remunerada',
    'crédito na conta corrente',
    'credito na conta corrente',
    'débito na conta corrente',
    'debito na conta corrente',
    'saldo de abertura',
    'saldo de fechamento',
    'valor de rendimento remunera',
]

# Stop sections
_STOP_LOWER = [
    'fale com nossa central',
    'ligue para:',
    '© 2026 btg',
    '© 2025 btg',
]


def _normalizar_valor(texto: str) -> Decimal:
    negativo = texto.strip().startswith('-')
    limpo = texto.replace('-', '').replace('.', '').replace(',', '.').strip()
    try:
        v = Decimal(limpo)
        return -v if negativo else v
    except (InvalidOperation, ValueError):
        return Decimal('0')


class ParserBTG(ParserBase):
    """Parser para extratos BTG Pactual (Conta corrente PJ)."""

    BANCO = 'btg'

    def extrair(self) -> list[dict]:
        if pdfplumber is None:
            self.avisos.append('pdfplumber nao instalado.')
            return []

        linhas_raw: list[str] = []
        try:
            with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text() or ''
                    linhas_raw.extend(texto.splitlines())
        except Exception as e:
            self.avisos.append(f'Erro ao ler PDF: {e}')
            return []

        transacoes: list[dict] = []
        em_lancamentos = False

        i = 0
        while i < len(linhas_raw):
            linha = linhas_raw[i].strip()
            i += 1

            if not linha:
                continue

            line_lower = linha.lower()

            # Detectar inicio da secao de lancamentos
            if '02. lançamentos' in line_lower or '02. lancamentos' in line_lower:
                em_lancamentos = True
                continue

            # Skip header de coluna
            if 'data lançamento' in line_lower or 'data lancamento' in line_lower:
                continue

            if not em_lancamentos:
                continue

            # Stop sections
            if any(s in line_lower for s in _STOP_LOWER):
                continue

            # Skip linhas de detalhe bancario
            if _RE_DETALHE_BANCO.match(linha):
                continue

            # Skip chaves Pix
            if _RE_CHAVE_PIX.match(linha):
                continue

            # Tentar extrair transacao com data
            m = _RE_DATA.match(linha)
            if m:
                data = m.group(1)
                resto = m.group(2).strip()
            else:
                # Linha de continuacao de descricao — pode ter data na proxima linha
                # Ex: "Pix enviado para Fulano -"
                # Seguido por: "DD/MM/YYYY -1.234,56 saldo"
                # Acumular como buffer para a proxima linha com data
                # Verificar se a proxima linha tem data e pode ser a continuacao
                if i < len(linhas_raw):
                    proxima = linhas_raw[i].strip()
                    m_prox = _RE_DATA.match(proxima)
                    if m_prox:
                        # Descricao esta nesta linha, data+valor na proxima
                        data = m_prox.group(1)
                        resto_prox = m_prox.group(2).strip()
                        # Juntar descricao
                        desc_combinada = linha.rstrip(' -')
                        valores = _RE_VALOR.findall(resto_prox)
                        if valores:
                            valor_str = valores[0]
                            valor = _normalizar_valor(valor_str)
                            if valor == 0:
                                continue
                            desc_lower = desc_combinada.lower()
                            if any(s in desc_lower for s in _SKIP_LOWER):
                                i += 1
                                continue
                            tipo = 'entrada' if valor > 0 else 'saida'
                            t = self._transacao(
                                data=data,
                                descricao=desc_combinada.strip(),
                                valor=abs(valor),
                                tipo=tipo,
                                banco=self.BANCO,
                                raw=f'{linha} | {proxima}',
                            )
                            transacoes.append(t)
                            i += 1  # Consumir a proxima linha
                continue

            # Extrair valores do resto da linha
            valores = _RE_VALOR.findall(resto)
            if not valores:
                continue

            # Primeiro valor = transacao, segundo = saldo
            valor_str = valores[0]
            valor = _normalizar_valor(valor_str)
            if valor == 0:
                continue

            # Descricao = texto antes do primeiro valor
            pos_valor = resto.find(valor_str)
            descricao = resto[:pos_valor].strip() if pos_valor > 0 else resto

            if not descricao:
                continue

            # Skip movimentacoes internas
            desc_lower = descricao.lower()
            if any(s in desc_lower for s in _SKIP_LOWER):
                continue

            tipo = 'entrada' if valor > 0 else 'saida'

            t = self._transacao(
                data=data,
                descricao=descricao,
                valor=abs(valor),
                tipo=tipo,
                banco=self.BANCO,
                raw=linha,
            )
            transacoes.append(t)

        return self._post_processar(transacoes)
