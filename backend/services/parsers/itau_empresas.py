"""
itau_empresas.py – Parser de extrato do Itaú Empresas (conta PJ).

Diferenças em relação ao Itaú PF:
  - Nome do banco: 'Itaú Empresas'
  - Cabeçalhos e rodapés específicos de conta empresarial (CNPJ, razão social)
  - Seções de "Entradas" / "Saídas" mais explícitas
  - Linhas de saldo intermediário mais frequentes (saldo do dia, saldo parcial)
  - Descrições mais longas com CNPJ/razão social de contrapartes
  - Possível aparição de "Extrato de Conta Corrente PJ" ou "Gerenciador Financeiro"

Herda toda a lógica de parsing do ParserItau e sobrepõe apenas os pontos
que diferem no formato PJ.
"""

import re
import pdfplumber
from .base import ParserBase, _RE_ANO


BANCO = 'Itaú Empresas'

_MESES = {
    'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
    'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
    'set': '09', 'out': '10', 'nov': '11', 'dez': '12',
}

_RE_DATA_ABREV = re.compile(r'^(\d{2})\s*/\s*([a-zA-Zç]{3})\b')
_RE_LINHA = re.compile(
    r'^(?:(\d{2}/\d{2}(?:/\d{2,4})?)\s+)?(.+?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2}-?)'
    r'(?:\s+\d{1,3}(?:\.\d{3})*,\d{2})?\s*$'
)
# Linhas a ignorar — inclui todos os do PF mais específicos do PJ
_IGNORAR = [
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
    'saldo parcial',
    'saldo disponível',
    'saldo disponivel',
    'saldo contábil',
    'saldo contabil',
    's a l d o',
    # Cabeçalhos
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
    # PJ-específicos
    'conta corrente pj',
    'extrato de conta pj',
    'gerenciador financeiro',
    'extrato empresas',
    'razão social',
    'razao social',
    'cnpj:',
    'agência/conta',
    'agencia/conta',
    'período do extrato',
    'periodo do extrato',
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
    # Legendas
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
    # Limites
    'limite contratado',
    'limite de crédito',
    'limite de credito',
    'saldo total dispon',
    'saldo dispon',
    # NOTA: 'limite da conta' removido — filtrava "JUROS LIMITE DA CONTA" (tx legítima)
    'limite da conta garantida',  # mais específico
    # Rodapé
    'ouvidoria',
    'sac itau',
    'sac itaú',
    # PJ extras
    'capital de giro',
    'limite de cheque',
    'limite cc',
    # Saldos internos (nao sao transacoes de CC)
    'sdo cta/apl',
    'sdo cta',
]

_ENTRADAS = [
    'pix recebido', 'ted recebida', 'doc recebido',
    'credito', 'crédito', 'estorno', 'devolução', 'devolucao',
    'deposito', 'depósito', 'res aplic', 'rend',
    'tbi', 'est ',
    'transferencia recebida', 'transferência recebida',
    'recebimento', 'receita', 'faturamento',
]

_SAIDAS = [
    'pix enviado', 'ted enviado', 'doc enviado',
    'debito', 'débito', 'pagamento', 'compra',
    'saque', 'tarifa', 'taxa', 'cheque', 'darf',
    'simples nacional', 'fgts', 'seguro',
    'fornecedor', 'pagto', 'boleto',
]


def _converter_data_abrev(dia: str, mes_abrev: str, ano_ref: int | None) -> str:
    from datetime import datetime
    mes_num = _MESES.get(mes_abrev.lower()[:3], '00')
    ano = str(ano_ref) if ano_ref else str(datetime.now().year)
    return f'{dia.zfill(2)}/{mes_num}/{ano}'


class ParserItauEmpresas(ParserBase):
    """
    Parser para extratos do Itaú Empresas (conta corrente PJ).

    Usa a mesma lógica de linha do Itaú PF com filtros adicionais
    para os elementos específicos de extratos empresariais.
    """

    def extrair(self) -> list[dict]:
        transacoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
            total_paginas = len(pdf.pages)
            ano_ref = None
            data_atual: str = ''
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

                        # Rend Pago Aplic Aut Mais
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

                        if any(x in linha_lower for x in _IGNORAR):
                            t_emb = self._extrair_transacao_embutida(linha.strip(), data_atual, ano_ref)
                            if t_emb:
                                data_atual = t_emb['data'] or data_atual
                                transacoes.append(t_emb)
                            continue

                        resultado = self._processar_linha(linha, data_atual, ano_ref)
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
                    self.avisos.append(f'Itaú Empresas: erro na página {num}: {e}')

        if not transacoes and total_paginas > 0:
            self.avisos.append('Extrato com saldo zero — nenhuma transação encontrada.')

        return self._post_processar(transacoes)

    def _extrair_transacao_embutida(
        self, linha: str, data_atual: str, ano_ref: int | None
    ) -> dict | None:
        """
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
                data=data, descricao=desc, valor=valor,
                tipo=tipo, banco=BANCO, raw=linha,
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
        # Minimo 3 chars para desc (nao 5) — "IOF" e uma tx legitima de 3 chars
        if not re.search(r'[a-zA-ZÀ-ÿ]', desc) or len(desc) < 3:
            return None

        desc_lower = desc.lower()
        if any(x in desc_lower for x in _IGNORAR):
            return None

        # Filtra resíduos de linhas de saldo cortadas pelo pdfplumber
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
            data=data_atual, descricao=desc, valor=valor,
            tipo=tipo, banco=BANCO, raw=linha,
        )

    def _extrair_data_linha(self, linha: str, ano_ref: int | None) -> str:
        linha = linha.strip()
        m = _RE_DATA_ABREV.match(linha)
        if m:
            return _converter_data_abrev(m.group(1), m.group(2), ano_ref)
        m = re.match(r'^(\d{2}/\d{2}(?:/\d{2,4})?)', linha)
        if m:
            return self._normalizar_data(m.group(1), ano_referencia=ano_ref)
        return ''

    def _normalizar_linha(self, linha: str, ano_ref: int | None) -> tuple[str, str]:
        linha = linha.strip()
        m = _RE_DATA_ABREV.match(linha)
        if m:
            data_norm = _converter_data_abrev(m.group(1), m.group(2), ano_ref)
            sufixo = linha[m.end():].strip()
            return f'{data_norm} {sufixo}', data_norm
        return linha, ''

    def _processar_linha(
        self, linha: str, data_atual: str, ano_ref: int | None
    ) -> dict | None | str:
        linha = linha.strip()
        if not linha:
            return None

        if '%' in linha:
            return None

        if linha.upper().startswith('R$'):
            return None

        linha_lower = linha.lower()

        if linha_lower.startswith('total'):
            return None

        if any(x in linha_lower for x in _IGNORAR):
            return None

        # Filtra linhas que contêm CNPJ isolado (padrão XX.XXX.XXX/XXXX-XX)
        if re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', linha):
            # Linha de identificação de empresa — ignora
            return None

        linha_norm, data_abrev = self._normalizar_linha(linha, ano_ref)

        m = _RE_LINHA.match(linha_norm)
        if not m:
            return 'skip'

        data_raw = m.group(1)
        desc_raw = m.group(2).strip()
        valor_raw = m.group(3)

        if not re.search(r'[a-zA-ZÀ-ÿ]', desc_raw):
            return None

        # Descricao muito curta provavelmente e fragmento — mas "IOF" (3 chars) e legitima
        if len(desc_raw.strip()) < 3:
            return None

        desc_lower = desc_raw.lower()
        if any(x in desc_lower for x in _IGNORAR):
            return None

        valor = self._normalizar_valor(valor_raw)
        if valor == 0.0:
            return None

        valor = self._segunda_verificacao_valor(linha, valor)
        if valor == 0.0:
            return None

        if data_raw:
            data = self._normalizar_data(data_raw, ano_referencia=ano_ref)
        elif data_abrev:
            data = data_abrev
        else:
            data = data_atual

        if data and not self._validar_data(data):
            return None

        negativo = valor_raw.endswith('-') or valor_raw.startswith('-')
        tipo_por_sinal = 'saida' if negativo else 'entrada'

        tipo = self._verificar_tipo_cruzado(
            tipo_por_sinal=tipo_por_sinal,
            descricao=desc_raw,
            palavras_entrada=_ENTRADAS,
            palavras_saida=_SAIDAS,
        )

        return self._transacao(
            data=data, descricao=desc_raw, valor=valor,
            tipo=tipo, banco=BANCO, raw=linha,
        )
