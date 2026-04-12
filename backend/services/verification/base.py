"""
base.py — Classe base abstrata para verificadores contábeis de extratos bancários.

Define a interface padrão de verificação. Cada banco deve implementar
os métodos de extração de saldos intermediários e classificação de linhas.

Todos os cálculos financeiros usam Decimal (NUNCA float).
"""

import re
import logging
from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import List, Optional, Tuple

from .models import VerificationResult, DivergencePoint, TransactionRecord

logger = logging.getLogger(__name__)


def _to_decimal(value) -> Decimal:
    """Converte float/int/str para Decimal de forma segura."""
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    try:
        # Converte float para string primeiro para evitar imprecisão
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')


class BankVerifier(ABC):
    """
    Classe base abstrata para verificação contábil de extratos.

    Subclasses devem implementar:
      - extract_intermediate_balances(texto_pdf) -> lista de saldos intermediários
      - classify_line(line) -> 'TRANSACAO' | 'SALDO_INFORMATIVO' | 'IGNORAR'
      - bank_name -> propriedade com o nome do banco
    """

    # Padrões comuns de linhas de saldo que NÃO são transações.
    # Subclasses podem estender esta lista.
    _SALDO_KEYWORDS: List[str] = [
        'saldo anterior', 'saldo do dia', 'saldo final',
        'saldo total', 'saldo disponivel', 'saldo disponível',
        'saldo bloqueado', 'saldo em c/c', 'saldo em conta',
        'sdo anterior', 's.anterior', 'saldo inicial',
        'saldo aplic', 'saldo contábil', 'saldo contabil',
        'saldo parcial',
    ]

    @property
    @abstractmethod
    def bank_name(self) -> str:
        """Nome do banco para exibição."""
        ...

    @abstractmethod
    def extract_intermediate_balances(
        self, texto_pdf: str
    ) -> List[Tuple[str, Decimal]]:
        """
        Extrai saldos intermediários (saldo do dia, saldo parcial, etc.) do texto do PDF.

        Returns:
            Lista de tuplas (data_ou_posicao, valor_saldo) na ordem em que aparecem.
            Se não houver saldos intermediários, retorna lista vazia.
        """
        ...

    def classify_line(self, line: str) -> str:
        """
        Classifica uma linha do extrato.

        Returns:
            'TRANSACAO' | 'SALDO_INFORMATIVO' | 'IGNORAR'
        """
        if not line or not line.strip():
            return 'IGNORAR'

        line_lower = line.lower().strip()

        # Verifica se é linha de saldo informativo
        for keyword in self._SALDO_KEYWORDS:
            if keyword in line_lower:
                return 'SALDO_INFORMATIVO'

        return 'TRANSACAO'

    def _converter_transacoes(
        self, transacoes_parser: List[dict]
    ) -> List[TransactionRecord]:
        """
        Converte a lista de transações do parser (dicts com float)
        para TransactionRecords com Decimal.
        """
        records = []
        for idx, t in enumerate(transacoes_parser):
            tipo = t.get('tipo', '')
            # Ignora transações marcadas como 'ignorar' ou 'posicao'
            if tipo not in ('entrada', 'saida'):
                continue

            valor = _to_decimal(t.get('valor', 0))
            if valor <= 0:
                continue

            records.append(TransactionRecord(
                position=idx,
                date=t.get('data', ''),
                description=t.get('descricao', ''),
                value=valor,
                transaction_type=tipo,
                raw=t.get('raw', ''),
            ))
        return records

    def _calcular_saldo(
        self,
        saldo_inicial: Decimal,
        transacoes: List[TransactionRecord],
    ) -> Decimal:
        """
        Calcula o saldo final a partir do saldo inicial e das transações.

        Formula: saldo = saldo_inicial + sum(creditos) - sum(debitos)
        """
        saldo = saldo_inicial
        for t in transacoes:
            if t.transaction_type == 'entrada':
                saldo += t.value
            elif t.transaction_type == 'saida':
                saldo -= t.value
        return saldo

    def _validacao_progressiva(
        self,
        saldo_inicial: Decimal,
        transacoes: List[TransactionRecord],
        saldos_intermediarios: List[Tuple[str, Decimal]],
    ) -> List[DivergencePoint]:
        """
        Valida progressivamente: aplica transações na ordem e compara
        com cada saldo intermediário informado pelo banco.

        Estratégia: para cada saldo intermediário, acumula as transações
        até encontrar a data correspondente e compara.

        Returns:
            Lista de DivergencePoints onde houve divergência.
        """
        if not saldos_intermediarios:
            return []

        divergencias = []
        saldo_acumulado = saldo_inicial
        idx_transacao = 0

        for saldo_date, saldo_esperado in saldos_intermediarios:
            # Avança as transações até (e incluindo) a data do saldo intermediário
            while idx_transacao < len(transacoes):
                t = transacoes[idx_transacao]
                # Se a transação é da mesma data ou anterior ao saldo, inclui
                if self._data_menor_ou_igual(t.date, saldo_date):
                    if t.transaction_type == 'entrada':
                        saldo_acumulado += t.value
                    elif t.transaction_type == 'saida':
                        saldo_acumulado -= t.value
                    idx_transacao += 1
                else:
                    break

            # Compara saldo acumulado com saldo esperado
            diff = saldo_esperado - saldo_acumulado
            # Tolerância de R$ 0.01 para arredondamento
            if abs(diff) > Decimal('0.01'):
                # Transações próximas (contexto para investigação)
                start = max(0, idx_transacao - 5)
                end = min(len(transacoes), idx_transacao + 5)
                surrounding = transacoes[start:end]

                divergencias.append(DivergencePoint(
                    position=idx_transacao,
                    date=saldo_date,
                    expected_balance=saldo_esperado,
                    calculated_balance=saldo_acumulado,
                    difference=diff,
                    surrounding_transactions=surrounding,
                ))

        return divergencias

    @staticmethod
    def _data_menor_ou_igual(data_a: str, data_b: str) -> bool:
        """
        Compara duas datas no formato DD/MM/YYYY.
        Retorna True se data_a <= data_b.
        """
        try:
            da = data_a.split('/')
            db = data_b.split('/')
            if len(da) != 3 or len(db) != 3:
                return True  # Se formato inválido, não bloqueia
            a = (int(da[2]), int(da[1]), int(da[0]))
            b = (int(db[2]), int(db[1]), int(db[0]))
            return a <= b
        except (ValueError, IndexError):
            return True  # Não bloqueia em caso de erro

    def verify(
        self,
        transacoes_parser: List[dict],
        saldo_inicial: Optional[float],
        saldo_final: Optional[float],
        file_name: str = '',
        texto_pdf: str = '',
        excel_saldo: Optional[float] = None,
    ) -> VerificationResult:
        """
        Executa toda a verificação contábil de um extrato.

        Args:
            transacoes_parser: Lista de transações extraídas pelo parser (dicts com float).
            saldo_inicial: Saldo anterior informado pelo banco (float do extrator).
            saldo_final: Saldo final informado pelo banco (float do extrator).
            file_name: Nome do arquivo processado.
            texto_pdf: Texto completo do PDF (para extrair saldos intermediários).
            excel_saldo: Saldo final calculado na planilha Excel (opcional).

        Returns:
            VerificationResult com status e detalhes.
        """
        result = VerificationResult(
            bank_name=self.bank_name,
            file_name=file_name,
            status='SKIPPED',
        )

        # Se não temos saldo inicial E saldo final, não é possível verificar
        if saldo_inicial is None and saldo_final is None:
            result.skip_reason = 'Saldo inicial e final nao disponiveis para este banco/extrato'
            return result

        # Converte transações para Decimal
        transacoes = self._converter_transacoes(transacoes_parser)
        if not transacoes:
            result.skip_reason = 'Nenhuma transacao para verificar'
            return result

        # Converte saldos para Decimal
        dec_saldo_inicial = _to_decimal(saldo_inicial)
        dec_saldo_final = _to_decimal(saldo_final) if saldo_final is not None else None
        dec_excel_saldo = _to_decimal(excel_saldo) if excel_saldo is not None else None

        # Separa créditos e débitos
        creditos = [t for t in transacoes if t.transaction_type == 'entrada']
        debitos = [t for t in transacoes if t.transaction_type == 'saida']

        total_creditos = sum((t.value for t in creditos), Decimal('0'))
        total_debitos = sum((t.value for t in debitos), Decimal('0'))

        # Calcula saldo final
        saldo_calculado = dec_saldo_inicial + total_creditos - total_debitos

        # Preenche resultado
        result.opening_balance = dec_saldo_inicial
        result.calculated_closing_balance = saldo_calculado
        result.expected_closing_balance = dec_saldo_final
        result.excel_closing_balance = dec_excel_saldo
        result.total_credits = total_creditos
        result.total_debits = total_debitos
        result.transaction_count = len(transacoes)
        result.credit_count = len(creditos)
        result.debit_count = len(debitos)

        # Etapa C — Validação progressiva com saldos intermediários
        saldos_intermediarios = []
        if texto_pdf:
            try:
                saldos_intermediarios = self.extract_intermediate_balances(texto_pdf)
            except Exception as e:
                logger.warning(f'Erro ao extrair saldos intermediarios de {file_name}: {e}')

        divergencias_intermediarias = self._validacao_progressiva(
            dec_saldo_inicial, transacoes, saldos_intermediarios
        )

        # Etapa B — Validação do saldo final
        divergencias = list(divergencias_intermediarias)

        if dec_saldo_final is not None:
            diff_final = dec_saldo_final - saldo_calculado
            result.difference = diff_final

            if abs(diff_final) > Decimal('0.01'):
                divergencias.append(DivergencePoint(
                    position=len(transacoes),
                    date='FINAL',
                    expected_balance=dec_saldo_final,
                    calculated_balance=saldo_calculado,
                    difference=diff_final,
                    surrounding_transactions=transacoes[-5:] if transacoes else [],
                ))
        else:
            result.difference = Decimal('0')

        # Etapa D — Validação cruzada com Excel
        if dec_excel_saldo is not None and dec_saldo_final is not None:
            excel_diff = dec_excel_saldo - dec_saldo_final
            if abs(excel_diff) > Decimal('0.01'):
                logger.warning(
                    f'Divergencia Excel vs Extrato para {file_name}: '
                    f'Excel={dec_excel_saldo}, Extrato={dec_saldo_final}, Diff={excel_diff}'
                )

        # Define status
        result.divergence_points = divergencias
        if divergencias:
            result.status = 'DIVERGENT'
        else:
            result.status = 'OK'

        return result
