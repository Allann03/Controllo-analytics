"""
bb.py – Parser de extrato do Banco do Brasil.

Formato "Extrato de Conta Corrente" do BB (pdfplumber):

  Cada transação ocupa 2–3 linhas:

    Tipo A – data sozinha + linha de valor com desc inline:
      '02/04/2025'
      '14128 699702352000140 Cap Giro Digital Estorno 45,21 (+)'

    Tipo B – data + histórico + linha de valor + continuação:
      '01/04/2025 Compra com Cartão'
      '99008 326844 42,51 (-)'
      '01/04 15:13 ASSAI ATACADISTA'   ← continuação com nome do estabelecimento

    Tipo C – histórico antes da data + linha de valor:
      'Pix - Recebido'
      '02/04/2025'
      '14397 21447308261232 02/04 14:47 NOME 150,00 (+)'

    Tipo D – data truncada por quebra de página + lote + valor:
      '09/04/202 13105 40901 Pagamento de Boleto 1.779,56 (-)'

  Sinal: (+) = entrada/crédito  |  (-) = saída/débito
  Data 00/00/0000 = saldo do dia — ignorar.
  Linha 'S A L D O' = fim das transações.

  Linha de continuação de cartão:
    Formato: 'DD/MM HH:MM NOME_ESTABELECIMENTO'
    Aparece logo após a linha de valor de 'Compra com Cartão'.
    O nome do estabelecimento é extraído e anexado à descrição:
      'Compra com Cartão — ASSAI ATACADISTA'
"""

import re
import pdfplumber
from .base import ParserBase, _RE_ANO


BANCO = 'Banco do Brasil'

# Linha apenas com data DD/MM/YYYY
_RE_DATA_SOZINHA = re.compile(r'^(\d{2}/\d{2}/\d{4})\s*$')

# Linha data + histórico: DD/MM/YYYY texto
_RE_DATA_DESC = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.+)$')

# Linha de valor principal: LOTE DOC [desc] VALOR (+|-)
# LOTE = 3-6 dígitos; tudo entre doc e valor é a descrição inline opcional
_RE_VALOR = re.compile(
    r'^(\d{3,6})\s+(\S+)\s*(.*?)\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*\(([+-])\)\s*$'
)

# Tipo D: data com ano truncado + lote + doc + desc + valor
# Ex: '09/04/202 13105 40901 Pagamento de Boleto 1.779,56 (-)'
_RE_DATA_TRUNC_VALOR = re.compile(
    r'^(\d{2}/\d{2}/\d{2,3})\s+(\d{3,6})\s+(\S+)\s*(.*?)\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*\(([+-])\)\s*$'
)

# Linha de continuação de cartão: DD/MM HH:MM [chave_pix_opcional] NOME
# Ex: '29/11 18:35 PAROQUIA SAO PEDRO A'
# Ex: '01/12 08:24 00004332567889 CLAUDIA ELI'  ← Pix (chave antes do nome)
_RE_CONTINUACAO = re.compile(
    r'^(\d{2}/\d{2})\s+(\d{2}:\d{2})\s+(.+)$'
)

# Linhas de cabeçalho/rodapé a ignorar
_SKIP = [
    'extrato de conta corrente',
    'cliente',
    'agência', 'agencia',
    'lançamentos', 'lancamentos',
    'dia lote documento',
    'total aplicações', 'total aplicacoes',
    'saldos por dia base', 'sujeitos a confirmação', 'sujeitos a confirmacao',
]

_ENTRADAS = [
    'pix - recebido', 'pix recebido', 'ordem bancária', 'ordem bancaria',
    'ted', 'credito', 'crédito', 'estorno de débito', 'estorno de debito',
    'estorno', 'devolução', 'devolucao', 'deposito', 'depósito',
    'cap giro digital estorno',
]

_SAIDAS = [
    'pix - enviado', 'pix enviado', 'compra com cartão', 'compra com cartao',
    'pagamento de boleto', 'pagto conta telefone',
    'debito', 'débito', 'tarifa', 'taxa',
    'cobrança de juros', 'cobranca de juros', 'cobrança de i.o.f', 'cobrança de iof',
    'cap giro dig amortização', 'cap giro dig amortizacao',
    'saque', 'darf', 'fgts', 'simples nacional',
]


class ParserBB(ParserBase):
    """Parser para extratos do Banco do Brasil (Extrato de Conta Corrente)."""

    def _tipo_complemento(self, desc: str) -> str | None:
        """
        Determina o tipo de linha de complemento esperada após a transação.

        'timestamp' → DD/MM HH:MM [chave] NOME
          (Compra com Cartão, Pix - Enviado, Pix - Recebido)

        'texto' → linha de texto puro com o nome do beneficiário
          (Pagamento de Boleto, Pagto Conta Telefone)

        None → sem complemento esperado
        """
        d = desc.lower()
        if any(x in d for x in (
            'compra com cart', 'pix - enviado', 'pix - recebido',
            'pix enviado', 'pix recebido',
        )):
            return 'timestamp'
        if 'pagamento de boleto' in d or 'pagto' in d:
            return 'texto'
        return None

    def _extrair_saldos_intermediarios(self) -> list[dict]:
        """Extrai saldos do dia do extrato BB. Padrão: NNNNN Saldo do dia X.XXX,XX (+/-)."""
        saldos = []
        _re_data = re.compile(r'^(\d{2}/\d{2}/\d{4})')
        _re_saldo = re.compile(
            r'Saldo\s+do\s+dia\s+([\d.,]+)\s*\(([+-])\)', re.IGNORECASE
        )
        try:
            with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
                data_atual = None
                for page in pdf.pages:
                    texto = page.extract_text() or ''
                    for linha in texto.split('\n'):
                        stripped = linha.strip()
                        m_data = _re_data.match(stripped)
                        if m_data and not stripped.startswith('00/00'):
                            data_atual = m_data.group(1)
                        m_saldo = _re_saldo.search(stripped)
                        if m_saldo and data_atual:
                            valor = self._normalizar_valor(m_saldo.group(1))
                            saldos.append({'data': data_atual, 'saldo': valor})
        except Exception:
            pass
        return saldos

    def extrair(self) -> list[dict]:
        transacoes: list[dict] = []
        ano_ref = None
        data_atual = ''
        desc_pre = ''
        # 'timestamp' | 'texto' | None — tipo de complemento aguardado
        aguarda_complemento: str | None = None

        with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
            total_paginas = len(pdf.pages)

            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    texto = pagina.extract_text() or ''
                    if not texto.strip():
                        continue

                    if ano_ref is None:
                        m = _RE_ANO.search(texto)
                        if m:
                            ano_ref = int(m.group(1))

                    for linha in texto.splitlines():
                        linha = linha.strip()
                        if not linha:
                            continue

                        linha_lower = linha.lower()

                        # ── Fim das transações ─────────────────────────────
                        if 's a l d o' in linha_lower:
                            return self._post_processar(transacoes)

                        # ── Cabeçalhos e rodapés ───────────────────────────
                        if any(x in linha_lower for x in _SKIP):
                            continue

                        # ── Saldo do dia / Saldo anterior (não são transações)
                        if 'saldo do dia' in linha_lower or 'saldo anterior' in linha_lower:
                            aguarda_complemento = None
                            continue

                        # ── Data inválida 00/00/0000 ───────────────────────
                        if linha.startswith('00/00/0000'):
                            aguarda_complemento = None
                            continue

                        # ── Linha de complemento: enriquece a última transação ──
                        #
                        # 'timestamp': DD/MM HH:MM [chave] NOME
                        #   → Compra com Cartão, Pix Enviado, Pix Recebido
                        # 'texto': nome do beneficiário em texto puro
                        #   → Pagamento de Boleto
                        if aguarda_complemento:
                            if aguarda_complemento == 'timestamp':
                                m_cont = _RE_CONTINUACAO.match(linha)
                                if m_cont:
                                    nome = self._extrair_nome_estabelecimento(m_cont.group(3))
                                    if nome and transacoes:
                                        base = transacoes[-1]['descricao']
                                        transacoes[-1]['descricao'] = f'{base} — {nome}'
                                    aguarda_complemento = None
                                    continue
                                # Não é continuação — reseta e processa normalmente
                                aguarda_complemento = None

                            elif aguarda_complemento == 'texto':
                                # Beneficiário do boleto: linha de texto puro (sem timestamp,
                                # sem padrão de valor, sem padrão de data)
                                if (
                                    not _RE_VALOR.match(linha)
                                    and not _RE_DATA_TRUNC_VALOR.match(linha)
                                    and not _RE_DATA_SOZINHA.match(linha)
                                    and not _RE_DATA_DESC.match(linha)
                                    and not _RE_CONTINUACAO.match(linha)
                                    and re.search(r'[a-zA-ZÀ-ÿ]', linha)
                                ):
                                    if transacoes:
                                        transacoes[-1]['descricao'] += f' — {linha}'
                                    aguarda_complemento = None
                                    continue
                                aguarda_complemento = None

                        # ── Tipo D: data truncada + lote + valor ───────────
                        m_dt = _RE_DATA_TRUNC_VALOR.match(linha)
                        if m_dt:
                            data_str   = m_dt.group(1)
                            desc_raw   = m_dt.group(4).strip()
                            valor_raw  = m_dt.group(5)
                            sinal      = m_dt.group(6)
                            # Reconstrói ano truncado (ex: '202' → '2026')
                            from datetime import datetime as _dt
                            partes = data_str.split('/')
                            if len(partes[2]) < 4:
                                partes[2] = str(ano_ref) if ano_ref else str(_dt.now().year)
                            data_atual = f'{partes[0]}/{partes[1]}/{partes[2]}'
                            desc = desc_pre if desc_pre else desc_raw
                            t = self._montar(data_atual, desc, valor_raw, sinal, linha)
                            if t:
                                transacoes.append(t)
                                aguarda_complemento = self._tipo_complemento(desc)
                            desc_pre = ''
                            continue

                        # ── Data sozinha: DD/MM/YYYY ───────────────────────
                        m_ds = _RE_DATA_SOZINHA.match(linha)
                        if m_ds:
                            data_atual = self._normalizar_data(
                                m_ds.group(1), ano_referencia=ano_ref
                            )
                            # Limpa desc_pre se parecer continuação de linha anterior
                            # (ex: '02/04 15:03 Nome' — timestamp de Pix)
                            if desc_pre and desc_pre[0].isdigit():
                                desc_pre = ''
                            continue

                        # ── Data + histórico: DD/MM/YYYY texto ────────────
                        m_dd = _RE_DATA_DESC.match(linha)
                        if m_dd:
                            data_atual = self._normalizar_data(
                                m_dd.group(1), ano_referencia=ano_ref
                            )
                            desc_pre = m_dd.group(2).strip()
                            continue

                        # ── Linha de valor: LOTE DOC [desc] VALOR (+|-) ───
                        m_v = _RE_VALOR.match(linha)
                        if m_v:
                            desc_inline = self._extrair_desc_inline(m_v.group(3))
                            valor_raw   = m_v.group(4)
                            sinal       = m_v.group(5)

                            # Prioridade de descrição:
                            #  1. desc_inline "limpa" (não começa com timestamp DD/MM)
                            #     Ex: 'Cap Giro Dig Amortização', 'Tar. agrupadas...'
                            #  2. desc_pre (histórico acumulado antes da linha de valor)
                            #     Ex: 'Pix - Recebido', 'Compra com Cartão'
                            #  3. desc_inline ruidosa (timestamp de Pix como fallback)
                            if desc_inline and not re.match(r'^\d{2}/\d{2}', desc_inline):
                                desc = desc_inline
                            else:
                                desc = desc_pre or desc_inline

                            t = self._montar(data_atual, desc, valor_raw, sinal, linha)
                            if t:
                                transacoes.append(t)
                                aguarda_complemento = self._tipo_complemento(desc)
                            desc_pre = ''
                            continue

                        # ── Linha de descrição standalone (acumula) ────────
                        if re.search(r'[a-zA-ZÀ-ÿ]', linha):
                            desc_pre = linha

                except Exception as e:
                    self.avisos.append(f'BB: erro na página {num}: {e}')

        if not transacoes and total_paginas > 0:
            self.avisos.append('Extrato com saldo zero — nenhuma transação encontrada.')

        return self._post_processar(transacoes)

    def _extrair_nome_estabelecimento(self, texto: str) -> str:
        """
        Extrai o nome do estabelecimento da parte após 'DD/MM HH:MM' na linha
        de continuação de Compra com Cartão.

        Casos:
          '29/11 18:35 PAROQUIA SAO PEDRO A'  → group(3) = 'PAROQUIA SAO PEDRO A'
          '01/12 08:24 00004332567889 CLAUDIA' → group(3) = '00004332567889 CLAUDIA'
            (chave Pix — começa com número longo; retorna o texto após o número)

        O group(3) já vem sem o prefixo DD/MM HH:MM.
        """
        texto = texto.strip()
        if not texto:
            return ''
        # Se começa com uma sequência longa de dígitos (CPF/CNPJ/chave Pix = ≥8 dígitos),
        # pula esse token e usa o restante como nome.
        m = re.match(r'^(\d{8,})\s+(.+)$', texto)
        if m:
            return m.group(2).strip()
        # Caso comum: começa direto com o nome do estabelecimento
        return texto

    def _extrair_desc_inline(self, mid: str) -> str:
        """
        Remove o número de documento do início da string do meio da linha,
        retornando apenas a descrição textual.

        Ex: '699702352000140 Cap Giro Digital Estorno' → 'Cap Giro Digital Estorno'
        Ex: '326844'                                   → ''
        Ex: 'Tar. agrupadas - ocorrencia 07/04/2025'   → (mantém, não começa com dígito)
        """
        mid = mid.strip()
        if not mid:
            return ''
        partes = mid.split(None, 1)
        if partes[0].isdigit():
            return partes[1].strip() if len(partes) > 1 else ''
        return mid

    def _montar(
        self,
        data: str,
        desc: str,
        valor_raw: str,
        sinal: str,
        raw: str,
    ) -> dict | None:
        """Valida e monta uma transação a partir dos campos extraídos."""
        if not data or not desc:
            return None

        desc_lower = desc.lower()
        # Filtra linhas de saldo do dia (não são transações reais).
        # NÃO filtrar 'rende' nem 'aplic' — são movimentações BB Rende Fácil
        # que afetam o saldo da conta e precisam constar para gap=0.
        if 'saldo' in desc_lower and ('dia' in desc_lower or 'anterior' in desc_lower):
            return None

        valor = self._normalizar_valor(valor_raw)
        if valor == 0.0:
            return None

        if not self._validar_data(data):
            return None

        tipo_sinal = 'entrada' if sinal == '+' else 'saida'
        tipo = self._verificar_tipo_cruzado(
            tipo_por_sinal=tipo_sinal,
            descricao=desc,
            palavras_entrada=_ENTRADAS,
            palavras_saida=_SAIDAS,
        )

        return self._transacao(
            data=data,
            descricao=desc,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=raw,
        )
