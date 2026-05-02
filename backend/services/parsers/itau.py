"""
itau.py – Parser de extrato do Itaú.

Formato: texto com linhas de transação.

Formatos de data suportados:
  - DD/MM         (ex: 01/08)
  - DD/MM/AA      (ex: 01/08/25)
  - DD/MM/AAAA    (ex: 01/08/2025)
  - DD / mmm      (ex: 01 / ago)   ← formato mensal do Itaú

A data pode aparecer somente na primeira linha de cada dia — as demais
transações do mesmo dia não repetem a data.

Valor: último token da linha, formato BR.
  - sem '-' = crédito (entrada)
  - com '-' no final OU no início = débito (saída)

Verificação cruzada de tipo:
  1. Sinal do valor (autoritário) — '-' indica débito
  2. Palavras-chave da descrição (confirmação)
  Quando os dois concordam → alta confiança.
  Quando discordam → sinal tem prioridade.
"""

import re
import pdfplumber
from .base import ParserBase, _RE_ANO


BANCO = 'Itaú'

# Mapa de abreviações de mês para número (minúsculas)
_MESES = {
    'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
    'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
    'set': '09', 'out': '10', 'nov': '11', 'dez': '12',
}

# Regex para capturar data DD / mmm no início de linha
_RE_DATA_ABREV = re.compile(
    r'^(\d{2})\s*/\s*([a-zA-Zç]{3})\b'
)

# Regex principal: data opcional + descrição + valor monetário
# Valor pode ter '-' no início OU no final (débito)
# Regex principal: data opcional + descricao + valor monetario + saldo opcional
# O saldo pode ter sufixo "-" (conta negativa) — sem isso, regex backtrackeia
# e o saldo vira o "valor" capturado (causa do bug MEDIO-PARSER-3).
_RE_LINHA = re.compile(
    r'^(?:(\d{2}/\d{2}(?:/\d{2,4})?)\s+)?(.+?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2}-?)'
    r'(?:\s+\d{1,3}(?:\.\d{3})*,\d{2}-?)?\s*$'
)

# Linhas que devem ser completamente ignoradas (saldos, cabeçalhos, legendas)
_IGNORAR = [
    # Saldos e aplicações automáticas — NUNCA são transações
    'saldo aplic aut mais',
    'res aplic aut mais',
    'rend pago aplic aut mais',
    'apl aplic aut mais',
    'aplic aut mais',
    'aplicação automática',
    'aplicacao automatica',
    'saldo anterior',
    'saldo em ',
    'saldo do dia',
    'saldo final',
    's a l d o',
    # Cabeçalhos de tabela
    'data descri',
    'entradas (cr',
    'saídas (d',
    'saidas (d',
    'saída',
    'total entradas',
    'total saídas',
    'total saidas',
    'totalentradas',
    'totalsa',
    # Linhas de agrupamento
    'conta corrente|movimenta',
    'depósitos e ',
    'depositos e ',
    'transferências, docs',
    'transferencias, docs',
    'outras entradas',
    'outras saídas',
    'outras saidas',
    '(créditos)',
    '(débitos)',
    '(creditos)',
    '(debitos)',
    # Informações de conta
    'minha conta',
    'minha agência',
    # Legendas de colunas
    'a =agendamento',
    'b = ações',
    'c = crédito',
    'd = débito',
    'g = aplicação',
    'p = poupança',
    'para demais siglas',
    'extrato mensal ag',
    'na conta corrente',
    'notas explicativas',
    'para demais',
    'em vigor',
    # Limites e crédito
    'limite contratado',
    'limite de crédito',
    'limite de credito',
    'saldo total dispon',
    'saldo dispon',
    # NOTA: 'limite da conta' removido — filtrava "Juros Limite da Conta" (tx legitima)
    'limite da conta garantida',
    # Rodapé
    'ouvidoria',
    'sac itau',
    'sac itaú',
]

_ENTRADAS = [
    'pix recebido', 'ted recebida', 'doc recebido',
    'credito', 'crédito', 'estorno', 'devolução', 'devolucao',
    'deposito', 'depósito', 'res aplic', 'rend',
    'tbi', 'est ',
    'transferencia recebida', 'transferência recebida',
]

_SAIDAS = [
    'pix enviado', 'ted enviado', 'doc enviado',
    'debito', 'débito', 'pagamento', 'compra',
    'saque', 'tarifa', 'taxa', 'cheque', 'darf',
    'simples nacional', 'fgts', 'seguro',
]


def _converter_data_abrev(dia: str, mes_abrev: str, ano_ref: int | None) -> str:
    """Converte '01 / ago' em '01/08/AAAA'."""
    from datetime import datetime
    mes_num = _MESES.get(mes_abrev.lower()[:3], '00')
    ano = str(ano_ref) if ano_ref else str(datetime.now().year)
    return f'{dia.zfill(2)}/{mes_num}/{ano}'


class ParserItau(ParserBase):
    """Parser para extratos do Itaú (texto com rastreamento de data por dia)."""

    def extrair(self) -> list[dict]:
        """Extrai transações do extrato Itaú com tripla verificação."""
        transacoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
            total_paginas = len(pdf.pages)
            ano_ref = None
            data_atual: str = ''
            # Quando True, paramos de capturar transações (seção informativa)
            encerrou_transacoes = False

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
                        linha_lower = linha.strip().lower()

                        # Detecta fim da seção de transações
                        if (
                            'saldo final' in linha_lower
                            or 'totalizador de aplica' in linha_lower
                            or 'lançamentos futuros' in linha_lower
                            or 'lancamentos futuros' in linha_lower
                            or 'saldo da conta corrente' in linha_lower
                        ):
                            encerrou_transacoes = True

                        if encerrou_transacoes:
                            continue

                        # Rend Pago Aplic Aut Mais: rendimento creditado na conta
                        # O 1º valor depois de "Mais" é o rendimento; o 2º é o saldo
                        if 'rend pago aplic aut mais' in linha_lower:
                            m_rend = re.search(r'[Mm]ais\s+([\d.,]+)', linha)
                            if m_rend and data_atual:
                                valor_rend = self._normalizar_valor(m_rend.group(1))
                                if valor_rend > 0:
                                    transacoes.append(self._transacao(
                                        data=data_atual,
                                        descricao='Rend Pago Aplic Aut Mais',
                                        valor=valor_rend,
                                        tipo='entrada',
                                        banco=BANCO,
                                        raw=linha.strip(),
                                    ))
                            continue

                        # Para linhas em _IGNORAR que contêm transação embutida
                        # (ex: "Para demais siglas ... DD/MM DESC val-")
                        if any(x in linha_lower for x in _IGNORAR):
                            t_emb = self._extrair_transacao_embutida(
                                linha.strip(), data_atual, ano_ref
                            )
                            if t_emb:
                                data_atual = t_emb['data'] or data_atual
                                transacoes.append(t_emb)
                            continue

                        resultado = self._processar_linha(
                            linha, data_atual, ano_ref
                        )
                        if resultado is None:
                            continue
                        if resultado == 'skip':
                            nova_data = self._extrair_data_linha(linha, ano_ref)
                            if nova_data:
                                data_atual = nova_data
                            continue
                        data_atual = resultado['data'] or data_atual
                        transacoes.append(resultado)

                except Exception as e:
                    self.avisos.append(f'Itaú: erro na página {num}: {e}')

        if not transacoes and total_paginas > 0:
            self.avisos.append(
                'Extrato com saldo zero — nenhuma transação encontrada.'
            )

        # Tripla verificação: estrutura + data + deduplicação
        return self._post_processar(transacoes)

    def _extrair_transacao_embutida(
        self, linha: str, data_atual: str, ano_ref: int | None
    ) -> dict | None:
        """
        Tenta extrair transação embutida em linhas de metadados.

        Caso 1: linha com legenda que termina com 'DD/MM DESC val-'
        Caso 2: pdfplumber fundiu legenda de coluna com transação adjacente,
                sem data (ex: 'P = poupança automática Sispag Fornecedores 2.408,44-')
        """
        # Tentativa 1: padrão com DD/MM no meio da linha
        m = re.search(
            r'(\d{2}/\d{2})\s+(.+?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2}-?)\s*$',
            linha,
        )
        if m:
            data_str = m.group(1)
            desc = m.group(2).strip()
            valor_raw = m.group(3)

            if not re.search(r'[a-zA-ZÀ-ÿ]', desc) or len(desc) < 3:
                return None

            desc_lower = desc.lower()
            if any(x in desc_lower for x in _IGNORAR):
                return None

            valor = self._normalizar_valor(valor_raw)
            if valor == 0.0:
                return None

            data = self._normalizar_data(data_str, ano_referencia=ano_ref)
            if not self._validar_data(data):
                return None

            negativo = valor_raw.endswith('-') or valor_raw.startswith('-')
            tipo = 'saida' if negativo else 'entrada'

            return self._transacao(
                data=data,
                descricao=desc,
                valor=valor,
                tipo=tipo,
                banco=BANCO,
                raw=linha,
            )

        # Tentativa 2: sem data — pdfplumber fundiu legenda + transação adjacente
        if not data_atual:
            return None

        m2 = re.search(r'(-?\d{1,3}(?:\.\d{3})*,\d{2}-?)\s*$', linha)
        if not m2:
            return None

        valor_raw = m2.group(1)
        pre_valor = linha[:m2.start()].strip()

        # Remove prefixo ignorável para recuperar apenas a desc da transação
        pre_lower = pre_valor.lower()
        desc = pre_valor
        for ign in _IGNORAR:
            idx = pre_lower.find(ign)
            if idx >= 0:
                after = pre_valor[idx + len(ign):].lstrip(' =:;,')
                if after and re.search(r'[a-zA-ZÀ-ÿ]', after):
                    desc = after.strip()
                break

        # Exige ao menos dois tokens: linhas mescladas por pdfplumber sempre
        # produzem "legenda + descrição" com espaço; tokens únicos (ex: "C/C")
        # são resíduos de linhas de saldo, não transações.
        if not re.search(r'[a-zA-ZÀ-ÿ]', desc) or len(desc) < 5 or ' ' not in desc:
            return None

        desc_lower = desc.lower()
        if any(x in desc_lower for x in _IGNORAR):
            return None

        # Filtra resíduos de linhas de saldo cortadas pelo pdfplumber
        # Ex: "SALDO DISPONÍVEL DIA" vira "ÍVEL DIA" após strip do prefixo
        _RESIDUOS_SALDO = [
            'vel dia', 'ível dia', 'ivel dia', 'nível dia', 'nivel dia',
            'spon', 'ispon', 'dispon',
            'aldo do dia', 'aldo final', 'aldo anterior',
            'aldo parcial', 'aldo contab', 'aldo contáb',
        ]
        if any(r in desc_lower for r in _RESIDUOS_SALDO):
            return None

        valor = self._normalizar_valor(valor_raw)
        if valor == 0.0:
            return None

        negativo = valor_raw.endswith('-') or valor_raw.startswith('-')
        tipo = 'saida' if negativo else 'entrada'

        return self._transacao(
            data=data_atual,
            descricao=desc,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=linha,
        )

    def _extrair_data_linha(self, linha: str, ano_ref: int | None) -> str:
        """Retorna a data encontrada no início da linha, ou ''."""
        linha = linha.strip()

        # Formato DD / mmm
        m = _RE_DATA_ABREV.match(linha)
        if m:
            return _converter_data_abrev(m.group(1), m.group(2), ano_ref)

        # Formato DD/MM ou DD/MM/AAAA
        m = re.match(r'^(\d{2}/\d{2}(?:/\d{2,4})?)', linha)
        if m:
            return self._normalizar_data(m.group(1), ano_referencia=ano_ref)

        return ''

    def _normalizar_linha(self, linha: str, ano_ref: int | None) -> tuple[str, str]:
        """
        Normaliza a linha convertendo 'DD / mmm' para 'DD/MM/AAAA'.
        Retorna (linha_normalizada, data_extraida_ou_vazio).
        """
        linha = linha.strip()
        m = _RE_DATA_ABREV.match(linha)
        if m:
            data_norm = _converter_data_abrev(m.group(1), m.group(2), ano_ref)
            sufixo = linha[m.end():].strip()
            linha_norm = f'{data_norm} {sufixo}'
            return linha_norm, data_norm
        return linha, ''

    def _processar_linha(
        self, linha: str, data_atual: str, ano_ref: int | None
    ) -> dict | None | str:
        """
        Processa uma linha do extrato Itaú com verificação item a item.

        Returns:
            dict   – transação válida
            None   – linha ignorada (saldo, cabeçalho, valor zero)
            'skip' – linha sem transação, pode conter data
        """
        linha = linha.strip()
        if not linha:
            return None

        # Percentuais são linhas de taxa/juros informativas — ignorar
        if '%' in linha:
            return None

        # Linha começa com R$ → saldo ou total — ignorar
        if linha.upper().startswith('R$'):
            return None

        linha_lower = linha.lower()

        # Linha começa com 'total' → totalizador — ignorar
        if linha_lower.startswith('total'):
            return None

        # Verifica lista de ignorados (saldos, aplicações automáticas, cabeçalhos)
        if any(x in linha_lower for x in _IGNORAR):
            return None

        # Normaliza formato 'DD / mmm' → 'DD/MM/AAAA'
        linha_norm, data_abrev = self._normalizar_linha(linha, ano_ref)

        m = _RE_LINHA.match(linha_norm)
        if not m:
            return 'skip'

        data_raw = m.group(1)     # pode ser None
        desc_raw = m.group(2).strip()
        valor_raw = m.group(3)

        # Descrição sem letras = linha numérica de tabela — ignorar
        if not re.search(r'[a-zA-ZÀ-ÿ]', desc_raw):
            return None

        # Descrição muito curta provavelmente é fragmento de texto cortado
        # pelo pdfplumber (ex: "CODE" de "PIX QR CODE")
        # Minimo 3 chars — "IOF" (3 chars) e transacao legitima
        if len(desc_raw.strip()) < 3:
            return None

        desc_lower = desc_raw.lower()
        if any(x in desc_lower for x in _IGNORAR):
            return None

        # ── Verificação 1: valor ──────────────────────────────────────
        valor = self._normalizar_valor(valor_raw)
        if valor == 0.0:
            return None

        # Dupla verificação de valor: re-extrai do raw e confirma
        valor = self._segunda_verificacao_valor(linha, valor)
        if valor == 0.0:
            return None

        # ── Verificação 2: data ───────────────────────────────────────
        # Prioridade: data na linha normalizada > data abreviada > data atual
        if data_raw:
            data = self._normalizar_data(data_raw, ano_referencia=ano_ref)
        elif data_abrev:
            data = data_abrev
        else:
            data = data_atual

        # Valida data antes de criar transação
        if data and not self._validar_data(data):
            return None

        # ── Verificação 3: tipo (sinal + palavras-chave cruzados) ─────
        # No Itaú, o sinal é AUTORITÁRIO:
        #   '-' no início ou no final do valor = débito/saída
        #   sem '-' = crédito/entrada
        negativo = valor_raw.endswith('-') or valor_raw.startswith('-')
        tipo_por_sinal = 'saida' if negativo else 'entrada'

        # Verificação cruzada com palavras-chave (confirma o sinal)
        tipo = self._verificar_tipo_cruzado(
            tipo_por_sinal=tipo_por_sinal,
            descricao=desc_raw,
            palavras_entrada=_ENTRADAS,
            palavras_saida=_SAIDAS,
        )

        return self._transacao(
            data=data,
            descricao=desc_raw,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=linha,
        )
