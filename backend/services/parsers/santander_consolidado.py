"""
santander_consolidado.py – Parser para Santander "Extrato Consolidado Inteligente".

Formato: extrato mensal impresso multi-linha com sufixo "-" para debitos.
Quarto formato Santander identificado no sistema.

Caracteristicas:
  - Pagina 1 = propaganda (ignorar)
  - Pagina 2+ = Resumo + Conta Corrente / Movimentacao
  - Transacoes multi-linha: valor com sufixo "-" = debito, sem sufixo = credito
  - Data DD/MM propagada (ano extraido do cabecalho "mes/YYYY")
  - Secoes auxiliares apos "SALDO EM DD/MM" final (ignorar todas)
  - Linhas CONTAMAX, CDB/RDB = transacoes normais (nao ignorar)
"""

import re
import pdfplumber
from decimal import Decimal
from .base import ParserBase

BANCO = 'Santander'

# Meses para extrair ano de referencia
_MESES = {
    'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'março': 3,
    'abril': 4, 'maio': 5, 'junho': 6, 'julho': 7,
    'agosto': 8, 'setembro': 9, 'outubro': 10,
    'novembro': 11, 'dezembro': 12,
}

# Regex para valor BR no final da linha (com ou sem sufixo "-")
# Captura: "22,98-", "10.000,00", "2.535,67-", "24.877,90"
_RE_VALOR_FIM = re.compile(
    r'((?:\d{1,3}\.)*\d{1,3},\d{2})(-)?\s*(?:(\d{1,3}(?:\.\d{3})*,\d{2})\s*)?$'
)

# Data curta DD/MM no inicio da linha
_RE_DATA_INICIO = re.compile(r'^(\d{2}/\d{2})\s+(.+)$')

# Linhas a ignorar completamente
_IGNORAR_EXATAS = {
    'extrato consolidado inteligente',
    'data descrição nº documento movimentos (r$) saldo (r$)',
    'data descrição n documento movimentos (r$) saldo (r$)',
    'créditos débitos',
    'creditos debitos',
    'conta corrente',
    'movimentação',
    'movimentacao',
    'fale conosco',
}

# Meses escritos que aparecem como cabecalho de pagina (ex: "fevereiro/2025")
_IGNORAR_MESES = {f'{m}/' for m in _MESES}

_IGNORAR_CONTEM = [
    'pagina:', 'extrato_pj_a4_inteligente', 'balp_uy_',
    'central de atendimento', 'ouvidoria', '4004', '0800',
    'sac ', 'https://', 'whatsapp', 'central de vendas',
    'prezado cliente', 'santander tem', 'soluções',
    'getnet:', 'cobranças:', '- pix:', 'pagamento a fornecedores',
    'tributos:', 'fopa:', 'internet banking empresarial',
    'resumo -', 'nome', 'agência', 'conta corrente',
    '(=) saldo', '(+) total', '(-) total',
    '(+) saldo de investimentos', 'depósitos', 'outros créditos',
    'compras com cartão', 'pagamentos / transferências', 'outros débitos',
    'libras', 'se não ficou', 'ou pelo nosso',
    'no exterior', 'para contratação', 'das 8h',
    'de segunda', 'acesse:', 'loja:',
    'consultas, informações',
    # Secoes auxiliares (apos SALDO EM final)
    'saldos por período', 'saldos por periodo',
    'débito automático', 'debito automatico',
    'compras com cartão de débito', 'comprovantes de pagamento',
    'transferências entre contas', 'transferencias entre contas',
    'investimentos', 'contamax empresarial',
    'posição consolidada', 'posicao consolidada',
    'pacote de serviços', 'pacote de servicos',
    'programa de relacionamento',
    'índices econômicos', 'indices economicos',
    'contas de consumo', 'limite para',
    'canal código', 'canal codigo',
    # Cabeçalhos das seções auxiliares
    'data número do cartão', 'data numero do cartao',
    'data de nome da', 'data canal tipo',
    'dia saldo de', '(+) (+) (-)',
    '* valores deduzidos',
    'números referentes',
    '"sesuaempresa',
    'saldo devedor',
]

# Regex para SALDO EM DD/MM (marca inicio/fim das transacoes)
_RE_SALDO_EM = re.compile(r'^SALDO EM (\d{2}/\d{2})\s+([\d.,]+)$', re.IGNORECASE)


class ParserSantanderConsolidado(ParserBase):
    """
    Parser para Santander Extrato Consolidado Inteligente.
    Suporta transacoes multi-linha com sufixo "-" para debitos.
    """

    def extrair(self) -> list[dict]:
        linhas_brutas: list[str] = []
        ano_ref: int | None = None

        with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    texto = pagina.extract_text() or ''
                    if not texto.strip():
                        continue

                    # Extrair ano do cabecalho (ex: "fevereiro/2025")
                    if ano_ref is None:
                        ano_ref = self._extrair_ano(texto)

                    for linha in texto.splitlines():
                        linhas_brutas.append(linha.strip())
                except Exception as e:
                    self.avisos.append(f'Santander Consolidado: erro pagina {num}: {e}')

        if ano_ref is None:
            ano_ref = 2025
            self.avisos.append('Ano de referencia nao encontrado, usando 2025.')

        transacoes = self._processar_linhas(linhas_brutas, ano_ref)
        return self._post_processar(transacoes)

    def _extrair_ano(self, texto: str) -> int | None:
        """Extrai ano do cabecalho 'mes/YYYY'."""
        for linha in texto.splitlines():
            lt = linha.strip().lower()
            for mes_nome in _MESES:
                if lt.startswith(mes_nome + '/'):
                    try:
                        return int(lt.split('/')[1].strip())
                    except (ValueError, IndexError):
                        pass
            # Fallback: qualquer 20XX no texto
            m = re.search(r'\b(20\d{2})\b', linha)
            if m:
                return int(m.group(1))
        return None

    def _processar_linhas(self, linhas: list[str], ano_ref: int) -> list[dict]:
        """Processa todas as linhas, reagrupando multi-linha."""
        transacoes: list[dict] = []
        zona_transacoes = False
        fim_transacoes = False
        data_atual: str | None = None

        # Buffer para reagrupamento multi-linha
        tx_pendente: dict | None = None  # {data, desc, valor, tipo, raw, doc}
        saldo_em_count = 0  # conta quantos "SALDO EM" encontramos na zona

        i = 0
        while i < len(linhas):
            linha = linhas[i]
            i += 1

            if not linha:
                continue

            if fim_transacoes:
                continue

            if not zona_transacoes:
                # Detectar inicio da zona pelo cabecalho "Movimentacao"
                if 'movimenta' in linha.lower():
                    zona_transacoes = True
                continue

            # Verificar se e SALDO EM (primeiro = abertura, segundo = fechamento)
            m_saldo = _RE_SALDO_EM.match(linha)
            if m_saldo:
                saldo_em_count += 1
                if saldo_em_count == 1:
                    # SALDO EM inicial (abertura) — ignorar, transacoes vem depois
                    continue
                else:
                    # SALDO EM final (fechamento) — flush pendente e parar
                    if tx_pendente:
                        transacoes.append(self._finalizar_tx(tx_pendente, ano_ref))
                        tx_pendente = None
                    fim_transacoes = True
                    continue

            # Ignorar linhas de metadados
            if self._ignorar(linha):
                continue

            # Tentar extrair valor do final da linha
            valor_info = self._extrair_valor_fim(linha)

            if valor_info is not None:
                # Linha com valor — e uma transacao (ou parte de uma)
                # Flush transacao pendente anterior
                if tx_pendente:
                    transacoes.append(self._finalizar_tx(tx_pendente, ano_ref))

                valor, negativo, saldo = valor_info

                # Extrair data do inicio (se presente)
                m_data = _RE_DATA_INICIO.match(linha)
                if m_data:
                    data_atual = m_data.group(1)
                    resto = m_data.group(2)
                else:
                    resto = linha

                # Separar descricao, doc e valor do resto
                desc, doc = self._separar_desc_doc_valor(resto, valor, negativo, saldo)

                tipo = 'saida' if negativo else 'entrada'

                tx_pendente = {
                    'data': data_atual,
                    'desc': desc,
                    'valor': valor,
                    'tipo': tipo,
                    'raw': linha,
                    'doc': doc,
                }
            else:
                # Linha sem valor — continuacao de descricao da tx pendente
                if tx_pendente:
                    extra = linha.strip()
                    # Ignorar cabecalhos de pagina que aparecem no meio das transacoes
                    if extra and not self._ignorar(extra):
                        tx_pendente['desc'] = tx_pendente['desc'] + ' ' + extra
                        tx_pendente['raw'] = tx_pendente['raw'] + ' | ' + linha
                # Se nao tem tx pendente, ignorar (pode ser cabecalho ou lixo)

        # Flush ultima pendente
        if tx_pendente:
            transacoes.append(self._finalizar_tx(tx_pendente, ano_ref))

        return transacoes

    def _extrair_valor_fim(self, linha: str) -> tuple | None:
        """Extrai valor do final da linha. Retorna (valor_decimal, negativo_bool, saldo_decimal|None) ou None."""
        # Procurar valor BR no final da linha
        # Pode ter: "desc VALOR-" ou "desc VALOR- SALDO" ou "desc VALOR SALDO"
        # Regex: captura valor principal + possivel saldo
        stripped = linha.rstrip()

        # Tentar match com saldo apos valor (CONTAMAX: "2.535,67- 0,00")
        m2 = re.search(r'((?:\d{1,3}\.)*\d{1,3},\d{2})(-?)\s+((?:\d{1,3}\.)*\d{1,3},\d{2})\s*$', stripped)
        if m2:
            val_raw = m2.group(1)
            neg = m2.group(2) == '-'
            saldo_raw = m2.group(3)
            val = self._normalizar_valor(val_raw)
            saldo = self._normalizar_valor(saldo_raw)
            if val > 0:
                return (val, neg, saldo)

        # Tentar match com valor simples no final
        m1 = re.search(r'((?:\d{1,3}\.)*\d{1,3},\d{2})(-?)\s*$', stripped)
        if m1:
            val_raw = m1.group(1)
            neg = m1.group(2) == '-'
            val = self._normalizar_valor(val_raw)
            if val > 0:
                return (val, neg, None)

        return None

    def _separar_desc_doc_valor(self, resto: str, valor: Decimal, negativo: bool, saldo) -> tuple:
        """Separa descricao e nro documento do resto da linha (apos remover data e valor)."""
        # Remover o valor (e saldo) do final
        texto = resto.rstrip()

        # Remover valor com possivel saldo do final
        suf = f'{self._format_br(valor)}'
        if negativo:
            suf += '-'
        if saldo is not None:
            suf_saldo = f' {self._format_br(saldo)}'
        else:
            suf_saldo = ''

        # Remover tudo apos a descricao
        # Encontrar a posicao do valor no texto (buscar de tras para frente)
        val_pattern = re.escape(self._format_br(valor))
        if negativo:
            val_pattern += r'-?'
        m = re.search(val_pattern + r'(-?\s*(?:\d{1,3}(?:\.\d{3})*,\d{2})?)?\s*$', texto)
        if m:
            desc_part = texto[:m.start()].strip()
        else:
            desc_part = texto.strip()

        # Remover " - " solitario do final (separador de coluna)
        desc_part = re.sub(r'\s+-\s*$', '', desc_part).strip()

        # Extrair nro documento (5-6 digitos no final da desc)
        doc = None
        m_doc = re.search(r'\s+(\d{5,6})\s*$', desc_part)
        if m_doc:
            doc = m_doc.group(1)
            desc_part = desc_part[:m_doc.start()].strip()

        return desc_part, doc

    def _format_br(self, val: Decimal) -> str:
        """Formata Decimal como string BR para busca."""
        s = f'{float(val):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        # Simplificar: remover ponto de milhar se < 1000
        if val < 1000:
            return f'{float(val):.2f}'.replace('.', ',')
        return s

    def _finalizar_tx(self, tx: dict, ano_ref: int) -> dict:
        """Converte tx pendente em transacao padrao."""
        data = ''
        if tx['data']:
            data = self._normalizar_data(tx['data'], ano_referencia=ano_ref)

        desc = tx['desc'].strip()
        # Limpar desc: remover "-" solto no inicio
        desc = re.sub(r'^-\s+', '', desc).strip()

        return self._transacao(
            data=data,
            descricao=desc,
            valor=tx['valor'],
            tipo=tx['tipo'],
            banco=BANCO,
            raw=tx['raw'],
        )

    def _ignorar(self, linha: str) -> bool:
        """Verifica se a linha deve ser ignorada."""
        lt = linha.lower().strip()
        if lt in _IGNORAR_EXATAS:
            return True
        # Cabecalho de pagina: "fevereiro/2025" etc.
        for m_prefix in _IGNORAR_MESES:
            if lt.startswith(m_prefix):
                return True
        for padrao in _IGNORAR_CONTEM:
            if padrao in lt:
                return True
        return False
