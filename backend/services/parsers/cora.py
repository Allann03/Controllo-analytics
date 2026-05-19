"""
cora.py – Parser de extrato do Banco Cora.

Formato: texto por linha (NÃO tabela).
Linhas de data:  'DD/MM/YYYY Saldo do dia R$ X'   → extrai data, ignora saldo
Linhas de transação: 'Tipo Nome CNPJ/CPF + R$ valor' (entrada)
                 ou: 'Tipo Nome CNPJ/CPF - R$ valor' (saída)

O sinal '+' indica entrada, '-' indica saída — autoritário.
Saldo do dia → ignorado explicitamente.
"""

import re
import pdfplumber
from .base import ParserBase


BANCO = 'Cora'

# Linha de data: "30/12/2025 Saldo do dia R$ 0,00"
_RE_DATA_LINHA = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+Saldo do dia', re.IGNORECASE)

# Transação: qualquer coisa + sinal (+ ou -) + R$ + valor
# Ex: "Transf Pix enviada FERNANDO AUGUS… 284.604.948-37 - R$ 205,00"
# Ex: "Transferência recebida Vis Otica Ltda 44.899.953/0001-09 + R$ 1.180,00"
_RE_TRANSACAO = re.compile(
    r'^(.+?)\s+([+-])\s+R\$\s*([\d.,]+)\s*$'
)

# Linhas completamente ignoradas
_IGNORAR = [
    'saldo do dia', 'saldo inicial', 'saldo final', 'saldo disponível',
    'total de entradas', 'total de saídas', 'total de saidas',
    'extrato do período', 'extrato do periodo',
    'extrato gerado', 'ouvidoria', 'sac', 'cora scfi',
    'cnpj', 'agência:', 'agencia:', 'conta:',
]


class ParserCora(ParserBase):
    """Parser para extratos do Banco Cora (formato texto por linha)."""

    def _extrair_saldos_intermediarios(self) -> list[dict]:
        """Extrai 'DD/MM/YYYY Saldo do dia R$ X,XX' do extrato Cora."""
        saldos = []
        _re_saldo = re.compile(
            r'(\d{2}/\d{2}/\d{4})\s+Saldo\s+do\s+dia\s+R\$\s*([\d.,]+)',
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
        """Extrai transações do extrato Cora via texto."""
        transacoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
            data_atual = ''

            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    texto = pagina.extract_text() or ''
                    for linha in texto.splitlines():
                        linha = linha.strip()
                        if not linha:
                            continue

                        # Header de data — extrai data, ignora saldo
                        m_data = _RE_DATA_LINHA.match(linha)
                        if m_data:
                            data_atual = self._normalizar_data(m_data.group(1))
                            continue

                        # Ignora linhas de metadados
                        linha_lower = linha.lower()
                        if any(x in linha_lower for x in _IGNORAR):
                            continue

                        # Linha de transação
                        t = self._processar_linha(linha, data_atual)
                        if t:
                            transacoes.append(t)

                except Exception as e:
                    self.avisos.append(f'Cora: erro na página {num}: {e}')

        # Tripla verificação: estrutura + data + deduplicação
        return self._post_processar(transacoes)

    def _processar_linha(self, linha: str, data_atual: str) -> dict | None:
        m = _RE_TRANSACAO.match(linha)
        if not m:
            return None

        desc_raw = m.group(1).strip()
        sinal = m.group(2)       # '+' ou '-'
        valor_raw = m.group(3)

        # ── Verificação 1: valor ──────────────────────────────────────
        valor = self._normalizar_valor(valor_raw)
        if valor == 0.0:
            return None

        # ── Verificação 2: tipo — sinal é autoritário na Cora ─────────
        tipo = 'entrada' if sinal == '+' else 'saida'

        return self._transacao(
            data=data_atual,
            descricao=desc_raw,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=linha,
        )
