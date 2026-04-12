"""
sicredi.py – Parser de extrato do Sicredi.

Suporta dois formatos:
  1. Tabela pdfplumber: Data | Histórico | [Nº Doc |] Débito | Crédito | Saldo
     Colunas detectadas dinamicamente a partir do cabeçalho da tabela
     (ou pelo número de colunas das linhas de dados, como fallback).
  2. PDF escaneado (imagem): OCR via easyocr + pymupdf (fitz)
     Colunas detectadas por posição-x:
       Data (x<200) | Descrição (160<x<760) | Documento (730<x<920)
       Valor (900<x<1050) | Saldo (x>1020)

Filtros:
  - APLIC. FINANC. FUNDOS → aplicação automática, IGNORADA
  - Saldo anterior / Saldo do dia / Saldo final → IGNORADOS

Verificação cruzada:
  - Coluna Crédito preenchida → entrada
  - Coluna Débito preenchida → saída
  - Sem colunas separadas → palavras-chave da descrição
"""

import re
from decimal import Decimal, InvalidOperation
import pdfplumber
from .base import ParserBase


BANCO = 'Sicredi'

_IGNORAR = [
    # Aplicações automáticas — NUNCA são transações de caixa
    'aplic. financ.', 'aplic financ', 'aplicação financ', 'aplicacao financ',
    'aplicacao automatica', 'aplicação automática',
    # Saldos — várias variantes
    'saldo anterior', 'saldo do dia', 'saldo final', 'saldo inicial',
    'saldo atual', 'saldo disponível', 'saldo disponivel',
    's a l d o',  # versão espaçada (OCR)
    # Cabeçalhos de tabela
    'data', 'histórico', 'historico', 'débito', 'debito', 'crédito', 'credito',
    'documento', 'nº doc', 'nr doc', 'valor', 'saldo',
    # Totalizadores
    'total débitos', 'total creditos', 'total créditos', 'total debitos',
    'total do período', 'total do periodo',
    # Rodapés
    'página', 'pagina', 'continua',
]

_IGNORAR_OCR = [
    'aplic. financ.', 'aplic financ', 'aplicação financ', 'aplicacao financ',
    'saldo anterior', 'saldo do dia', 'saldo final', 'saldo',
    'data', 'histórico', 'historico', 'documento', 'valor (rs)', 'valor (r$)',
    'sicredi', 'associado:', 'cooperativa:', 'conta:', 'extrato', 'período',
    'periodo', 'lançamentos futuros', 'lancamentos futuros',
]

_ENTRADAS = [
    'recebimento pix', 'recebimento', 'credito', 'crédito',
    'resgate aplic', 'resg.aplic', 'resg aplic', 'resgaplic', 'resgate',
    'transferencia recebida', 'transferência recebida',
    'pix recebido', 'ted recebido', 'doc recebido',
    'pix cred', 'pix_cred', 'pix-cred',
]

_SAIDAS = [
    'deb.', 'debito', 'débito', 'pagamento', 'tarifa', 'taxa',
    'plano int capital', 'compras', 'saque', 'ted enviado', 'pix enviado',
    'transferência enviada', 'transferencia enviada',
    'pix deb', 'pix_deb', 'pix-deb',
    'débito automático', 'debito automatico',
    'debit', 'cheque', 'boleto', 'mensalidade', 'anuidade',
    'ted deb', 'doc deb', 'carne', 'carnê',
]

_RE_DATA = re.compile(r'^\d{2}/\d{2}/\d{4}$')
_RE_VALOR = re.compile(r'^-?[\d.,]+$')


def _normalizar_valor_ocr(texto: str) -> Decimal:
    """
    Converte valor extraído via OCR para Decimal com sinal preservado.
    Trata erros comuns: '5,606,70' → 5606.70, '1,015,58' → 1015.58.
    Retorna valor negativo se o texto começar com '-'.
    """
    if not texto:
        return Decimal('0')
    t = texto.strip().replace(' ', '')
    t = re.sub(r'R\$\s*', '', t)
    negativo = t.startswith('-')
    t = t.lstrip('-')
    n_virgulas = t.count(',')
    n_pontos = t.count('.')
    resultado = Decimal('0')
    if n_virgulas == 0 and n_pontos == 0:
        try:
            resultado = Decimal(t)
        except (InvalidOperation, ValueError):
            return Decimal('0')
    elif n_virgulas == 1 and n_pontos == 0:
        t = t.replace(',', '.')
        try:
            resultado = Decimal(t)
        except (InvalidOperation, ValueError):
            return Decimal('0')
    elif n_virgulas >= 1 and n_pontos >= 1:
        t = t.replace('.', '').replace(',', '.')
        try:
            resultado = Decimal(t)
        except (InvalidOperation, ValueError):
            return Decimal('0')
    elif n_virgulas >= 2:
        partes = t.rsplit(',', 1)
        inteiro = partes[0].replace(',', '').replace('.', '')
        decimal = partes[1]
        try:
            resultado = Decimal(f'{inteiro}.{decimal}')
        except (InvalidOperation, ValueError):
            return Decimal('0')
    return -resultado if negativo else resultado


def _parece_valor_monetario(s: str) -> bool:
    """
    Retorna True se a string parece ser um valor monetário brasileiro.
    Valores monetários têm vírgula (separador decimal BR) ou ponto decimal
    com no máximo 10 caracteres. Números de documento (inteiros sem vírgula)
    retornam False.
    """
    if not s or s in ('', '-', '0', '0,00'):
        return False
    s_clean = s.strip().replace('-', '').replace(' ', '')
    # Deve ter vírgula (separador decimal BR) para ser valor monetário
    return ',' in s_clean or ('.' in s_clean and len(s_clean) <= 10)


class ParserSicredi(ParserBase):
    """Parser para extratos do Sicredi (tabela pdfplumber com fallback OCR)."""

    def extrair(self) -> list[dict]:
        """Extrai transações do extrato Sicredi."""
        transacoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or "") as pdf:
            tem_texto = False
            for pagina in pdf.pages:
                texto = pagina.extract_text() or ''
                if texto.strip():
                    tem_texto = True
                    break

            if tem_texto:
                transacoes = self._extrair_tabela(pdf)
            else:
                transacoes = self._extrair_ocr()

        # Tripla verificação: estrutura + data + deduplicação
        return self._post_processar(transacoes)

    # ------------------------------------------------------------------ #
    # Extração via tabela pdfplumber                                      #
    # ------------------------------------------------------------------ #

    def _extrair_tabela(self, pdf) -> list[dict]:
        transacoes: list[dict] = []
        for num, pagina in enumerate(pdf.pages, start=1):
            try:
                tabelas = pagina.extract_tables()
                for tabela in tabelas:
                    # Detecta posição das colunas Débito e Crédito nesta tabela
                    col_debito, col_credito = self._detectar_colunas(tabela)
                    for linha in tabela:
                        t = self._processar_linha_tabela(linha, col_debito, col_credito)
                        if t:
                            transacoes.append(t)
            except Exception as e:
                self.avisos.append(f'Sicredi: erro na página {num}: {e}')
        return transacoes

    def _detectar_colunas(self, tabela: list) -> tuple[int, int]:
        """
        Detecta os índices das colunas Débito e Crédito a partir da linha
        de cabeçalho da tabela. Retorna (col_debito, col_credito).

        Estratégia:
          1. Procura linha que contenha simultaneamente 'débito' e 'crédito'
             e usa os índices dessas células.
          2. Fallback: inspeciona o número de colunas da primeira linha de
             dados com data válida.
             - 6 colunas: Data | Histórico | Nº Doc | Débito | Crédito | Saldo → (3, 4)
             - 5 colunas: Data | Histórico | Débito | Crédito | Saldo     → (2, 3)
             - outro:     assume (2, 3)
        """
        # Passo 1: varredura pelo cabeçalho
        for linha in tabela:
            if not linha:
                continue
            cells = [str(c or '').lower().strip() for c in linha]
            has_debito = any('débit' in c or 'debit' in c for c in cells)
            has_credito = any('crédit' in c or 'credit' in c for c in cells)
            if has_debito and has_credito:
                col_deb = next(
                    (i for i, c in enumerate(cells) if 'débit' in c or 'debit' in c), 2
                )
                col_cred = next(
                    (i for i, c in enumerate(cells) if 'crédit' in c or 'credit' in c), 3
                )
                return col_deb, col_cred

        # Passo 2: fallback por contagem de colunas em linha de dados
        for linha in tabela:
            if not linha or len(linha) < 3:
                continue
            data_raw = str(linha[0] or '').strip()
            if re.match(r'\d{2}/\d{2}/\d{4}', data_raw):
                n = len(linha)
                if n >= 6:
                    # Data | Histórico | Nº Doc | Débito | Crédito | Saldo
                    return 3, 4
                elif n == 5:
                    # Data | Histórico | Débito | Crédito | Saldo
                    return 2, 3
                else:
                    return 2, 3

        return 2, 3

    def _processar_linha_tabela(
        self, linha: list, col_debito: int = 2, col_credito: int = 3
    ) -> dict | None:
        if not linha or len(linha) < 3:
            return None

        data_raw = str(linha[0] or '').strip()
        desc_raw = str(linha[1] or '').strip() if len(linha) > 1 else ''

        if not data_raw or not desc_raw:
            return None

        desc_lower = desc_raw.lower()
        data_lower = data_raw.lower()

        # Ignora cabeçalhos pela coluna data
        if any(x in data_lower for x in ['data', 'lançamento', 'lancamento']):
            return None
        # Ignora linhas de saldo e cabeçalhos pela descrição
        if any(x in desc_lower for x in _IGNORAR):
            return None
        # Verifica se tem dígitos na data (evita processar linhas de texto)
        if not any(c.isdigit() for c in data_raw):
            return None

        # Extrai débito e crédito usando índices detectados dinamicamente
        debito_raw = (
            str(linha[col_debito] or '').strip() if len(linha) > col_debito else ''
        )
        credito_raw = (
            str(linha[col_credito] or '').strip() if len(linha) > col_credito else ''
        )

        tem_credito = _parece_valor_monetario(credito_raw)
        tem_debito = _parece_valor_monetario(debito_raw)

        # ── Verificação 1: tipo por coluna (crédito/débito separados) ─────
        if tem_credito and not tem_debito:
            tipo = 'entrada'
            valor = self._normalizar_valor(credito_raw)

        elif tem_debito and not tem_credito:
            # Coluna débito com sinal negativo explícito → saída com certeza
            if debito_raw.lstrip().startswith('-'):
                tipo = 'saida'
            else:
                # Coluna débito padrão (quase sempre saída) com verificação cruzada
                tipo = self._verificar_tipo_cruzado(
                    tipo_por_sinal='saida',
                    descricao=desc_raw,
                    palavras_entrada=_ENTRADAS,
                    palavras_saida=_SAIDAS,
                )
            valor = self._normalizar_valor(debito_raw)

        elif tem_debito and tem_credito:
            # Ambos preenchidos (raro): usa palavras-chave e seleciona o valor correto
            v_deb = self._normalizar_valor(debito_raw)
            v_cred = self._normalizar_valor(credito_raw)
            tipo = self._verificar_tipo_cruzado(
                tipo_por_sinal='',
                descricao=desc_raw,
                palavras_entrada=_ENTRADAS,
                palavras_saida=_SAIDAS,
            )
            valor = v_deb if tipo == 'saida' else v_cred

        else:
            # Nenhum valor encontrado nas colunas esperadas — tenta colunas
            # adjacentes como fallback para layouts não mapeados.
            # Ignora a última coluna (provavelmente saldo).
            valor_raw = ''
            for i in range(2, len(linha) - 1):
                c = str(linha[i] or '').strip()
                if _parece_valor_monetario(c):
                    valor_raw = c
                    break
            if not valor_raw:
                return None
            tipo_por_sinal = 'saida' if valor_raw.lstrip().startswith('-') else ''
            tipo = self._verificar_tipo_cruzado(
                tipo_por_sinal=tipo_por_sinal,
                descricao=desc_raw,
                palavras_entrada=_ENTRADAS,
                palavras_saida=_SAIDAS,
            )
            valor = self._normalizar_valor(valor_raw)

        # ── Verificação 2: valor > 0 ──────────────────────────────────────
        if valor == 0.0:
            return None

        # Sanity check: valores acima de 10 milhões são suspeitos (podem ser saldo)
        if valor > 10_000_000:
            self.avisos.append(
                f'Sicredi: valor suspeito R$ {valor:,.2f} — '
                f'{desc_raw[:40]} (verifique se não é saldo)'
            )

        data = self._normalizar_data(data_raw)

        return self._transacao(
            data=data,
            descricao=desc_raw,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw='|'.join(str(c) for c in linha),
        )

    # ------------------------------------------------------------------ #
    # Extração via OCR (PDF escaneado)                                    #
    # ------------------------------------------------------------------ #

    def _extrair_ocr(self) -> list[dict]:
        """Extrai transações via OCR usando easyocr + pymupdf."""
        try:
            import fitz
            import numpy as np
        except ImportError:
            self.avisos.append(
                'Sicredi: pymupdf não instalado. Instale: pip install pymupdf'
            )
            return []

        try:
            import easyocr
        except ImportError:
            self.avisos.append(
                'Sicredi: easyocr não instalado. Instale: pip install easyocr'
            )
            return []

        transacoes: list[dict] = []
        try:
            reader = easyocr.Reader(['pt'], gpu=False, verbose=False)
        except Exception as e:
            self.avisos.append(f'Sicredi OCR: erro ao iniciar reader: {e}')
            return []

        try:
            doc = fitz.open(self.pdf_path)
        except Exception as e:
            self.avisos.append(f'Sicredi OCR: erro ao abrir PDF: {e}')
            return []

        for num_pag, page in enumerate(doc, start=1):
            try:
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                img = np.frombuffer(
                    pix.samples, dtype=np.uint8
                ).reshape(pix.height, pix.width, pix.n)

                resultados = reader.readtext(
                    img, detail=1, paragraph=False,
                    min_size=8, contrast_ths=0.1
                )

                itens = [
                    (bbox, text.strip(), conf)
                    for bbox, text, conf in resultados
                    if conf >= 0.3 and text.strip()
                ]

                linhas_por_y = self._agrupar_por_y(itens, tolerancia=12)

                for linha_itens in linhas_por_y:
                    t = self._processar_linha_ocr(linha_itens)
                    if t:
                        transacoes.append(t)

            except Exception as e:
                self.avisos.append(f'Sicredi OCR: erro na página {num_pag}: {e}')

        doc.close()

        if not transacoes:
            self.avisos.append(
                'Sicredi OCR: nenhuma transação encontrada. '
                'Verifique a qualidade do PDF.'
            )

        return transacoes

    def _agrupar_por_y(self, itens: list, tolerancia: int = 12) -> list[list]:
        if not itens:
            return []
        pontos = []
        for bbox, text, conf in itens:
            y_top = bbox[0][1]
            x_left = bbox[0][0]
            pontos.append((y_top, x_left, text))
        pontos.sort(key=lambda p: p[0])
        grupos: list[list[tuple]] = []
        grupo_atual: list[tuple] = []
        y_ref = None
        for y, x, text in pontos:
            if y_ref is None or abs(y - y_ref) <= tolerancia:
                grupo_atual.append((x, text))
                if y_ref is None:
                    y_ref = y
            else:
                if grupo_atual:
                    grupos.append(sorted(grupo_atual, key=lambda p: p[0]))
                grupo_atual = [(x, text)]
                y_ref = y
        if grupo_atual:
            grupos.append(sorted(grupo_atual, key=lambda p: p[0]))
        return grupos

    def _processar_linha_ocr(self, linha_itens: list[tuple]) -> dict | None:
        """Processa uma linha de itens OCR (lista de (x, texto))."""
        data_str = ''
        desc_parts: list[str] = []
        valor_str = ''

        for x, texto in linha_itens:
            texto_low = texto.lower()

            if any(ig in texto_low for ig in _IGNORAR_OCR):
                return None

            if x < 130:
                if _RE_DATA.match(texto):
                    data_str = texto
            elif 130 <= x < 720:
                desc_parts.append(texto)
            elif 720 <= x < 905:
                pass  # coluna documento — ignorado
            elif 905 <= x < 990:
                if not valor_str and _RE_VALOR.match(texto):
                    valor_str = texto
            # Saldo (x ≥ 990) — ignorado

        if not data_str:
            return None

        desc_raw = ' '.join(desc_parts).strip()
        if not desc_raw:
            return None

        desc_lower = desc_raw.lower()

        if any(ig in desc_lower for ig in _IGNORAR):
            return None

        valor_signed = _normalizar_valor_ocr(valor_str)
        if valor_signed == 0.0:
            return None

        # Usa o sinal para ajudar na classificação (negativo = saída com certeza)
        tipo_por_sinal = 'saida' if valor_signed < 0 else ''
        valor = abs(valor_signed)

        tipo = self._verificar_tipo_cruzado(
            tipo_por_sinal=tipo_por_sinal,
            descricao=desc_raw,
            palavras_entrada=_ENTRADAS,
            palavras_saida=_SAIDAS,
        )

        data = self._normalizar_data(data_str)

        return self._transacao(
            data=data,
            descricao=desc_raw,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=' | '.join(t for _, t in linha_itens),
        )
