"""
gerador_excel.py — Excel básico no formato contábil (Sessão 22, spec Allan).

Layout fixo de 7 colunas, 1 aba, sem totalizadores. Destinado a importação
em sistema contábil. Para o Excel contábil com partida dobrada e plano de
contas, ver gerador_excel_contabil.py (não tocado nesta sessão).
"""

from datetime import datetime
from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font


_CABECALHOS = ["Lançamento", "Data", "Débito", "Crédito", "Valor", "Histórico", "Complemento"]
_LARGURAS = [12, 12, 10, 10, 14, 10, 50]


def _to_float(val) -> float:
    if isinstance(val, Decimal):
        return float(val)
    if val is None:
        return 0.0
    return float(val)


def _parse_data(data_str):
    """'DD/MM/YYYY' -> datetime.date. Retorna o próprio str se não parsear."""
    if isinstance(data_str, datetime):
        return data_str.date()
    try:
        return datetime.strptime(str(data_str), "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return data_str


def gerar_excel(transacoes: list, caminho_saida: str, saldo_inicial: float = None) -> str:
    """Gera Excel básico no layout S22 (7 colunas, 1 aba, sem totalizadores).

    saldo_inicial: aceito por compatibilidade com chamadas legadas. Não é mais
    usado no Excel básico (S22 — spec Allan). O Excel contábil
    (gerador_excel_contabil.py) ainda usa saldo_inicial.
    """
    # Filtra tipo='posicao' (saldos de carteira de investimento, não movimentação de caixa).
    # Decisão da Sessão 22 — spec do Allan é Excel contábil, posições não são lançamentos.
    transacoes_filtradas = [t for t in (transacoes or []) if t.get("tipo") != "posicao"]

    wb = Workbook()
    ws = wb.active
    ws.title = "Lançamentos"

    header_font = Font(bold=True)
    for col_idx, (cab, larg) in enumerate(zip(_CABECALHOS, _LARGURAS), start=1):
        cell = ws.cell(row=1, column=col_idx, value=cab)
        cell.font = header_font
        ws.column_dimensions[cell.column_letter].width = larg

    for i, t in enumerate(transacoes_filtradas, start=1):
        row = i + 1
        valor = abs(_to_float(t.get("valor", 0)))
        data_val = _parse_data(t.get("data", ""))

        ws.cell(row=row, column=1, value=i)
        c_data = ws.cell(row=row, column=2, value=data_val)
        if isinstance(data_val, (datetime,)) or hasattr(data_val, "year"):
            c_data.number_format = "DD/MM/YYYY"
        c_valor = ws.cell(row=row, column=5, value=valor)
        c_valor.number_format = "#,##0.00"
        ws.cell(row=row, column=7, value=t.get("descricao", ""))

    wb.save(caminho_saida)
    return caminho_saida
