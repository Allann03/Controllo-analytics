"""
itau_n2.py – Parser para o extrato ANTARTI.CO Itaú (formato N2).

Colunas: Data | Lançamentos | Razão Social | CNPJ/CPF | Valor (R$) | Saldo (R$)

Exemplos:
  26/06/2025 PIX RECEBIDO ANDRÉ FELIPE DE ALMEIDA SILVA 651.754.927-72 20.456,40
  26/06/2025 SALDO TOTAL DISPONÍVEL DIA 20.456,40
  02/07/2025 TAR PLANO ADAPT 2 06/25 -279,00
  29/07/2025 PIX RECEBIDO EDI WILLIAN GUERREIRO 23.651.970/0001-52 100.000,00
  21/08/2025 BUSINESS 0503-3468 -107,35
  25/08/2025 APLICACAO CDB DI -100.000,00
"""

import re
from decimal import Decimal, InvalidOperation
from ..base import ParserBase

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# Data no início da linha: DD/MM/YYYY
_RE_DATA_INICIO = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.*)', re.DOTALL)

# Valor monetário BR com sinal opcional (último na linha = valor da transação)
_RE_VALOR = re.compile(r'-?\d{1,3}(?:\.\d{3})*,\d{2}')

# CNPJ: XX.XXX.XXX/XXXX-XX
_RE_CNPJ = re.compile(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}')
# CPF: XXX.XXX.XXX-XX
_RE_CPF = re.compile(r'\d{3}\.\d{3}\.\d{3}-\d{2}')

# Trailing numbers (doc/sequência)
_RE_TRAILING_NUMS = re.compile(r'(\s+\d+)+\s*$')

_SKIP_LOWER = [
    'saldo anterior',
    'saldo total disponível',
    'saldo total disponivel',
    'rendimento aplicação automática',
    'rendimento aplicacao automatica',
    'data lançamentos',
    'data lancamentos',
]


def _e_linha_skip(linha: str) -> bool:
    ll = linha.lower().strip()
    if not ll:
        return True
    for token in _SKIP_LOWER:
        if token in ll:
            return True
    return False


def _normalizar_float(texto: str) -> Decimal:
    negativo = texto.strip().startswith('-')
    limpo = texto.replace('-', '').replace('.', '').replace(',', '.').strip()
    try:
        v = Decimal(limpo)
        return -v if negativo else v
    except (InvalidOperation, ValueError):
        return Decimal('0')


def _limpar_descricao(texto: str) -> str:
    # Remove CNPJ e CPF
    texto = _RE_CNPJ.sub('', texto)
    texto = _RE_CPF.sub('', texto)
    # Remove trailing numbers
    texto = _RE_TRAILING_NUMS.sub('', texto)
    return texto.strip()


class ParserItauN2(ParserBase):
    """
    Parser para extratos Itaú no formato N2 (ANTARTI.CO).

    Cada linha começa com DD/MM/YYYY.
    O último valor monetário na linha é o valor da transação.
    Antes dele: descrição + possível razão social e CNPJ/CPF.
    """

    BANCO = 'itau_n2'

    def extrair(self) -> list[dict]:
        if pdfplumber is None:
            self.avisos.append('pdfplumber não instalado.')
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

        for linha in linhas_raw:
            if _e_linha_skip(linha):
                continue

            m = _RE_DATA_INICIO.match(linha)
            if not m:
                continue

            data = m.group(1)
            resto = m.group(2).strip()

            # Encontra todos os valores na linha completa (a partir do 'resto')
            valores = _RE_VALOR.findall(resto)
            if not valores:
                continue

            valor_str = valores[-1]
            valor_f = _normalizar_float(valor_str)
            if valor_f == 0.0:
                continue

            # Descrição = tudo antes do último valor monetário
            pos_ultimo = resto.rfind(valor_str)
            desc_raw = resto[:pos_ultimo].strip()
            descricao = _limpar_descricao(desc_raw)

            if not descricao:
                descricao = _limpar_descricao(resto)

            tipo = 'entrada' if valor_f > 0 else 'saida'

            t = self._transacao(
                data=data,
                descricao=descricao,
                valor=abs(valor_f),
                tipo=tipo,
                banco=self.BANCO,
                raw=linha,
            )
            transacoes.append(t)

        return self._post_processar(transacoes)
