"""
c6bank.py – Parser de extrato do C6 Bank.

Formato: texto por linha (extração de texto, NÃO tabela).
Cada transação ocupa uma linha com o formato:
  DD/MM DD/MM Tipo Descrição [-]R$ valor

Nota: extract_tables() não é usado porque o pdfplumber falha ao
detectar o valor de linhas subsequentes no mesmo dia (col[4]=None).
A extração de texto é completa e precisa.

Classificação de tipo:
  - '-R$' no valor → saída
  - 'R$' sem '-' → entrada
  O sinal monetário é autoritário para o C6 Bank.
"""

import re
import pdfplumber
from .base import ParserBase


BANCO = 'C6Bank'

_RE_ANO = re.compile(r'\b(20\d{2})\b')
_RE_ANO_PERIODO = re.compile(r'per[ií]odo.*?(\d{4})', re.IGNORECASE)

# Linha de transação: DD/MM DD/MM <desc> [-]R$ valor
_RE_TRANSACAO = re.compile(
    r'^(\d{2}/\d{2})\s+\d{2}/\d{2}\s+(.+?)\s+(-?R\$\s*[\d.,]+)\s*$'
)

_IGNORAR_LINHAS = [
    'saldo do dia', 'data lançamento', 'data contábil', 'tipo descrição',
    'sem lançamentos', 'extrato período', 'extrato exportado',
    'agência:', 'informações sujeitas',
]


class ParserC6Bank(ParserBase):
    """Parser para extratos do C6 Bank (formato texto linha a linha)."""

    def _extrair_saldos_intermediarios(self) -> list[dict]:
        """Extrai 'Saldo do dia DD/MM/YY R$ X.XXX,XX' do extrato C6 Bank."""
        saldos = []
        _re_saldo = re.compile(
            r'Saldo\s+do\s+dia\s+(\d{2}/\d{2}/\d{2})\s+R\$\s*([\d.,]+)',
            re.IGNORECASE
        )
        try:
            with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
                for page in pdf.pages:
                    texto = page.extract_text() or ''
                    for linha in texto.split('\n'):
                        m = _re_saldo.search(linha)
                        if m:
                            data = self._normalizar_data(m.group(1))
                            valor = self._normalizar_valor(m.group(2))
                            saldos.append({'data': data, 'saldo': valor})
        except Exception:
            pass
        return saldos

    def extrair(self) -> list[dict]:
        """Extrai transações do extrato C6 Bank via texto."""
        transacoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
            # Extrai ano de referência do texto das primeiras páginas.
            ano_ref = None
            for pagina in pdf.pages[:3]:
                try:
                    texto = pagina.extract_text() or ''
                    m_per = _RE_ANO_PERIODO.search(texto)
                    if m_per:
                        ano_ref = int(m_per.group(1))
                        break
                    if ano_ref is None:
                        m = _RE_ANO.search(texto)
                        if m:
                            ano_ref = int(m.group(1))
                except Exception:
                    pass

            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    texto = pagina.extract_text() or ''
                    for linha in texto.splitlines():
                        t = self._processar_linha_texto(linha, ano_ref)
                        if t:
                            transacoes.append(t)
                except Exception as e:
                    self.avisos.append(f'C6Bank: erro na página {num}: {e}')

        return self._post_processar(transacoes)

    def _processar_linha_texto(self, linha: str, ano_ref: int | None) -> dict | None:
        """Processa uma linha de texto no formato 'DD/MM DD/MM desc [-]R$ valor'."""
        linha = linha.strip()
        if not linha:
            return None

        linha_lower = linha.lower()
        if any(x in linha_lower for x in _IGNORAR_LINHAS):
            return None

        m = _RE_TRANSACAO.match(linha)
        if not m:
            return None

        data_str = m.group(1)   # DD/MM
        desc_raw = m.group(2).strip()
        valor_str = m.group(3)

        if not desc_raw or not any(c.isalpha() for c in desc_raw):
            return None

        valor = self._normalizar_valor(valor_str)
        if valor == 0.0:
            return None

        # Sinal monetário é autoritário no C6 Bank
        tipo = 'saida' if '-' in valor_str else 'entrada'

        data = self._normalizar_data(data_str, ano_referencia=ano_ref)

        return self._transacao(
            data=data,
            descricao=desc_raw,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=linha,
        )
