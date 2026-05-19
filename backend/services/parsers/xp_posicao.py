"""
xp_posicao.py – Parser de posição consolidada da XP Investimentos.

Formato: tabela com 10 colunas (posição de ativos — NÃO são transações correntes).

Mapeamento de colunas (baseado no layout real do PDF):
  [0] = ATIVO (nome do ativo)
  [1] = APLICAÇÃO (data de aplicação)
  [2] = CARÊNCIA
  [3] = VENCIMENTO
  [4] = TAXA
  [5] = DISPONÍVEL (quantidade/cota)
  [6] = GARANTIA
  [7] = VALOR APLICADO
  [8] = POSIÇÃO MERCADO
  [9] = VALOR LÍQUIDO

Retorna ativos/posições com tipo='posicao' (não débitos/créditos).
"""

import re
import pdfplumber
from .base import ParserBase


BANCO = 'XP Posição'

_IGNORAR_NOME = [
    'ativo', 'aplicação', 'aplicacao', 'carência', 'carencia',
    'vencimento', 'taxa', 'disponível', 'disponivel', 'garantia',
    'valor aplicado', 'posição', 'posicao', 'mercado', 'líquido', 'liquido',
    'total', 'subtotal', 'renda fixa', 'renda variável', 'renda variavel',
    'fundos', 'tesouro', 'historico', 'histórico',
]

_SECOES = [
    'renda fixa', 'renda variável', 'renda variavel',
    'fundos de investimento', 'tesouro direto', 'coe',
    'previdência', 'previdencia', 'prefixada', 'pré-fixada', 'pós-fixada',
]


class ParserXPPosicao(ParserBase):
    """
    Parser para posição consolidada da XP Investimentos.

    Retorna ativos/posições com tipo='posicao'.
    """

    def __init__(self, pdf_path: str, password: str | None = None) -> None:
        super().__init__(pdf_path, password)
        self._secao_atual: str = 'Geral'

    def extrair(self) -> list[dict]:
        """Extrai posições do relatório de posição consolidada XP."""
        posicoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or "") as pdf:
            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    texto = pagina.extract_text() or ''
                    self._detectar_secao(texto)

                    tabelas = pagina.extract_tables()
                    for tabela in tabelas:
                        for linha in tabela:
                            p = self._processar_linha(linha)
                            if p:
                                posicoes.append(p)
                except Exception as e:
                    self.avisos.append(f'XP Posição: erro na página {num}: {e}')

        # Passe de validação: estrutura + deduplicação (sem validação de data — posições podem ter data vazia)
        return self._post_processar(posicoes)

    def _detectar_secao(self, texto: str) -> None:
        """Atualiza seção atual com base no texto da página."""
        texto_lower = texto.lower()
        for sec in _SECOES:
            if sec in texto_lower:
                self._secao_atual = sec.title()
                break

    def _processar_linha(self, linha: list) -> dict | None:
        if not linha or len(linha) < 4:
            return None

        # Col 0: nome do ativo
        nome_raw = str(linha[0] or '').strip()
        if not nome_raw or len(nome_raw) < 3:
            return None

        nome_lower = nome_raw.lower()
        if any(x in nome_lower for x in _IGNORAR_NOME):
            return None

        # O nome deve começar com letra (ativos como CDB, LCA, etc.)
        if not nome_raw[0].isalpha():
            return None

        def _get(idx: int) -> str:
            if len(linha) > idx:
                val = str(linha[idx] or '').strip()
                # Remove newlines internos (ex: "R$\n50.000,00")
                return val.replace('\n', ' ').strip()
            return ''

        # Colunas corretas conforme layout real
        data_aplic_raw = _get(1)   # APLICAÇÃO
        carencia_raw = _get(2)     # CARÊNCIA
        vencimento_raw = _get(3)   # VENCIMENTO
        taxa = _get(4)             # TAXA
        # [5] = DISPONÍVEL (cota/qtd)
        # [6] = GARANTIA
        valor_aplicado_raw = _get(7)   # VALOR APLICADO
        posicao_mercado_raw = _get(8)  # POSIÇÃO MERCADO
        valor_liquido_raw = _get(9)    # VALOR LÍQUIDO

        # Valor principal: prefere VALOR LÍQUIDO, depois POSIÇÃO MERCADO, depois APLICADO
        valor_principal = valor_liquido_raw or posicao_mercado_raw or valor_aplicado_raw
        valor = self._normalizar_valor(valor_principal)

        # Filtra linhas sem valor válido (headers duplicados, rodapés, etc.)
        if valor == 0.0:
            return None

        # Usa vencimento como data do registro; fallback para data de aplicação
        data_str = vencimento_raw or data_aplic_raw
        data = self._normalizar_data(data_str)

        return self._transacao(
            data=data,
            descricao=nome_raw,
            valor=valor,
            tipo='posicao',
            banco=BANCO,
            raw='|'.join(str(c) for c in linha),
            secao=self._secao_atual,
            data_aplicacao=self._normalizar_data(data_aplic_raw),
            vencimento=self._normalizar_data(vencimento_raw),
            taxa=taxa,
            valor_aplicado=self._normalizar_valor(valor_aplicado_raw),
            posicao_mercado=self._normalizar_valor(posicao_mercado_raw),
            valor_liquido=self._normalizar_valor(valor_liquido_raw),
        )
