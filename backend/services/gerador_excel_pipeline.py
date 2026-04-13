"""
gerador_excel_pipeline.py — Geracao de Excel conforme pipeline de 8 passos.

Gera arquivo .xlsx com 3 abas:
  1. Transacoes (colunas separadas Entrada/Saida + saldo progressivo)
  2. Resumo (metricas do extrato + resultado do pipeline)
  3. Log de Validacao (todos os 8 passos)
"""

from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def _f(val) -> float:
    """Converte para float (openpyxl nao aceita Decimal)."""
    if isinstance(val, Decimal):
        return float(val)
    if val is None:
        return 0.0
    return float(val)


def gerar_excel_pipeline(
    transacoes: list,
    caminho_saida: str,
    saldo_inicial: float = None,
    saldo_final: float = None,
    banco_display: str = '',
    layout: str = '',
    gap: float = None,
    reconciliacao: str = '',
    confianca: str = '',
    checkpoints_ok: int = 0,
    checkpoints_total: int = 0,
    warnings: list = None,
    divergencias: list = None,
    log_passos: list = None,
    num_paginas: int = 0,
) -> str:
    """Gera Excel do pipeline de 8 passos."""

    warnings = warnings or []
    divergencias = divergencias or []
    log_passos = log_passos or []

    wb = Workbook()

    # Estilos
    COR_HEADER = "1e3a5f"
    COR_VERDE = "2E7D32"
    COR_VERDE_CL = "E8F5E9"
    COR_VERMELHO = "C62828"
    COR_VERMELHO_CL = "FFEBEE"
    COR_AMARELO_CL = "FFF8E1"
    COR_BORDA = "CCCCCC"

    h_font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
    h_fill = PatternFill("solid", start_color=COR_HEADER)
    h_align = Alignment(horizontal="center", vertical="center")
    n_font = Font(name="Arial", size=9)
    e_fill = PatternFill("solid", start_color=COR_VERDE_CL)
    s_fill = PatternFill("solid", start_color=COR_VERMELHO_CL)
    w_fill = PatternFill("solid", start_color=COR_AMARELO_CL)
    thin = Side(style="thin", color=COR_BORDA)
    brd = Border(left=thin, right=thin, top=thin, bottom=thin)
    money_fmt = '#,##0.00'
    right_align = Alignment(horizontal="right")
    center_align = Alignment(horizontal="center")

    # ── ABA 1: Transacoes ────────────────────────────────────────────

    ws = wb.active
    ws.title = "Transações"

    cols = ["Data", "Descrição", "Entrada (R$)", "Saída (R$)", "Saldo (R$)", "Observação"]
    widths = [12, 50, 16, 16, 16, 30]

    for c, (col, w) in enumerate(zip(cols, widths), 1):
        cell = ws.cell(row=1, column=c, value=col)
        cell.font, cell.fill, cell.alignment, cell.border = h_font, h_fill, h_align, brd
        ws.column_dimensions[get_column_letter(c)].width = w

    saldo_corrente = _f(saldo_inicial) if saldo_inicial is not None else 0.0

    # Mapa de divergencias por data para observacao
    div_por_data = {}
    for d in divergencias:
        div_por_data.setdefault(d.get('data', ''), []).append(d)

    for row, t in enumerate(transacoes, 2):
        tipo = t.get("tipo", "saida")
        valor = _f(t.get("valor", 0))

        if tipo == "entrada":
            saldo_corrente += valor
            val_entrada = valor
            val_saida = None
            fill = e_fill
        else:
            saldo_corrente -= valor
            val_entrada = None
            val_saida = valor
            fill = s_fill

        # Observacao: warnings e divergencias
        obs_parts = []
        data_tx = t.get("data", "")
        if data_tx in div_por_data:
            obs_parts.append("⚠️ Divergência checkpoint")
        obs = "; ".join(obs_parts)

        values = [
            t.get("data", ""),
            t.get("descricao", ""),
            val_entrada,
            val_saida,
            round(saldo_corrente, 2),
            obs,
        ]

        for c, val in enumerate(values, 1):
            cell = ws.cell(row=row, column=c, value=val)
            cell.border = brd
            cell.font = n_font
            if c == 1:
                cell.alignment = center_align
            elif c in (3, 4, 5):
                if val is not None:
                    cell.number_format = money_fmt
                    cell.alignment = right_align
                    if c == 3:
                        cell.font = Font(name="Arial", size=9, color=COR_VERDE)
                    elif c == 4:
                        cell.font = Font(name="Arial", size=9, color=COR_VERMELHO)
            elif c == 6 and obs:
                cell.fill = w_fill

    # Totais
    tot_row = len(transacoes) + 3
    total_e = sum(_f(t['valor']) for t in transacoes if t.get('tipo') == 'entrada')
    total_s = sum(_f(t['valor']) for t in transacoes if t.get('tipo') == 'saida')

    ws.cell(row=tot_row, column=2, value="TOTAIS").font = Font(name="Arial", bold=True, size=10)
    c_te = ws.cell(row=tot_row, column=3, value=total_e)
    c_te.font = Font(name="Arial", bold=True, color=COR_VERDE, size=10)
    c_te.number_format = money_fmt
    c_ts = ws.cell(row=tot_row, column=4, value=total_s)
    c_ts.font = Font(name="Arial", bold=True, color=COR_VERMELHO, size=10)
    c_ts.number_format = money_fmt

    # ── ABA 2: Resumo ────────────────────────────────────────────────

    ws2 = wb.create_sheet("Resumo")
    ws2.column_dimensions["A"].width = 30
    ws2.column_dimensions["B"].width = 40

    # Header
    for c, val in enumerate(["Métrica", "Valor"], 1):
        cell = ws2.cell(row=1, column=c, value=val)
        cell.font, cell.fill, cell.alignment, cell.border = h_font, h_fill, h_align, brd

    # Determine periodo
    datas = sorted(set(t['data'] for t in transacoes if t.get('data')),
                   key=lambda d: (int(d[6:10]), int(d[3:5]), int(d[0:2]))
                   if len(d) >= 10 else (0, 0, 0))
    periodo = f"{datas[0]} a {datas[-1]}" if len(datas) >= 2 else (datas[0] if datas else "")

    resumo_data = [
        ("Banco", banco_display),
        ("Layout", layout),
        ("Período", periodo),
        ("Saldo Inicial", f"R$ {saldo_inicial:,.2f}" if saldo_inicial is not None else "N/A"),
        ("Saldo Final", f"R$ {saldo_final:,.2f}" if saldo_final is not None else "N/A"),
        ("Total Entradas", f"R$ {total_e:,.2f}"),
        ("Total Saídas", f"R$ {total_s:,.2f}"),
        ("Gap", f"R$ {gap:.2f}" if gap is not None else "N/A"),
        ("Transações", str(len(transacoes))),
        ("Confiança", confianca),
        ("Reconciliação", reconciliacao),
        ("Checkpoints OK", f"{checkpoints_ok}/{checkpoints_total}" if checkpoints_total > 0 else "N/A"),
        ("Warnings", str(len(warnings))),
        ("Páginas", str(num_paginas)),
    ]

    for row, (metrica, valor) in enumerate(resumo_data, 2):
        ws2.cell(row=row, column=1, value=metrica).font = Font(name="Arial", bold=True, size=10)
        c_val = ws2.cell(row=row, column=2, value=valor)
        c_val.font = n_font
        c_val.border = brd

        # Colorir confianca
        if metrica == "Confiança":
            if valor == "ALTA":
                c_val.font = Font(name="Arial", bold=True, color=COR_VERDE, size=10)
            elif valor == "BAIXA":
                c_val.font = Font(name="Arial", bold=True, color=COR_VERMELHO, size=10)

    # ── ABA 3: Log de Validacao ──────────────────────────────────────

    ws3 = wb.create_sheet("Log de Validação")
    ws3.column_dimensions["A"].width = 10
    ws3.column_dimensions["B"].width = 10
    ws3.column_dimensions["C"].width = 30
    ws3.column_dimensions["D"].width = 8
    ws3.column_dimensions["E"].width = 70
    ws3.column_dimensions["F"].width = 50

    log_cols = ["Hora", "Passo", "Nome", "Status", "Mensagem", "Detalhes"]
    for c, val in enumerate(log_cols, 1):
        cell = ws3.cell(row=1, column=c, value=val)
        cell.font, cell.fill, cell.alignment, cell.border = h_font, h_fill, h_align, brd

    for row, entry in enumerate(log_passos, 2):
        ts = getattr(entry, 'timestamp', '')
        passo = getattr(entry, 'passo', 0)
        nome = getattr(entry, 'nome', '')
        ok = getattr(entry, 'ok', False)
        msg = getattr(entry, 'mensagem', '')
        det = '; '.join(getattr(entry, 'detalhes', [])[:3])

        values = [ts, f"Passo {passo}", nome, "✅" if ok else "❌", msg, det]
        for c, val in enumerate(values, 1):
            cell = ws3.cell(row=row, column=c, value=val)
            cell.font = n_font
            cell.border = brd
            if c == 4:
                cell.alignment = center_align
                if not ok:
                    cell.fill = PatternFill("solid", start_color=COR_VERMELHO_CL)

    # Warnings no final do log
    if warnings:
        row_w = len(log_passos) + 3
        ws3.cell(row=row_w, column=1, value="WARNINGS").font = Font(name="Arial", bold=True, size=10)
        for i, w in enumerate(warnings):
            ws3.cell(row=row_w + 1 + i, column=2, value=w).font = n_font

    wb.save(caminho_saida)
    return caminho_saida
