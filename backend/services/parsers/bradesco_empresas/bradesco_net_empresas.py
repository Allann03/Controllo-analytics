"""
bradesco_net_empresas.py – Parser para o extrato Bradesco Net Empresas.

Formato multi-linha com colunas:
  Data | Lançamento | Dcto. | Crédito (R$) | Débito (R$) | Saldo (R$)

Exemplos de linhas:
  02/04/2025 TRANSFERENCIA PIX
  REM: CICLO VIAGENS E TURIS 02/04 703435 9.700,00 -39.930,27
  ENCARGOS C GARANTIDA
  IOF CONTR 4874340 4874340 -249,85 -40.132,42
  OPERACAO CAPITAL GIRO
  CONTR 014869289 PARC 043/052 3510092 -7.478,08 -50.000,00
"""

import re
from .._empresa_base import ParserEmpresaBase, _RE_VALOR, _RE_TRAILING_INTS

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# Data no início da linha: DD/MM/YYYY
_RE_DATA_LINHA = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.*)')

# Sessão 18 — Marcadores que indicam INÍCIO de seção pós-período pedido.
# A partir dessas linhas, todas as transações pertencem a um momento posterior
# ao período do extrato (ex: "Últimos Lançamentos" = movimentações entre fim
# do período e data de emissão; "Saldos Invest Fácil / Plus" = saldos de
# investimento por dia, não são transações de conta corrente). O parser deve
# IGNORAR todas as linhas após encontrar um desses títulos. Marcadores são
# substring-based e tolerantes a encoding (sem acento opcional).
_MARCADORES_FIM_PERIODO = [
    'últimos lançamentos',
    'ultimos lancamentos',
    'saldos invest fácil',
    'saldos invest facil',
]

def _extrair_valores(linha: str):
    """
    Retorna lista de todos os valores monetários encontrados na linha.
    Cada item é a string original (pode ter sinal negativo).
    """
    return _RE_VALOR.findall(linha)


def _limpar_descricao(texto: str) -> str:
    """Remove sequências de inteiros no final e espaços extras."""
    texto = _RE_TRAILING_INTS.sub('', texto)
    return texto.strip()


class ParserBradescoNetEmpresas(ParserEmpresaBase):
    """
    Parser para extratos Bradesco Net Empresas.

    O formato é multi-linha:
    - Uma linha pode iniciar com DD/MM/YYYY seguida de descrição parcial
    - Linhas seguintes continuam a descrição ou carregam os valores
    - Uma linha "de valor" contém os 2 últimos valores monetários:
        penúltimo = valor da transação, último = saldo
    - Linhas de continuação sem valor são acumuladas no buffer de descrição
    """

    BANCO = 'bradesco_net_empresas'

    # Linhas a ignorar (cabeçalhos, rodapés, saldos)
    _SKIP_LOWER = [
        'saldo anterior', 'saldo do dia', 'saldo final', 'saldo em',
        'total disponível', 'total disponivel',
        'lançamento', 'lancamento', 'dcto',
        'banco bradesco', 'extrato', 'período', 'periodo',
        'cpf', 'cnpj',
        'os dados acima', 'nome do usuário', 'nome do usuario',
        'data da operação', 'data da operacao',
        '|',
        'saldos invest fácil', 'saldos invest facil', 'saldo invest fácil', 'saldo invest facil',
        'crédito (r$)', 'credito (r$)', 'débito (r$)', 'debito (r$)',
        'saldo (r$)',
        'últimos lançamentos', 'ultimos lancamentos',
    ]

    def extrair(self) -> list[dict]:
        if pdfplumber is None:
            self.avisos.append('pdfplumber não instalado.')
            return []

        linhas_raw: list[str] = []
        try:
            with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text() or ''
                    linhas_raw.extend(texto.splitlines())
        except Exception as e:
            self.avisos.append(f'Erro ao ler PDF: {e}')
            return []

        transacoes: list[dict] = []
        data_atual: str = ''
        desc_buffer: list[str] = []

        def _emitir(data: str, desc_parts: list[str], valor_str: str, raw: str):
            """Monta e registra uma transação."""
            descricao = ' '.join(desc_parts).strip()
            descricao = _limpar_descricao(descricao)
            if not descricao:
                return
            valor_f = self._normalizar_float(valor_str)
            if valor_f == 0.0:
                return
            tipo = 'entrada' if valor_f > 0 else 'saida'
            t = self._transacao(
                data=data,
                descricao=descricao,
                valor=abs(valor_f),
                tipo=tipo,
                banco=self.BANCO,
                raw=raw,
            )
            transacoes.append(t)

        # Primeira passada: reagrupar linhas multi-linha.
        # Cada transacao pode ter:
        #   Linha N:   descricao parte 1 (texto puro)
        #   Linha N+1: [data] [desc_complemento] doc valor saldo (linha de valores)
        #   Linha N+2: descricao parte 2 (continuacao, texto puro)
        # O reagrupamento junta as 3 partes antes de emitir a transacao.

        # Sessão 18 — Flag de fim de período. Quando a leitura cruza um
        # marcador como "Últimos Lançamentos" ou "Saldos Invest Fácil / Plus",
        # tudo o que vem depois pertence a momento posterior ao período pedido
        # e NÃO deve ser extraído como transação. O flag é cross-página
        # (preserva-se entre iterações de página). Para PDFs sem essas seções
        # (caso comum), o flag nunca dispara e o parser lê até o fim.
        secao_terminada = False

        i = 0
        while i < len(linhas_raw):
            linha = linhas_raw[i]
            i += 1

            # Detecta entrada em seção pós-período (Últimos Lançamentos /
            # Saldos Invest Fácil). Uma vez setado, ignora resto do PDF.
            if not secao_terminada:
                ll_strip = linha.lower().strip()
                if any(marker in ll_strip for marker in _MARCADORES_FIM_PERIODO):
                    secao_terminada = True
                    desc_buffer = []
                    continue
            if secao_terminada:
                continue

            # "Total" line marks end of a period section (mas pode ser o
            # Total do bloco principal, antes de "Últimos Lançamentos").
            # Apenas drena o buffer de descrição e segue.
            if linha.strip().lower().startswith('total ') and _extrair_valores(linha):
                desc_buffer = []
                continue

            if self._e_linha_skip(linha):
                continue

            # Verifica se a linha comeca com uma data
            m_data = _RE_DATA_LINHA.match(linha)
            if m_data:
                nova_data = m_data.group(1)
                resto = m_data.group(2).strip()

                valores = _extrair_valores(linha)
                if len(valores) >= 2:
                    # Linha completa: data + desc + valor + saldo
                    pos_penultimo = linha.rfind(valores[-2])
                    desc_inline = linha[:pos_penultimo].strip()
                    m_d = _RE_DATA_LINHA.match(desc_inline)
                    if m_d:
                        desc_inline = m_d.group(2).strip()
                    desc_parts = desc_buffer + ([desc_inline] if desc_inline else [])

                    # Olhar proxima linha: se e descricao pura, e continuacao
                    desc_depois = ''
                    if i < len(linhas_raw):
                        prox = linhas_raw[i].strip()
                        if prox and not self._e_linha_skip(prox) and not _RE_DATA_LINHA.match(prox) and len(_extrair_valores(prox)) < 2:
                            desc_depois = prox
                            i += 1

                    if desc_depois:
                        desc_parts.append(desc_depois)

                    _emitir(nova_data if nova_data else data_atual, desc_parts, valores[-2], linha)
                    data_atual = nova_data
                    desc_buffer = []
                else:
                    # Linha apenas com data + inicio da descricao
                    data_atual = nova_data
                    desc_buffer = [resto] if resto else []
            else:
                # Linha de continuacao (sem data no inicio)
                valores = _extrair_valores(linha)
                if len(valores) >= 2:
                    # Linha de valor: penultimo = transacao, ultimo = saldo
                    pos_penultimo = linha.rfind(valores[-2])
                    desc_complemento = linha[:pos_penultimo].strip()
                    desc_parts = desc_buffer + ([desc_complemento] if desc_complemento else [])

                    # Olhar proxima linha: se e descricao pura, e continuacao desta tx
                    desc_depois = ''
                    if i < len(linhas_raw):
                        prox = linhas_raw[i].strip()
                        if prox and not self._e_linha_skip(prox) and not _RE_DATA_LINHA.match(prox) and len(_extrair_valores(prox)) < 2:
                            desc_depois = prox
                            i += 1

                    if desc_depois:
                        desc_parts.append(desc_depois)

                    _emitir(data_atual, desc_parts, valores[-2], linha)
                    desc_buffer = []
                elif len(valores) == 1:
                    desc_buffer.append(linha.strip())
                else:
                    # Linha de descricao pura — acumula
                    desc_buffer.append(linha.strip())

        # Deduplicacao removida — causava descarte de transacoes legitimas
        # identicas (ex: multiplos TITULO DE CAPITALIZACAO no mesmo dia/valor).
        # Se necessario, deduplicacao deve ocorrer na camada de banco de dados.
        return self._post_processar(transacoes)
