"""
Categorizador Inteligente de Transações Bancárias — v2.0
3 Camadas: Exata → Prefixo/Abreviação → Contextual

Descrições bancárias são ABREVIADAS:
"TL PAG SIS SONDA" = Supermercado Sonda via Sispag
"DA ELETROPAULO" = Conta de energia via débito automático
"DA VIVO FIXO" = Conta de telefone via débito automático
"""

import re

# ============================================================
# CAMADA 1 — Matches por NOME DE ESTABELECIMENTO (substring)
# ============================================================
ESTABELECIMENTOS = {
    # --- Supermercados ---
    "sonda": "Supermercado",
    "extra ": "Supermercado",
    "carrefour": "Supermercado",
    "assai": "Supermercado",
    "atacadao": "Supermercado",
    "atacadão": "Supermercado",
    "pao de acucar": "Supermercado",
    "pão de açúcar": "Supermercado",
    "dia ": "Supermercado",
    "big ": "Supermercado",
    "walmart": "Supermercado",
    "sam's": "Supermercado",
    "sams club": "Supermercado",
    "makro": "Supermercado",
    "natural da terra": "Supermercado",
    "hirota": "Supermercado",
    "st marche": "Supermercado",

    # --- Alimentação ---
    "ifood": "Alimentação",
    "rappi": "Alimentação",
    "uber eats": "Alimentação",
    "ze delivery": "Alimentação",
    "zé delivery": "Alimentação",
    "mcdonald": "Alimentação",
    "burger king": "Alimentação",
    "starbucks": "Alimentação",
    "subway": "Alimentação",
    "habib": "Alimentação",
    "outback": "Alimentação",
    "madero": "Alimentação",
    "coco bambu": "Alimentação",
    "restaur": "Alimentação",
    "lanchonete": "Alimentação",
    "padaria": "Alimentação",
    "confeitaria": "Alimentação",
    "pizzaria": "Alimentação",
    "churrascaria": "Alimentação",
    "bar e rest": "Alimentação",
    "gastro": "Alimentação",
    "açougue": "Alimentação",
    "acougue": "Alimentação",
    "hortifruti": "Alimentação",
    "hortifruit": "Alimentação",
    "sacolao": "Alimentação",
    "sacolão": "Alimentação",

    # --- Combustível / Postos ---
    "shell": "Combustível",
    "ipiranga": "Combustível",
    "br distribui": "Combustível",
    "petrobras": "Combustível",
    "posto ": "Combustível",
    "auto posto": "Combustível",
    "ale combusti": "Combustível",

    # --- Farmácias ---
    "drogasil": "Farmácia",
    "drogaraia": "Farmácia",
    "droga raia": "Farmácia",
    "drogaria": "Farmácia",
    "farmacia": "Farmácia",
    "farmácia": "Farmácia",
    "panvel": "Farmácia",
    "pacheco": "Farmácia",
    "pague menos": "Farmácia",
    "ultrafarma": "Farmácia",
    "nissei": "Farmácia",
    "araujo ": "Farmácia",
    "venancio": "Farmácia",

    # --- Transporte ---
    "uber ": "Transporte",
    "99app": "Transporte",
    "99 ": "Transporte",
    "cabify": "Transporte",
    "localiza": "Transporte",
    "movida": "Transporte",
    "unidas": "Transporte",
    "sem parar": "Transporte",
    "conectcar": "Transporte",
    "autopass": "Transporte",
    "estacionamento": "Transporte",
    "estapar": "Transporte",

    # --- Saúde ---
    "amil": "Saúde",
    "sul america": "Saúde",
    "sulamerica": "Saúde",
    "unimed": "Saúde",
    "hapvida": "Saúde",
    "notre dame": "Saúde",
    "notredame": "Saúde",
    "plano de saude": "Saúde",
    "plano de saúde": "Saúde",
    "hospital": "Saúde",
    "clinica": "Saúde",
    "clínica": "Saúde",
    "laboratorio": "Saúde",
    "laboratório": "Saúde",
    "dasa ": "Saúde",
    "fleury": "Saúde",
    "animatrix": "Saúde",

    # --- Energia ---
    "eletropaulo": "Energia",
    "enel": "Energia",
    "cemig": "Energia",
    "cpfl": "Energia",
    "elektro": "Energia",
    "equatorial": "Energia",
    "energisa": "Energia",
    "celesc": "Energia",
    "copel": "Energia",

    # --- Água/Esgoto ---
    "sabesp": "Água/Esgoto",
    "aguas do rio": "Água/Esgoto",
    "águas do rio": "Água/Esgoto",
    "cedae": "Água/Esgoto",
    "sanepar": "Água/Esgoto",
    "copasa": "Água/Esgoto",
    "casan": "Água/Esgoto",

    # --- Telefone/Internet ---
    "vivo": "Telefone/Internet",
    "claro": "Telefone/Internet",
    "tim ": "Telefone/Internet",
    "oi ": "Telefone/Internet",
    "net ": "Telefone/Internet",

    # --- Streaming/Assinatura ---
    "netflix": "Streaming/Assinatura",
    "spotify": "Streaming/Assinatura",
    "amazon prime": "Streaming/Assinatura",
    "disney": "Streaming/Assinatura",
    "hbo max": "Streaming/Assinatura",
    "globoplay": "Streaming/Assinatura",
    "youtube prem": "Streaming/Assinatura",
    "apple": "Streaming/Assinatura",

    # --- Moradia ---
    "aluguel": "Moradia",
    "condominio": "Moradia",
    "condomínio": "Moradia",
    "iptu": "Moradia",
    "imobiliaria": "Moradia",
    "imobiliária": "Moradia",
    "inbox guarda": "Moradia",

    # --- Educação ---
    "escola": "Educação",
    "faculdade": "Educação",
    "universidade": "Educação",
    "udemy": "Educação",
    "alura": "Educação",
    "coursera": "Educação",

    # --- Fornecedores (extratos reais) ---
    "suprimax": "Fornecedores",
    "mouragro": "Fornecedores",
    "agrolife": "Fornecedores",
    "vitavet": "Fornecedores",
    "vettec": "Fornecedores",
    "rio citavet": "Fornecedores",
    "seropec": "Fornecedores",
    "gla com de prod": "Fornecedores",

    # --- Vendas / Receitas ---
    "recebimento vendas": "Vendas",
    "antecipação": "Vendas",
    "antecipacao": "Vendas",
    "cielo": "Vendas",
    "credito visa": "Vendas",
    "credito mastercard": "Vendas",
    "cobrança": "Vendas",
    "cobranca": "Vendas",
    "liberação de dinheiro": "Vendas",
    "liberacao de dinheiro": "Vendas",

    # --- Hotelaria / Turismo ---
    "hotel": "Hotelaria",
    "hostel": "Hotelaria",
    "pousada": "Hotelaria",
    "resort": "Hotelaria",
    "ibis ": "Hotelaria",
    "melia": "Hotelaria",
    "atlantica": "Hotelaria",
    "slaviero": "Hotelaria",
    "nobile": "Hotelaria",
    "transameric": "Hotelaria",
    "windsor": "Hotelaria",
    "cvc brasil": "Turismo",
    "trend viage": "Turismo",
    "coris brasi": "Turismo",
}

# ============================================================
# CAMADA 2 — Matches por PREFIXO BANCÁRIO
# Ordenar por comprimento descrescente garante maior especificidade
# ============================================================
PREFIXOS_BANCARIOS = {
    # Tributos
    "sispag trib municipal": "Impostos Municipais",
    "sispag trib cod barras": "Impostos/Tributos",
    "sispag trib": "Impostos/Tributos",
    "simples nacional": "Impostos",
    "das - simples": "Impostos",
    "das simples": "Impostos",
    "darf": "Impostos",
    "receita federal": "Impostos",
    "sefaz": "Impostos",
    "secretaria da fazenda": "Impostos",
    "secret. da fazenda": "Impostos",
    "pag orgaos gov": "Impostos/Governo",

    # Transferências internas Itaú
    "sispag transf cc": "Transferência Interna",
    "sispag fornecedores": "Pagamento Fornecedores",
    "sispag plantao": "Pagamento Fornecedores",
    "sispag ": "Pagamentos Diversos",
    "tl pag sis": "Pagamentos Diversos",
    "tl pag": "Pagamentos Diversos",
    "tbi ": "Transferência Interna",
    "tbi 8730": "Transferência Interna",

    # Boletos / Pagamentos
    "boleto pago": "Pagamentos Diversos",
    "pag boleto": "Pagamentos Diversos",
    "pag multas": "Multas",
    "pagamento de boleto": "Pagamentos Diversos",
    "pagamento efetuado": "Pagamentos Diversos",
    "pagamento de conta": "Pagamentos Diversos",
    "pagamento com qr code": "Pagamentos Diversos",
    "pagamento de assinatura": "Assinaturas",

    # Débitos automáticos (Itaú: "DA ELETROPAULO", etc.)
    "da eletropaulo": "Energia",
    "da enel": "Energia",
    "da vivo": "Telefone/Internet",
    "da claro": "Telefone/Internet",
    "conta de telefone": "Telefone/Internet",
    "da ": "Débito Automático",

    # Tarifas bancárias
    "mensalidade cesta": "Tarifas Bancárias",
    "tar pix": "Tarifas Bancárias",
    "tar contr": "Tarifas Bancárias",
    "tarifa bancaria": "Tarifas Bancárias",
    "tarifa": "Tarifas Bancárias",
    "débito serviço cobrança": "Tarifas Bancárias",
    "debito servico cobranca": "Tarifas Bancárias",

    # Seguros / Empréstimos
    "debito seguro": "Seguros",
    "debito presta": "Empréstimos",
    "parcela giro": "Empréstimos",
    "parcela | empréstimo": "Empréstimos",
    "parcela | emprestimo": "Empréstimos",
    "consorcio": "Consórcio",
    "consórcio": "Consórcio",
    "financiamento": "Veículos",
    "pgto mercedes": "Veículos",
    "ourocap": "Capitalização",
    "plano int capital": "Seguros/Capitalização",
    "brasilprev": "Previdência",

    # TED / Transferências
    "ted enviada": "Transferência Enviada",
    "envio de ted": "Transferência Enviada",
    "ted-transf elet": "Transferência Recebida",
    "ted-crédito em conta": "Transferência Recebida",
    "ted-credito em conta": "Transferência Recebida",
    "transferência recebida": "Transferência Recebida",
    "transferencia recebida": "Transferência Recebida",

    # Cartão de crédito
    "cartao credito": "Cartão de Crédito",
    "fatura cartao": "Cartão de Crédito",

    # Depósitos
    "dep dinheiro": "Depósito",
    "deposito": "Depósito",
    "depósito": "Depósito",

    # Impostos sobre renda / investimento
    "juros ": "Juros Bancários",
    "iof ": "IOF",
    "irrf": "Imposto de Renda",
    "ir -": "Imposto de Renda",

    # Investimentos
    "bb rende": "Investimentos",
    "rende facil": "Investimentos",
    "aplic aut mais": "Investimentos",
    "aplic. financ": "Investimentos",
    "resgate aplic": "Investimentos",
    "inter corporate": "Investimentos",
    "credito resgate fundo": "Investimentos",

    # Vendas via maquininha
    "pix | maquininha": "Vendas",
    "pix maquininha": "Vendas",
}

# ============================================================
# CAMADA 3 — Contextual
# ============================================================
INDICADORES_PJ = [
    "ltda", "s/a", "s.a.", "eireli", " me ", " epp",
    "cnpj", "instituicao", "instituição", "comercio",
    "comércio", "servicos", "serviços", "distribui",
    "industria", "indústria", "tecnologia", "assessoria",
    "consultoria", "contabil", "contábil",
]


def aplicar_categorias(descricao: str) -> str:
    """
    Categoriza uma transação em 3 camadas de precisão crescente.
    """
    if not descricao:
        return "Outros"

    desc_lower = descricao.lower().strip()

    # ---- CAMADA 1: Estabelecimento ----
    for termo, categoria in ESTABELECIMENTOS.items():
        if termo in desc_lower:
            return categoria

    # ---- CAMADA 2: Prefixo Bancário (mais específico primeiro) ----
    for prefixo, categoria in sorted(PREFIXOS_BANCARIOS.items(), key=lambda x: -len(x[0])):
        if prefixo in desc_lower:
            # Caso especial: boleto pago → verificar se o nome do estabelecimento está no resto
            if prefixo in ("boleto pago", "pag boleto", "pagamento de conta", "pagamento efetuado"):
                resto = desc_lower.replace(prefixo, "").strip()
                for termo, cat_estab in ESTABELECIMENTOS.items():
                    if termo in resto:
                        return cat_estab
            return categoria

    # ---- CAMADA 3: Contextual ----
    eh_pix = any(t in desc_lower for t in [
        "pix enviado", "pix recebido", "pix transf",
        "transferencia pix", "transf pix",
    ])
    eh_ted = any(t in desc_lower for t in [
        "ted ", "transferencia", "transferência", "transf ",
    ])

    if eh_pix or eh_ted:
        for ind in INDICADORES_PJ:
            if ind in desc_lower:
                return "Transferência PJ"
        # Padrão de CPF: ***123456-**
        if re.search(r"\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[-\s]?\d{2}", desc_lower):
            return "Transferência PF"
        # 2+ palavras capitalizadas no original = nome de pessoa
        palavras = descricao.split()
        nomes_proprios = sum(1 for p in palavras if p[:1].isupper() and len(p) > 2)
        if nomes_proprios >= 2:
            return "Transferência PF"
        return "Transferência"

    if any(t in desc_lower for t in ["boleto", "pagamento", "pagto"]):
        return "Pagamentos Diversos"

    if any(t in desc_lower for t in ["compra", "compras nacionais"]):
        return "Compras Cartão"

    if any(t in desc_lower for t in ["saque", "saq "]):
        return "Saque"

    if any(t in desc_lower for t in ["estorno", "devolução", "devolucao"]):
        return "Estorno"

    if any(t in desc_lower for t in ["ajuste de saldo", "movimentação operacional"]):
        return "Ajuste Interno"

    return "Outros"
