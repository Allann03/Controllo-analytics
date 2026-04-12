"""
santander.py – Parser de extrato de investimentos ContaMax do Santander.

Formato: texto por linha (NÃO tabela — pdfplumber perde linhas sem bordas).
ATENÇÃO: este é extrato ContaMax (investimentos) — NÃO é extrato de conta corrente.

Cada linha de transação:
  DD/MM/YYYY DD/MM/YYYY NUMERO_APLICACAO aplics(R$) ... valor_liquido(R$)

Regra:
  - 4º token (após 2 datas + nº aplicação) > 0 → aplicação (saída de caixa)
  - Último valor na linha > 0                  → resgate creditado (entrada)
  Se ambos > 0 (improvável), entra tem prioridade.
"""

import re
import pdfplumber
from .base import ParserBase
from .santander_empresarial import ParserSantanderEmpresas
from .santander_consolidado import ParserSantanderConsolidado


BANCO = 'Santander'

# Linha de transação: data_mov data_aplic nroaplic aplicacoes ... valor_liquido
_RE_TRANSACAO = re.compile(
    r'^(\d{2}/\d{2}/\d{4})\s+\d{2}/\d{2}/\d{4}\s+(\d{10,})\s+([\d.,]+)\s+'
)

# Último valor BR na linha (= valor líquido creditado)
_RE_ULTIMO_VALOR = re.compile(r'([\d.]+,\d{2})\s*$')

_IGNORAR = [
    'acumulado', 'data do', 'data da', 'n° da', 'n? da', 'aplica',
    'rendimento', 'resgates', 'total das', 'valor l', 'internet banking',
    'cw tour', 'agência', 'extrato do', 'central de', 'ouvidoria',
    'sac ', '4004', '4003', '4002', '0800', 'https://',
]


class ParserSantander(ParserBase):
    """
    Parser para extratos ContaMax / investimentos do Santander.
    Usa extração de texto para capturar todas as linhas de transação.
    """

    def extrair(self) -> list[dict]:
        """
        Extrai transações do extrato Santander.

        Auto-detecção de formato:
          N1 (ContaMax/Investimentos): linhas com duas datas + nº de aplicação de 10+ dígitos
          N2 (Internet Banking Empresarial / Conta Corrente): linhas com data + histórico + valor ±
        Se nenhuma transação N1 for encontrada, delega ao parser N2.
        """
        transacoes: list[dict] = []

        with pdfplumber.open(self.pdf_path, password=self.password or "") as pdf:
            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    texto = pagina.extract_text() or ''
                    for linha in texto.splitlines():
                        t = self._processar_linha(linha)
                        if t:
                            transacoes.append(t)
                except Exception as e:
                    self.avisos.append(f'Santander: erro na página {num}: {e}')

        # Se N1 não produziu resultados, tenta N2 (Internet Banking Empresarial)
        if not transacoes:
            self.avisos.append(
                'Santander: formato ContaMax não detectado — '
                'tentando parser Internet Banking Empresarial (N2).'
            )
            parser_n2 = ParserSantanderEmpresas(self.pdf_path, password=self.password)
            transacoes_n2 = parser_n2.extrair()
            self.avisos.extend(parser_n2.avisos)
            if transacoes_n2:
                return transacoes_n2

            # N2 também sem resultado — tenta N3 (Extrato Consolidado Inteligente)
            self.avisos.append(
                'Santander: formato Empresarial (N2) não detectado — '
                'tentando parser Extrato Consolidado Inteligente (N3).'
            )
            parser_n3 = ParserSantanderConsolidado(self.pdf_path, password=self.password)
            transacoes_n3 = parser_n3.extrair()
            self.avisos.extend(parser_n3.avisos)
            return transacoes_n3

        return self._post_processar(transacoes)

    def _processar_linha(self, linha: str) -> dict | None:
        linha = linha.strip()
        if not linha:
            return None

        linha_lower = linha.lower()
        if any(x in linha_lower for x in _IGNORAR):
            return None

        # A linha deve começar com DD/MM/YYYY DD/MM/YYYY NROAPLIC valor...
        m = _RE_TRANSACAO.match(linha)
        if not m:
            return None

        data_mov = m.group(1)
        num_aplic = m.group(2)
        aplicacao_raw = m.group(3)  # 4º token = aplicações (saída)

        # Último valor na linha = valor líquido creditado (entrada)
        m_last = _RE_ULTIMO_VALOR.search(linha)
        if not m_last:
            return None
        valor_liq_raw = m_last.group(1)

        aplicacao = self._normalizar_valor(aplicacao_raw)
        valor_liq = self._normalizar_valor(valor_liq_raw)

        if aplicacao == 0.0 and valor_liq == 0.0:
            return None

        # Prioridade: resgate (entrada) sobre aplicação (saída)
        if valor_liq > 0.0:
            tipo = 'entrada'
            valor = valor_liq
            desc = f'Resgate ContaMax {num_aplic}'
        else:
            tipo = 'saida'
            valor = aplicacao
            desc = f'Aplicação ContaMax {num_aplic}'

        data = self._normalizar_data(data_mov)

        return self._transacao(
            data=data,
            descricao=desc,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=linha,
        )
