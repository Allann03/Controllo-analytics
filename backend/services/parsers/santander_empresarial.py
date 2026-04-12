"""
santander_empresarial.py – Parser para extrato Santander Internet Banking Empresarial.

Formato: Conta Corrente / Internet Banking (extrato de conta corrente, NÃO ContaMax).

Cada linha de transação:
  DD/MM/YYYY HISTÓRICO [DOCUMENTO] VALOR [SALDO]

Onde VALOR pode ser negativo (saída/débito) ou positivo (entrada/crédito).

Entradas a filtrar:
  - SALDO ANTERIOR
  - RESGATE CONTAMAX / APLICAÇÃO CONTAMAX (movimentações internas de fundo)
  - Linhas de cabeçalho e rodapé
"""

import re
import pdfplumber
from .base import ParserBase


BANCO = 'Santander'

# Linha de transação: deve começar com DD/MM/YYYY (data válida)
_RE_DATA_INICIO = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.+)$')

# Formato App: data por extenso com icone Unicode
# "\uf166 Sexta, 31 de outubro de 2025"
_MESES_PT = {
    'janeiro': '01', 'fevereiro': '02', 'março': '03', 'marco': '03',
    'abril': '04', 'maio': '05', 'junho': '06', 'julho': '07',
    'agosto': '08', 'setembro': '09', 'outubro': '10',
    'novembro': '11', 'dezembro': '12',
}
_RE_DATA_EXTENSO = re.compile(
    r'[\uf000-\uf999]?\s*\w+,?\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
    re.IGNORECASE,
)

# Transacao formato App: "DESCRICAO CREDITO|DEBITO R$ VALOR"
_RE_TX_APP = re.compile(
    r'^(.+?)\s+(CREDITO|DEBITO)\s+R\$\s*([\d.,]+)\s*$',
    re.IGNORECASE,
)

# Valor monetário BR com formato correto:
# Aceita: -1.234,56 | 1.234,56 | 123,45 | -0,01
# Rejeita: 12345 (sem vírgula decimal) | 1234.56 (formato americano)
_RE_VALOR_BR = re.compile(r'(-?(?:\d{1,3}(?:\.\d{3})*|\d+),\d{2})')

_IGNORAR = [
    # Saldos contábeis — não são transações
    'saldo anterior', 'saldo do dia', 'saldo final', 'saldo inicial',
    # Movimentações internas ContaMax (aparecem no CC mas não afetam caixa operacional)
    'resgate contamax', 'aplicacao contamax', 'aplicação contamax',
    'aplic contamax', 'aplic. contamax',
    # Cabeçalhos e rodapés
    'internet banking', 'banco santander', 'conta corrente', 'historico',
    'histórico', 'documento', 'data', 'extrato', 'agência', 'agencia',
    'ouvidoria', 'sac ', '4004', '4003', '0800', 'https://', 'acesso',
    'central de atendimento', 'cw tour',
]



class ParserSantanderEmpresas(ParserBase):
    """
    Parser para extrato Santander Internet Banking Empresarial (Conta Corrente).
    Detecta automaticamente linhas com data + histórico + valor ± saldo.
    """

    def extrair(self) -> list[dict]:
        transacoes: list[dict] = []
        todas_linhas: list[str] = []

        with pdfplumber.open(self.pdf_path, password=self.password or "") as pdf:
            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    texto = pagina.extract_text() or ''
                    for linha in texto.splitlines():
                        todas_linhas.append(linha)
                        t = self._processar_linha(linha)
                        if t:
                            transacoes.append(t)
                except Exception as e:
                    self.avisos.append(f'Santander Empresarial: erro na página {num}: {e}')

        # Se formato padrão (DD/MM/YYYY) não encontrou nada, tentar formato App
        # (datas por extenso + "CREDITO/DEBITO R$ VALOR")
        if not transacoes:
            transacoes = self._extrair_formato_app(todas_linhas)

        return self._post_processar(transacoes)

    def _extrair_formato_app(self, linhas: list[str]) -> list[dict]:
        """Extrai transações do formato App Santander Empresas (datas por extenso)."""
        transacoes: list[dict] = []
        data_atual = ''

        for linha in linhas:
            stripped = linha.strip()
            if not stripped:
                continue

            # Tentar data por extenso
            m_data = _RE_DATA_EXTENSO.search(stripped)
            if m_data:
                dia = m_data.group(1).zfill(2)
                mes_nome = m_data.group(2).lower()
                ano = m_data.group(3)
                mes_num = _MESES_PT.get(mes_nome)
                if mes_num:
                    data_atual = f'{dia}/{mes_num}/{ano}'
                continue

            # Ignorar cabeçalhos e rodapés
            ll = stripped.lower()
            if any(x in ll for x in _IGNORAR):
                continue

            # Tentar transação: "DESCRICAO CREDITO|DEBITO R$ VALOR"
            m_tx = _RE_TX_APP.match(stripped)
            if m_tx and data_atual:
                desc = m_tx.group(1).strip()
                tipo_raw = m_tx.group(2).upper()
                valor = self._normalizar_valor(m_tx.group(3))
                if valor < 0.01:
                    continue
                tipo = 'entrada' if tipo_raw == 'CREDITO' else 'saida'
                transacoes.append(self._transacao(
                    data=data_atual, descricao=desc, valor=valor,
                    tipo=tipo, banco=BANCO, raw=stripped,
                ))

        return transacoes

    def _processar_linha(self, linha: str) -> dict | None:
        linha = linha.strip()
        if not linha:
            return None

        linha_lower = linha.lower()

        # Filtra cabeçalhos, saldos e movimentações internas
        if any(x in linha_lower for x in _IGNORAR):
            return None

        # A linha deve começar com uma data DD/MM/YYYY
        m = _RE_DATA_INICIO.match(linha)
        if not m:
            return None

        data_raw = m.group(1)
        resto = m.group(2).strip()

        # Extrai todos os valores monetários BR da linha
        # Usa finditer para capturar posições (necessário para extrair a descrição)
        matches = list(_RE_VALOR_BR.finditer(resto))
        if not matches:
            return None

        # Precisa de ao menos um valor com vírgula decimal para ser transação real
        # O penúltimo match = valor da transação; o último = saldo (se existir)
        if len(matches) >= 2:
            valor_match = matches[-2]
        else:
            valor_match = matches[-1]

        valor_raw = valor_match.group(1)

        # Descrição = tudo antes do primeiro valor monetário na linha
        # (o texto antes do primeiro valor numérico é o histórico)
        primeiro_valor_pos = matches[0].start()
        desc = resto[:primeiro_valor_pos].strip()

        # Remove número de documento no final da descrição (5+ dígitos consecutivos)
        desc = re.sub(r'\s+\d{5,}\s*$', '', desc).strip()

        if not desc or len(desc) < 3:
            return None

        # Normaliza o valor preservando o sinal para determinar o tipo
        negativo = valor_raw.lstrip().startswith('-')
        valor = self._normalizar_valor(valor_raw)

        if valor < 0.01:
            return None

        # Negativo = débito (saída), Positivo = crédito (entrada)
        tipo = 'saida' if negativo else 'entrada'

        data = self._normalizar_data(data_raw)

        return self._transacao(
            data=data,
            descricao=desc,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=linha,
        )
