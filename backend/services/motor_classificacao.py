"""
Motor de Classificação Contábil — Padrão Contmatic
====================================================
Recebe transações do Excel (Data|Banco|Categoria|Descrição|Tipo|Valor)
e classifica cada uma com Débito e Crédito usando contas reduzidas.

Output: {debito: "10201", credito: "2501", status: "automatico"}

Cascata de prioridade:
  1. Regras customizadas do usuário (prioridade máxima)
  2. Cadastro de pessoas (sócios/clientes/fornecedores)
  3. Regras automáticas do sistema (regex → nome de conta → código reduzido)
  4. Fallback "A Classificar"
"""

import re
from typing import Optional

# ─── Padrões para FILTRAR linhas que NÃO são transações ─────────────
FILTRO_SALDO = re.compile(
    r"[IÍ]VEL\s*DIA|SALDO\s*DISPON|SALDO\s*DO\s*DIA|S\s*A\s*L\s*D\s*O",
    re.IGNORECASE,
)
FILTRO_TOTAIS = re.compile(
    r"^(TOTAL|ENTRADAS\s*:|SAÍDAS\s*:|SAIDAS\s*:|SALDO\s*:)",
    re.IGNORECASE,
)

# ─── Extração de CPF/CNPJ da descrição ─────────────────────────────
_RE_CNPJ = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
_RE_CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")


def extrair_documento(descricao: str) -> Optional[str]:
    m = _RE_CNPJ.search(descricao)
    if m:
        return m.group()
    m = _RE_CPF.search(descricao)
    if m:
        return m.group()
    return None


def extrair_nome_pagador(descricao: str) -> Optional[str]:
    """Extrai nome entre o verbo da operação e o documento."""
    padrao = re.compile(
        r"(?:PIX\s+RECEBIDO|PIX\s+DEVOLVIDO|PIX\s+ENV(?:IADO)?|TED\s+RECEBIDA|DOC\s+RECEBID[OA]?)\s+"
        r"(.+?)\s+\d{2,3}[\.\d/\-]+$",
        re.IGNORECASE,
    )
    m = padrao.search(descricao.strip())
    if m:
        return m.group(1).strip()
    return None


def deve_filtrar(descricao: str) -> bool:
    """True se a linha NÃO é transação (saldo informativo, totais de rodapé)."""
    return bool(FILTRO_SALDO.search(descricao) or FILTRO_TOTAIS.search(descricao))


# ─── Regras padrão do sistema ──────────────────────────────────────
# Cada regra: (regex, nome_conta_destino)
# O nome_conta_destino é buscado no plano de contas do usuário por keyword match.
# Se não encontrado, usa a conta fallback (A Classificar).

REGRAS_SAIDA = [
    # (regex na descrição, keywords para buscar no plano, tipo_conta)
    (r"TAR|TARIFA|PLANO\s*ADAPT", "tarifa"),
    (r"\bIOF\b", "iof"),
    (r"JUROS|ENCARGOS|MORA", "juros"),
    (r"SISPAG\s*FORNEC|PAG\s*FORNEC|PGTO\s*FORNEC", "fornecedor"),
    (r"SISPAG\s*TRIBUTOS|TRIBUTO|DARF|GUIA", "tributo"),
    (r"SIMPLES|DAS\b", "simples"),
    (r"SALARIO|FOLHA|PGTO\s*FUNC|PRO.?LABORE", "salario"),
    (r"\bFGTS\b", "fgts"),
    (r"\bINSS\b|GPS", "inss"),
    (r"ENERGIA|ENEL|CEMIG|CPFL|LIGHT|ELETRO", "energia"),
    (r"AGUA|SABESP|COPASA|SANEAGO", "agua"),
    (r"TELEFONE|TELECOM|VIVO|CLARO|\bTIM\b|\bOI\b", "telecom"),
    (r"ALUGUEL|LOCACAO|CONDOMINIO", "aluguel"),
    (r"BUSINESS|CARTAO\s*CORP", "viagem"),
    (r"APLICACA[OÃ]|APLIC\s*CDB|APLIC\s*POUP|INVESTIMENTO", "aplicacao"),
    (r"PIX\s*ENV|PIX\s*TRANSF|TRANSF\s*ENV|TED\s*ENV", "_fallback_despesa"),
    (r"\bCODE\b|QR\s*CODE|PIX\s*QR", "_fallback_despesa"),
]

REGRAS_ENTRADA = [
    (r"PIX\s*RECEBIDO|TED\s*RECEBIDA|DOC\s*RECEBID|DEPOSITO|DEP\s*DINHEIRO", "recebimento"),
    (r"REND.*APLIC|RENDIMENTO|REND\s*PAGO", "rendimento"),
    (r"RESGATE|RESG\s*CDB|RESG\s*POUP", "aplicacao"),
    (r"ESTORNO.*TAR|ESTORNO.*TARIFA", "_estorno_tarifa"),
    (r"ESTORNO|DEVOLUCAO|DEVOLVIDO", "_fallback_receita"),
    (r"PIX\s*DEVOLVIDO", "_fallback_receita"),
]

# Keywords de busca: mapeiam o nome interno → keywords para buscar no plano de contas do usuário
# Para cada regra, buscamos no plano uma conta cuja descrição contenha alguma das keywords
KEYWORDS_CONTA = {
    "tarifa":       ["tarifa", "bancária", "bancaria"],
    "iof":          ["iof"],
    "juros":        ["juros pago", "juros", "encargo"],
    "fornecedor":   ["fornecedor"],
    "tributo":      ["tributo municipal", "tributos municipais", "tributo"],
    "simples":      ["simples", "das"],
    "salario":      ["salário", "salario", "a pagar"],
    "fgts":         ["fgts"],
    "inss":         ["inss"],
    "energia":      ["energia", "elétrica", "eletrica"],
    "agua":         ["água", "agua", "esgoto"],
    "telecom":      ["telecomunic", "telefone"],
    "aluguel":      ["aluguel", "locação", "locacao"],
    "viagem":       ["viagem", "viagens", "deslocamento", "transporte"],
    "aplicacao":    ["aplicaç", "aplicac", "cdb", "rdb", "investimento", "poupança", "poupanca"],
    "rendimento":   ["rendimento", "receita financeira", "receitas financeiras"],
    "recebimento":  ["receita de serviço", "receita de servico", "receita de venda", "serviços prestados", "servicos prestados"],
    "socio":        ["sócio", "socio", "capital social", "conta sócio"],
    "cliente":      ["cliente", "a receber"],
}


def _buscar_conta_no_plano(nome_interno: str, plano: dict) -> Optional[str]:
    """
    Busca no plano de contas do usuário uma conta cuja descrição
    contenha as keywords associadas ao nome_interno.

    plano: dict de {codigo_reduzido: descricao}
    Retorna: codigo_reduzido ou None
    """
    keywords = KEYWORDS_CONTA.get(nome_interno, [])
    if not keywords:
        return None

    for codigo, descricao in plano.items():
        desc_lower = descricao.lower()
        for kw in keywords:
            if kw.lower() in desc_lower:
                return str(codigo)
    return None


def _buscar_fallback(plano: dict, tipo: str) -> str:
    """Busca a conta 'A Classificar' no plano. tipo: 'despesa' ou 'receita'."""
    keywords_desp = ["despesas diversas", "a classificar", "despesa"]
    keywords_rec = ["receitas diversas", "a classificar", "receita"]
    keywords = keywords_desp if tipo == "despesa" else keywords_rec

    # Busca exata primeiro
    for codigo, descricao in plano.items():
        desc_lower = descricao.lower()
        if "a classificar" in desc_lower:
            if tipo == "despesa" and ("despesa" in desc_lower or codigo.startswith("4")):
                return str(codigo)
            if tipo == "receita" and ("receita" in desc_lower or codigo.startswith("3")):
                return str(codigo)

    # Busca genérica
    for codigo, descricao in plano.items():
        desc_lower = descricao.lower()
        for kw in keywords:
            if kw in desc_lower:
                return str(codigo)

    # Último recurso
    return "49901" if tipo == "despesa" else "39901"


# ─── Matching ─────────────────────────────────────────────────────

def _match_regras_usuario(descricao: str, tipo: str, regras_usuario: list) -> Optional[dict]:
    """Verifica regras customizadas do usuário (prioridade máxima)."""
    desc_upper = descricao.upper()
    for regra in regras_usuario:
        if regra.get("tipo_transacao", "ambos") not in ("ambos", tipo):
            continue
        padrao = regra.get("padrao", "")
        if not padrao:
            continue
        try:
            if re.search(padrao, desc_upper, re.IGNORECASE):
                return {
                    "debito": regra.get("conta_debito_codigo", ""),
                    "credito": regra.get("conta_credito_codigo", ""),
                    "status": "regra_usuario",
                }
        except re.error:
            if padrao.upper() in desc_upper:
                return {
                    "debito": regra.get("conta_debito_codigo", ""),
                    "credito": regra.get("conta_credito_codigo", ""),
                    "status": "regra_usuario",
                }
    return None


def _match_cadastro(descricao: str, cadastros: list) -> Optional[dict]:
    """Verifica se nome ou CPF/CNPJ na descrição bate com cadastro."""
    doc = extrair_documento(descricao)
    nome = extrair_nome_pagador(descricao)
    desc_upper = descricao.upper()

    for cad in cadastros:
        matched = False
        # Match por documento
        if doc and cad.get("documento"):
            doc_limpo = re.sub(r"[.\-/]", "", doc)
            cad_limpo = re.sub(r"[.\-/]", "", cad["documento"])
            if doc_limpo == cad_limpo:
                matched = True
        # Match por nome
        if not matched and cad.get("nome"):
            cad_nome_upper = cad["nome"].upper()
            if cad_nome_upper in desc_upper or (nome and cad_nome_upper in nome.upper()):
                matched = True

        if matched:
            return {
                "conta_codigo": cad.get("conta_codigo", ""),
                "tipo_cadastro": cad.get("tipo", ""),  # socio | cliente | fornecedor
                "status": "cadastro",
            }
    return None


# ─── Classificação principal ──────────────────────────────────────

def classificar_transacao(
    descricao: str,
    tipo: str,  # "Entrada" | "Saída"
    banco: str,
    conta_banco_codigo: str,
    regras_usuario: list,
    cadastros: list,
    plano: dict,  # codigo_reduzido -> descricao
) -> dict:
    """
    Classifica uma transação individual.
    Retorna: {debito: str, credito: str, status: str}
    debito e credito são códigos reduzidos (ex: "10201", "2501")
    """
    desc_upper = descricao.upper()
    is_saida = tipo.upper().startswith("SA") or "SAÍDA" in tipo.upper()

    fallback_desp = _buscar_fallback(plano, "despesa")
    fallback_rec = _buscar_fallback(plano, "receita")

    # ─── 1. Regras customizadas do usuário ──────────────────────
    r = _match_regras_usuario(descricao, "saida" if is_saida else "entrada", regras_usuario)
    if r:
        if is_saida:
            debito = r["debito"] or fallback_desp
            credito = r["credito"] or conta_banco_codigo
        else:
            debito = r["debito"] or conta_banco_codigo
            credito = r["credito"] or fallback_rec
        return {"debito": debito, "credito": credito, "status": "regra_usuario"}

    # ─── 2. Cadastro de pessoas ─────────────────────────────────
    cad = _match_cadastro(descricao, cadastros)
    if cad:
        conta_cad = cad["conta_codigo"]
        tipo_cad = cad["tipo_cadastro"]  # socio | cliente | fornecedor

        if not conta_cad:
            # Se o cadastro não tem conta associada, tenta buscar no plano
            if tipo_cad == "socio":
                conta_cad = _buscar_conta_no_plano("socio", plano) or fallback_rec
            elif tipo_cad == "cliente":
                conta_cad = _buscar_conta_no_plano("cliente", plano) or fallback_rec
            elif tipo_cad == "fornecedor":
                conta_cad = _buscar_conta_no_plano("fornecedor", plano) or fallback_desp

        if is_saida:
            return {"debito": conta_cad or fallback_desp, "credito": conta_banco_codigo, "status": "cadastro"}
        else:
            return {"debito": conta_banco_codigo, "credito": conta_cad or fallback_rec, "status": "cadastro"}

    # ─── 3. Regras automáticas do sistema ───────────────────────
    if is_saida:
        for regex, nome_interno in REGRAS_SAIDA:
            if re.search(regex, desc_upper, re.IGNORECASE):
                if nome_interno == "_fallback_despesa":
                    return {"debito": fallback_desp, "credito": conta_banco_codigo, "status": "pendente"}

                conta = _buscar_conta_no_plano(nome_interno, plano)
                if conta:
                    return {"debito": conta, "credito": conta_banco_codigo, "status": "automatico"}
                else:
                    return {"debito": fallback_desp, "credito": conta_banco_codigo, "status": "pendente"}

        # Fallback saída
        return {"debito": fallback_desp, "credito": conta_banco_codigo, "status": "pendente"}
    else:
        # Entrada — regras automáticas
        for regex, nome_interno in REGRAS_ENTRADA:
            if re.search(regex, desc_upper, re.IGNORECASE):
                if nome_interno == "_fallback_receita":
                    return {"debito": conta_banco_codigo, "credito": fallback_rec, "status": "pendente"}

                if nome_interno == "_estorno_tarifa":
                    # Estorno de tarifa: reverte a conta de tarifas
                    conta_tar = _buscar_conta_no_plano("tarifa", plano)
                    if conta_tar:
                        return {"debito": conta_banco_codigo, "credito": conta_tar, "status": "automatico"}
                    return {"debito": conta_banco_codigo, "credito": fallback_rec, "status": "pendente"}

                conta = _buscar_conta_no_plano(nome_interno, plano)
                if conta:
                    return {"debito": conta_banco_codigo, "credito": conta, "status": "automatico"}
                else:
                    return {"debito": conta_banco_codigo, "credito": fallback_rec, "status": "pendente"}

        # Fallback entrada
        return {"debito": conta_banco_codigo, "credito": fallback_rec, "status": "pendente"}


def classificar_lote(
    transacoes: list,
    conta_banco_map: dict,   # nome_banco -> codigo_reduzido
    regras_usuario: list,
    cadastros: list,
    plano: dict,             # codigo_reduzido -> descricao
) -> list:
    """
    Classifica um lote de transações no formato Contmatic.
    Filtra linhas de saldo/totais.
    Retorna lista de dicts com: data, lancamento, historico, descricao, debito, credito, valor, status
    """
    resultado = []
    seq = 0

    for tx in transacoes:
        descricao = str(tx.get("descricao", "") or "").strip()
        if not descricao:
            continue
        if deve_filtrar(descricao):
            continue

        banco = str(tx.get("banco", "") or "").strip()
        tipo = str(tx.get("tipo", "") or "").strip()
        conta_banco = conta_banco_map.get(banco, "")

        classificacao = classificar_transacao(
            descricao=descricao,
            tipo=tipo,
            banco=banco,
            conta_banco_codigo=conta_banco,
            regras_usuario=regras_usuario,
            cadastros=cadastros,
            plano=plano,
        )

        seq += 1
        resultado.append({
            "data": tx.get("data", ""),
            "lancamento": seq,
            "historico": 1,
            "descricao": descricao,
            "debito": classificacao["debito"],
            "credito": classificacao["credito"],
            "valor": tx.get("valor", 0),
            "status": classificacao["status"],
        })

    return resultado
