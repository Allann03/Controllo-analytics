"""
verifiers.py — Implementação de verificadores contábeis para cada banco.

Cada classe herda de BankVerifier e implementa a extração de saldos intermediários
usando os MESMOS padrões/regex dos parsers originais do banco.

IMPORTANTE: Este módulo NÃO modifica nenhum parser existente. Ele apenas
CONSOME os dados já extraídos e os valida contabilmente.
"""

import re
import logging
from decimal import Decimal, InvalidOperation
from typing import List, Tuple, Optional

from .base import BankVerifier, _to_decimal

logger = logging.getLogger(__name__)


def _parse_valor_br_decimal(texto: str) -> Optional[Decimal]:
    """
    Converte string monetária brasileira para Decimal.
    Ex: '1.234,56' -> Decimal('1234.56'), '1234,56' -> Decimal('1234.56')
    NUNCA usa float intermediário.
    """
    if not texto:
        return None
    texto = texto.strip().replace(' ', '')
    texto = re.sub(r'R\$\s*', '', texto)
    texto = texto.replace('-', '').replace('+', '')
    if ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    try:
        val = Decimal(texto)
        return abs(val) if val < Decimal('100000000') else None
    except (InvalidOperation, ValueError):
        return None


def _ultimo_valor_br_decimal(linha: str) -> Optional[Decimal]:
    """Extrai o último valor BR da linha como Decimal."""
    m = re.search(r'([\d.,]+)\s*[CD]?\s*$', linha.strip())
    return _parse_valor_br_decimal(m.group(1)) if m else None


def _r_num_decimal(linha: str) -> Optional[Decimal]:
    """Valor após 'R$' na linha como Decimal; fallback = último número."""
    m = re.search(r'[Rr]\$\s*([\d.,]+)', linha)
    return _parse_valor_br_decimal(m.group(1)) if m else _ultimo_valor_br_decimal(linha)


# ═══════════════════════════════════════════════════════════════════════
#  ITAÚ (PF)
# ═══════════════════════════════════════════════════════════════════════

class ItauVerifier(BankVerifier):
    """Verificador para extratos Itaú (PF)."""

    _SALDO_KEYWORDS = BankVerifier._SALDO_KEYWORDS + [
        's a l d o', 'saldo aplic aut mais',
        'saldo total dispon',
    ]

    @property
    def bank_name(self) -> str:
        return 'Itau'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        """Extrai saldos intermediários do Itaú: 'saldo anterior' por página."""
        saldos = []
        # Regex pula a data DD/MM que segue "dia" e captura o valor monetário
        _re_std = re.compile(
            r'saldo\s+total\s+dispon\S*\s+dia\s+\d{2}/\d{2}\s+([\d.,]+)',
            re.IGNORECASE
        )

        for linha in texto_pdf.splitlines():
            # Saldo total disponível no dia = saldo intermediário
            m = _re_std.search(linha)
            if m:
                v = _parse_valor_br_decimal(m.group(1))
                if v is not None:
                    data_m = re.search(r'(\d{2}/\d{2}/?\d{0,4})', linha)
                    data = data_m.group(1) if data_m else ''
                    saldos.append((data, v))

        return saldos


# ═══════════════════════════════════════════════════════════════════════
#  ITAÚ EMPRESAS (PJ)
# ═══════════════════════════════════════════════════════════════════════

class ItauEmpresasVerifier(BankVerifier):
    """Verificador para extratos Itaú Empresas (PJ)."""

    _SALDO_KEYWORDS = BankVerifier._SALDO_KEYWORDS + [
        'saldo disponível', 'saldo contábil', 'saldo parcial',
        'conta corrente pj', 'capital de giro', 'limite de cheque',
    ]

    @property
    def bank_name(self) -> str:
        return 'Itau Empresas'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        saldos = []
        _re_sf = re.compile(r'saldo\s+final\s+([\d.,]+)', re.IGNORECASE)
        _re_cc = re.compile(r'saldo\s+em\s+c/c\s+([\d.,]+)', re.IGNORECASE)

        for linha in texto_pdf.splitlines():
            for pat in (_re_sf, _re_cc):
                m = pat.search(linha)
                if m:
                    v = _parse_valor_br_decimal(m.group(1))
                    if v is not None:
                        data_m = re.search(r'(\d{2}/\d{2}/?\d{0,4})', linha)
                        data = data_m.group(1) if data_m else ''
                        saldos.append((data, v))
        return saldos


# ═══════════════════════════════════════════════════════════════════════
#  BRADESCO
# ═══════════════════════════════════════════════════════════════════════

class BradescoVerifier(BankVerifier):
    """Verificador para extratos Bradesco."""

    _SALDO_KEYWORDS = BankVerifier._SALDO_KEYWORDS + [
        'últimos lançamentos', 'ultimos lancamentos',
        'os dados acima', 'rentab.invest facilcred',
    ]

    @property
    def bank_name(self) -> str:
        return 'Bradesco'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        """
        Bradesco: usa apenas a PRIMEIRA linha 'Total X -Y Z' (período principal).
        Ignora seções pós-período (Últimos Lançamentos, Saldos Invest).
        """
        saldos = []
        _re_total = re.compile(
            r'^total\s+[\d.,]+\s+[-]?[\d.,]+\s+([\d.,]+)\s*$',
            re.IGNORECASE
        )
        _stop_markers = ('últimos lançamentos', 'ultimos lancamentos',
                         'os dados acima', 'saldos invest')
        for linha in texto_pdf.splitlines():
            ll = linha.lower().strip()
            if any(m in ll for m in _stop_markers):
                break
            m = _re_total.match(ll)
            if m:
                v = _parse_valor_br_decimal(m.group(1))
                if v is not None:
                    saldos.append(('', v))
        return saldos


# ═══════════════════════════════════════════════════════════════════════
#  BANCO DO BRASIL
# ═══════════════════════════════════════════════════════════════════════

class BancoDoBrasilVerifier(BankVerifier):
    """Verificador para extratos Banco do Brasil."""

    _SALDO_KEYWORDS = BankVerifier._SALDO_KEYWORDS + [
        's a l d o', 'bb rende fácil', 'bb rende facil',
        'apl aplic aut', 'res aplic aut', 'rend pago aplic aut',
    ]

    @property
    def bank_name(self) -> str:
        return 'Banco do Brasil'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        """BB: 'SALDO DO DIA' linhas com valor e data."""
        saldos = []
        for linha in texto_pdf.splitlines():
            ll = linha.lower()
            if 'saldo do dia' in ll:
                v = _ultimo_valor_br_decimal(linha)
                if v is not None:
                    data_m = re.search(r'(\d{2}/\d{2}/?\d{0,4})', linha)
                    data = data_m.group(1) if data_m else ''
                    saldos.append((data, v))
        return saldos


# ═══════════════════════════════════════════════════════════════════════
#  SANTANDER
# ═══════════════════════════════════════════════════════════════════════

class SantanderVerifier(BankVerifier):
    """Verificador para extratos Santander (todos os formatos)."""

    _SALDO_KEYWORDS = BankVerifier._SALDO_KEYWORDS + [
        'acumulado', 'contamax', 'resgate contamax',
        'aplicacao contamax', 'internet banking',
    ]

    @property
    def bank_name(self) -> str:
        return 'Santander'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        """Santander: não expõe saldos intermediários de forma padronizada."""
        return []


# ═══════════════════════════════════════════════════════════════════════
#  CAIXA
# ═══════════════════════════════════════════════════════════════════════

class CaixaVerifier(BankVerifier):
    """Verificador para extratos Caixa Econômica Federal."""

    _SALDO_KEYWORDS = BankVerifier._SALDO_KEYWORDS + [
        'saldo dia', 'saldo anterior ao período',
        'saldo anterior ao periodo', 'saldo em conta corrente',
    ]

    @property
    def bank_name(self) -> str:
        return 'Caixa'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        """Caixa: 'SALDO DIA' ou 'SALDO DO DIA' com valor R$."""
        saldos = []
        for linha in texto_pdf.splitlines():
            ll = linha.lower()
            if ('saldo dia' in ll or 'saldo do dia' in ll) and 'anterior' not in ll:
                v = _r_num_decimal(linha) or _ultimo_valor_br_decimal(linha)
                if v is not None:
                    data_m = re.search(r'(\d{2}/\d{2}/?\d{0,4})', linha)
                    data = data_m.group(1) if data_m else ''
                    saldos.append((data, v))
        return saldos


# ═══════════════════════════════════════════════════════════════════════
#  NUBANK
# ═══════════════════════════════════════════════════════════════════════

class NubankVerifier(BankVerifier):
    """Verificador para extratos Nubank."""

    _SALDO_KEYWORDS = BankVerifier._SALDO_KEYWORDS + [
        'saldo do dia', 'saldo disponível', 'saldo disponivel',
        'rendimento líquido', 'rendimento liquido',
        'movimentações', 'movimentacoes',
    ]

    @property
    def bank_name(self) -> str:
        return 'Nubank'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        """
        Nubank: 'Saldo final do período' na última linha;
        não possui saldos intermediários por dia no padrão.
        """
        return []


# ═══════════════════════════════════════════════════════════════════════
#  INTER
# ═══════════════════════════════════════════════════════════════════════

class InterVerifier(BankVerifier):
    """Verificador para extratos Banco Inter."""

    _SALDO_KEYWORDS = BankVerifier._SALDO_KEYWORDS + [
        'total de entradas', 'total de saídas', 'total de saidas',
        'fale com a gente',
    ]

    @property
    def bank_name(self) -> str:
        return 'Inter'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        """Inter: 'Saldo do dia: R$ X,XX' por dia."""
        saldos = []
        _re_dia = re.compile(r'saldo\s+do\s+dia:\s*(?:-?R\$\s*)?([\d.,]+)', re.IGNORECASE)
        for linha in texto_pdf.splitlines():
            ll = linha.lower()
            if 'saldo total' in ll:
                continue
            m = _re_dia.search(linha)
            if m:
                v = _parse_valor_br_decimal(m.group(1))
                if v is not None:
                    data_m = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', linha)
                    data = ''
                    if data_m:
                        _MESES = {
                            'janeiro': '01', 'fevereiro': '02', 'março': '03', 'marco': '03',
                            'abril': '04', 'maio': '05', 'junho': '06',
                            'julho': '07', 'agosto': '08', 'setembro': '09',
                            'outubro': '10', 'novembro': '11', 'dezembro': '12',
                        }
                        dia = data_m.group(1).zfill(2)
                        mes = _MESES.get(data_m.group(2).lower(), '01')
                        ano = data_m.group(3)
                        data = f'{dia}/{mes}/{ano}'
                    saldos.append((data, v))
        return saldos


# ═══════════════════════════════════════════════════════════════════════
#  SICREDI
# ═══════════════════════════════════════════════════════════════════════

class SicrediVerifier(BankVerifier):
    """Verificador para extratos Sicredi."""

    _SALDO_KEYWORDS = BankVerifier._SALDO_KEYWORDS + [
        'aplic. financ', 'aplicação automática', 'aplicacao automatica',
        'total débitos', 'total debitos', 'total créditos', 'total creditos',
    ]

    @property
    def bank_name(self) -> str:
        return 'Sicredi'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        """Sicredi: 'Saldo do dia' ou 'Saldo final'."""
        saldos = []
        for linha in texto_pdf.splitlines():
            ll = linha.lower()
            if 'saldo do dia' in ll or 'saldo final' in ll:
                v = _ultimo_valor_br_decimal(linha)
                if v is not None:
                    data_m = re.search(r'(\d{2}/\d{2}/\d{4})', linha)
                    data = data_m.group(1) if data_m else ''
                    saldos.append((data, v))
        return saldos


# ═══════════════════════════════════════════════════════════════════════
#  STONE
# ═══════════════════════════════════════════════════════════════════════

class StoneVerifier(BankVerifier):
    """Verificador para extratos Stone."""

    _SALDO_KEYWORDS = BankVerifier._SALDO_KEYWORDS + [
        'contraparte', 'stone institui', 'stone pagamentos',
    ]

    @property
    def bank_name(self) -> str:
        return 'Stone'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        """Stone: saldo na última coluna de cada transação; sem saldo intermediário explícito."""
        return []


# ═══════════════════════════════════════════════════════════════════════
#  C6BANK
# ═══════════════════════════════════════════════════════════════════════

class C6BankVerifier(BankVerifier):
    """Verificador para extratos C6 Bank."""

    _SALDO_KEYWORDS = BankVerifier._SALDO_KEYWORDS + [
        'data lançamento', 'data lancamento', 'data contábil',
        'data contabil', 'sem lançamentos', 'sem lancamentos',
    ]

    @property
    def bank_name(self) -> str:
        return 'C6 Bank'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        """C6Bank: 'Saldo do dia DD/MM/YY R$ X,XX'."""
        saldos = []
        _re_c6 = re.compile(
            r'saldo\s+do\s+dia\s+(\d{2}/\d{2}/?\d{0,4})\s+R\$\s*([\d.,]+)',
            re.IGNORECASE
        )
        for linha in texto_pdf.splitlines():
            if '\u2022' in linha or '\u2192' in linha:
                continue
            m = _re_c6.search(linha)
            if m:
                v = _parse_valor_br_decimal(m.group(2))
                if v is not None:
                    saldos.append((m.group(1), v))
        return saldos


# ═══════════════════════════════════════════════════════════════════════
#  PAGBANK
# ═══════════════════════════════════════════════════════════════════════

class PagBankVerifier(BankVerifier):
    """Verificador para extratos PagBank."""

    @property
    def bank_name(self) -> str:
        return 'PagBank'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        """PagBank: 'DD/MM/YYYY Saldo do dia R$ X,XX'."""
        saldos = []
        _re_pgb = re.compile(
            r'(\d{2}/\d{2}/\d{4})\s+saldo\s+do\s+dia\s+R\$\s*([\d.,]+)',
            re.IGNORECASE
        )
        for linha in texto_pdf.splitlines():
            m = _re_pgb.search(linha)
            if m:
                v = _parse_valor_br_decimal(m.group(2))
                if v is not None:
                    saldos.append((m.group(1), v))
        return saldos


# ═══════════════════════════════════════════════════════════════════════
#  MERCADO PAGO
# ═══════════════════════════════════════════════════════════════════════

class MercadoPagoVerifier(BankVerifier):
    """Verificador para extratos Mercado Pago."""

    _SALDO_KEYWORDS = BankVerifier._SALDO_KEYWORDS + [
        'detalhe dos movimentos',
    ]

    @property
    def bank_name(self) -> str:
        return 'Mercado Pago'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        """Mercado Pago: sem saldos intermediários padronizados."""
        return []


# ═══════════════════════════════════════════════════════════════════════
#  CORA
# ═══════════════════════════════════════════════════════════════════════

class CoraVerifier(BankVerifier):
    """Verificador para extratos Cora."""

    _SALDO_KEYWORDS = BankVerifier._SALDO_KEYWORDS + [
        'extrato do período', 'extrato do periodo',
        'extrato gerado', 'cora scfi',
    ]

    @property
    def bank_name(self) -> str:
        return 'Cora'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        """Cora: 'DD/MM/YYYY Saldo do dia R$ X,XX'."""
        saldos = []
        _re_cora = re.compile(
            r'(\d{2}/\d{2}/\d{4})\s+saldo\s+do\s+dia\s+R\$\s*([\d.,]+)',
            re.IGNORECASE
        )
        for linha in texto_pdf.splitlines():
            m = _re_cora.search(linha)
            if m:
                v = _parse_valor_br_decimal(m.group(2))
                if v is not None:
                    saldos.append((m.group(1), v))
        return saldos


# ═══════════════════════════════════════════════════════════════════════
#  BS2
# ═══════════════════════════════════════════════════════════════════════

class BS2Verifier(BankVerifier):
    """Verificador para extratos BS2."""

    _SALDO_KEYWORDS = BankVerifier._SALDO_KEYWORDS + [
        'remuneração', 'remuneracao', 'aplic automática',
        'aplic automatica', 'bs2 banco',
    ]

    @property
    def bank_name(self) -> str:
        return 'BS2'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        """BS2: sem saldos intermediários padronizados."""
        return []


# ═══════════════════════════════════════════════════════════════════════
#  SUMUP
# ═══════════════════════════════════════════════════════════════════════

class SumUpVerifier(BankVerifier):
    """Verificador para extratos SumUp."""

    @property
    def bank_name(self) -> str:
        return 'SumUp'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        return []


# ═══════════════════════════════════════════════════════════════════════
#  XP EXTRATO
# ═══════════════════════════════════════════════════════════════════════

class XPExtratoVerifier(BankVerifier):
    """Verificador para extratos XP (conta corrente)."""

    @property
    def bank_name(self) -> str:
        return 'XP'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        return []


# ═══════════════════════════════════════════════════════════════════════
#  XP POSIÇÃO
# ═══════════════════════════════════════════════════════════════════════

class XPPosicaoVerifier(BankVerifier):
    """Verificador para extratos XP (posição consolidada)."""

    @property
    def bank_name(self) -> str:
        return 'XP Posicao'

    def extract_intermediate_balances(self, texto_pdf: str) -> List[Tuple[str, Decimal]]:
        return []


# ═══════════════════════════════════════════════════════════════════════
#  SANTANDER CONSOLIDADO
# ═══════════════════════════════════════════════════════════════════════

class SantanderConsolidadoVerifier(SantanderVerifier):
    """Verificador para extratos Santander Consolidado."""

    @property
    def bank_name(self) -> str:
        return 'Santander Consolidado'


# ═══════════════════════════════════════════════════════════════════════
#  SANTANDER EMPRESAS
# ═══════════════════════════════════════════════════════════════════════

class SantanderEmpresasVerifier(SantanderVerifier):
    """Verificador para Santander Internet Banking Empresarial."""

    @property
    def bank_name(self) -> str:
        return 'Santander Empresas'


# ═══════════════════════════════════════════════════════════════════════
#  SANTANDER EMPRESAS V1
# ═══════════════════════════════════════════════════════════════════════

class SantanderEmpresasV1Verifier(SantanderVerifier):
    """Verificador para Santander Empresas V1 (CREDITO/DEBITO R$)."""

    @property
    def bank_name(self) -> str:
        return 'Santander Empresas V1'


# ═══════════════════════════════════════════════════════════════════════
#  SANTANDER EMPRESAS V2
# ═══════════════════════════════════════════════════════════════════════

class SantanderEmpresasV2Verifier(SantanderVerifier):
    """Verificador para Santander Empresas V2 (Consolidado)."""

    @property
    def bank_name(self) -> str:
        return 'Santander Empresas V2'


# ═══════════════════════════════════════════════════════════════════════
#  BRADESCO NET EMPRESAS
# ═══════════════════════════════════════════════════════════════════════

class BradescoNetEmpresasVerifier(BradescoVerifier):
    """Verificador para Bradesco Net Empresas."""

    _SALDO_KEYWORDS = BradescoVerifier._SALDO_KEYWORDS + [
        'total disponível', 'total disponivel',
        'data da operação', 'data da operacao',
    ]

    @property
    def bank_name(self) -> str:
        return 'Bradesco Net Empresas'


# ═══════════════════════════════════════════════════════════════════════
#  ITAÚ N2
# ═══════════════════════════════════════════════════════════════════════

class ItauN2Verifier(ItauVerifier):
    """Verificador para Itaú N2 (formato ANTARTI.CO)."""

    @property
    def bank_name(self) -> str:
        return 'Itau N2'


# ═══════════════════════════════════════════════════════════════════════
#  INTER N2
# ═══════════════════════════════════════════════════════════════════════

class InterN2Verifier(InterVerifier):
    """Verificador para Inter N2."""

    @property
    def bank_name(self) -> str:
        return 'Inter N2'


# ═══════════════════════════════════════════════════════════════════════
#  ITAÚ EMPRESAS N2
# ═══════════════════════════════════════════════════════════════════════

class ItauEmpresasN2Verifier(ItauEmpresasVerifier):
    """Verificador para Itaú Empresas N2."""

    @property
    def bank_name(self) -> str:
        return 'Itau Empresas N2'


# ═══════════════════════════════════════════════════════════════════════
#  MAPEAMENTO banco_key -> Verificador
# ═══════════════════════════════════════════════════════════════════════

VERIFIERS: dict[str, type[BankVerifier]] = {
    'itau': ItauVerifier,
    'itau_empresas': ItauEmpresasVerifier,
    'bradesco': BradescoVerifier,
    'bradesco_empresas': BradescoVerifier,
    'bradesco_net_empresas': BradescoNetEmpresasVerifier,
    'santander': SantanderVerifier,
    'santander_empresas': SantanderEmpresasVerifier,
    'santander_consolidado': SantanderConsolidadoVerifier,
    'santander_empresas_v1': SantanderEmpresasV1Verifier,
    'santander_empresas_v2': SantanderEmpresasV2Verifier,
    'bb': BancoDoBrasilVerifier,
    'caixa': CaixaVerifier,
    'nubank': NubankVerifier,
    'inter': InterVerifier,
    'inter_n2': InterN2Verifier,
    'sicredi': SicrediVerifier,
    'stone': StoneVerifier,
    'c6bank': C6BankVerifier,
    'pagbank': PagBankVerifier,
    'mercado_pago': MercadoPagoVerifier,
    'cora': CoraVerifier,
    'bs2': BS2Verifier,
    'sumup': SumUpVerifier,
    'xp_extrato': XPExtratoVerifier,
    'xp_posicao': XPPosicaoVerifier,
    'itau_n2': ItauN2Verifier,
    'itau_empresas_n2': ItauEmpresasN2Verifier,
}
