"""
bs2.py – Parser de extrato do BS2 Banco.

Formato: texto por linha.
Cada linha de transação:
  DD/MM/YYYY  Tipo  Descrição  [-]R$ valor

Linhas de saldo:
  "Saldo Inicial  R$ X,XX"
  "Saldo Final    R$ X,XX"

Regras:
  - Valor com '-' ou tipo com palavra de débito → saida
  - Caso contrário → entrada
  - Remuneração de aplicação automática é filtrada (movimentação interna)
"""

import re
import pdfplumber
from .base import ParserBase


BANCO = 'BS2'

# Linha de transação: DD/MM/YYYY + conteúdo
_RE_DATA_INICIO = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.+)$')

# Valor monetário BR (com ou sem sinal)
_RE_VALOR_BR = re.compile(r'(-?R?\$?\s*[\d.]+,\d{2}|-?[\d.]+,\d{2}[-]?)')

# Sinal de negativo no final do valor: "1.234,56-"
_RE_VALOR_NEG_FINAL = re.compile(r'^([\d.]+,\d{2})-$')

_IGNORAR = [
    'saldo inicial', 'saldo final', 'saldo anterior', 'saldo do dia',
    # NOTA: Remuneracao Aplicacao Automatica e credito real (rendimento).
    # NAO filtrar — contribui para o saldo.
    'bs2 banco', 'banco bs2', 'extrato', 'período', 'periodo',
    'data tipo descrição', 'data tipo descricao',  # cabecalho da tabela
    'histórico', 'historico',
    'ouvidoria', 'sac ', '0800', 'https://', 'agência', 'agencia',
    'cnpj', 'cpf',
]

_ENTRADAS = [
    'pix recebido', 'pix credito', 'crédito pix', 'credito pix',
    'ted recebida', 'ted recebido',
    'transferencia recebida', 'transferência recebida',
    'deposito', 'depósito', 'resgate', 'estorno', 'devolução', 'devolucao',
    'recebimento', 'recebiment',  # BS2 usa "Recebiment Cartao Credito"
    'pix recebido manual',
    'remuneração', 'remuneracao',  # rendimento de aplicacao automatica
]

_SAIDAS = [
    'pix enviado', 'pix debito', 'débito pix', 'debito pix',
    'ted enviada', 'ted enviado',
    'transferencia enviada', 'transferência enviada',
    'pagamento de título', 'pagamento de titulo',
    'pagamento boleto', 'pagamento cartao',
    'pgto concess', 'pgto tributo',
    'tarifa ted', 'tarifa ',
    'taxa', 'saque', 'saída', 'saida',
    'compra', 'darf', 'simples nacional', 'despesa',
]


class ParserBS2(ParserBase):
    """Parser para extratos do BS2 Banco (formato texto por linha)."""

    def extrair(self) -> list[dict]:
        """Extrai transações do extrato BS2 via texto."""
        transacoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    texto = pagina.extract_text() or ''
                    for linha in texto.splitlines():
                        t = self._processar_linha(linha.strip())
                        if t:
                            transacoes.append(t)
                except Exception as e:
                    self.avisos.append(f'BS2: erro na página {num}: {e}')

        return self._post_processar(transacoes)

    def _processar_linha(self, linha: str) -> dict | None:
        if not linha:
            return None

        linha_lower = linha.lower()

        if any(x in linha_lower for x in _IGNORAR):
            return None

        # A linha deve começar com DD/MM/YYYY
        m = _RE_DATA_INICIO.match(linha)
        if not m:
            return None

        data_raw = m.group(1)
        resto = m.group(2).strip()

        # Extrai todos os valores monetários da linha
        matches = list(_RE_VALOR_BR.finditer(resto))
        if not matches:
            return None

        # Último valor = valor da transação (ou penúltimo se houver saldo no final)
        if len(matches) >= 2:
            valor_match = matches[-2]
        else:
            valor_match = matches[-1]

        valor_raw = valor_match.group(0).strip()

        # Verifica sinal: pode ser "-R$ X" ou "X-" (minus no final)
        negativo = valor_raw.startswith('-') or valor_raw.endswith('-')

        # Normaliza o valor
        valor_limpo = valor_raw.replace('R$', '').replace('$', '').strip().rstrip('-').lstrip('-').strip()
        valor = self._normalizar_valor(valor_limpo)
        if valor == 0.0:
            return None

        # Descrição = texto antes do primeiro valor monetário
        primeiro_pos = matches[0].start()
        desc = resto[:primeiro_pos].strip()

        # Remove número de documento (5+ dígitos) no final da descrição
        desc = re.sub(r'\s+\d{5,}\s*$', '', desc).strip()

        if not desc or len(desc) < 3:
            return None

        # BS2: todos os valores sao positivos no formato "R$ X,XX".
        # O "-" que aparece antes de "R$" e separador de descricao, nao sinal.
        # Tipo determinado EXCLUSIVAMENTE por palavras-chave na descricao.
        # Exemplos:
        #   "Pix Recebido Chave Crédito Pix Chave - Fulano R$ 5.900,00" = ENTRADA
        #   "Pagamento de Título - R$ 117,37" = SAIDA
        #   "Ted Enviada Outra Tit Ib ... - R$ 13.457,89" = SAIDA
        tipo = self._verificar_tipo_cruzado(
            tipo_por_sinal='',  # ignora sinal — BS2 nao usa sinal no valor
            descricao=desc,
            palavras_entrada=_ENTRADAS,
            palavras_saida=_SAIDAS,
        )

        data = self._normalizar_data(data_raw)

        return self._transacao(
            data=data,
            descricao=desc,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=linha,
        )
