"""
stone_n2.py – Parser N2 para extratos Stone no formato Crédito/Débito.

Formato tabular:
  DATA | TIPO (Crédito/Débito) | LANÇAMENTO | VALOR (R$) | SALDO (R$) | [CONTRAPARTE]

Diferença do N1:
  - N1 reconhece "Entrada" / "Saída" no texto
  - N2 reconhece "Crédito" / "Débito" (formato tabular dos extratos mais recentes)

Ativado automaticamente como fallback quando ParserStone (N1) não extrai nenhuma
transação.
"""

import re
import pdfplumber
from .base import ParserBase

BANCO = 'Stone'

# Início de linha de transação: DD/MM/YY(YY) + Crédito|Débito
_RE_DATA_INICIO = re.compile(
    r'^\d{2}/\d{2}/\d{2,4}\s+(?:Cr[eé]dito|D[eé]bito)',
    re.IGNORECASE,
)

# Linha completa: DATA  TIPO  DESCRIÇÃO  VALOR  SALDO
_RE_LINHA_COMPLETA = re.compile(
    r'^(\d{2}/\d{2}/\d{2,4})\s+(Cr[eé]dito|D[eé]bito)\s+(.*?)\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})\s*$',
    re.IGNORECASE,
)

_IGNORAR = [
    'data', 'tipo', 'lançamento', 'lancamento', 'valor', 'saldo',
    'contraparte', 'histórico', 'historico', 'emitido em', 'página',
    'pagina', 'período', 'periodo', 'dados da conta', 'nome', 'documento',
    'instituição', 'agência', 'conta', 'stone institui', 'stone pagamentos',
]


class ParserStoneN2(ParserBase):
    """Parser N2 para extratos Stone com formato Crédito/Débito."""

    def extrair(self) -> list[dict]:
        transacoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    # Tenta tabela primeiro
                    tabelas = pagina.extract_tables()
                    achou = False
                    for tabela in tabelas:
                        for linha in tabela:
                            t = self._processar_linha_tabela(linha)
                            if t:
                                transacoes.append(t)
                                achou = True

                    # Fallback: texto linha a linha
                    if not achou:
                        texto = pagina.extract_text() or ''
                        transacoes.extend(self._extrair_texto_pagina(texto))

                except Exception as e:
                    self.avisos.append(f'StoneN2: erro na página {num}: {e}')

        return self._post_processar(transacoes)

    # ------------------------------------------------------------------ #
    # Extração por texto                                                  #
    # ------------------------------------------------------------------ #

    def _extrair_texto_pagina(self, texto: str) -> list[dict]:
        transacoes: list[dict] = []
        linhas = texto.splitlines()
        i = 0
        while i < len(linhas):
            linha = linhas[i].strip()
            if not linha:
                i += 1
                continue

            if _RE_DATA_INICIO.match(linha):
                # Tenta match completo na linha atual
                m = _RE_LINHA_COMPLETA.match(linha)
                if m:
                    t = self._montar_de_match(m, linha)
                    if t:
                        transacoes.append(t)
                else:
                    # Descrição/valor pode estar espalhada nas próximas linhas
                    partes = [linha]
                    j = i + 1
                    while j < len(linhas) and j < i + 4:
                        prox = linhas[j].strip()
                        if not prox or _RE_DATA_INICIO.match(prox):
                            break
                        partes.append(prox)
                        j += 1
                    linha_juntada = ' '.join(partes)
                    m2 = _RE_LINHA_COMPLETA.match(linha_juntada)
                    if m2:
                        t = self._montar_de_match(m2, linha_juntada)
                        if t:
                            transacoes.append(t)
                        i = j - 1  # avança além das linhas consumidas
            i += 1
        return transacoes

    def _montar_de_match(self, m: re.Match, raw: str) -> dict | None:
        data_raw = m.group(1)
        tipo_raw = m.group(2)
        desc_raw = m.group(3).strip()
        valor_raw = m.group(4)
        # grupo 5 = saldo — ignoramos (saldo corrente, não valor da transação)

        desc_lower = desc_raw.lower()
        if any(x in desc_lower for x in _IGNORAR):
            return None

        valor = self._normalizar_valor(valor_raw)
        if valor == 0.0:
            return None
        valor = self._segunda_verificacao_valor(raw, valor)

        tipo = self._tipo_de_coluna(tipo_raw)
        data = self._normalizar_data(data_raw)
        desc = desc_raw or 'Stone'

        return self._transacao(data=data, descricao=desc, valor=valor, tipo=tipo,
                               banco=BANCO, raw=raw)

    # ------------------------------------------------------------------ #
    # Extração por tabela                                                 #
    # ------------------------------------------------------------------ #

    def _processar_linha_tabela(self, linha: list) -> dict | None:
        if not linha or len(linha) < 4:
            return None

        data_raw = str(linha[0] or '').strip()
        if not data_raw or not re.match(r'^\d{2}/\d{2}', data_raw):
            return None

        tipo_col = str(linha[1] or '').strip()
        tipo_lower = tipo_col.lower()
        if not any(x in tipo_lower for x in (
            'crédito', 'credito', 'débito', 'debito', 'entrada', 'saída', 'saida'
        )):
            return None

        # Descrição: coluna 2 (LANÇAMENTO)
        desc_raw = str(linha[2] or '').strip() if len(linha) > 2 else ''
        desc_lower = desc_raw.lower()
        if any(x in desc_lower for x in _IGNORAR):
            return None

        # VALOR: coluna 3 (antes do SALDO na coluna 4)
        # Layout: DATA | TIPO | LANÇAMENTO | VALOR | SALDO | [CONTRAPARTE]
        valor_raw = ''
        if len(linha) > 3:
            v = str(linha[3] or '').strip()
            if v and re.search(r'\d+,\d{2}', v):
                valor_raw = v
        if not valor_raw:
            # Fallback: penúltimo número presente na linha
            candidatos = [str(c or '').strip() for c in linha]
            for cell in reversed(candidatos[:-1]):
                if cell and re.search(r'\d+,\d{2}', cell) and '/' not in cell:
                    valor_raw = cell
                    break

        if not valor_raw:
            return None

        valor = self._normalizar_valor(valor_raw)
        if valor == 0.0:
            return None
        raw_tab = '|'.join(str(c or '') for c in linha)
        valor = self._segunda_verificacao_valor(raw_tab, valor)

        tipo = self._tipo_de_coluna(tipo_col)
        data = self._normalizar_data(data_raw)
        desc = desc_raw or 'Stone'

        return self._transacao(
            data=data,
            descricao=desc,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw='|'.join(str(c or '') for c in linha),
        )

    # ------------------------------------------------------------------ #
    # Helper                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _tipo_de_coluna(texto: str) -> str:
        t = texto.lower()
        if 'crédito' in t or 'credito' in t or 'entrada' in t:
            return 'entrada'
        if 'débito' in t or 'debito' in t or 'saída' in t or 'saida' in t:
            return 'saida'
        return 'saida'
