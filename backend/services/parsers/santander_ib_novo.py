r"""
santander_ib_novo.py – Parser para Santander Internet Banking Empresarial,
layout NOVO.

Características exclusivas do layout (do diagnóstico Parte 1, seção 8):
  1. Bullet '•' no início de cada linha de transação. O pdfplumber NÃO
     preserva U+2022; em vez disso emite glifos da Private Use Area da
     fonte Wingdings/iconográfica:
       - U+F12E = crédito (entrada)
       - U+F131 = débito  (saída)
     Esses glifos NÃO são usados como sinal de tipo: o sinal canônico
     é o '- R$' descrito no diagnóstico. O prefixo PUA é apenas
     descartado.
  2. Datas em ordem DESCENDENTE no PDF (31/01 → 30/01 → ...). Após o
     parse o resultado é reordenado por data ASCENDENTE preservando a
     ordem relativa dentro do mesmo dia (sort estável).
  3. Sinal de débito é '- R$' (hífen + ESPAÇO + R$). Crédito é
     'R$' sem hífen.
  4. Linhas de saldo (formato 'DD/MM/YYYY Saldo do dia R$ X,XX') são
     filtradas: o filtro casa apenas quando 'Saldo do dia' aparece
     imediatamente após a data, evitando falsos positivos com
     descrições que contenham a expressão.

Cabeçalhos/footers (logos, telefones, totalizadores 'A - Saldo de Conta
Corrente R$ ...') NÃO começam com data DD/MM/YYYY e portanto são
naturalmente filtrados pelo regex de transação.

Quebras de página geram duplicatas (a última linha de uma página
reaparece como primeira da página seguinte). A dedup compara a primeira
transação parseada de cada nova página com a última da página anterior;
se idênticas em (data, descrição normalizada, valor), descarta a primeira
da nova página. Duplicatas legítimas dentro da mesma página (mesmo dia,
mesma descrição, mesmo valor — pagamentos repetidos reais) são
preservadas.
"""

import re
import pdfplumber
from .base import ParserBase


BANCO = 'Santander'

# Cabeçalhos do fixture de ground truth (Turno 1 do projeto).
_RE_FIXTURE_HEADER = re.compile(r'^(#\s*(SOURCE|PAGES)|=====\s*PAGE)', re.IGNORECASE)

# Marcador de início de página no fixture.
_RE_FIXTURE_PAGE_BREAK = re.compile(r'^=====\s*PAGE\b', re.IGNORECASE)

# 'DD/MM/YYYY Saldo do dia ...' logo no início (ajuste 1 do plano: regex
# ancorada à posição da data, não substring).
_RE_SALDO_DO_DIA = re.compile(r'^\d{2}/\d{2}/\d{4}\s+Saldo\s+do\s+dia\b', re.IGNORECASE)

# Linha de transação. Após strip e remoção de prefixo (PUA + espaços):
#   data         '- '?  R$  valor
# Aceita 'R\$\s*' (espaço opcional) para tolerar PDFs que cohlam o R\$
# ao número.
_RE_TRANSACAO = re.compile(
    r'^(\d{2}/\d{2}/\d{4})\s+(.+?)(\s+-)?\s+R\$\s*([\d.]+,\d{2})\s*$'
)


def _strip_prefix(linha: str) -> str:
    """Remove glifos da Private Use Area Unicode no início + espaços."""
    i = 0
    n = len(linha)
    while i < n:
        ch = linha[i]
        if ch.isspace() or 0xF000 <= ord(ch) <= 0xF999:
            i += 1
            continue
        break
    return linha[i:]


class ParserSantanderIBNovo(ParserBase):
    """
    Parser para o layout novo do Internet Banking Empresarial Santander.
    """

    def _extrair_saldos_intermediarios(self) -> list[dict]:
        """Sessão 19 — extrai os 'DD/MM/YYYY Saldo do dia R$ X,XX' como
        saldos diários (saldo de FECHAMENTO de cada dia). Útil para o
        validador da Sessão 18 (Check 2 saldos diários, Check 3 continuidade).

        Retorna lista [{data: 'DD/MM/YYYY', saldo: float}] em ordem
        cronológica ASCENDENTE.
        """
        from decimal import Decimal as _D
        saldos: list[dict] = []
        try:
            with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
                for pagina in pdf.pages:
                    try:
                        texto = pagina.extract_text() or ''
                    except Exception:
                        continue
                    for raw in texto.splitlines():
                        linha = _strip_prefix(raw).rstrip()
                        if not linha:
                            continue
                        m = re.match(
                            r'^(\d{2}/\d{2}/\d{4})\s+Saldo\s+do\s+dia\s+R\$\s*([\d.]+,\d{2})',
                            linha, re.IGNORECASE,
                        )
                        if not m:
                            continue
                        data = m.group(1)
                        valor_raw = m.group(2)
                        try:
                            v = float(_D(valor_raw.replace('.', '').replace(',', '.')))
                        except Exception:
                            continue
                        saldos.append({'data': data, 'saldo': v})
        except Exception:
            return []

        # Ordenar por data ASC (sort estável)
        def _chave(s):
            d = s['data']
            return (int(d[6:10]), int(d[3:5]), int(d[0:2]))
        saldos.sort(key=_chave)
        # Dedup por data (preserva o último — útil se PDF repete a linha)
        vistos = {}
        for s in saldos:
            vistos[s['data']] = s
        return list(vistos.values())

    def extrair(self) -> list[dict]:
        partes_por_pagina: list[str] = []
        with pdfplumber.open(self.pdf_path, password=self.password or '') as pdf:
            for num, pagina in enumerate(pdf.pages, start=1):
                try:
                    texto = pagina.extract_text() or ''
                    partes_por_pagina.append(texto)
                except Exception as e:
                    self.avisos.append(
                        f'Santander IB novo: erro na página {num}: {e}'
                    )
        # Reusa o mesmo wrapper que aceita .txt: emula marcadores de página.
        texto_emulado = '\n===== PAGE =====\n'.join(partes_por_pagina)
        return self._post_processar(self._parse_texto(texto_emulado))

    def _parse_texto(self, texto: str) -> list[dict]:
        """Wrapper testável: recebe texto cru (ou conteúdo do fixture) e
        devolve a lista de transações já em ordem ASC e deduplicadas
        cross-page."""
        paginas: list[list[str]] = [[]]
        for raw in texto.splitlines():
            if _RE_FIXTURE_PAGE_BREAK.match(raw.strip()):
                paginas.append([])
                continue
            if _RE_FIXTURE_HEADER.match(raw.strip()):
                continue
            paginas[-1].append(raw)

        transacoes: list[dict] = []
        ultima_da_pagina_anterior: tuple | None = None

        for pagina_linhas in paginas:
            tx_da_pagina: list[dict] = []
            for linha in pagina_linhas:
                tx = self._parse_linha(linha)
                if tx is not None:
                    tx_da_pagina.append(tx)
            if tx_da_pagina and ultima_da_pagina_anterior is not None:
                primeira = tx_da_pagina[0]
                chave = (
                    primeira['data'],
                    primeira['descricao'],
                    float(primeira['valor']),
                    primeira['tipo'],
                )
                if chave == ultima_da_pagina_anterior:
                    tx_da_pagina = tx_da_pagina[1:]
            transacoes.extend(tx_da_pagina)
            if tx_da_pagina:
                ultima = tx_da_pagina[-1]
                ultima_da_pagina_anterior = (
                    ultima['data'],
                    ultima['descricao'],
                    float(ultima['valor']),
                    ultima['tipo'],
                )

        # Reordena por data ASC, sort estável preserva ordem dentro do dia.
        def _chave_ordem(tx: dict) -> tuple:
            d = tx['data']  # 'DD/MM/YYYY'
            return (int(d[6:10]), int(d[3:5]), int(d[0:2]))

        transacoes.sort(key=_chave_ordem)
        return transacoes

    def _parse_linha(self, linha_raw: str) -> dict | None:
        linha = _strip_prefix(linha_raw).rstrip()
        if not linha:
            return None
        if _RE_SALDO_DO_DIA.match(linha):
            return None

        m = _RE_TRANSACAO.match(linha)
        if not m:
            return None

        data_raw = m.group(1)
        descricao = m.group(2).strip()
        sinal = m.group(3)
        valor_raw = m.group(4)

        if not descricao:
            return None

        valor = self._normalizar_valor(valor_raw)
        if valor < 0.01:
            return None

        tipo = 'saida' if sinal else 'entrada'
        data = self._normalizar_data(data_raw)

        return self._transacao(
            data=data,
            descricao=descricao,
            valor=valor,
            tipo=tipo,
            banco=BANCO,
            raw=linha_raw,
        )
