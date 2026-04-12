from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import os


def _to_float(val) -> float:
    """Converte Decimal/int/float para float (openpyxl não aceita Decimal)."""
    if isinstance(val, Decimal):
        return float(val)
    return val

def gerar_excel(transacoes: list, caminho_saida: str, saldo_inicial: float = None) -> str:
    if not transacoes:
        raise ValueError("Nenhuma transação encontrada para gerar o Excel.")

    wb = Workbook()

    # ------------------------------------------------------------------ #
    #  ESTILOS                                                           #
    # ------------------------------------------------------------------ #
    cor_roxo        = "6200EA"
    cor_verde_esc   = "2E7D32"
    cor_verde_cl    = "E8F5E9"
    cor_vermelho_esc = "C62828"
    cor_vermelho_cl  = "FFEBEE"
    cor_borda        = "CCCCCC"

    header_font  = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    header_fill  = PatternFill("solid", start_color=cor_roxo, end_color=cor_roxo)
    header_align = Alignment(horizontal="center", vertical="center")
    normal_font  = Font(name="Arial", size=10)
    entrada_fill = PatternFill("solid", start_color=cor_verde_cl,    end_color=cor_verde_cl)
    saida_fill   = PatternFill("solid", start_color=cor_vermelho_cl, end_color=cor_vermelho_cl)
    entrada_font = Font(name="Arial", color=cor_verde_esc,    size=10)
    saida_font   = Font(name="Arial", color=cor_vermelho_esc, size=10)

    thin   = Side(style="thin", color=cor_borda)
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # ------------------------------------------------------------------ #
    #  ABA: TRANSAÇÕES                                                   #
    # ------------------------------------------------------------------ #
    ws = wb.active
    ws.title = "Transações"

    # ATUALIZADO: Inserida a 'Categoria' e ajustadas as larguras
    cabecalhos = ["Data", "Banco", "Categoria", "Descrição", "Tipo", "Valor (R$)"]
    larguras   = [14,     12,      25,          50,          12,     16]

    for col, (cab, larg) in enumerate(zip(cabecalhos, larguras), 1):
        cell = ws.cell(row=1, column=col, value=cab)
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = header_align
        cell.border    = border
        ws.column_dimensions[get_column_letter(col)].width = larg

    ws.row_dimensions[1].height = 22

    for row_idx, t in enumerate(transacoes, 2):
        tipo     = t.get("tipo", "entrada")
        r_fill   = entrada_fill if tipo == "entrada" else saida_fill
        r_font   = entrada_font if tipo == "entrada" else saida_font

        # ATUALIZADO: Trazendo a tag de categoria que a nossa IA criou
        valores = [
            t.get("data",      ""),
            t.get("banco",     ""),
            t.get("categoria", "Outras Despesas"),
            t.get("descricao", ""),
            "Entrada" if tipo == "entrada" else "Saída",
            _to_float(t.get("valor", 0.0)),
        ]

        for col, val in enumerate(valores, 1):
            cell        = ws.cell(row=row_idx, column=col, value=val)
            cell.border = border
            cell.fill   = r_fill
            
            # ATUALIZADO: Tipo agora é col 5 e Valor é col 6
            if col in (5, 6):
                cell.font = r_font
            else:
                cell.font = normal_font
                
            if col == 6:
                cell.number_format = '#,##0.00'
                cell.alignment     = Alignment(horizontal="right")
            elif col == 1:
                cell.alignment = Alignment(horizontal="center")
            elif col == 5:
                cell.alignment = Alignment(horizontal="center")

    # Totais
    entradas = float(sum(t["valor"] for t in transacoes if t.get("tipo") == "entrada"))
    saidas   = float(sum(t["valor"] for t in transacoes if t.get("tipo") == "saida"))
    si       = float(saldo_inicial) if saldo_inicial is not None else 0.0
    saldo    = si + entradas - saidas

    tot = len(transacoes) + 2

    def _celula_total(ws, row, col, val, cor, fmt=None):
        c = ws.cell(row=row, column=col, value=val)
        c.font = Font(name="Arial", bold=True, color=cor, size=10)
        if fmt:
            c.number_format = fmt
            c.alignment     = Alignment(horizontal="right")
        return c

    # ATUALIZADO: O bloco de totais andou uma coluna para a direita
    ws.cell(row=tot, column=4, value="TOTAIS").font = Font(name="Arial", bold=True, size=10)

    row_offset = 0
    # Saldo Inicial (exibe somente se foi informado)
    if saldo_inicial is not None:
        cor_si = cor_verde_esc if si >= 0 else cor_vermelho_esc
        _celula_total(ws, tot + row_offset, 5, f"Saldo Inicial: R$ {si:,.2f}", cor_si)
        _celula_total(ws, tot + row_offset, 6, si, cor_si, '#,##0.00')
        row_offset += 1

    _celula_total(ws, tot + row_offset,     5, f"Entradas: R$ {entradas:,.2f}", cor_verde_esc)
    _celula_total(ws, tot + row_offset,     6, entradas, cor_verde_esc, '#,##0.00')
    row_offset += 1
    _celula_total(ws, tot + row_offset, 5, f"Saídas:   R$ {abs(saidas):,.2f}", cor_vermelho_esc)
    _celula_total(ws, tot + row_offset, 6, saidas, cor_vermelho_esc, '#,##0.00')
    row_offset += 1
    cor_saldo = cor_verde_esc if saldo >= 0 else cor_vermelho_esc
    _celula_total(ws, tot + row_offset, 5, f"Saldo Final: R$ {saldo:,.2f}", cor_saldo)
    # Fórmula real do Excel para auditoria: =Saldo Inicial + Entradas - ABS(Saídas)
    si_cell  = f"F{tot}" if saldo_inicial is not None else None
    ent_cell = f"F{tot + (1 if saldo_inicial is not None else 0)}"
    sai_cell = f"F{tot + (2 if saldo_inicial is not None else 1)}"
    if si_cell:
        formula = f"={si_cell}+{ent_cell}+{sai_cell}"
    else:
        formula = f"={ent_cell}+{sai_cell}"
    c_saldo = ws.cell(row=tot + row_offset, column=6, value=formula)
    c_saldo.font = Font(name="Arial", bold=True, color=cor_saldo, size=10)
    c_saldo.number_format = '#,##0.00'
    c_saldo.alignment = Alignment(horizontal="right")

    # ------------------------------------------------------------------ #
    #  ABA: RESUMO POR BANCO                                             #
    # ------------------------------------------------------------------ #
    ws2 = wb.create_sheet("Resumo por Banco")
    for col, larg in enumerate([22, 20, 20, 20], 1):
        ws2.column_dimensions[get_column_letter(col)].width = larg

    for col, cab in enumerate(["Banco", "Total Entradas", "Total Saídas", "Saldo"], 1):
        cell           = ws2.cell(row=1, column=col, value=cab)
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = header_align
        cell.border    = border

    bancos: dict = {}
    for t in transacoes:
        b = t.get("banco", "Desconhecido")
        if b not in bancos:
            bancos[b] = {"entrada": 0.0, "saida": 0.0}
        if t.get("tipo") == "entrada":
            bancos[b]["entrada"] += float(t.get("valor", 0))
        else:
            bancos[b]["saida"]   += float(t.get("valor", 0))

    for row_idx, (banco, vals) in enumerate(bancos.items(), 2):
        saldo_b = vals["entrada"] + vals["saida"]
        cor_s   = cor_verde_esc if saldo_b >= 0 else cor_vermelho_esc
        ws2.cell(row=row_idx, column=1, value=banco).font = normal_font
        for col, val, cor in [
            (2, vals["entrada"], "000000"),
            (3, vals["saida"],   "000000"),
            (4, saldo_b,         cor_s),
        ]:
            c               = ws2.cell(row=row_idx, column=col, value=val)
            c.font          = Font(name="Arial", size=10, color=cor)
            c.number_format = '#,##0.00'
            c.alignment     = Alignment(horizontal="right")
            c.border        = border

    # ------------------------------------------------------------------ #
    #  ABA: CALENDÁRIO DIÁRIO                                            #
    # ------------------------------------------------------------------ #
    ws3 = wb.create_sheet("Resumo Diário")
    ws3.column_dimensions["A"].width = 16
    ws3.column_dimensions["B"].width = 18
    ws3.column_dimensions["C"].width = 18
    ws3.column_dimensions["D"].width = 18

    for col, cab in enumerate(["Data", "Entradas", "Saídas", "Saldo do Dia"], 1):
        cell           = ws3.cell(row=1, column=col, value=cab)
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = header_align
        cell.border    = border

    datas: dict = {}
    for t in transacoes:
        d = t.get("data", "")
        if d not in datas:
            datas[d] = {"entrada": 0.0, "saida": 0.0}
        if t.get("tipo") == "entrada":
            datas[d]["entrada"] += float(t.get("valor", 0))
        else:
            datas[d]["saida"]   += float(t.get("valor", 0))

    # Ordena por data DD/MM/YYYY
    def _sort_data(d):
        try:
            parts = d.split("/")
            return (int(parts[2]), int(parts[1]), int(parts[0]))
        except Exception:
            return (0, 0, 0)

    for row_idx, (data, vals) in enumerate(sorted(datas.items(), key=lambda x: _sort_data(x[0])), 2):
        saldo_d = vals["entrada"] + vals["saida"]
        cor_s   = cor_verde_esc if saldo_d >= 0 else cor_vermelho_esc
        ws3.cell(row=row_idx, column=1, value=data).font = normal_font
        for col, val, cor in [
            (2, vals["entrada"], cor_verde_esc),
            (3, vals["saida"],   cor_vermelho_esc),
            (4, saldo_d,         cor_s),
        ]:
            c               = ws3.cell(row=row_idx, column=col, value=val)
            c.font          = Font(name="Arial", size=10, color=cor)
            c.number_format = '#,##0.00'
            c.alignment     = Alignment(horizontal="right")
            c.border        = border

    wb.save(caminho_saida)
    return caminho_saida