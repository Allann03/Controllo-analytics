import re
from .parser_base import ParserBase


class ParserStone(ParserBase):
    """Parser para extratos Stone (formato com TIPO, DESCRIÇÃO, VALOR, SALDO)."""

    banco_nome = "Stone"

    def extrair_transacoes(self, texto_paginas: list[str]) -> list[dict]:
        transacoes = []
        texto_completo = "\n".join(texto_paginas)
        ano = self.extrair_ano_referencia(texto_completo)

        for pagina in texto_paginas:
            linhas = pagina.split("\n")
            data_atual = None

            for linha in linhas:
                linha = linha.strip()

                match_data = re.match(r"^(\d{2}/\d{2}/\d{2})\s", linha)
                if match_data:
                    data_atual = match_data.group(1)
                    continue

                if not data_atual:
                    continue

                match_valor = re.search(r"(-?\s*R\$\s*[\d.,]+)", linha)
                if match_valor:
                    valor_raw = match_valor.group(1)
                    descricao = linha[:match_valor.start()].strip()

                    if self.eh_linha_ignoravel(descricao):
                        continue

                    valor = self.limpar_valor(valor_raw)
                    if valor == 0:
                        continue

                    transacoes.append({
                        "data": self.padronizar_data(data_atual, ano),
                        "descricao": descricao,
                        "valor": valor,
                        "tipo": "saida" if valor < 0 else "entrada",
                    })

        return transacoes
