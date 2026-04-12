"""
xp_extrato.py – Parser de extrato de conta da XP Investimentos.

Formato: texto por linha.
Estrutura por transação:
  Descrição (uma ou mais linhas)
  DD/MM/YY  DD/MM/YY  -?R$ valor  R$ saldo

A linha com as DUAS datas e o valor é a linha de lançamento.
A descrição está nas linhas ANTERIORES a essa linha.

Tipos: Vencimento CDB, IR/IOF deductions, RESGATE, TED BCO,
APLICAÇÃO FUNDOS.
"""

import re
import pdfplumber
from .base import ParserBase


BANCO = 'XP Extrato'

# Linha de lançamento sem descrição inline: DD/MM/YY  DD/MM/YY  -?R$ valor  R$ saldo
_RE_LANCAMENTO = re.compile(
    r'^(\d{2}/\d{2}/\d{2,4})\s+\d{2}/\d{2}/\d{2,4}\s+(-?R\$\s*[\d.,]+)\s+(-?R\$\s*[\d.,]+)'
)

# Linha de lançamento COM descrição inline: DD/MM/YY  DD/MM/YY  DESCRICAO  -?R$ valor  R$ saldo
_RE_LANCAMENTO_INLINE = re.compile(
    r'^(\d{2}/\d{2}/\d{2,4})\s+\d{2}/\d{2}/\d{2,4}\s+([A-Za-zÀ-ÿ].+?)\s+(-?R\$\s*[\d.,]+)\s+(-?R\$\s*[\d.,]+)\s*$'
)

_IGNORAR = [
    'liq mov', 'histórico', 'historico', 'valor (r$)', 'saldo (r$)',
    'extrato da conta', 'extrato para simples', 'saldo disponível',
    'saldo disponivel', 'informações detalhadas', 'informacoes',
    'projeções futuras', 'resgates de fundos', 'termos de', 'ouvidoria',
    'sac,', 'ligar para', 'home', 'investimentos praticidades',
    'esconder valores', 'meu extrato', 'pure brazil',
    'data da consulta', 'código assessor', 'assessor:',
    'completo /', 'r$ 0,00', 'r$0,00',
    'importante:', 'estas informações', 'informa',
    'dias úteis',
]

_ENTRADAS = [
    'vencimento cdb', 'vencimento lca', 'vencimento lci', 'vencimento cri',
    'vencimento cra', 'vencimento debenture', 'vencimento',
    'resgate', 'rendimento', 'crédito', 'credito',
    'irrf s/resgate', 'ir - vencimento',  # estes são saídas (IR = débito)
]

_SAIDAS_EXPLÍCITAS = [
    'irrf', 'ir -', 'ir–', 'iof', 'aplicação', 'aplicacao',
    'ted bco', 'ted ter', 'ted tec', 'retirada',
]


class ParserXPExtrato(ParserBase):
    """Parser para extrato de conta da XP Investimentos (texto por linha)."""

    def extrair(self) -> list[dict]:
        """Extrai transações do extrato XP via texto."""
        transacoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or "") as pdf:
            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    texto = pagina.extract_text() or ''
                    transacoes.extend(self._processar_pagina(texto))
                except Exception as e:
                    self.avisos.append(f'XP Extrato: erro na página {num}: {e}')

        # Tripla verificação: estrutura + data + deduplicação
        return self._post_processar(transacoes)

    def _processar_pagina(self, texto: str) -> list[dict]:
        transacoes: list[dict] = []
        linhas = texto.splitlines()
        desc_buffer: list[str] = []

        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue

            linha_lower = linha.lower()

            # Ignora cabeçalhos/metadados
            if any(x in linha_lower for x in _IGNORAR):
                desc_buffer.clear()
                continue

            # Linha de lançamento sem descrição inline: DD/MM  DD/MM  -R$ valor  R$ saldo
            m = _RE_LANCAMENTO.match(linha)
            if m:
                data_str = m.group(1)
                valor_raw = m.group(2)
                desc = ' '.join(desc_buffer).strip() if desc_buffer else 'Movimentação XP'
                t = self._montar_transacao(data_str, desc, valor_raw, linha)
                if t:
                    transacoes.append(t)
                desc_buffer.clear()
                continue

            # Linha de lançamento COM descrição inline: DD/MM  DD/MM  DESCRICAO  R$ valor  R$ saldo
            m2 = _RE_LANCAMENTO_INLINE.match(linha)
            if m2:
                data_str = m2.group(1)
                desc_inline = m2.group(2).strip()
                valor_raw = m2.group(3)
                # Usa descrição inline; ignora desc_buffer (resíduos de transação anterior)
                t = self._montar_transacao(data_str, desc_inline, valor_raw, linha)
                if t:
                    transacoes.append(t)
                desc_buffer.clear()
                continue

            # Linha de descrição — acumula
            desc_buffer.append(linha)

        return transacoes

    def _montar_transacao(
        self, data_str: str, desc: str, valor_raw: str, raw: str
    ) -> dict | None:
        valor = self._normalizar_valor(valor_raw)
        if valor == 0.0:
            return None

        negativo = '-' in valor_raw
        desc_lower = desc.lower()

        # IR, IOF, TED, Aplicação = saída
        if any(s in desc_lower for s in _SAIDAS_EXPLÍCITAS) or negativo:
            tipo = 'saida'
        else:
            tipo = 'entrada'

        # Normaliza data DD/MM/YY → DD/MM/YYYY
        data = self._normalizar_data(data_str)

        return self._transacao(
            data=data,
            descricao=desc,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=raw,
        )
