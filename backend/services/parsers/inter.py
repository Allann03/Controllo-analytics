"""
inter.py – Parser de extrato do Banco Inter.

Formato: texto por linha (NÃO tabela).
Linhas de data:   'N de Mês de AAAA Saldo do dia: R$ X ...'
Linhas de transação: 'Tipo: "Descrição" [-]R$ valor R$ saldo'
                 ou: 'TIPO -R$ valor R$ saldo'

Saldo do dia → ignorado (não é transação).
Aplicações automáticas → ignoradas.
Verificação cruzada: sinal do R$ + palavras-chave.
"""

import re
import pdfplumber
from .base import ParserBase


BANCO = 'Inter'

# Mês por extenso → número
_MESES = {
    'janeiro': '01', 'fevereiro': '02', 'março': '03', 'marco': '03',
    'abril': '04', 'maio': '05', 'junho': '06',
    'julho': '07', 'agosto': '08', 'setembro': '09',
    'outubro': '10', 'novembro': '11', 'dezembro': '12',
}

# Ex: "1 de Dezembro de 2025 Saldo do dia: ..."
_RE_DATA_HEADER = re.compile(
    r'^(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', re.IGNORECASE
)

# Transação: tipo/desc + [-]R$ valor + R$ saldo (ao final)
_RE_TRANSACAO = re.compile(
    r'^(.+?)\s+(-?R\$\s*[\d.,]+)\s+-?R\$\s*[\d.,]+\s*$'
)

# Tipo e descrição entre aspas: "Pix recebido: "texto""
_RE_TIPO_DESC = re.compile(r'^([^:]+?)(?::\s*"([^"]+)")?$')

# Linhas que devem ser inteiramente ignoradas
_IGNORAR = [
    'saldo do dia', 'saldo total', 'saldo disponível', 'saldo disponivel',
    'saldo bloqueado', 'saldo inicial', 'saldo final',
    'fale com a gente',
    'sac:', 'ouvidoria:', 'deficiência', 'deficiencia',
    'data', 'valor', 'solicitado em',
    'total de entradas', 'total de saídas', 'total de saidas',
]

_ENTRADAS = [
    'recebido', 'recebida', 'credito', 'crédito', 'resgate',
    'estorno', 'devolução', 'devolucao',
    'transferencia recebida', 'transferência recebida',
]

_SAIDAS = [
    'enviado', 'enviada', 'pagamento', 'pagto', 'debito', 'débito',
    'tarifa', 'taxa', 'saque', 'compra', 'simples nacional', 'darf',
]

# Tipos de movimentação interna que NÃO devem ser capturados como transação
# Nota: aplicação de fundos é um débito real da conta — deve ser incluída
_IGNORAR_TIPOS: list[str] = []


class ParserInter(ParserBase):
    """Parser para extratos do Banco Inter (formato texto por linha)."""

    def _extrair_saldos_intermediarios(self) -> list[dict]:
        """Extrai 'D de Mes de AAAA Saldo do dia: R$ X.XXX,XX' do extrato Inter."""
        saldos = []
        _re_saldo = re.compile(
            r'Saldo\s+do\s+dia:\s*-?R\$\s*([\d.,]+)', re.IGNORECASE
        )
        try:
            with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
                data_atual = None
                for page in pdf.pages:
                    texto = page.extract_text() or ''
                    for linha in texto.split('\n'):
                        m_data = _RE_DATA_HEADER.match(linha.strip())
                        if m_data:
                            dia, mes_nome, ano = m_data.group(1), m_data.group(2).lower(), m_data.group(3)
                            num_mes = _MESES.get(mes_nome, '')
                            if num_mes:
                                data_atual = f"{int(dia):02d}/{num_mes}/{ano}"
                        m_saldo = _re_saldo.search(linha)
                        if m_saldo and data_atual:
                            valor = self._normalizar_valor(m_saldo.group(1))
                            saldos.append({'data': data_atual, 'saldo': valor})
        except Exception:
            pass
        return saldos

    def extrair(self) -> list[dict]:
        """Extrai transações do extrato Inter via texto."""
        transacoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
            data_atual = ''

            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    texto = pagina.extract_text() or ''
                    for linha in texto.splitlines():
                        t = self._processar_linha(linha.strip(), data_atual)
                        if t == 'data':
                            data_atual = self._extrair_data(linha)
                        elif t is not None:
                            if data_atual:
                                t['data'] = data_atual
                            transacoes.append(t)
                except Exception as e:
                    self.avisos.append(f'Inter: erro na página {num}: {e}')

        # Tripla verificação: estrutura + data + deduplicação
        return self._post_processar(transacoes)

    def _extrair_data(self, linha: str) -> str:
        """Extrai data no formato DD/MM/AAAA de um header de data."""
        m = _RE_DATA_HEADER.match(linha.strip())
        if not m:
            return ''
        dia = m.group(1).zfill(2)
        mes_nome = m.group(2).lower()
        mes = _MESES.get(mes_nome, '01')
        ano = m.group(3)
        return f'{dia}/{mes}/{ano}'

    def _processar_linha(self, linha: str, data_atual: str) -> dict | str | None:
        """
        Returns:
            'data'  – linha é um header de data
            dict    – transação válida
            None    – linha ignorada
        """
        if not linha:
            return None

        linha_lower = linha.lower()

        # Header de data: "1 de Dezembro de 2025..."
        if _RE_DATA_HEADER.match(linha):
            return 'data'

        # Ignora saldos do dia e metadados
        if any(x in linha_lower for x in _IGNORAR):
            return None

        # Linha de transação: tipo/desc + valor + saldo
        m = _RE_TRANSACAO.match(linha)
        if not m:
            return None

        tipo_desc_raw = m.group(1).strip()
        valor_raw = m.group(2).strip()  # pode começar com '-R$' ou 'R$'

        tipo_desc_lower = tipo_desc_raw.lower()

        # Ignora aplicações internas (movimentação automática)
        if any(x in tipo_desc_lower for x in _IGNORAR_TIPOS):
            return None

        # Separa tipo e descrição (para linhas com ': "desc"')
        m2 = _RE_TIPO_DESC.match(tipo_desc_raw)
        if m2 and m2.group(2):
            tipo_raw = m2.group(1).strip()
            desc = f'{tipo_raw}: {m2.group(2).strip()}'
        else:
            desc = tipo_desc_raw

        # ── Verificação 1: valor ──────────────────────────────────────
        valor = self._normalizar_valor(valor_raw)
        if valor == 0.0:
            return None

        # ── Verificação 2: tipo (sinal + palavras-chave) ──────────────
        negativo = valor_raw.startswith('-') or '-R$' in valor_raw
        tipo_por_sinal = 'saida' if negativo else ''

        tipo = self._verificar_tipo_cruzado(
            tipo_por_sinal=tipo_por_sinal,
            descricao=desc,
            palavras_entrada=_ENTRADAS,
            palavras_saida=_SAIDAS,
        )

        return self._transacao(
            data=data_atual,
            descricao=desc,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=linha,
        )
