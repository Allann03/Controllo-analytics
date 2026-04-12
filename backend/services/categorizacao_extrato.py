"""
Categorização automática de lançamentos de extrato bancário.
Esta é uma ADIÇÃO ao pipeline do extrator de PDF — roda DEPOIS da extração.
A lógica de leitura/parsing do PDF não é alterada.
"""
import re
import unicodedata
from typing import Optional

# ------------------------------------------------------------------ #
#  REGRAS DE CATEGORIZAÇÃO (configuráveis — não hardcoded no fluxo) #
# ------------------------------------------------------------------ #

# Formato: { "categoria": { "icone": "...", "keywords": [...] } }
# Ordem importa: a primeira categoria que bater vence.
REGRAS_CATEGORIAS: list[dict] = [
    {
        "categoria": "Receita / Entrada",
        "icone": "💰",
        "keywords": [
            "SALARIO", "PROVENTOS", "CREDITO EM CONTA", "DEPOSITO IDENTIFICADO",
            "PIX RECEBIDO", "TED RECEBIDO", "DOC RECEBIDO", "TRANSFERENCIA RECEBIDA",
            "PAGAMENTO RECEBIDO", "RECEBIMENTO",
        ],
        "somente_entradas": True,  # só aplica se o valor for positivo/entrada
    },
    {
        "categoria": "Supermercado",
        "icone": "🛒",
        "keywords": [
            "CARREFOUR", "PAO DE ACUCAR", "ASSAI", "ATACADAO", "EXTRA HIPER",
            "SAMS CLUB", "SAM S CLUB", "MAKRO", "BIG SUPERMERCADO", "WALMART",
            "PREZUNIC", "SUPERNOSSO", "SUPERMERCADO", "HIPER", "ATACADO",
        ],
    },
    {
        "categoria": "Alimentação / Restaurante",
        "icone": "🍔",
        "keywords": [
            "IFOOD", "UBER EATS", "RAPPI", "ZDELIVERY", "JAMES DELIVERY",
            "MCDONALDS", "MC DONALDS", "BURGER KING", "SUBWAY", "HABIBS", "HABIB S",
            "OUTBACK", "MADERO", "GIRAFFAS", "BOB S", "BOBS",
            "RESTAURANTE", "LANCHONETE", "PADARIA", "CAFETERIA", "PIZZARIA",
            "SUSHI", "CHURRASCARIA", "PASTELARIA", "HAMBURGUER",
        ],
    },
    {
        "categoria": "Transporte / Viagem",
        "icone": "🚗",
        "keywords": [
            "UBER", "99POP", "99 POP", "CABIFY", "INDRIVE",
            "LATAM", "GOL LINHAS", "AZUL LINHAS", "AVIANCA",
            "BOOKING", "AIRBNB", "DECOLAR", "HURB", "SUBMARINO VIAGENS",
            "PEDAGIO", "SEM PARAR", "CONECTCAR", "VELOE",
            "MOVIDA", "LOCALIZA", "UNIDAS", "HERTZ",
            "TREM", "METRO", "ONIBUS", "BUS", "BILHETE UNICO",
        ],
    },
    {
        "categoria": "Farmácia / Saúde",
        "icone": "💊",
        "keywords": [
            "DROGASIL", "DROGA RAIA", "DROGARIA PACHECO", "PAGUE MENOS",
            "ULTRAFARMA", "DROGARIA", "FARMACIA", "FARMA",
            "UNIMED", "AMIL", "HAPVIDA", "BRADESCO SAUDE", "SULAMÉRICA SAUDE",
            "LABORATORIO", "CLINICA", "HOSPITAL", "PLANO DE SAUDE",
            "CONSULTA MEDICA", "EXAME",
        ],
    },
    {
        "categoria": "Combustível",
        "icone": "⛽",
        "keywords": [
            "SHELL", "IPIRANGA", "BR DISTRIBUIDORA", "PETROBRAS DISTRIBUIDORA",
            "ALE COMBUSTIVEIS", "RIOPOL", "POSTO ", "COMBUSTIVEL",
            "GASOLINA", "ETANOL", "ALCOOL COMBUSTIVEL",
        ],
    },
    {
        "categoria": "Moradia / Utilities",
        "icone": "🏠",
        "keywords": [
            "CEMIG", "COPASA", "SABESP", "LIGHT SERVICOS", "ENEL DISTRIBUICAO",
            "CPFL ENERGIA", "ENERGISA", "COELBA", "CELPE", "COSERN",
            "COMGAS", "GAS NATURAL", "NATURGY",
            "NET SERVICOS", "CLARO SA", "VIVO TELECOMUNICACOES", "TIM CELULAR",
            "OI MOVEL", "SKY", "ALUGUEL", "CONDOMINIO", "IPTU", "AGUA E ESGOTO",
        ],
    },
    {
        "categoria": "Assinaturas / Digital",
        "icone": "📱",
        "keywords": [
            "NETFLIX", "SPOTIFY", "AMAZON PRIME", "DISNEY PLUS", "HBO MAX",
            "GLOBOPLAY", "YOUTUBE PREMIUM", "APPLE SERVICES", "GOOGLE",
            "MICROSOFT", "ADOBE", "DROPBOX", "GITHUB", "FIGMA",
            "LINKEDIN PREMIUM", "CANVA",
        ],
    },
    {
        "categoria": "Educação",
        "icone": "🎓",
        "keywords": [
            "ESCOLA", "FACULDADE", "UNIVERSIDADE", "COLEGIO",
            "UDEMY", "ALURA", "DESCOMPLICA", "COURSERA", "ROCKETSEAT",
            "MENSALIDADE ESCOLAR", "CURSO", "TREINAMENTO", "CAPACITACAO",
        ],
    },
    {
        "categoria": "Vestuário",
        "icone": "👔",
        "keywords": [
            "RENNER", "C&A", "RIACHUELO", "ZARA", "HERING", "MARISA",
            "NETSHOES", "CENTAURO", "SHEIN", "SHOPEE", "TOTVS FASHION",
            "AREZZO", "MELISSA", "LUPO",
        ],
    },
    {
        "categoria": "Tributos / Impostos",
        "icone": "🏛️",
        "keywords": [
            "DARF", "DAS ", "SIMPLES NACIONAL", "FGTS", "GPS ",
            "ISS ", "ICMS", "IPTU", "IPVA", "PIS ", "COFINS",
            "CSLL", "IRPJ", "IRRF", "INSS", "IMPOSTO", "TRIBUTO",
            "TAXA MUNICIPAL", "TAXA ESTADUAL", "TAXA FEDERAL",
            "GRU ", "GARE ", "GNRE", "DAM ", "DARE ",
        ],
    },
    {
        "categoria": "Fornecedores / Pagamentos",
        "icone": "🏭",
        "keywords": [
            "FORNECEDOR", "FORNEC", "SISPAG", "PAGAMENTO A ",
            "BOLETO", "LIQUIDACAO DE BOLETO", "PAGTO BOLETO",
            "FATURA ", "NF ", "NOTA FISCAL",
        ],
    },
    {
        "categoria": "Transferências",
        "icone": "🔄",
        "keywords": [
            "PIX ENVIADO", "PIX TRANSFERENCIA", "TED ENVIADO", "DOC ENVIADO",
            "TRANSFERENCIA ENVIADA", "TRANSF ENTRE CONTAS",
            "TBI REMETENTE", "TBI FAVORECIDO",
        ],
    },
    {
        "categoria": "Cartão de Crédito",
        "icone": "💳",
        "keywords": [
            "CARTAO ", "CARD ", "VISA ", "MASTERCARD", "ELO ",
            "COMPRA CARTAO", "CARTAO CREDITO", "CARTAO DEBITO",
            "BUSINESS CARD", "CORPORATE CARD",
        ],
    },
    {
        "categoria": "Serviços Financeiros",
        "icone": "🏦",
        "keywords": [
            "TARIFA BANCARIA", "TARIFA ", "TAR ", "IOF", "JUROS ",
            "ANUIDADE", "SEGURO ", "TED ", "DOC ", "TAXA DE ",
            "COBRANCA ", "MULTA ", "FATURA CARTAO", "PAGAMENTO FATURA",
            "RENTAB", "RENDIMENTO", "APLIC ", "RESGATE ",
            "CDB ", "LCI ", "LCA ", "TESOURO ",
        ],
    },
    {
        "categoria": "Outros",
        "icone": "📦",
        "keywords": [],
        "fallback": True,
    },
]

# Prefixos bancários a remover antes de categorizar
_PREFIXOS_BANCARIOS = [
    "NUPAY ", "SISPAG ", "PIX QR CODE ", "PIX ", "PAG ", "PAGSEGURO ",
    "DEB AUT ", "PGTO ", "PAGTO ", "DEBITO AUTOMATICO ", "DEBITO AUTO ",
    "COMPRA ", "COMPRA DEBITO ", "COMPRA CREDITO ", "TRF ", "TRANSF ",
]


# ------------------------------------------------------------------ #
#  NORMALIZAÇÃO                                                       #
# ------------------------------------------------------------------ #

def _normalizar(texto: str) -> str:
    """Remove acentos, converte para uppercase, colapsa espaços."""
    sem_acento = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sem_acento.upper().strip())


def _remover_prefixos(descricao: str) -> str:
    """Remove prefixos bancários da descrição para melhorar a classificação."""
    for prefixo in _PREFIXOS_BANCARIOS:
        if descricao.startswith(prefixo):
            descricao = descricao[len(prefixo):]
            break
    return descricao.strip()


# ------------------------------------------------------------------ #
#  CORE — categorizador                                              #
# ------------------------------------------------------------------ #

def categorizar(descricao: str, valor: float = 0.0) -> dict:
    """
    Categoriza um lançamento de extrato.

    Retorna:
        {
          "categoria": str,
          "icone": str,
          "confianca": "alta" | "media" | "baixa",
          "keyword_usada": str | None,
        }
    """
    if not descricao:
        return _resultado_fallback()

    desc_norm = _normalizar(descricao)
    desc_sem_prefixo = _remover_prefixos(desc_norm)

    for regra in REGRAS_CATEGORIAS:
        # Pula fallback — ele é o último recurso
        if regra.get("fallback"):
            continue

        # Se a regra é "somente_entradas", pular se for saída
        if regra.get("somente_entradas") and valor <= 0:
            continue

        for kw in regra["keywords"]:
            kw_norm = _normalizar(kw)
            # Verifica tanto na desc original (com prefixo) quanto sem prefixo
            if kw_norm in desc_norm or kw_norm in desc_sem_prefixo:
                # Distingue UBER vs UBER EATS
                if kw_norm == "UBER" and "UBER EATS" in desc_norm:
                    continue  # deixa cair em Alimentação
                confianca = "alta" if kw_norm == desc_sem_prefixo[:len(kw_norm)] else "media"
                return {
                    "categoria": regra["categoria"],
                    "icone": regra["icone"],
                    "confianca": confianca,
                    "keyword_usada": kw,
                }

    return _resultado_fallback()


def _resultado_fallback() -> dict:
    return {
        "categoria": "Outros",
        "icone": "📦",
        "confianca": "baixa",
        "keyword_usada": None,
    }


# ------------------------------------------------------------------ #
#  APLICAR EM LISTA DE TRANSAÇÕES (pós-processamento)               #
# ------------------------------------------------------------------ #

def categorizar_transacoes(transacoes: list[dict]) -> list[dict]:
    """
    Recebe a lista de transações já extraída do PDF e adiciona
    o campo 'categoria', 'icone_categoria' e 'confianca_categoria'.
    NÃO altera nenhuma outra informação da transação.
    """
    for t in transacoes:
        descricao = t.get("descricao") or t.get("historico") or ""
        valor = float(t.get("valor") or 0.0)
        resultado = categorizar(descricao, valor)
        t["categoria"] = resultado["categoria"]
        t["icone_categoria"] = resultado["icone"]
        t["confianca_categoria"] = resultado["confianca"]
    return transacoes


# ------------------------------------------------------------------ #
#  RESUMO POR CATEGORIA                                              #
# ------------------------------------------------------------------ #

def resumo_por_categoria(transacoes: list[dict]) -> list[dict]:
    """
    Agrega totais por categoria para exibição no painel.
    Retorna lista ordenada por valor (maior primeiro).
    """
    totais: dict[str, dict] = {}
    for t in transacoes:
        cat = t.get("categoria", "Outros")
        icone = t.get("icone_categoria", "📦")
        valor = abs(float(t.get("valor") or 0.0))
        if cat not in totais:
            totais[cat] = {"categoria": cat, "icone": icone, "total": 0.0, "quantidade": 0}
        totais[cat]["total"] += valor
        totais[cat]["quantidade"] += 1

    return sorted(totais.values(), key=lambda x: x["total"], reverse=True)
