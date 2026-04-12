"""
Parser do Itau Extrato Mensal (formato tabular PJ/Empresas).

Layout:
  - Colunas: data | descricao | entradas R$ (creditos) | saidas R$ (debitos) | saldo R$
  - Saidas com sufixo '-' no valor (ex: 651,00-)
  - Entradas sem sufixo (ex: 400.533,02)
  - Linhas sem data = mesma data da ultima transacao com data
  - Stop sections: totalizador de aplicacoes, Aplicacoes Automaticas,
    Debitos automaticos efetuados, Cheque Especial, 02. Investimentos

Identificadores unicos:
  - "extrato mensal ag" no cabecalho
  - "saldo aplic aut mais" no corpo
  - 4 colunas: entradas R$ / saidas R$ / saldo R$

BLOCO 8 -- P0 Itau.
"""

import re
from decimal import Decimal
from .base import ParserBase

# -- Regex para valor brasileiro (com ou sem sufixo '-') -----------------------
_RE_VALOR_BR = re.compile(r'-?\d{1,3}(?:\.\d{3})*,\d{2}-?')

# -- Regex para data DD/MM no inicio da linha ----------------------------------
_RE_DATA = re.compile(r'^(\d{2}/\d{2})\s+')

# -- Stop sections — parar de extrair transacoes ao encontrar -----------------
_STOP_SECTIONS = [
    'totalizador de aplicações automáticas',
    'totalizador de aplicacoes automaticas',
    'conta corrente | aplicações automáticas',
    'conta corrente | aplicacoes automaticas',
    'conta corrente | débitos automáticos efetuados',
    'conta corrente | debitos automaticos efetuados',
    'conta corrente | cheque especial',
    '02. investimentos',
    'notas explicativas',
    'indicadores de mercado',
]

# -- Linhas de saldo (NAO sao transacoes) -------------------------------------
_SALDO_SKIP = [
    'saldo aplic aut mais',
    'saldo anterior',
    'saldo em c/c',
    'saldo final',
    'saldo total disponível',
    'saldo total disponivel',
]

# -- Aplicacoes automaticas (movimentacao interna de investimento) --------------
# O extrato diz: "Os valores referentes ao totalizador de aplicações automáticas
# NÃO estão somados no resumo de movimentação de conta corrente."
# Apl (aplicacao) e Res (resgate) sao movimentacoes internas — excluir.
# Rend (rendimento) e DA (debito automatico) sao creditados/debitados na C/C — manter.
_APLIC_AUTO_SKIP = [
    'apl aplic aut mais',
    'res aplic aut mais',
]

# -- Entradas (creditos) — keywords -------------------------------------------
_ENTRADAS = [
    'rede mast', 'rede visa', 'rede elo',
    'pix transf', 'pix receb',
    'ted ', 'doc ', 'tec ',
    'res aplic aut mais', 'rend pago aplic aut mais',
    'resgate', 'estorno',
    'mov tít cob disp', 'mov tit cob disp',
    'sispag ancoradouro', 'sispag tp air', 'sispag global',
    'sispag inti', 'sispag lkm',
]

# -- Saidas (debitos) — keywords ----------------------------------------------
_SAIDAS = [
    'sispag fornecedores', 'sispag tributos',
    'apl aplic aut mais',
    'tar pix', 'tar/', 'tarifa',
    'da vivo', 'da claro', 'da net serv',
    'déb autor', 'deb autor',
    'pre aplicação', 'pre aplicacao',
    'ag. aplicação', 'ag. aplicacao',
    'iof',
]


class ParserItauExtratoMensal(ParserBase):
    """Parser para Itau Extrato Mensal (formato tabular com colunas entradas/saidas/saldo)."""

    def extrair(self) -> list[dict]:
        import pdfplumber

        transacoes = []
        data_atual = None
        ano_ref = None
        stop = False

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                if stop:
                    break

                text = page.extract_text() or ''
                lines = text.split('\n')

                for line in lines:
                    line_strip = line.strip()
                    if not line_strip:
                        continue

                    line_lower = line_strip.lower()

                    # -- Detectar ano de referencia do cabecalho --
                    if ano_ref is None:
                        m_ano = re.search(r'(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\s+(\d{4})', line_lower)
                        if m_ano:
                            ano_ref = int(m_ano.group(1))

                    # -- Stop sections --
                    if any(s in line_lower for s in _STOP_SECTIONS):
                        stop = True
                        break

                    # -- Skip cabecalhos de coluna --
                    if 'entradas r$' in line_lower or 'saídas r$' in line_lower or 'saidas r$' in line_lower:
                        continue
                    if line_lower.startswith('este material'):
                        continue

                    # -- Legendas coladas com transacao: "P = poupança automática Sispag Fornecedores 1.345,87-"
                    # Extrair a parte da transacao apos a legenda
                    _LEGENDAS = [
                        'a = agendamento', 'b = ações movimentadas', 'b = acoes movimentadas',
                        'pela bolsa de valores', 'c = crédito a compensar', 'c = credito a compensar',
                        'd = débito a compensar', 'd = debito a compensar',
                        'g = aplicação programada', 'g = aplicacao programada',
                        'p = poupança automática', 'p = poupanca automatica',
                        'para demais siglas, consulte as notas',
                        'explicativas no final do extrato',
                    ]
                    legenda_encontrada = False
                    for leg in _LEGENDAS:
                        if line_lower.startswith(leg):
                            # Verificar se ha uma transacao colada apos a legenda
                            resto_apos_leg = line_strip[len(leg):].strip()
                            if resto_apos_leg and _RE_VALOR_BR.search(resto_apos_leg):
                                # Ha um valor — tratar como transacao
                                line_strip = resto_apos_leg
                                line_lower = line_strip.lower()
                                legenda_encontrada = True
                            else:
                                legenda_encontrada = True
                                break
                    if legenda_encontrada and not _RE_VALOR_BR.search(line_strip):
                        continue

                    # -- Detectar linhas de saldo (pular) --
                    if any(s in line_lower for s in _SALDO_SKIP):
                        continue

                    # -- Pular aplicacoes automaticas (movimentacao interna) --
                    if any(s in line_lower for s in _APLIC_AUTO_SKIP):
                        continue

                    # -- Extrair data se presente --
                    m_data = _RE_DATA.match(line_strip)
                    if m_data:
                        data_str = m_data.group(1)
                        # Resolver ano
                        if ano_ref:
                            data_atual = f"{data_str}/{ano_ref}"
                        else:
                            data_atual = f"{data_str}/2025"
                        # Restante da linha apos a data
                        resto = line_strip[m_data.end():].strip()
                    else:
                        resto = line_strip

                    if not data_atual:
                        continue

                    # -- Extrair valores da linha --
                    valores = _RE_VALOR_BR.findall(resto)
                    if not valores:
                        continue

                    # -- Extrair descricao (texto antes do primeiro valor) --
                    primeiro_val_pos = resto.find(valores[0])
                    descricao = resto[:primeiro_val_pos].strip() if primeiro_val_pos > 0 else ''

                    if not descricao:
                        continue

                    # Limpar descricao
                    descricao = re.sub(r'\s+', ' ', descricao).strip()

                    # -- Identificar se e saldo ou aplic auto com descricao --
                    desc_lower = descricao.lower()
                    if any(s in desc_lower for s in _SALDO_SKIP):
                        continue
                    if any(s in desc_lower for s in _APLIC_AUTO_SKIP):
                        continue

                    # -- Determinar valor e tipo --
                    # Itau Extrato Mensal: entradas na coluna esquerda, saidas na coluna direita
                    # Saidas tem sufixo '-' (ex: 651,00-)
                    # Se ha 2+ valores, o ultimo pode ser saldo (ignorar)

                    # Pegar o primeiro valor que nao e o saldo final da linha
                    valor_str = valores[0]

                    # Verificar sufixo '-' para saida
                    eh_saida = valor_str.endswith('-') or valor_str.startswith('-')

                    # Normalizar valor
                    valor_limpo = valor_str.replace('-', '').strip()
                    valor = self._normalizar_valor(valor_limpo)

                    if valor is None or valor <= 0:
                        continue

                    # -- Determinar tipo por keyword + sinal --
                    if eh_saida:
                        tipo = 'saida'
                    elif any(k in desc_lower for k in _SAIDAS):
                        tipo = 'saida'
                    elif any(k in desc_lower for k in _ENTRADAS):
                        tipo = 'entrada'
                    else:
                        # Se tem sufixo '-', e saida; senao, usar heuristica
                        # Valores na coluna "saidas" sempre tem '-'
                        tipo = 'entrada'

                    transacoes.append(self._transacao(
                        data=data_atual,
                        descricao=descricao,
                        valor=valor,
                        tipo=tipo,
                        banco='itau_extrato_mensal',
                        raw=line_strip,
                    ))

        return self._post_processar(transacoes)
