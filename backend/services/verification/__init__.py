"""
verification — Camada de verificação contábil de extratos bancários.

Roda APÓS o processamento e geração do Excel, sem interferir no fluxo existente.
Todos os cálculos usam Decimal para precisão financeira.
"""

from .models import VerificationResult, DivergencePoint, TransactionRecord
from .orchestrator import executar_verificacao

__all__ = [
    'VerificationResult',
    'DivergencePoint',
    'TransactionRecord',
    'executar_verificacao',
]
