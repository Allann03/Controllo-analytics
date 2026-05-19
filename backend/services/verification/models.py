"""
models.py — Dataclasses padronizadas para resultados de verificação contábil.

Todos os valores monetários usam Decimal (NUNCA float) para evitar
erros de arredondamento em cálculos financeiros.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class TransactionRecord:
    """Representação de uma transação para fins de verificação."""
    position: int              # Índice/posição na lista original
    date: str                  # DD/MM/YYYY
    description: str
    value: Decimal             # Sempre positivo
    transaction_type: str      # 'entrada' | 'saida'
    raw: str = ''              # Linha bruta original


@dataclass
class DivergencePoint:
    """Ponto onde a verificação detectou divergência de saldo."""
    position: int                                  # Linha ou índice
    date: str                                      # Data do saldo intermediário
    expected_balance: Decimal                      # Saldo informado pelo banco
    calculated_balance: Decimal                    # Saldo calculado
    difference: Decimal                            # expected - calculated
    surrounding_transactions: List[TransactionRecord] = field(default_factory=list)


@dataclass
class VerificationResult:
    """Resultado completo da verificação contábil de um extrato."""
    bank_name: str
    file_name: str
    status: str                # 'OK' | 'DIVERGENT' | 'REPROCESSED_OK' | 'REPROCESSED_FAIL' | 'SKIPPED'
    opening_balance: Optional[Decimal] = None
    calculated_closing_balance: Optional[Decimal] = None
    expected_closing_balance: Optional[Decimal] = None
    excel_closing_balance: Optional[Decimal] = None
    total_credits: Decimal = Decimal('0')
    total_debits: Decimal = Decimal('0')
    transaction_count: int = 0
    credit_count: int = 0
    debit_count: int = 0
    difference: Decimal = Decimal('0')
    divergence_points: List[DivergencePoint] = field(default_factory=list)
    was_reprocessed: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    skip_reason: str = ''      # Motivo caso status == 'SKIPPED'

    def to_dict(self) -> dict:
        """Converte para dict serializável (Decimal -> str)."""
        def _dec(v: Optional[Decimal]) -> Optional[str]:
            return str(v) if v is not None else None

        return {
            'bank_name': self.bank_name,
            'file_name': self.file_name,
            'status': self.status,
            'opening_balance': _dec(self.opening_balance),
            'calculated_closing_balance': _dec(self.calculated_closing_balance),
            'expected_closing_balance': _dec(self.expected_closing_balance),
            'excel_closing_balance': _dec(self.excel_closing_balance),
            'total_credits': str(self.total_credits),
            'total_debits': str(self.total_debits),
            'transaction_count': self.transaction_count,
            'credit_count': self.credit_count,
            'debit_count': self.debit_count,
            'difference': str(self.difference),
            'divergence_points': [
                {
                    'position': dp.position,
                    'date': dp.date,
                    'expected_balance': str(dp.expected_balance),
                    'calculated_balance': str(dp.calculated_balance),
                    'difference': str(dp.difference),
                    'surrounding_transactions': [
                        {
                            'position': tr.position,
                            'date': tr.date,
                            'description': tr.description,
                            'value': str(tr.value),
                            'transaction_type': tr.transaction_type,
                        }
                        for tr in dp.surrounding_transactions
                    ],
                }
                for dp in self.divergence_points
            ],
            'was_reprocessed': self.was_reprocessed,
            'timestamp': self.timestamp.isoformat(),
            'skip_reason': self.skip_reason,
        }

    def format_message(self) -> str:
        """Formata mensagem legível para exibição na interface."""
        if self.status == 'OK':
            return (
                f"Verificacao contabil OK — {self.bank_name}\n"
                f"Transacoes: {self.transaction_count} | "
                f"Creditos: R$ {self.total_credits:,.2f} | "
                f"Debitos: R$ {self.total_debits:,.2f}"
            )

        if self.status == 'REPROCESSED_OK':
            return (
                f"Verificacao contabil OK (apos releitura) — {self.bank_name}\n"
                f"Transacoes: {self.transaction_count}"
            )

        if self.status == 'SKIPPED':
            return f"Verificacao ignorada — {self.bank_name}: {self.skip_reason}"

        # DIVERGENT ou REPROCESSED_FAIL
        lines = [
            f"DIVERGENCIA DETECTADA NA VERIFICACAO DO EXTRATO",
            f"",
            f"Banco: {self.bank_name}",
            f"Arquivo: {self.file_name}",
            f"",
            f"Resumo:",
            f"  Saldo Anterior (extrato): R$ {self.opening_balance or Decimal('0'):,.2f}",
            f"  Total de Creditos: R$ {self.total_credits:,.2f}",
            f"  Total de Debitos: R$ {self.total_debits:,.2f}",
            f"  Saldo Final Calculado: R$ {self.calculated_closing_balance or Decimal('0'):,.2f}",
            f"  Saldo Final do Extrato: R$ {self.expected_closing_balance or Decimal('0'):,.2f}",
        ]
        if self.excel_closing_balance is not None:
            lines.append(f"  Saldo Final da Planilha: R$ {self.excel_closing_balance:,.2f}")

        lines.append(f"")
        lines.append(f"Diferenca: R$ {self.difference:,.2f}")

        if self.divergence_points:
            dp = self.divergence_points[0]
            lines.extend([
                f"",
                f"Ponto da divergencia:",
                f"  Detectada na posicao {dp.position} (data: {dp.date})",
                f"  Saldo esperado: R$ {dp.expected_balance:,.2f}",
                f"  Saldo calculado: R$ {dp.calculated_balance:,.2f}",
            ])

        lines.extend([
            f"",
            f"Possiveis causas:",
            f"  - Transacao nao lida no trecho indicado",
            f"  - Linha de saldo computada como transacao",
            f"  - Valor lido incorretamente",
        ])

        return '\n'.join(lines)
