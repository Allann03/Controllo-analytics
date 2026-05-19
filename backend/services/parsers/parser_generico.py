import re
from .parser_base import ParserBase


class ParserGenerico(ParserBase):
    """
    Parser genérico que tenta extrair transações de qualquer extrato.
    Funciona para: C6 Bank, PagBank, Mercado Pago, Inter, Sicredi, Caixa,
    Cora, Bradesco, Santander, Banco do Brasil, Nubank e outros.

    Estratégia: busca linhas com data + descrição + valor monetário.
    """

    banco_nome = "Genérico"

    def extrair_transacoes(self, texto_paginas: list[str]) -> list[dict]:
        transacoes = []
        texto_completo = "\n".join(texto_paginas)
        ano = self.extrair_ano_referencia(texto_completo)

        padrao_data = re.compile(r"^(\d{2}[/-]\d{2}[/-]?\d{0,4})")
        padrao_valor = re.compile(
            r"(-?\s*R?\$?\s*[\d]{1,3}(?:\.[\d]{3})*,\d{2})"
        )

        for pagina in texto_paginas:
            linhas = pagina.split("\n")
            data_atual = None

            for linha in linhas:
                linha_limpa = linha.strip()
                if not linha_limpa:
                    continue

                match_data = padrao_data.match(linha_limpa)
                if match_data:
                    data_str = match_data.group(1).replace("-", "/")
                    data_atual = data_str

                if not data_atual:
                    continue

                valores = padrao_valor.findall(linha_limpa)
                if not valores:
                    continue

                valor_raw = valores[0]

                pos_data_fim = len(data_atual) if (
                    linha_limpa.startswith(data_atual.replace("/", "-"))
                    or linha_limpa.startswith(data_atual)
                ) else 0
                pos_valor = linha_limpa.find(valor_raw)
                if pos_valor <= pos_data_fim:
                    continue

                descricao = linha_limpa[pos_data_fim:pos_valor].strip()
                descricao = re.sub(r"^\s*[-|]\s*", "", descricao).strip()

                if not descricao or len(descricao) < 3:
                    continue

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
