"""
santander_empresas_v1.py – Parser para o extrato Santander Internet Banking Empresarial.

Formato com grupos por data e etiquetas CREDITO/DEBITO:

  Segunda, 30 de junho de 2025
  RESGATE CONTAMAX AUTOMATICO CREDITO R$ 12.705,15
  PIX ENVIADO DEBITO R$ 5.848,20
  PIX ENVIADO DEBITO R$ 413,45

  Sexta, 27 de junho de 2025
  RESGATE CONTAMAX AUTOMATICO CREDITO R$ 5.172,41
  PAGAMENTO CARTAO CREDITO BCE DEBITO R$ 1.941,35
  PIX RECEBIDO CREDITO R$ 5.989,20
"""

import re
from decimal import Decimal, InvalidOperation
from ..base import ParserBase

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# Cabeçalho de data: "Segunda, 30 de junho de 2025"
_RE_DATA_HEADER = re.compile(
    r'^(Segunda|Ter[çc]a|Quarta|Quinta|Sexta|S[áa]bado|Domingo),?\s+'
    r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
    re.IGNORECASE,
)

# Linha de transação: "DESCRIÇÃO CREDITO R$ 1.234,56" ou "DESCRIÇÃO DEBITO R$ 1.234,56"
_RE_TRANSACAO = re.compile(
    r'^(.+?)\s+(CREDITO|DEBITO)\s+R\$\s*([\d.,]+)\s*$',
    re.IGNORECASE,
)

_MESES = {
    'janeiro': '01', 'fevereiro': '02', 'março': '03', 'marco': '03',
    'abril': '04', 'maio': '05', 'junho': '06', 'julho': '07',
    'agosto': '08', 'setembro': '09', 'outubro': '10',
    'novembro': '11', 'dezembro': '12',
}

# Descrições a ignorar (CREDITO automático do próprio banco)
_SKIP_DESC_LOWER = [
    'resgate contamax',
    'aplicacao contamax',
    'aplicação contamax',
    'saldo anterior',
    'saldo',
]


def _desc_deve_ignorar(descricao: str) -> bool:
    dl = descricao.lower().strip()
    for token in _SKIP_DESC_LOWER:
        if token in dl:
            return True
    return False


def _parse_data(dia: str, mes_str: str, ano: str) -> str:
    mes_num = _MESES.get(mes_str.lower().strip())
    if not mes_num:
        return ''
    return f'{dia.zfill(2)}/{mes_num}/{ano}'


class ParserSantanderEmpresasV1(ParserBase):
    """
    Parser para extratos Santander Internet Banking Empresarial.

    Identifica blocos de data por dia da semana + data por extenso.
    Dentro de cada bloco, extrai transações com etiqueta CREDITO/DEBITO.
    """

    BANCO = 'santander_empresas_v1'

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
        data_atual: str = ''

        for linha in linhas_raw:
            linha_stripped = linha.strip()
            if not linha_stripped:
                continue

            # Verifica se é cabeçalho de data
            m_data = _RE_DATA_HEADER.match(linha_stripped)
            if m_data:
                dia = m_data.group(2)
                mes_str = m_data.group(3)
                ano = m_data.group(4)
                data_atual = _parse_data(dia, mes_str, ano)
                continue

            # Verifica se é linha de transação
            m_tx = _RE_TRANSACAO.match(linha_stripped)
            if m_tx and data_atual:
                descricao = m_tx.group(1).strip()
                tipo_label = m_tx.group(2).upper()
                valor_str = m_tx.group(3)

                if _desc_deve_ignorar(descricao):
                    continue

                tipo = 'entrada' if tipo_label == 'CREDITO' else 'saida'

                # Normaliza valor (formato BR)
                valor_norm = valor_str.replace('.', '').replace(',', '.')
                try:
                    valor_f = Decimal(valor_norm)
                except (InvalidOperation, ValueError):
                    self.avisos.append(f'Valor inválido ignorado: {valor_str!r} — {descricao}')
                    continue

                if valor_f <= 0:
                    continue

                t = self._transacao(
                    data=data_atual,
                    descricao=descricao,
                    valor=round(valor_f, 2),
                    tipo=tipo,
                    banco=self.BANCO,
                    raw=linha_stripped,
                )
                transacoes.append(t)

        return self._post_processar(transacoes)
