"""
mercado_pago.py – Parser de extrato do Mercado Pago.

Formato: texto por linha (sem tabela extraível pelo pdfplumber).
Data: DD-MM-YYYY (hifens, não barras)
Linhas principais: 'DD-MM-YYYY [Descrição] ID R$ valor R$ saldo'
Linhas de continuação: continuação de descrição da linha anterior

Sinal '-' antes de R$ = saída; sem '-' = entrada.
Verificação cruzada: sinal + palavras-chave.
"""

import re
import pdfplumber
from .base import ParserBase


BANCO = 'Mercado Pago'

# Valor monetário BR com sinal opcional antes OU depois do R$
# Cobre: R$ 4,66 | -R$ 63,20 | R$ -63,20 | R$ 1.449,26
_RE_VALOR_MP = re.compile(r'(-?R\$\s*-?[\d.,]+|R\$\s*-[\d.,]+)')

# Linha principal: DD-MM-YYYY ... valor R$ saldo
_RE_LINHA_PRINCIPAL = re.compile(
    r'^(\d{2}-\d{2}-\d{4})\s+.*?(R\$\s*-?[\d.,]+|-R\$\s*[\d.,]+)\s+R\$\s*[\d.,]+\s*$'
)

# Captura a descrição da linha (entre date e o último ID numérico ou antes do R$)
_RE_DATE_DESC = re.compile(
    r'^(\d{2}-\d{2}-\d{4})\s+(?:(.+?)\s+)?(\d{10,})\s+(R\$\s*-?[\d.,]+|-R\$\s*[\d.,]+)\s+R\$'
)

# Linha apenas com ID e valor
_RE_DATE_ID_VALOR = re.compile(
    r'^(\d{2}-\d{2}-\d{4})\s+(\d{10,})\s+(R\$\s*-?[\d.,]+|-R\$\s*[\d.,]+)\s+R\$\s*[\d.,]+'
)

_IGNORAR = [
    'extrato de conta', 'detalhe dos movimentos', 'data descri',
    'entradas:', 'saidas:', 'saídas:', 'saldo inicial', 'saldo final', 'saldo',
    'periodo:', 'período:', 'cpf/cnpj', 'agência', 'conta:',
    'valor', 'total',
]

_ENTRADAS_TIPO = [
    'liberação de dinheiro', 'liberacao de dinheiro',
    'pix recebido', 'recebimento',
    'crédito em conta', 'credito em conta',
    'credito', 'crédito',
]

_SAIDAS_TIPO = [
    'pagamento', 'pagamento de assinatura', 'enviado',
    'transferência enviada', 'transferencia enviada',
    'retirada', 'debito', 'débito', 'qr', 'pix enviado',
]


def _normalizar_data_mp(data_str: str) -> str:
    """Converte DD-MM-YYYY para DD/MM/YYYY."""
    partes = data_str.split('-')
    if len(partes) == 3:
        return f'{partes[0]}/{partes[1]}/{partes[2]}'
    return data_str


class ParserMercadoPago(ParserBase):
    """Parser para extratos do Mercado Pago (formato texto)."""

    def extrair(self) -> list[dict]:
        """Extrai transações do extrato Mercado Pago via texto."""
        transacoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or "") as pdf:
            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    texto = pagina.extract_text() or ''
                    transacoes.extend(self._processar_pagina(texto))
                except Exception as e:
                    self.avisos.append(f'MercadoPago: erro na página {num}: {e}')

        # Tripla verificação: estrutura + data + deduplicação
        return self._post_processar(transacoes)

    def _processar_pagina(self, texto: str) -> list[dict]:
        """Processa o texto de uma página e retorna transações."""
        transacoes: list[dict] = []
        linhas = texto.splitlines()
        desc_buffer: list[str] = []

        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue

            linha_lower = linha.lower()
            if any(x in linha_lower for x in _IGNORAR):
                desc_buffer.clear()
                continue

            # Verifica se a linha começa com data
            if re.match(r'^\d{2}-\d{2}-\d{4}', linha):
                t = self._processar_linha_data(linha, desc_buffer)
                if t:
                    transacoes.append(t)
                desc_buffer.clear()
            else:
                # Linha de continuação/descrição
                if not re.match(r'^\d+/\d+$', linha):
                    desc_buffer.append(linha)

        return transacoes

    def _processar_linha_data(
        self, linha: str, desc_buffer: list[str]
    ) -> dict | None:
        """Processa uma linha que começa com data."""

        # Tenta formato completo: date + desc + ID + R$ value R$ saldo
        m_full = _RE_DATE_DESC.match(linha)
        if m_full:
            data_str = m_full.group(1)
            desc_na_linha = (m_full.group(2) or '').strip()
            valor_raw = m_full.group(4)
            desc = desc_na_linha or ' '.join(desc_buffer).strip() or 'Movimentação'
        else:
            m_id = _RE_DATE_ID_VALOR.match(linha)
            if m_id:
                data_str = m_id.group(1)
                valor_raw = m_id.group(3)
                desc = ' '.join(desc_buffer).strip() or 'Movimentação'
            else:
                m_gen = _RE_LINHA_PRINCIPAL.match(linha)
                if not m_gen:
                    return None
                data_str = m_gen.group(1)
                valor_raw = m_gen.group(2)
                desc = ' '.join(desc_buffer).strip() or 'Movimentação'

        # ── Verificação 1: valor ──────────────────────────────────────
        valor = self._normalizar_valor(valor_raw)
        if valor == 0.0:
            return None

        # ── Verificação 2: tipo — sinal monetário é autoritário ───────
        # No Mercado Pago: '-' no valor (R$ -1.449,26 ou -R$ 63,20) = saída;
        # valor positivo = entrada. Não usa palavras-chave para substituir o sinal
        # porque descrições como "Pagamento com Código QR" são ENTRADAS (cliente
        # paga ao lojista via QR code).
        negativo = '-' in valor_raw
        tipo = 'saida' if negativo else 'entrada'

        data = _normalizar_data_mp(data_str)

        return self._transacao(
            data=data,
            descricao=desc,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=linha,
        )
