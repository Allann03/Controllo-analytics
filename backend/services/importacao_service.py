"""
Motor de Importação — Controllo Analytics
Suporta .xlsx, .xls, .csv com processamento em stream (sem carregar tudo em RAM).
"""

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from data.database.models import (
    Importacao,
    LancamentoMensal,
    MapeamentoTemplate,
)

# ──────────────────────────────────────────────────────────────────
#  Campos destino por tipo_dado
# ──────────────────────────────────────────────────────────────────

CAMPOS_DESTINO: dict[str, list[dict]] = {
    "faturamento": [
        {"campo": "ano",             "label": "Ano",              "obrigatorio": True},
        {"campo": "mes",             "label": "Mês (1-12)",        "obrigatorio": True},
        {"campo": "receita_bruta",   "label": "Receita Bruta",     "obrigatorio": True},
        {"campo": "deducoes_receita","label": "Deduções da Receita","obrigatorio": False},
    ],
    "folha": [
        {"campo": "ano",             "label": "Ano",              "obrigatorio": True},
        {"campo": "mes",             "label": "Mês (1-12)",        "obrigatorio": True},
        {"campo": "folha_pagamento", "label": "Folha de Pagamento","obrigatorio": True},
    ],
    "impostos": [
        {"campo": "ano",             "label": "Ano",              "obrigatorio": True},
        {"campo": "mes",             "label": "Mês (1-12)",        "obrigatorio": True},
        {"campo": "ir_csll",         "label": "IR + CSLL",        "obrigatorio": False},
        {"campo": "tributos_pagar",  "label": "Tributos a Pagar", "obrigatorio": False},
    ],
    "despesas": [
        {"campo": "ano",                 "label": "Ano",                       "obrigatorio": True},
        {"campo": "mes",                 "label": "Mês (1-12)",                 "obrigatorio": True},
        {"campo": "custo_servicos",      "label": "Custo de Serviços",         "obrigatorio": False},
        {"campo": "despesas_adm",        "label": "Despesas Administrativas",  "obrigatorio": False},
        {"campo": "despesas_comerciais", "label": "Despesas Comerciais",       "obrigatorio": False},
        {"campo": "despesas_financeiras","label": "Despesas Financeiras",      "obrigatorio": False},
        {"campo": "outras_despesas",     "label": "Outras Despesas",           "obrigatorio": False},
    ],
    "dre": [
        {"campo": "ano",                 "label": "Ano",                  "obrigatorio": True},
        {"campo": "mes",                 "label": "Mês (1-12)",            "obrigatorio": True},
        {"campo": "receita_bruta",       "label": "Receita Bruta",         "obrigatorio": True},
        {"campo": "deducoes_receita",    "label": "Deduções da Receita",   "obrigatorio": False},
        {"campo": "custo_servicos",      "label": "Custo Serv./Produtos",  "obrigatorio": False},
        {"campo": "despesas_adm",        "label": "Despesas Administrativas","obrigatorio": False},
        {"campo": "despesas_comerciais", "label": "Despesas Comerciais",   "obrigatorio": False},
        {"campo": "despesas_financeiras","label": "Despesas Financeiras",  "obrigatorio": False},
        {"campo": "outras_despesas",     "label": "Outras Despesas",       "obrigatorio": False},
        {"campo": "ir_csll",             "label": "IR + CSLL",             "obrigatorio": False},
        {"campo": "folha_pagamento",     "label": "Folha de Pagamento",    "obrigatorio": False},
    ],
    "fluxo": [
        {"campo": "ano",                 "label": "Ano",                  "obrigatorio": True},
        {"campo": "mes",                 "label": "Mês (1-12)",            "obrigatorio": True},
        {"campo": "entradas_caixa",      "label": "Entradas de Caixa",    "obrigatorio": True},
        {"campo": "saidas_caixa",        "label": "Saídas de Caixa",      "obrigatorio": True},
        {"campo": "saldo_inicial_caixa", "label": "Saldo Inicial de Caixa","obrigatorio": False},
    ],
    "balanco": [
        {"campo": "ano",                    "label": "Ano",                       "obrigatorio": True},
        {"campo": "mes",                    "label": "Mês (1-12)",                 "obrigatorio": True},
        {"campo": "caixa_equivalentes",     "label": "Caixa e Equivalentes",      "obrigatorio": False},
        {"campo": "contas_receber",         "label": "Contas a Receber",          "obrigatorio": False},
        {"campo": "estoques",               "label": "Estoques",                  "obrigatorio": False},
        {"campo": "outros_ativo_circ",      "label": "Outros Ativos Circulantes", "obrigatorio": False},
        {"campo": "ativo_nao_circulante",   "label": "Ativo Não Circulante",      "obrigatorio": False},
        {"campo": "fornecedores",           "label": "Fornecedores",              "obrigatorio": False},
        {"campo": "emprestimos_cp",         "label": "Empréstimos C/P",           "obrigatorio": False},
        {"campo": "tributos_pagar",         "label": "Tributos a Pagar",          "obrigatorio": False},
        {"campo": "outros_passivo_circ",    "label": "Outros Passivos Circulantes","obrigatorio": False},
        {"campo": "passivo_nao_circulante", "label": "Passivo Não Circulante",    "obrigatorio": False},
        {"campo": "capital_social",         "label": "Capital Social",            "obrigatorio": False},
        {"campo": "reservas",               "label": "Reservas",                  "obrigatorio": False},
        {"campo": "lucros_acumulados",      "label": "Lucros Acumulados",         "obrigatorio": False},
    ],
    "generico": [
        {"campo": "ano",          "label": "Ano",         "obrigatorio": True},
        {"campo": "mes",          "label": "Mês (1-12)",   "obrigatorio": True},
        {"campo": "receita_bruta","label": "Receita Bruta","obrigatorio": False},
        {"campo": "custo_servicos","label": "Custo",       "obrigatorio": False},
        {"campo": "despesas_adm", "label": "Despesas Adm", "obrigatorio": False},
    ],
}

TIPOS_DADO = list(CAMPOS_DESTINO.keys())

# ──────────────────────────────────────────────────────────────────
#  Leitura de arquivo (stream) → list[dict]
# ──────────────────────────────────────────────────────────────────

def _limpar_numero(valor: Any) -> float:
    """Converte string '1.234,56' ou '1234.56' em float."""
    if valor is None:
        return 0.0
    s = str(valor).strip().replace(" ", "").replace("\xa0", "")
    # formato brasileiro: 1.234,56
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def ler_cabecalho_xlsx(conteudo: bytes) -> list[str]:
    """Retorna apenas o cabeçalho (primeira linha) de um xlsx via stream."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    ws = wb.active
    cabecalho: list[str] = []
    for row in ws.iter_rows(min_row=1, max_row=1, values_only=True):
        cabecalho = [str(c).strip() if c is not None else "" for c in row]
        break
    wb.close()
    return cabecalho


def ler_cabecalho_csv(conteudo: bytes) -> list[str]:
    """Retorna o cabeçalho de um CSV detectando delimitador automaticamente."""
    texto = conteudo.decode("utf-8-sig", errors="replace")
    sniffer = csv.Sniffer()
    dialeto = sniffer.sniff(texto[:2048], delimiters=",;\t|")
    reader = csv.reader(io.StringIO(texto), dialeto)
    for row in reader:
        return [c.strip() for c in row]
    return []


def ler_linhas_xlsx(conteudo: bytes, mapeamento: dict[str, str]) -> tuple[list[dict], list[str]]:
    """Stream-lê xlsx e aplica mapeamento. Retorna (registros, erros)."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    ws = wb.active

    cabecalho: list[str] = []
    registros: list[dict] = []
    erros: list[str] = []

    for idx, row in enumerate(ws.iter_rows(values_only=True)):
        if idx == 0:
            cabecalho = [str(c).strip() if c is not None else f"col{i}" for i, c in enumerate(row)]
            continue
        if all(c is None for c in row):
            continue

        linha: dict[str, Any] = {}
        for col_orig, campo_dest in mapeamento.items():
            if col_orig in cabecalho:
                pos = cabecalho.index(col_orig)
                val = row[pos] if pos < len(row) else None
                linha[campo_dest] = val
            else:
                linha[campo_dest] = None

        ok, msg = _validar_linha(linha, idx + 1)
        if not ok:
            erros.append(msg)
        else:
            registros.append(linha)

    wb.close()
    return registros, erros


def ler_linhas_csv(conteudo: bytes, mapeamento: dict[str, str]) -> tuple[list[dict], list[str]]:
    """Stream-lê CSV e aplica mapeamento."""
    texto = conteudo.decode("utf-8-sig", errors="replace")
    sniffer = csv.Sniffer()
    dialeto = sniffer.sniff(texto[:2048], delimiters=",;\t|")
    reader = csv.DictReader(io.StringIO(texto), dialect=dialeto)

    registros: list[dict] = []
    erros: list[str] = []

    for idx, row in enumerate(reader, start=2):
        linha: dict[str, Any] = {}
        for col_orig, campo_dest in mapeamento.items():
            linha[campo_dest] = row.get(col_orig)

        ok, msg = _validar_linha(linha, idx)
        if not ok:
            erros.append(msg)
        else:
            registros.append(linha)

    return registros, erros


def _validar_linha(linha: dict, num: int) -> tuple[bool, str]:
    """Valida que ano e mes estão presentes e são válidos."""
    try:
        ano = int(_limpar_numero(linha.get("ano")))
        mes = int(_limpar_numero(linha.get("mes")))
    except (ValueError, TypeError):
        return False, f"Linha {num}: ano/mês inválidos"

    if not (1900 < ano < 2100):
        return False, f"Linha {num}: ano {ano} fora do intervalo esperado"
    if not (1 <= mes <= 12):
        return False, f"Linha {num}: mês {mes} fora do intervalo 1-12"
    return True, ""


# ──────────────────────────────────────────────────────────────────
#  Preview (sem persistir)
# ──────────────────────────────────────────────────────────────────

def preview_arquivo(conteudo: bytes, nome_arquivo: str) -> dict:
    """
    Retorna cabeçalho do arquivo e sugestão de mapeamento automático.
    Não persiste nada no banco.
    """
    ext = nome_arquivo.rsplit(".", 1)[-1].lower()
    if ext in ("xlsx", "xls"):
        colunas = ler_cabecalho_xlsx(conteudo)
    elif ext == "csv":
        colunas = ler_cabecalho_csv(conteudo)
    else:
        raise ValueError(f"Formato não suportado: .{ext}. Use .xlsx ou .csv")

    sugestoes = _auto_mapear(colunas)
    return {"colunas": colunas, "sugestoes": sugestoes}


# Heurística simples de auto-mapeamento por palavras-chave
_KEYWORDS: dict[str, list[str]] = {
    "ano":                 ["ano", "year", "exercicio", "exercício"],
    "mes":                 ["mes", "mês", "month", "competência", "competencia"],
    "receita_bruta":       ["receita bruta", "faturamento bruto", "receita total", "gross revenue"],
    "deducoes_receita":    ["deduções", "deducoes", "impostos s/", "impostos sobre receita"],
    "custo_servicos":      ["cmv", "cmc", "csv", "custo de serviços", "custo de produtos", "cogs"],
    "despesas_adm":        ["despesas adm", "despesas gerais", "g&a", "geral e adm"],
    "despesas_comerciais": ["despesas comerciais", "vendas", "marketing"],
    "despesas_financeiras":["despesas financeiras", "juros", "financial"],
    "outras_despesas":     ["outras despesas", "other expenses"],
    "ir_csll":             ["ir", "csll", "irpj", "ir+csll", "imposto de renda"],
    "folha_pagamento":     ["folha", "salários", "salarios", "payroll", "rh"],
    "entradas_caixa":      ["entradas", "recebimentos", "cash in"],
    "saidas_caixa":        ["saídas", "saidas", "pagamentos", "cash out"],
    "saldo_inicial_caixa": ["saldo inicial", "saldo anterior", "opening balance"],
    "caixa_equivalentes":  ["caixa", "disponível", "disponivel", "cash"],
    "contas_receber":      ["contas a receber", "clientes", "receivables"],
    "estoques":            ["estoque", "inventário", "inventario"],
    "ativo_nao_circulante":["ativo não circulante", "ativo fixo", "imobilizado"],
    "fornecedores":        ["fornecedores", "suppliers", "payables"],
    "emprestimos_cp":      ["empréstimos", "emprestimos", "financiamentos", "dívidas"],
    "tributos_pagar":      ["tributos a pagar", "impostos a pagar", "tax payable"],
    "capital_social":      ["capital social", "capital"],
    "lucros_acumulados":   ["lucros acumulados", "resultados acumulados"],
}


def _auto_mapear(colunas: list[str]) -> dict[str, str]:
    """Retorna {coluna_original: campo_destino} para colunas reconhecidas."""
    mapeamento: dict[str, str] = {}
    for col in colunas:
        col_lower = col.lower().strip()
        for campo, keywords in _KEYWORDS.items():
            if any(kw in col_lower for kw in keywords):
                mapeamento[col] = campo
                break
    return mapeamento


# ──────────────────────────────────────────────────────────────────
#  Processamento e upsert em LancamentoMensal
# ──────────────────────────────────────────────────────────────────

def processar_importacao(
    db: Session,
    empresa_id: int,
    usuario_id: int,
    nome_arquivo: str,
    tipo_dado: str,
    mapeamento: dict[str, str],
    conteudo: bytes,
) -> dict:
    """
    Processa o arquivo, faz upsert em LancamentoMensal e registra em Importacao.
    Retorna resumo do processamento.
    """
    agora = datetime.now(timezone.utc).isoformat()
    importacao = Importacao(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        nome_arquivo=nome_arquivo,
        tipo_dado=tipo_dado,
        status="processando",
        criado_em=agora,
    )
    db.add(importacao)
    db.flush()

    ext = nome_arquivo.rsplit(".", 1)[-1].lower()
    try:
        if ext in ("xlsx", "xls"):
            registros, erros = ler_linhas_xlsx(conteudo, mapeamento)
        elif ext == "csv":
            registros, erros = ler_linhas_csv(conteudo, mapeamento)
        else:
            raise ValueError(f"Formato .{ext} não suportado")

        meses_atualizados: set[tuple[int, int]] = set()
        for reg in registros:
            ano = int(_limpar_numero(reg.get("ano")))
            mes = int(_limpar_numero(reg.get("mes")))

            # Busca ou cria o lançamento
            lanc = (
                db.query(LancamentoMensal)
                .filter_by(empresa_id=empresa_id, ano=ano, mes=mes)
                .first()
            )
            if not lanc:
                lanc = LancamentoMensal(
                    empresa_id=empresa_id,
                    ano=ano,
                    mes=mes,
                    criado_em=agora,
                    atualizado_em=agora,
                )
                db.add(lanc)
                db.flush()
            else:
                lanc.atualizado_em = agora

            # Atualiza apenas os campos mapeados
            campos_financeiros = {v for v in mapeamento.values() if v not in ("ano", "mes")}
            for campo in campos_financeiros:
                val = _limpar_numero(reg.get(campo))
                if val != 0.0 or campo in mapeamento.values():
                    setattr(lanc, campo, val)

            meses_atualizados.add((ano, mes))

        resumo = {
            "linhas_ok": len(registros),
            "linhas_erro": len(erros),
            "meses_atualizados": sorted(list(meses_atualizados)),
            "erros": erros[:20],  # max 20 erros no resumo
        }

        importacao.status = "concluido"
        importacao.linhas_processadas = len(registros)
        importacao.linhas_com_erro = len(erros)
        importacao.resumo_json = json.dumps(resumo, ensure_ascii=False)
        db.commit()
        return resumo

    except Exception as exc:
        db.rollback()
        importacao.status = "erro"
        importacao.mensagem_erro = str(exc)[:500]
        db.add(importacao)
        db.commit()
        raise


# ──────────────────────────────────────────────────────────────────
#  Templates de mapeamento
# ──────────────────────────────────────────────────────────────────

def salvar_template(
    db: Session,
    usuario_id: int,
    nome: str,
    tipo_dado: str,
    mapeamento: dict[str, str],
) -> MapeamentoTemplate:
    agora = datetime.now(timezone.utc).isoformat()
    t = MapeamentoTemplate(
        nome=nome,
        tipo_dado=tipo_dado,
        mapeamento_json=json.dumps(mapeamento, ensure_ascii=False),
        usuario_id=usuario_id,
        criado_em=agora,
        atualizado_em=agora,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def listar_templates(db: Session, usuario_id: int) -> list[dict]:
    templates = db.query(MapeamentoTemplate).filter_by(usuario_id=usuario_id).all()
    return [
        {
            "id": t.id,
            "nome": t.nome,
            "tipo_dado": t.tipo_dado,
            "mapeamento": json.loads(t.mapeamento_json),
            "criado_em": t.criado_em,
        }
        for t in templates
    ]


def deletar_template(db: Session, template_id: int, usuario_id: int) -> bool:
    t = db.query(MapeamentoTemplate).filter_by(id=template_id, usuario_id=usuario_id).first()
    if not t:
        return False
    db.delete(t)
    db.commit()
    return True


# ──────────────────────────────────────────────────────────────────
#  Geração de planilhas modelo (.xlsx) com openpyxl
# ──────────────────────────────────────────────────────────────────

_COR_HEADER = "5B21D4"   # roxo
_COR_HEADER_INSTRUCOES = "1E3A5F"  # azul escuro
_COR_LINHA_PAR = "F8F5FF"

_MODELOS: dict[str, dict] = {
    "faturamento": {
        "titulo": "Modelo — Faturamento Mensal",
        "colunas": [
            ("Ano",              "Ano com 4 dígitos. Ex: 2024"),
            ("Mês",              "Número do mês (1 a 12). Ex: 1 para Janeiro"),
            ("Receita Bruta",    "Total das receitas antes de impostos e deduções (R$)"),
            ("Deduções da Receita", "Impostos sobre receita: ISS, PIS, COFINS, ICMS (R$)"),
        ],
        "exemplos": [
            [2024, 1, 150000.00, 15000.00],
            [2024, 2, 162000.00, 16200.00],
            [2024, 3, 145000.00, 14500.00],
        ],
    },
    "despesas": {
        "titulo": "Modelo — Despesas e Custos Mensais",
        "colunas": [
            ("Ano",                     "Ano com 4 dígitos. Ex: 2024"),
            ("Mês",                     "Número do mês (1 a 12)"),
            ("Custo de Serviços",       "CMV, CSV ou CSP — custo direto da atividade (R$)"),
            ("Despesas Administrativas","Aluguel, energia, material, seguros, etc. (R$)"),
            ("Despesas Comerciais",     "Marketing, vendas, comissões, etc. (R$)"),
            ("Despesas Financeiras",    "Juros, tarifas bancárias, IOF (R$)"),
            ("Outras Despesas",         "Demais despesas não classificadas acima (R$)"),
        ],
        "exemplos": [
            [2024, 1, 45000.00, 22000.00, 12000.00, 5000.00, 2000.00],
            [2024, 2, 48000.00, 22000.00, 13000.00, 5000.00, 1500.00],
            [2024, 3, 43000.00, 22000.00, 11000.00, 4800.00, 1800.00],
        ],
    },
    "impostos": {
        "titulo": "Modelo — Impostos e Tributos Mensais",
        "colunas": [
            ("Ano",              "Ano com 4 dígitos. Ex: 2024"),
            ("Mês",              "Número do mês (1 a 12)"),
            ("IR + CSLL",        "IRPJ + Contribuição Social sobre Lucro Líquido (R$)"),
            ("Tributos a Pagar", "PIS, COFINS, ISS, ICMS e outros tributos (R$)"),
        ],
        "exemplos": [
            [2024, 1, 8000.00, 12000.00],
            [2024, 2, 9000.00, 13500.00],
            [2024, 3, 7500.00, 11000.00],
        ],
    },
    "folha": {
        "titulo": "Modelo — Folha de Pagamento Mensal",
        "colunas": [
            ("Ano",              "Ano com 4 dígitos. Ex: 2024"),
            ("Mês",              "Número do mês (1 a 12)"),
            ("Folha de Pagamento", "Custo total com pessoal: salários + encargos + benefícios (R$)"),
        ],
        "exemplos": [
            [2024, 1, 64350.00],
            [2024, 2, 64350.00],
            [2024, 3, 67675.00],
        ],
    },
    "fluxo": {
        "titulo": "Modelo — Fluxo de Caixa Mensal",
        "colunas": [
            ("Ano",                 "Ano com 4 dígitos. Ex: 2024"),
            ("Mês",                 "Número do mês (1 a 12)"),
            ("Entradas de Caixa",   "Total de recebimentos no mês (R$)"),
            ("Saídas de Caixa",     "Total de pagamentos no mês (R$)"),
            ("Saldo Inicial de Caixa", "Saldo em caixa no início do mês (R$)"),
        ],
        "exemplos": [
            [2024, 1, 148000.00, 112000.00, 50000.00],
            [2024, 2, 160000.00, 118000.00, 86000.00],
            [2024, 3, 142000.00, 108000.00, 128000.00],
        ],
    },
    "balanco": {
        "titulo": "Modelo — Balanço Patrimonial Mensal",
        "colunas": [
            ("Ano",                       "Ano com 4 dígitos"),
            ("Mês",                       "Número do mês (1 a 12)"),
            ("Caixa e Equivalentes",      "Disponibilidades: caixa, conta corrente (R$)"),
            ("Contas a Receber",          "Duplicatas e valores a receber de clientes (R$)"),
            ("Estoques",                  "Valor do estoque de mercadorias/produtos (R$)"),
            ("Outros Ativos Circulantes", "Demais ativos de curto prazo (R$)"),
            ("Ativo Não Circulante",      "Imobilizado, intangível, investimentos LP (R$)"),
            ("Fornecedores",              "Contas a pagar a fornecedores (R$)"),
            ("Empréstimos C/P",           "Parcelas de empréstimos vencendo em até 12 meses (R$)"),
            ("Tributos a Pagar",          "Impostos e contribuições a recolher (R$)"),
            ("Outros Passivos Circulantes","Demais obrigações de curto prazo (R$)"),
            ("Passivo Não Circulante",    "Dívidas com vencimento superior a 12 meses (R$)"),
            ("Capital Social",            "Capital integralizado pelos sócios (R$)"),
            ("Reservas",                  "Reservas de lucro e capital (R$)"),
            ("Lucros Acumulados",         "Resultado líquido acumulado (R$)"),
        ],
        "exemplos": [
            [2024, 1, 86000, 45000, 20000, 5000, 200000, 30000, 20000, 12000, 5000, 80000, 100000, 50000, 59000],
            [2024, 2, 128000, 48000, 19000, 5000, 198000, 28000, 20000, 13500, 5000, 78000, 100000, 50000, 103500],
            [2024, 3, 162000, 52000, 18500, 5000, 196000, 31000, 20000, 12000, 4500, 76000, 100000, 50000, 140000],
        ],
    },
    "dre": {
        "titulo": "Modelo — DRE Completa Mensal",
        "colunas": [
            ("Ano",                       "Ano com 4 dígitos"),
            ("Mês",                       "Número do mês (1 a 12)"),
            ("Receita Bruta",             "Receita total antes de impostos (R$)"),
            ("Deduções da Receita",       "Impostos sobre receita (ISS, PIS, COFINS, ICMS) (R$)"),
            ("Custo de Serviços",         "Custo direto da atividade/produto (CMV/CSV) (R$)"),
            ("Despesas Administrativas",  "Despesas gerais e administrativas (R$)"),
            ("Despesas Comerciais",       "Despesas de vendas e marketing (R$)"),
            ("Despesas Financeiras",      "Juros e encargos financeiros (R$)"),
            ("Outras Despesas",           "Demais despesas operacionais (R$)"),
            ("IR + CSLL",                 "Imposto de Renda + Contribuição Social (R$)"),
            ("Folha de Pagamento",        "Custo total com pessoal (R$)"),
        ],
        "exemplos": [
            [2024, 1, 150000, 15000, 45000, 20000, 10000, 5000, 2000, 8000, 64350],
            [2024, 2, 162000, 16200, 48600, 20000, 11000, 5000, 1500, 9000, 64350],
            [2024, 3, 145000, 14500, 43500, 20000, 10500, 4800, 1800, 7500, 67675],
        ],
    },
}


def gerar_modelo_xlsx(tipo_dado: str) -> bytes:
    """
    Gera um arquivo .xlsx formatado com dados de exemplo e aba de instruções.
    Usa openpyxl (já presente no projeto).
    """
    import openpyxl
    from openpyxl.styles import (
        Font, PatternFill, Alignment, Border, Side, numbers
    )
    from openpyxl.utils import get_column_letter

    if tipo_dado not in _MODELOS:
        raise ValueError(f"tipo_dado inválido: {tipo_dado}")

    modelo = _MODELOS[tipo_dado]
    wb = openpyxl.Workbook()

    # ── Aba Dados ──────────────────────────────────────────────────
    ws = wb.active
    ws.title = "Dados"

    # Estilos
    cor_header = _COR_HEADER
    fill_header = PatternFill("solid", fgColor=cor_header)
    fill_par = PatternFill("solid", fgColor=_COR_LINHA_PAR.replace("#", ""))
    font_header = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    font_titulo = Font(name="Calibri", bold=True, color="2D1B69", size=13)
    font_dado = Font(name="Calibri", size=10)
    alinhar_centro = Alignment(horizontal="center", vertical="center")
    alinhar_esq = Alignment(horizontal="left", vertical="center", wrap_text=False)
    borda_fina = Border(
        left=Side(style="thin", color="D1C4E9"),
        right=Side(style="thin", color="D1C4E9"),
        top=Side(style="thin", color="D1C4E9"),
        bottom=Side(style="thin", color="D1C4E9"),
    )
    fmt_numero = '#,##0.00'
    fmt_inteiro = '0'

    colunas = modelo["colunas"]
    n_cols = len(colunas)

    # Linha de título
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n_cols)
    cell_titulo = ws.cell(row=1, column=1, value=modelo["titulo"])
    cell_titulo.font = font_titulo
    cell_titulo.alignment = alinhar_esq
    cell_titulo.fill = PatternFill("solid", fgColor="EDE9FE")
    ws.row_dimensions[1].height = 24

    # Subtítulo instrucional
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=n_cols)
    cell_sub = ws.cell(row=2, column=1,
        value="Preencha a partir da linha 5. Não altere os cabeçalhos. Salve como .xlsx antes de importar.")
    cell_sub.font = Font(name="Calibri", italic=True, color="6B7280", size=9)
    cell_sub.alignment = alinhar_esq
    ws.row_dimensions[2].height = 16

    # Linha em branco separadora
    ws.row_dimensions[3].height = 8

    # Cabeçalhos (linha 4)
    for col_idx, (nome_col, _) in enumerate(colunas, start=1):
        cell = ws.cell(row=4, column=col_idx, value=nome_col)
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = alinhar_centro
        cell.border = borda_fina
    ws.row_dimensions[4].height = 22
    ws.freeze_panes = "A5"
    # AutoFilter na linha de cabeçalho
    ultima_col = get_column_letter(n_cols)
    ws.auto_filter.ref = f"A4:{ultima_col}4"

    # Linhas de exemplo (a partir da linha 5)
    for row_idx, exemplo in enumerate(modelo["exemplos"], start=5):
        fill_linha = fill_par if row_idx % 2 == 0 else PatternFill()
        for col_idx, val in enumerate(exemplo, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_dado
            cell.border = borda_fina
            cell.fill = fill_linha
            if col_idx <= 2:  # Ano e Mês
                cell.alignment = alinhar_centro
                cell.number_format = fmt_inteiro
            else:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = fmt_numero

    # Largura das colunas
    for col_idx, (nome_col, _) in enumerate(colunas, start=1):
        letra = get_column_letter(col_idx)
        if col_idx <= 2:
            ws.column_dimensions[letra].width = 10
        else:
            comprimento = max(len(nome_col) + 2, 20)
            ws.column_dimensions[letra].width = comprimento

    # ── Aba Instruções ─────────────────────────────────────────────
    wi = wb.create_sheet("Instruções")
    fill_hi = PatternFill("solid", fgColor=_COR_HEADER_INSTRUCOES)
    font_hi = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    font_body = Font(name="Calibri", size=10)
    font_titulo_i = Font(name="Calibri", bold=True, color="1E3A5F", size=13)

    wi.merge_cells("A1:C1")
    wi.cell(row=1, column=1, value=f"Instruções — {modelo['titulo']}").font = font_titulo_i
    wi.cell(row=1, column=1).fill = PatternFill("solid", fgColor="DBEAFE")
    wi.row_dimensions[1].height = 24

    wi.merge_cells("A2:C2")
    wi.cell(row=2, column=1,
        value="Use a aba 'Dados' para preencher. Esta aba explica cada coluna.").font = Font(
        name="Calibri", italic=True, color="6B7280", size=9)
    wi.row_dimensions[2].height = 16

    # Cabeçalhos da tabela de instruções
    for col_idx, label in enumerate(["Coluna", "Descrição", "Exemplo"], start=1):
        c = wi.cell(row=4, column=col_idx, value=label)
        c.fill = fill_hi
        c.font = font_hi
        c.alignment = alinhar_centro
        c.border = borda_fina
    wi.row_dimensions[4].height = 20

    for row_idx, (nome_col, descricao) in enumerate(colunas, start=5):
        fill_i = fill_par if row_idx % 2 == 0 else PatternFill()
        exemplo_val = modelo["exemplos"][0][row_idx - 5] if (row_idx - 5) < len(modelo["exemplos"][0]) else ""

        c1 = wi.cell(row=row_idx, column=1, value=nome_col)
        c2 = wi.cell(row=row_idx, column=2, value=descricao)
        c3 = wi.cell(row=row_idx, column=3, value=str(exemplo_val))

        for c in [c1, c2, c3]:
            c.font = font_body
            c.fill = fill_i
            c.border = borda_fina
            c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        wi.row_dimensions[row_idx].height = 20

    wi.column_dimensions["A"].width = 30
    wi.column_dimensions["B"].width = 55
    wi.column_dimensions["C"].width = 18

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ──────────────────────────────────────────────────────────────────
#  Histórico de importações
# ──────────────────────────────────────────────────────────────────

def listar_historico(db: Session, empresa_id: int) -> list[dict]:
    items = (
        db.query(Importacao)
        .filter_by(empresa_id=empresa_id)
        .order_by(Importacao.criado_em.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": i.id,
            "nome_arquivo": i.nome_arquivo,
            "tipo_dado": i.tipo_dado,
            "status": i.status,
            "linhas_processadas": i.linhas_processadas,
            "linhas_com_erro": i.linhas_com_erro,
            "resumo": json.loads(i.resumo_json) if i.resumo_json else {},
            "mensagem_erro": i.mensagem_erro,
            "criado_em": i.criado_em,
        }
        for i in items
    ]
