"""
Classe base para parsers de extratos empresariais.

Centraliza helpers e constantes compartilhadas por:
- bradesco_net_empresas
- btg
- itau_n2 (n2/itau_n2.py)

Origem: extracao de codigo duplicado mapeado em S25 Fase 4
(codigo_duplicado.md cluster #1, escopo revisado em S27.5 Fase 1).

NOTA: santander_empresas/v1.py NAO herda desta base - nao compartilha
nenhum helper/regex (verificado em S27.5 Fase 1).

NOTA: _limpar_descricao NAO esta nesta base - itau_n2 tem variante
legitima (remove CNPJ/CPF) que deve permanecer especializada.
"""

import re
from decimal import Decimal, InvalidOperation
from .base import ParserBase

# Valor monetario BR com sinal opcional. Extraido de 3 parsers em S27.5.
_RE_VALOR = re.compile(r'-?\d{1,3}(?:\.\d{3})*,\d{2}')

# Sequencia de inteiros no final da descricao (numeros de documento).
# Extraido de bradesco_net_empresas (_RE_TRAILING_INTS) e itau_n2
# (_RE_TRAILING_NUMS) - regex identico, nomes divergiam. Unificado.
_RE_TRAILING_INTS = re.compile(r'(\s+\d+)+\s*$')


class ParserEmpresaBase(ParserBase):
    """Classe base para parsers de extratos empresariais."""

    # Subclasses sobrescrevem com lista de tokens lower-case proprios.
    _SKIP_LOWER: list[str] = []

    def _e_linha_skip(self, linha: str) -> bool:
        """Retorna True se a linha deve ser ignorada."""
        ll = linha.lower().strip()
        if not ll:
            return True
        for token in self._SKIP_LOWER:
            if token in ll:
                return True
        return False

    def _normalizar_float(self, texto: str) -> Decimal:
        """Converte string monetaria BR (com possivel sinal) em Decimal com sinal."""
        negativo = texto.strip().startswith('-')
        limpo = texto.replace('-', '').replace('.', '').replace(',', '.').strip()
        try:
            v = Decimal(limpo)
            return -v if negativo else v
        except (InvalidOperation, ValueError):
            return Decimal('0')
