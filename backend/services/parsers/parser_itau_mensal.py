import re
from .parser_base import ParserBase


class ParserItauMensal(ParserBase):
    """Parser para Extrato Mensal do Itaú (formato multi-página com entradas/saídas)."""

    banco_nome = "Itaú (Mensal)"

    def extrair_transacoes(self, texto_paginas: list[str]) -> list[dict]:
        transacoes = []
        texto_completo = "\n".join(texto_paginas)
        ano = self.extrair_ano_referencia(texto_completo)

        for pagina in texto_paginas:
            linhas = pagina.split("\n")
            data_atual = None

            for linha in linhas:
                linha = linha.strip()
                if not linha:
                    continue

                match_data = re.match(r"^(\d{2}/\d{2})\s+(.+)", linha)
                if match_data:
                    data_atual = match_data.group(1)
                    resto = match_data.group(2).strip()
                else:
                    resto = linha

                if not data_atual:
                    continue

                match_valor = re.search(r"([\d]{1,3}(?:\.[\d]{3})*,\d{2})(-)?$", resto)
                if match_valor:
                    valor_str = match_valor.group(1)
                    eh_debito = match_valor.group(2) == "-"
                    descricao = resto[:match_valor.start()].strip()

                    if not descricao or self.eh_linha_ignoravel(descricao):
                        continue

                    valor = self.limpar_valor(valor_str)
                    if eh_debito:
                        valor = -abs(valor)

                    transacoes.append({
                        "data": self.padronizar_data(data_atual, ano),
                        "descricao": descricao,
                        "valor": valor,
                        "tipo": "saida" if valor < 0 else "entrada",
                    })

        return transacoes
