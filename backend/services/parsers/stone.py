"""
stone.py – Parser de extrato da Stone.

Suporta dois formatos:

Formato 1 (tabela 6 colunas — extratos antigos):
  DATA | TIPO | DESCRIÇÃO | VALOR | SALDO | CONTRAPARTE

Formato 2 (texto por linha — extratos novos com layout multi-linha):
  O layout Stone em PDF não é tabelado — o texto é extraído por pdfplumber em linhas.
  Cada transação pode aparecer em várias linhas, na ordem:
    [contraparte / descrição — em linhas anteriores à data]
    DD/MM/YY  Tipo  [descrição-inline | R$]  -?R$ valor  R$ saldo  [contraparte-tail]
    [descrição extra — em linhas seguintes à data]

  Casos suportados:
  a) Saída com contraparte inline:
     "31/12/25 Saída STONE S.A. - R$ 1,97 R$ 13.575,99"
  b) Entrada/Saída sem desc inline — descrição vem nas linhas ANTES:
     "Keliane Santos de Araujo"
     "31/12/25 Entrada R$ 65,00 R$ 13.480,40"
  c) Entrada com descrição inline:
     "31/12/25 Entrada VETERINARIOS BICHO BAO LTDA R$ 9.000,00 R$ 14.001,09"

Filtros:
  - "Parcela | Empréstimo" (Stone S.A.) → saída de empréstimo, capturada
  - "Recebimento vendas / Antecipação" → entrada de vendas capturada
  - Saldo, cabeçalhos, metadados → ignorados

Verificação tripla via _post_processar().
"""

import re
import pdfplumber
from .base import ParserBase


BANCO = 'Stone'

_RE_ANO = re.compile(r'\b(20\d{2})\b')

# Caso (a) e (c): DD/MM/YY Tipo <desc> -? R$ valor R$ saldo
_RE_LINHA_TEXTO = re.compile(
    r'^(\d{2}/\d{2}/\d{2,4})\s+(Entrada|Sa[ií]da)\s+(.+?)\s+-?\s*R\$\s*([\d.,]+)\s+R\$',
    re.IGNORECASE,
)

# Caso (b): DD/MM/YY Tipo R$ valor R$ saldo [tail]
# Não tem descrição entre o Tipo e o R$ do valor
_RE_LINHA_SIMPLES = re.compile(
    r'^(\d{2}/\d{2}/\d{2,4})\s+(Entrada|Sa[ií]da)\s+R\$\s*([\d.,]+)\s+R\$',
    re.IGNORECASE,
)

# Captura saldo (último R$ X,XX da linha) para extração de saldos intermediários.
_RE_SALDO_TAIL_N1 = re.compile(
    r'^(\d{2}/\d{2}/\d{2,4})\s+(?:Entrada|Sa[ií]da).*?R\$\s*[\d.,]+\s+R\$\s*([\d.,]+)',
    re.IGNORECASE,
)

# Detecta se uma linha é uma linha de data (início de nova transação)
_RE_E_DATA = re.compile(r'^\d{2}/\d{2}/\d{2,4}\s+(?:Entrada|Sa[ií]da)', re.IGNORECASE)

_IGNORAR_DESC = [
    'data', 'tipo', 'descrição', 'descricao', 'valor', 'saldo',
    'contraparte', 'lançamento', 'lancamento', 'histórico', 'historico',
    'emitido em', 'página', 'pagina', 'período', 'periodo',
    'dados da conta', 'nome', 'documento', 'instituição', 'agência', 'conta',
]

_IGNORAR_BUFFER = [
    'emitido em', 'página', 'pagina', 'período', 'periodo',
    'dados da conta', 'stone institui', 'stone pagamentos',
    'ag:', 'cc:', 'extrato de conta',
]


class ParserStone(ParserBase):
    """Parser para extratos da Stone (tabela e texto por linha)."""

    def _detectar_formato(self) -> str:
        """
        Detecta o formato do extrato lendo as primeiras páginas.

        Retorna:
          'n2'   → formato Crédito/Débito (N2 é o parser correto)
          'n1'   → formato Entrada/Saída  (N1 é o parser correto)
          'auto' → ambíguo, testa os dois
        """
        try:
            with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
                # Lê até 3 páginas para ter amostra suficiente
                texto = ' '.join(
                    (p.extract_text() or '') for p in pdf.pages[:3]
                ).lower()

            tem_credito_debito = 'crédito' in texto or 'débito' in texto
            tem_entrada_saida  = 'entrada' in texto or 'saída'  in texto

            if tem_credito_debito and not tem_entrada_saida:
                return 'n2'
            if tem_entrada_saida and not tem_credito_debito:
                return 'n1'
            # Ambos presentes → ambíguo
            return 'auto'
        except Exception:
            return 'auto'

    def extrair(self) -> list[dict]:
        """Extrai transações do extrato Stone com detecção automática de formato."""
        from .stone_n2 import ParserStoneN2

        fmt = self._detectar_formato()

        # ── Formato N2 identificado claramente → delega direto ───────────────
        if fmt == 'n2':
            n2 = ParserStoneN2(self.pdf_path, password=self.password)
            resultado = n2.extrair()
            self.avisos.extend(n2.avisos)
            return resultado

        # ── Formato N1 ou ambíguo: roda N1 primeiro ──────────────────────────
        transacoes: list[dict] = []
        with pdfplumber.open(self.pdf_path, password=self.password or "") as pdf:
            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    tabelas = pagina.extract_tables()
                    achou = False
                    for tabela in tabelas:
                        for linha in tabela:
                            t = self._processar_linha_tabela(linha)
                            if t:
                                transacoes.append(t)
                                achou = True
                    if not achou:
                        texto = pagina.extract_text() or ''
                        transacoes.extend(self._extrair_texto_pagina(texto))
                except Exception as e:
                    self.avisos.append(f'Stone: erro na página {num}: {e}')

        resultado_n1 = self._post_processar(transacoes)

        # ── Formato N1 confirmado → retorna sem verificação cruzada ─────────
        if fmt == 'n1':
            return resultado_n1

        # ── Formato ambíguo: roda N2 e escolhe o melhor ──────────────────────
        n2 = ParserStoneN2(self.pdf_path, password=self.password)
        resultado_n2 = n2.extrair()
        self.avisos.extend(n2.avisos)

        if not resultado_n1 and resultado_n2:
            return resultado_n2

        if resultado_n1 and resultado_n2:
            soma_n1 = round(
                sum(t['valor'] for t in resultado_n1 if t.get('tipo') == 'entrada') -
                sum(t['valor'] for t in resultado_n1 if t.get('tipo') == 'saida'), 2
            )
            soma_n2 = round(
                sum(t['valor'] for t in resultado_n2 if t.get('tipo') == 'entrada') -
                sum(t['valor'] for t in resultado_n2 if t.get('tipo') == 'saida'), 2
            )
            if len(resultado_n1) == len(resultado_n2) and abs(soma_n1 - soma_n2) < 0.01:
                return resultado_n1
            # Discordância genuína em formato ambíguo: avisa pois exige atenção
            maior = resultado_n2 if len(resultado_n2) > len(resultado_n1) else resultado_n1
            menor = len(resultado_n1) if len(resultado_n2) > len(resultado_n1) else len(resultado_n2)
            self.avisos.append(
                f'Atenção: parsers retornaram contagens diferentes '
                f'({len(resultado_n1)} vs {len(resultado_n2)} transações). '
                f'Usando o resultado com maior cobertura. Verifique o extrato manualmente.'
            )
            return maior

        return resultado_n1

    def _extrair_texto_pagina(self, texto: str) -> list[dict]:
        """
        Extrai transações de uma página Stone usando buffer pré-data.

        O layout Stone coloca contraparte/descrição nas linhas ANTES da
        linha com a data, e às vezes nas linhas APÓS. Esta função acumula
        linhas antes de cada data como descrição de fallback.
        """
        transacoes: list[dict] = []
        pre_buffer: list[str] = []  # linhas antes da data atual

        for linha in texto.splitlines():
            linha = linha.strip()
            if not linha:
                continue

            # Se é uma linha de transação (começa com data + Entrada/Saída)
            if _RE_E_DATA.match(linha):
                t = self._processar_linha_data(linha, pre_buffer)
                if t:
                    transacoes.append(t)
                pre_buffer.clear()
            else:
                # Acumula no buffer, filtrando cabeçalhos e metadados
                linha_lower = linha.lower()
                if not any(x in linha_lower for x in _IGNORAR_BUFFER):
                    if not any(x in linha_lower for x in _IGNORAR_DESC):
                        # Só acumula linhas com conteúdo descritivo
                        if re.search(r'[a-zA-ZÀ-ÿ]', linha):
                            pre_buffer.append(linha)

        return transacoes

    def _processar_linha_data(self, linha: str, pre_buffer: list[str]) -> dict | None:
        """
        Processa linha que começa com data + Tipo.

        Tenta regex completo (desc inline) primeiro; se falhar, usa regex
        simples e usa pre_buffer como descrição.
        """
        # Caso (a)/(c): com descrição inline antes do R$
        m = _RE_LINHA_TEXTO.match(linha)
        if m:
            data_raw = m.group(1)
            tipo_raw = m.group(2).lower()
            desc_raw = m.group(3).strip()
            valor_raw = m.group(4)

            desc_lower = desc_raw.lower()
            if any(x in desc_lower for x in _IGNORAR_DESC):
                desc_raw = ' '.join(pre_buffer).strip() or desc_raw

            # ── Verificação 1: valor ──────────────────────────────────
            valor = self._normalizar_valor(valor_raw)
            if valor == 0.0:
                return None
            valor = self._segunda_verificacao_valor(linha, valor)

            # ── Verificação 2: tipo — palavra Entrada/Saída é autoritária
            tipo = 'entrada' if 'entrada' in tipo_raw else 'saida'
            data = self._normalizar_data(data_raw)

            return self._transacao(
                data=data,
                descricao=desc_raw,
                valor=valor,
                tipo=tipo,
                banco=BANCO,
                raw=linha,
            )

        # Caso (b): R$ direto após o Tipo — usa buffer como descrição
        m2 = _RE_LINHA_SIMPLES.match(linha)
        if m2:
            data_raw = m2.group(1)
            tipo_raw = m2.group(2).lower()
            valor_raw = m2.group(3)

            # ── Verificação 1: valor ──────────────────────────────────
            valor = self._normalizar_valor(valor_raw)
            if valor == 0.0:
                return None
            valor = self._segunda_verificacao_valor(linha, valor)

            # Usa buffer como descrição; filtra entradas indesejadas do buffer
            desc_parts = [
                p for p in pre_buffer
                if not any(x in p.lower() for x in _IGNORAR_BUFFER)
            ]
            desc_raw = ' '.join(desc_parts).strip() or 'Stone'

            # ── Verificação 2: tipo — palavra Entrada/Saída é autoritária
            tipo = 'entrada' if 'entrada' in tipo_raw else 'saida'
            data = self._normalizar_data(data_raw)

            return self._transacao(
                data=data,
                descricao=desc_raw,
                valor=valor,
                tipo=tipo,
                banco=BANCO,
                raw=linha,
            )

        return None

    def _processar_linha_texto(self, linha: str) -> dict | None:
        """Mantido para compatibilidade (legado)."""
        return self._processar_linha_data(linha, [])

    # ------------------------------------------------------------------ #
    # Saldos intermediários — espelha o roteamento de extrair()           #
    # ------------------------------------------------------------------ #

    def _extrair_saldos_intermediarios(self) -> list[dict]:
        """
        Extrai saldo de fechamento por dia para alimentar a verificação
        progressiva do orquestrador. Stone não tem label "Saldo do dia":
        a coluna SALDO mostra saldo pós-tx e o extrato vem em ordem
        cronológica reversa, então a primeira ocorrência por data é o
        saldo de fechamento daquele dia.

        Roteia entre N1 (Layout B, "Entrada/Saída") e N2 (Layout A,
        "Crédito/Débito") espelhando o que extrair() faz.

        Retorna [{'data': 'DD/MM/YYYY', 'saldo': float}] em ordem
        cronológica crescente, ou [] se nada capturado.
        """
        from .stone_n2 import ParserStoneN2

        fmt = self._detectar_formato()

        if fmt == 'n2':
            return ParserStoneN2(self.pdf_path, password=self.password)._extrair_saldos_intermediarios()

        saldos_n1 = self._extrair_saldos_intermediarios_n1()

        if fmt == 'n1':
            return saldos_n1

        # Ambíguo: roda os dois e fica com o de maior cobertura, igual extrair()
        saldos_n2 = ParserStoneN2(self.pdf_path, password=self.password)._extrair_saldos_intermediarios()
        if not saldos_n1 and saldos_n2:
            return saldos_n2
        if saldos_n1 and saldos_n2 and len(saldos_n2) > len(saldos_n1):
            return saldos_n2
        return saldos_n1

    def _extrair_saldos_intermediarios_n1(self) -> list[dict]:
        """Layout B (Entrada/Saída, valores com prefixo R$)."""
        saldos_por_data: dict[str, float] = {}
        try:
            with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text() or ''
                    for linha in texto.splitlines():
                        m = _RE_SALDO_TAIL_N1.match(linha.strip())
                        if not m:
                            continue
                        data = self._normalizar_data(m.group(1))
                        # Primeira ocorrência por data = fechamento (extrato é reverso)
                        if data and data not in saldos_por_data:
                            saldos_por_data[data] = float(self._normalizar_valor(m.group(2)))
        except (FileNotFoundError, OSError):
            return []

        if not saldos_por_data:
            return []
        ordenadas = sorted(
            saldos_por_data.items(),
            key=lambda kv: (int(kv[0][6:10]), int(kv[0][3:5]), int(kv[0][0:2])),
        )
        return [{'data': d, 'saldo': s} for d, s in ordenadas]

    def _processar_linha_tabela(self, linha: list) -> dict | None:
        if not linha or len(linha) < 3:
            return None

        data_raw = str(linha[0] or '').strip()
        if not data_raw or not re.match(r'^\d{2}/\d{2}', data_raw):
            return None

        # Coluna TIPO (índice 1) pode ser 'Entrada' ou 'Saída'
        tipo_col = str(linha[1] or '').strip().lower()

        # Descrição (índice 2 ou 3 dependendo do layout)
        desc_raw = ''
        for idx in [2, 3]:
            if len(linha) > idx:
                cell = str(linha[idx] or '').strip()
                if cell and not cell.lower() in ('entrada', 'saída', 'saida'):
                    desc_raw = cell
                    break

        desc_lower = desc_raw.lower()
        if any(x in desc_lower for x in _IGNORAR_DESC):
            return None

        # Valor: prefere a coluna imediatamente após a descrição
        valor_raw = ''
        for cell in reversed(linha):
            cell_str = str(cell or '').strip()
            if cell_str and any(c.isdigit() for c in cell_str) and '/' not in cell_str:
                valor_raw = cell_str
                break

        if not valor_raw:
            return None

        # ── Verificação 1: valor ──────────────────────────────────────
        valor = self._normalizar_valor(valor_raw)
        if valor == 0.0:
            return None

        # ── Verificação 2: tipo — palavra Entrada/Saída é autoritária ─
        if 'entrada' in tipo_col or 'crédito' in tipo_col or 'credito' in tipo_col:
            tipo = 'entrada'
        elif 'saída' in tipo_col or 'saida' in tipo_col:
            tipo = 'saida'
        else:
            negativo = '-' in valor_raw or valor_raw.startswith('(')
            tipo = 'saida' if negativo else 'entrada'

        data = self._normalizar_data(data_raw)

        return self._transacao(
            data=data,
            descricao=desc_raw,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw='|'.join(str(c) for c in linha),
        )
