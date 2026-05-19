"""
nubank.py – Parser de extrato do Nubank (conta corrente PJ/PF).

Formato real do PDF (extraído por pdfplumber, colunas mescladas por linha):
  "DD MMM AAAA Total de entradas + X,XX"   ← data + seção (mesclados)
  "Tipo de Transação Contraparte Info Valor" ← tudo em 1 linha, valor ao final
  "(NNN) Agência: X Conta: Y"               ← detalhe Pix, linha de continuação
  "Total de saídas - X,XX"                  ← nova seção

Tripla verificação de tipo (entrada/saída):
  1. Sinal explícito (+/-) no valor — autoritário
  2. Seção atual (Total de entradas / Total de saídas) — muito confiável
  3. Palavras-chave da descrição — fallback

Filtros:
  - Linhas de detalhe bancário (Agência/Conta/conta n.) → ignoradas
  - Totais/resumos/saldos do dia → ignorados
  - Rodapé Nubank → ignorado
"""

import re
from decimal import Decimal, InvalidOperation
import pdfplumber
from .base import ParserBase


BANCO = 'Nubank'

_MESES = {
    'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
    'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
    'set': '09', 'out': '10', 'nov': '11', 'dez': '12',
    'jan.': '01', 'fev.': '02', 'mar.': '03', 'abr.': '04',
    'mai.': '05', 'jun.': '06', 'jul.': '07', 'ago.': '08',
    'set.': '09', 'out.': '10', 'nov.': '11', 'dez.': '12',
}

# Data isolada: "01 jan 2025"
_RE_DATA_DIA = re.compile(
    r'^(\d{1,2})\s+(?:de\s+)?([a-zA-Z]{3}\.?)\s+(?:de\s+)?(\d{4})\s*$',
    re.IGNORECASE
)
# Data no início da linha (com mais texto depois): "01 DEZ 2023 Total de entradas..."
_RE_DATA_DIA_PREFIX = re.compile(
    r'^(\d{1,2})\s+(?:de\s+)?([a-zA-Z]{3}\.?)\s+(?:de\s+)?(\d{4})',
    re.IGNORECASE
)

# Valor monetário BR puro na linha (somente valor): X,XX ou X.XXX,XX
_RE_VALOR_LINHA = re.compile(
    r'^([+\-\u2212\u2013])?\s*(?:R\$\s*)?((?:\d{1,3}\.)*\d{1,3},\d{2})\s*$'
)

# Linha com valor ao final: "Descrição Valor" (1+ espaços antes do valor)
# ← formato real do Nubank: valor fica na última coluna, separado por 1 espaço
_RE_VALOR_INLINE = re.compile(
    r'^(.+?)\s+([+\-\u2212\u2013]?\s*(?:R\$\s*)?(?:\d{1,3}\.)*\d{1,3},\d{2})\s*$'
)

# Linha de tabela com data: DD/MM/AAAA + descrição + valor
_RE_TABELA = re.compile(
    r'^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([+\-\u2212\u2013]?\s*(?:R\$\s*)?(?:\d{1,3}\.)*\d{1,3},\d{2})\s*$'
)

_RE_ANO = re.compile(r'\b(20\d{2})\b')

# Marcadores de detalhe bancário que aparecem fundidos com a linha de transação
# Ex: "Transfer...6,00(0237) Agência: 2458 Conta: 503643-7"
_RE_DETALHE_MARCADOR = re.compile(r'\(\d{3,4}\)|Agência:|Ag\.:', re.IGNORECASE)

# Número de conta bancária: "503643-7", "33409090-7", "1544919700-0"
_RE_NUMERO_CONTA = re.compile(r'^\d+[-]\d+\s*$')

_CABECALHOS_TABELA = ['data', 'descrição', 'descricao', 'valor']

# Linhas que encerram buffer sem criar transação (saldos, resumos)
_IGNORAR_FECHA_BUFFER = [
    'emitido em',
    'gerado em',
    'extrato de conta',
    'saldo do dia',
    'saldo anterior',
    'saldo inicial',
    'saldo final',
    'saldo disponível',
    'saldo disponivel',
    'saldo liquido',
    'saldo líquido',
    'rendimento líquido',
    'rendimento liquido',
    'movimentações',
    'movimentacoes',
]

# Linhas completamente ignoradas (rodapé, cabeçalho repetido)
_IGNORAR_SKIP = [
    'período:', 'periodo:',
    'transações no período',
    'transacoes no periodo',
    'tem alguma dúvida',
    'caso a solução',
    'atendimento 24h',
    'atendimento das',
    'mande uma mensagem',
    'nu financeira',
    'nu pagamentos s.a',
    'cnpj:',
    'extrato gerado',
    'disponíveis em nubank',
    'disponiveis em nubank',
    'valores em r$',
    'ouvidoria em 0800',
]

_ENTRADAS_KW = [
    'transferência recebida', 'transferencia recebida',
    'pix recebido', 'ted recebida', 'ted recebido',
    'crédito recebido', 'credito recebido',
    'depósito recebido', 'deposito recebido',
    'devolução recebida', 'devolucao recebida',
    'valor adicionado',
    'estorno',
    'recebido', 'recebida',
]

_SAIDAS_KW = [
    'transferência enviada', 'transferencia enviada',
    'pix enviado', 'compra no débito', 'compra no debito',
    'compra no crédito', 'compra no credito',
    'pagamento de fatura', 'pagamento de boleto',
    'resgate de empréstimo', 'resgate de emprestimo',
    'enviado', 'enviada',
    'pagamento', 'débito', 'debito',
    'tarifa', 'taxa', 'saque',
    'simples nacional',
]


def _parse_data_abrev(dia: str, mes_abrev: str, ano: str) -> str:
    mes_num = _MESES.get(mes_abrev.lower().rstrip('.'), '00')
    return f'{dia.zfill(2)}/{mes_num}/{ano}'


def _normalizar_unicode(s: str) -> str:
    return (
        s.replace('\u00a0', ' ')
         .replace('\u2212', '-')
         .replace('\u2013', '-')
         .replace('\u2014', '-')
         .strip()
    )


def _parse_valor_str(valor_str: str) -> tuple[Decimal, str]:
    """Extrai (valor_decimal, sinal) de string como '- R$ 1.234,56' ou '6,00'."""
    valor_str = _normalizar_unicode(valor_str)

    sinal = ''
    if valor_str.startswith('+'):
        sinal = 'entrada'
        valor_str = valor_str[1:].strip()
    elif valor_str.startswith('-'):
        sinal = 'saida'
        valor_str = valor_str[1:].strip()

    valor_str = re.sub(r'R\$\s*', '', valor_str).strip().replace(' ', '')
    if ',' in valor_str:
        valor_str = valor_str.replace('.', '').replace(',', '.')
    try:
        return abs(Decimal(valor_str)), sinal
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0'), sinal


class ParserNubank(ParserBase):
    """
    Parser para extratos Nubank (conta corrente PJ/PF).

    O PDF tem layout 3 colunas (tipo | contraparte | valor) que pdfplumber
    mescla em uma linha por transação:
        "Compra no débito L A Drogaria 13,49"
    Linhas de continuação de Pix (agência, conta, banco) são detectadas e
    descartadas para não poluir as descrições.

    Verificação tripla:
      1. Sinal explícito (+/-) → autoritário
      2. Seção do extrato (Total de entradas / Total de saídas) → confiável
      3. Palavras-chave da descrição → fallback
    """

    def extrair(self) -> list[dict]:
        transacoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or "") as pdf:
            ano_ref = None
            for p in pdf.pages[:3]:
                t = p.extract_text() or ''
                m = _RE_ANO.search(t)
                if m:
                    ano_ref = int(m.group(1))
                    break

            # Tenta tabelas estruturadas; fallback para texto
            tem_tabela = self._detectar_tabelas(pdf)
            if tem_tabela:
                transacoes = self._extrair_tabelas(pdf, ano_ref)
                if not transacoes:
                    transacoes = self._extrair_texto(pdf, ano_ref)
            else:
                transacoes = self._extrair_texto(pdf, ano_ref)

        return self._post_processar(transacoes)

    # ── Saldos intermediários para verificação progressiva ─────────────────────

    def _extrair_saldos_intermediarios(self) -> list[dict]:
        """Extrai 'Saldo do dia X.XXX,XX' do extrato Nubank."""
        saldos: list[dict] = []
        re_saldo_dia = re.compile(
            r'Saldo\s+do\s+dia\s+((?:\d{1,3}\.)*\d{1,3},\d{2})',
            re.IGNORECASE
        )
        try:
            with pdfplumber.open(self.pdf_path, password=self.password or "") as pdf:
                data_atual = None
                for pagina in pdf.pages:
                    texto = pagina.extract_text() or ''
                    for linha in texto.split('\n'):
                        stripped = linha.strip()
                        # Detectar data (isolada OU com prefix)
                        m_data = _RE_DATA_DIA.match(stripped) or _RE_DATA_DIA_PREFIX.match(stripped)
                        if m_data:
                            dia, mes_str, ano = m_data.group(1), m_data.group(2).lower().rstrip('.') + '.', m_data.group(3)
                            num_mes = _MESES.get(mes_str, '')
                            if num_mes:
                                data_atual = f"{int(dia):02d}/{num_mes}/{ano}"
                        # Detectar saldo do dia (pode estar na mesma linha ou em outra)
                        m_saldo = re_saldo_dia.search(linha)
                        if m_saldo and data_atual:
                            valor = self._normalizar_valor(m_saldo.group(1))
                            if valor > 0 or m_saldo.group(1).strip() == '0,00':
                                saldos.append({'data': data_atual, 'saldo': valor})
        except Exception:
            pass  # Verificação é informativa, nunca bloqueia
        return saldos

    # ── Detecção de formato ────────────────────────────────────────────────────

    def _detectar_tabelas(self, pdf) -> bool:
        for pagina in pdf.pages:
            for tab in (pagina.extract_tables() or []):
                for row in tab:
                    if row and any(c for c in row if c and str(c).strip()):
                        return True
        return False

    # ── Extração por tabelas ───────────────────────────────────────────────────

    def _extrair_tabelas(self, pdf, ano_ref: int | None) -> list[dict]:
        transacoes: list[dict] = []
        for num, pagina in enumerate(pdf.pages, start=1):
            try:
                for tabela in (pagina.extract_tables() or []):
                    for linha in tabela:
                        t = self._processar_linha_tabela(linha, ano_ref)
                        if t:
                            transacoes.append(t)
            except Exception as e:
                self.avisos.append(f'Nubank tabela página {num}: {e}')
        return transacoes

    def _processar_linha_tabela(self, linha: list, ano_ref: int | None) -> dict | None:
        cols = [_normalizar_unicode(str(c or '')) for c in linha]
        if not any(cols):
            return None

        data_raw = ''
        if re.match(r'^\d{2}/\d{2}/\d{4}$', cols[0]):
            data_raw, resto = cols[0], cols[1:]
        elif re.match(r'^\d{2}/\d{2}/\d{2}$', cols[0]):
            data_raw, resto = cols[0], cols[1:]
        else:
            m_d = re.match(r'^(\d{1,2})\s+([a-zA-Z]{3}\.?)\s+(\d{4})$', cols[0], re.IGNORECASE)
            if m_d:
                data_raw = _parse_data_abrev(m_d.group(1), m_d.group(2), m_d.group(3))
                resto = cols[1:]
            else:
                return None

        if not resto:
            return None

        valor_str, desc_parts = '', []
        for i, c in enumerate(resto):
            c_sem = c.replace(' ', '')
            if re.search(r'R\$\s*[\d.,]+', c) or re.match(r'^[+\-]?\s*(?:\d{1,3}\.)*\d{1,3},\d{2}$', c_sem):
                valor_str = c
                desc_parts = resto[:i]
                break
        else:
            return None

        desc_raw = ' '.join(desc_parts).strip() or ' '.join(resto[:-1]).strip()
        if desc_raw.lower() in _CABECALHOS_TABELA:
            return None

        valor, sinal = _parse_valor_str(valor_str)
        if valor == 0.0:
            return None

        tipo = self._determinar_tipo(sinal, desc_raw, '')
        data = self._normalizar_data(data_raw, ano_referencia=ano_ref)
        return self._transacao(
            data=data, descricao=desc_raw, valor=valor,
            tipo=tipo, banco=BANCO, raw='|'.join(str(c) for c in linha),
        )

    # ── Extração por texto (formato real Nubank) ──────────────────────────────

    def _extrair_texto(self, pdf, ano_ref: int | None) -> list[dict]:
        """
        Extrai transações linha a linha.

        A cada linha:
          1. Verifica se é data, seção, detalhe bancário ou ruído → trata ou descarta
          2. Tenta extrair transação inline (valor ao final da linha) ← caso mais comum
          3. Tenta extrair como linha de valor puro (valor isolado)
          4. Acumula no buffer se for descrição parcial (fallback)
        """
        transacoes: list[dict] = []
        data_atual = ''
        secao_atual = ''   # 'entrada' | 'saida' | ''
        desc_buffer: list[str] = []

        def _flush():
            nonlocal desc_buffer
            if desc_buffer and data_atual:
                t = self._processar_buffer(desc_buffer, data_atual, secao_atual)
                if t:
                    transacoes.append(t)
            desc_buffer = []

        for num, pagina in enumerate(pdf.pages, start=1):
            try:
                texto = pagina.extract_text() or ''
                for linha in texto.splitlines():
                    linha_norm = _normalizar_unicode(linha)
                    if not linha_norm:
                        _flush()
                        continue

                    linha_lower = linha_norm.lower()

                    # ── Rodapé / cabeçalho repetido → descarta completamente ──
                    if any(x in linha_lower for x in _IGNORAR_SKIP):
                        continue

                    # ── Cabeçalhos de tabela → descarta ──────────────────────
                    if linha_norm.strip().lower() in _CABECALHOS_TABELA:
                        continue

                    # ── Data isolada: "01 dez 2023" ───────────────────────────
                    m_data = _RE_DATA_DIA.match(linha_norm)
                    if m_data:
                        _flush()
                        data_atual = _parse_data_abrev(
                            m_data.group(1), m_data.group(2), m_data.group(3)
                        )
                        secao_atual = ''
                        continue

                    # ── Data fundida com seção: "01 DEZ 2023 Total de entradas..." ──
                    m_pfx = _RE_DATA_DIA_PREFIX.match(linha_norm)
                    if m_pfx and m_pfx.group(2).lower().rstrip('.') in _MESES:
                        _flush()
                        data_atual = _parse_data_abrev(
                            m_pfx.group(1), m_pfx.group(2), m_pfx.group(3)
                        )
                        resto = linha_norm[m_pfx.end():].lower()
                        if 'total de entradas' in resto or 'total de entrada' in resto:
                            secao_atual = 'entrada'
                        elif 'total de saídas' in resto or 'total de saidas' in resto:
                            secao_atual = 'saida'
                        else:
                            secao_atual = ''
                        continue

                    # ── Cabeçalho de seção isolado ────────────────────────────
                    if 'total de entradas' in linha_lower or 'total de entrada' in linha_lower:
                        _flush()
                        secao_atual = 'entrada'
                        continue

                    if 'total de saídas' in linha_lower or 'total de saidas' in linha_lower:
                        _flush()
                        secao_atual = 'saida'
                        continue

                    # ── Saldos e resumos → fecha buffer sem criar transação ───
                    if any(x in linha_lower for x in _IGNORAR_FECHA_BUFFER):
                        _flush()
                        continue

                    # ── Linha de detalhe bancário Pix → descarta ─────────────
                    # Antes de descartar, verifica se a linha é uma fusão de
                    # pdfplumber: "Transfer...6,00(0237) Agência: 2458 Conta: ..."
                    # Nesse caso, extrai o prefixo com valor antes do marcador.
                    if self._e_detalhe_bancario(linha_norm, linha_lower):
                        prefixo = self._prefixo_antes_detalhe(linha_norm)
                        if prefixo and data_atual:
                            m_pre = _RE_VALOR_INLINE.match(prefixo)
                            if m_pre and re.search(r'[a-zA-ZÀ-ÿ]', m_pre.group(1)):
                                valor, sinal = _parse_valor_str(m_pre.group(2))
                                if valor > 0:
                                    desc_buffer = []
                                    tipo = self._determinar_tipo(sinal, m_pre.group(1).strip(), secao_atual)
                                    transacoes.append(self._transacao(
                                        data=data_atual, descricao=m_pre.group(1).strip(),
                                        valor=valor, tipo=tipo, banco=BANCO, raw=linha_norm,
                                    ))
                        continue

                    # ── Linha DD/MM/AAAA inline (formato tabela no texto) ─────
                    m_tab = _RE_TABELA.match(linha_norm)
                    if m_tab:
                        _flush()
                        data_atual = self._normalizar_data(
                            m_tab.group(1), ano_referencia=ano_ref
                        )
                        desc_raw = m_tab.group(2).strip()
                        valor_str = m_tab.group(3)
                        valor, sinal = _parse_valor_str(valor_str)
                        if valor > 0 and desc_raw:
                            tipo = self._determinar_tipo(sinal, desc_raw, secao_atual)
                            transacoes.append(self._transacao(
                                data=data_atual, descricao=desc_raw,
                                valor=valor, tipo=tipo, banco=BANCO, raw=linha_norm,
                            ))
                        continue

                    # ── Valor puro (linha só com número) → fecha buffer ───────
                    m_val = _RE_VALOR_LINHA.match(linha_norm)
                    if m_val:
                        sinal_char = m_val.group(1) or ''
                        valor_raw = m_val.group(2)
                        valor, _ = _parse_valor_str(sinal_char + valor_raw)
                        desc_raw = ' '.join(desc_buffer).strip()
                        desc_buffer = []

                        if valor > 0 and desc_raw and data_atual:
                            sinal_exp = ('entrada' if sinal_char == '+'
                                         else 'saida' if sinal_char in ('-', '\u2212', '\u2013')
                                         else '')
                            tipo = self._determinar_tipo(sinal_exp, desc_raw, secao_atual)
                            transacoes.append(self._transacao(
                                data=data_atual, descricao=desc_raw,
                                valor=valor, tipo=tipo, banco=BANCO, raw=linha_norm,
                            ))
                        continue

                    # ── Valor inline ao final da linha: "Descrição Valor" ─────
                    # Formato real Nubank: tipo + contraparte + valor tudo numa linha
                    m_inline = _RE_VALOR_INLINE.match(linha_norm)
                    if m_inline and data_atual:
                        desc_parte = m_inline.group(1).strip()
                        valor_str = m_inline.group(2)
                        # Só processa se há texto (não é linha só numérica)
                        if re.search(r'[a-zA-ZÀ-ÿ]', desc_parte):
                            valor, sinal = _parse_valor_str(valor_str)
                            if valor > 0:
                                # Buffer residual (muito raro com este formato)
                                # é descartado para não misturar com a transação corrente
                                desc_buffer = []
                                tipo = self._determinar_tipo(sinal, desc_parte, secao_atual)
                                transacoes.append(self._transacao(
                                    data=data_atual, descricao=desc_parte,
                                    valor=valor, tipo=tipo, banco=BANCO, raw=linha_norm,
                                ))
                                continue

                    # ── Buffer: descrição parcial (fallback multilinhas) ──────
                    # Só acumula se a linha tem conteúdo relevante
                    if re.search(r'[a-zA-ZÀ-ÿ]', linha_norm):
                        desc_buffer.append(linha_norm)

            except Exception as e:
                self.avisos.append(f'Nubank texto página {num}: {e}')

        _flush()
        return transacoes

    def _processar_buffer(
        self, desc_buffer: list[str], data: str, secao: str
    ) -> dict | None:
        """Extrai transação de linhas acumuladas no buffer (fallback)."""
        if not desc_buffer:
            return None

        ultima = desc_buffer[-1]

        m_val = _RE_VALOR_LINHA.match(ultima)
        if m_val:
            sinal_char = m_val.group(1) or ''
            valor_raw = m_val.group(2)
            valor, _ = _parse_valor_str(sinal_char + valor_raw)
            desc_raw = ' '.join(desc_buffer[:-1]).strip()
        else:
            m_inline = _RE_VALOR_INLINE.match(ultima)
            if m_inline:
                desc_raw = (
                    ' '.join(desc_buffer[:-1]) + ' ' + m_inline.group(1)
                ).strip()
                valor_str = m_inline.group(2)
                sinal_char = '+' if '+' in valor_str else ('-' if '-' in valor_str else '')
                valor, _ = _parse_valor_str(valor_str)
            else:
                return None

        if valor == 0.0 or not desc_raw:
            return None

        sinal_exp = ('entrada' if sinal_char == '+'
                     else 'saida' if sinal_char in ('-', '\u2212', '\u2013')
                     else '')
        tipo = self._determinar_tipo(sinal_exp, desc_raw, secao)
        return self._transacao(
            data=data, descricao=desc_raw, valor=valor,
            tipo=tipo, banco=BANCO, raw=ultima,
        )

    # ── Detecção de linhas de detalhe bancário ────────────────────────────────

    def _prefixo_antes_detalhe(self, linha: str) -> str:
        """
        Para linhas fundidas pelo pdfplumber como
        "Transfer...6,00(0237) Agência: 2458 Conta: 503643-7",
        retorna o prefixo antes do marcador bancário, ex: "Transfer...6,00".
        Retorna '' se o marcador está no início (linha é detalhe puro).
        """
        m = _RE_DETALHE_MARCADOR.search(linha)
        if m and m.start() > 10:
            return linha[:m.start()].rstrip()
        return ''

    def _e_detalhe_bancario(self, linha: str, linha_lower: str) -> bool:
        """
        Detecta linhas de continuação de detalhes de Pix que NÃO são transações.

        Exemplos de linhas descartadas:
          "(0237) Agência: 2458 Conta: 503643-7"
          "PAGAMENTOS - IP (0260) Agência: 1 Conta:"
          "33409090-7"
          "/0003-61 - PAGSEGURO INTERNET IP S.A. (0290)"
          "DO BRASIL S.A. (0001) Agência: 1266 Conta:"
        """
        # Linha com agência E conta juntos (roteamento bancário)
        if ('ag' in linha_lower and 'ncia' in linha_lower and
                'conta' in linha_lower):
            return True

        # Linha iniciando com código de banco entre parênteses: "(0237)"
        if re.match(r'^\(\d{3,4}\)', linha.strip()):
            return True

        # Linha iniciando com "/": fragmento de CNPJ
        if linha.strip().startswith('/'):
            return True

        # Linha que é apenas número de conta: "503643-7", "1544919700-0"
        if _RE_NUMERO_CONTA.match(linha.strip()):
            return True

        return False

    # ── Verificação tripla de tipo ────────────────────────────────────────────

    def _determinar_tipo(
        self, sinal_explicito: str, descricao: str, secao: str
    ) -> str:
        """
        Verificação tripla do tipo:
          1. Seção do extrato → autoritária para Nubank
          2. Sinal explícito → secundário (fallback sem seção)
          3. Palavras-chave → fallback (default 'saida')

        Nota: no Nubank as transações individuais NUNCA têm sinal +/-.
        O sinal capturado pelo regex normalmente vem do traço na descrição
        (ex: "PAGAMENTOS - 500,00") e NÃO deve sobrepor a seção.
        """
        if secao in ('entrada', 'saida'):
            return secao

        if sinal_explicito in ('entrada', 'saida'):
            return sinal_explicito

        return self._verificar_tipo_cruzado(
            tipo_por_sinal='',
            descricao=descricao,
            palavras_entrada=_ENTRADAS_KW,
            palavras_saida=_SAIDAS_KW,
        )
