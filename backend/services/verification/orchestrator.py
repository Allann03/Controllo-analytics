"""
orchestrator.py — Orquestra a verificação contábil de extratos bancários.

Ponto de entrada: executar_verificacao()
Chamado APÓS o processamento e geração do Excel, envolvido em try/except
para NUNCA interferir no fluxo principal.
"""

import logging
import pdfplumber
from typing import Optional

from .models import VerificationResult
from .verifiers import VERIFIERS
from services.extrator_pdf import PARSERS

logger = logging.getLogger(__name__)


def _extrair_texto_pdf(pdf_path: str, password: str | None = None) -> str:
    """
    Extrai texto completo do PDF para análise de saldos intermediários.
    Retorna string vazia se falhar (não interfere no fluxo).
    """
    try:
        texto = ''
        with pdfplumber.open(pdf_path, password=password or '') as pdf:
            for pagina in pdf.pages:
                try:
                    texto += (pagina.extract_text() or '') + '\n'
                except Exception:
                    pass
        return texto
    except Exception as e:
        logger.warning(f'Erro ao extrair texto do PDF para verificacao: {e}')
        return ''


def _calcular_saldo_excel(transacoes: list) -> Optional[float]:
    """
    Calcula o saldo da planilha Excel a partir das transações.
    Reproduz a mesma lógica de gerador_excel.py sem modificá-lo.
    """
    if not transacoes:
        return None
    entradas = sum(t.get('valor', 0) for t in transacoes if t.get('tipo') == 'entrada')
    saidas = sum(t.get('valor', 0) for t in transacoes if t.get('tipo') == 'saida')
    return round(entradas - saidas, 2)


def executar_verificacao(
    banco_key: str,
    transacoes: list,
    saldo_inicial: Optional[float],
    saldo_final: Optional[float],
    file_name: str = '',
    pdf_path: str = '',
    password: str | None = None,
) -> VerificationResult:
    """
    Executa a verificação contábil de um extrato processado.

    Esta função é o ponto de entrada único para a camada de verificação.
    Ela seleciona o verificador correto para o banco, extrai saldos
    intermediários do PDF e executa a verificação completa.

    IMPORTANTE: Esta função NUNCA deve ser chamada sem try/except envolvendo-a.
    Se ocorrer qualquer erro interno, ela retorna um resultado SKIPPED.

    Args:
        banco_key: Identificador do banco (ex: 'itau', 'inter').
        transacoes: Lista de transações extraídas pelo parser.
        saldo_inicial: Saldo anterior extraído do PDF.
        saldo_final: Saldo final extraído do PDF.
        file_name: Nome do arquivo original (para relatório).
        pdf_path: Caminho do PDF (para extrair saldos intermediários).
        password: Senha do PDF (se protegido).

    Returns:
        VerificationResult com o resultado da verificação.
    """
    try:
        # Seleciona o verificador correto para o banco
        verifier_cls = VERIFIERS.get(banco_key)
        if not verifier_cls:
            return VerificationResult(
                bank_name=banco_key,
                file_name=file_name,
                status='SKIPPED',
                skip_reason=f'Verificador nao implementado para banco: {banco_key}',
            )

        verifier = verifier_cls()

        # Extrai texto do PDF para saldos intermediários
        texto_pdf = ''
        if pdf_path:
            texto_pdf = _extrair_texto_pdf(pdf_path, password)

        # Calcula saldo do Excel para validação cruzada
        excel_saldo = _calcular_saldo_excel(transacoes)

        # Executa verificação
        result = verifier.verify(
            transacoes_parser=transacoes,
            saldo_inicial=saldo_inicial,
            saldo_final=saldo_final,
            file_name=file_name,
            texto_pdf=texto_pdf,
            excel_saldo=excel_saldo,
        )

        # Se divergente, tenta releitura REAL (re-parseia o PDF)
        if result.status == 'DIVERGENT' and not pdf_path:
            # Sem PDF disponível para releitura — marca como falha
            result.status = 'REPROCESSED_FAIL'
            result.was_reprocessed = True
        elif result.status == 'DIVERGENT' and pdf_path:
            logger.info(
                f'Divergencia detectada para {file_name} ({banco_key}). '
                f'Diferenca: {result.difference}. Tentando releitura real...'
            )
            try:
                parser_cls = PARSERS.get(banco_key)
                if parser_cls:
                    parser = parser_cls(pdf_path, password=password)
                    transacoes_releitura = parser.extrair()
                    # Filtra tipo='ignorar' como faz extrator_pdf
                    transacoes_releitura = [
                        t for t in transacoes_releitura
                        if t.get('tipo') != 'ignorar'
                    ]

                    # Escolhe o conjunto com mais transações
                    transacoes_final = (
                        transacoes_releitura
                        if len(transacoes_releitura) > len(transacoes)
                        else transacoes
                    )

                    # Re-calcula saldo Excel com os dados escolhidos
                    excel_saldo_retry = _calcular_saldo_excel(transacoes_final)

                    # Re-verifica com os dados (potencialmente novos)
                    result_retry = verifier.verify(
                        transacoes_parser=transacoes_final,
                        saldo_inicial=saldo_inicial,
                        saldo_final=saldo_final,
                        file_name=file_name,
                        texto_pdf=texto_pdf,
                        excel_saldo=excel_saldo_retry,
                    )
                    result_retry.was_reprocessed = True

                    if result_retry.status == 'OK':
                        result_retry.status = 'REPROCESSED_OK'
                        logger.info(
                            f'Releitura real resolveu divergencia de {file_name} '
                            f'({len(transacoes)} -> {len(transacoes_final)} transacoes)'
                        )
                        return result_retry
                    else:
                        result.status = 'REPROCESSED_FAIL'
                        result.was_reprocessed = True
                else:
                    result.status = 'REPROCESSED_FAIL'
                    result.was_reprocessed = True
            except Exception as e:
                logger.warning(f'Erro na releitura real de {file_name}: {e}')
                result.status = 'REPROCESSED_FAIL'
                result.was_reprocessed = True

        # Log do resultado
        if result.status == 'OK':
            logger.info(
                f'Verificacao OK: {file_name} ({banco_key}) — '
                f'{result.transaction_count} transacoes, '
                f'creditos={result.total_credits}, debitos={result.total_debits}'
            )
        elif result.status in ('DIVERGENT', 'REPROCESSED_FAIL'):
            logger.warning(
                f'Verificacao DIVERGENTE: {file_name} ({banco_key}) — '
                f'Diferenca: {result.difference}'
            )

        return result

    except Exception as e:
        logger.error(f'Erro interno na verificacao de {file_name}: {e}', exc_info=True)
        return VerificationResult(
            bank_name=banco_key,
            file_name=file_name,
            status='SKIPPED',
            skip_reason=f'Erro interno: {str(e)}',
        )
