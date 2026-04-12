"""
Router de Relatórios Exportáveis
Gera arquivos Excel com múltiplas abas a partir dos dados financeiros registrados.
"""

import io
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from data.database.config import get_db
from data.database import models

router = APIRouter(prefix="/api/relatorios", tags=["relatorios"])

# ──────────────────────────────────────────────────────────────────
#  Auth
# ──────────────────────────────────────────────────────────────────

from services.auth_utils import get_current_user as _get_user, resolve_empresa_or_403


# ──────────────────────────────────────────────────────────────────
#  Helpers de estilo openpyxl
# ──────────────────────────────────────────────────────────────────

def _row_header(ws, texto: str, colunas: list, row: int, cor_hex: str = "1E293B"):
    from openpyxl.styles import Font, PatternFill, Alignment
    for col_idx, col in enumerate(colunas):
        c = ws.cell(row=row, column=col_idx + 1, value=col if col_idx > 0 else texto)
        c.font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
        c.fill = PatternFill("solid", start_color=cor_hex, end_color=cor_hex)
        c.alignment = Alignment(horizontal="center" if col_idx > 0 else "left", vertical="center")


# ──────────────────────────────────────────────────────────────────
#  Gerador de Excel Financeiro
# ──────────────────────────────────────────────────────────────────

def _gerar_excel_financeiro(
    empresa: models.Empresa,
    lanc: models.LancamentoMensal,
    orc: Optional[models.OrcamentoMensal],
    lancamentos_hist: list,
    ano: int,
    mes: int,
) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

    wb = Workbook()
    wb.remove(wb.active)  # remove aba padrão

    # ── helpers rápidos ─────────────────────────────────────────
    def h(ws, row, cols, cor="1E293B"):
        _row_header(ws, cols[0], cols, row, cor)

    def val(obj, campo, default=0.0):
        return getattr(obj, campo, default) or default

    # ── ABA 1: DRE ───────────────────────────────────────────────
    ws_dre = wb.create_sheet("DRE")
    ws_dre.column_dimensions["A"].width = 35
    ws_dre.column_dimensions["B"].width = 18

    titulo = f"DEMONSTRAÇÃO DE RESULTADO — {MESES[mes-1]}/{ano}"
    ws_dre.merge_cells("A1:B1")
    c = ws_dre["A1"]
    c.value = titulo
    c.font  = Font(name="Calibri", bold=True, size=13, color="FFFFFF")
    c.fill  = PatternFill("solid", start_color="4F6AFF", end_color="4F6AFF")
    c.alignment = Alignment(horizontal="center")
    ws_dre.row_dimensions[1].height = 28

    info_rows = [
        ("Empresa:",  empresa.nome),
        ("CNPJ:",     empresa.cnpj or "—"),
        ("Período:",  f"{MESES[mes-1]}/{ano}"),
        ("Gerado em:", datetime.now().strftime("%d/%m/%Y %H:%M")),
    ]
    for i, (lab, val_) in enumerate(info_rows, start=2):
        ws_dre.cell(row=i, column=1, value=lab).font = Font(bold=True, size=9, color="64748B")
        ws_dre.cell(row=i, column=2, value=val_).font = Font(size=9)

    h(ws_dre, 7, ["Linha", "Valor"], cor="2D2B4B")

    rl = val(lanc, "receita_bruta") - val(lanc, "deducoes_receita")
    lb = rl - val(lanc, "custo_servicos")
    total_desp = sum(val(lanc, c) for c in ["despesas_adm","despesas_comerciais","despesas_financeiras","outras_despesas"])
    ebit = lb - total_desp
    ll   = ebit - val(lanc, "ir_csll")

    linhas_dre = [
        ("Receita Bruta",             val(lanc, "receita_bruta"),        False, None),
        ("(–) Deduções da Receita",   -val(lanc, "deducoes_receita"),    False, None),
        ("= Receita Líquida",         rl,                                True,  "E2F0E8"),
        ("(–) Custo dos Serviços",    -val(lanc, "custo_servicos"),      False, None),
        ("= Lucro Bruto",             lb,                                True,  "E2F0E8"),
        ("(–) Despesas Adm.",         -val(lanc, "despesas_adm"),        False, None),
        ("(–) Despesas Comerciais",   -val(lanc, "despesas_comerciais"), False, None),
        ("(–) Despesas Financeiras",  -val(lanc, "despesas_financeiras"),False, None),
        ("(–) Outras Despesas",       -val(lanc, "outras_despesas"),     False, None),
        ("= EBIT",                    ebit,                              True,  "E2F0E8"),
        ("(–) IR + CSLL",             -val(lanc, "ir_csll"),             False, None),
        ("= Lucro Líquido",           ll,                                True,  "D6EAF8"),
    ]

    for i, (label, valor_, bold_, cor_) in enumerate(linhas_dre, start=8):
        c1 = ws_dre.cell(row=i, column=1, value=label)
        c2 = ws_dre.cell(row=i, column=2, value=valor_)
        c2.number_format = 'R$ #,##0.00'
        if bold_:
            c1.font = Font(bold=True, size=10)
            c2.font = Font(bold=True, size=10)
        if cor_:
            fill = PatternFill("solid", start_color=cor_, end_color=cor_)
            c1.fill = fill; c2.fill = fill

    # Margens
    r = len(linhas_dre) + 9
    ws_dre.cell(row=r, column=1, value="Margem Bruta (%)")
    ws_dre.cell(row=r, column=2, value=(lb / val(lanc, "receita_bruta") if val(lanc, "receita_bruta") else 0)).number_format = "0.00%"
    ws_dre.cell(row=r+1, column=1, value="Margem Líquida (%)")
    ws_dre.cell(row=r+1, column=2, value=(ll / val(lanc, "receita_bruta") if val(lanc, "receita_bruta") else 0)).number_format = "0.00%"

    # ── ABA 2: Fluxo de Caixa ────────────────────────────────────
    ws_fc = wb.create_sheet("Fluxo de Caixa")
    ws_fc.column_dimensions["A"].width = 35
    ws_fc.column_dimensions["B"].width = 18

    ws_fc.merge_cells("A1:B1")
    c = ws_fc["A1"]
    c.value = f"FLUXO DE CAIXA — {MESES[mes-1]}/{ano}"
    c.font  = Font(name="Calibri", bold=True, size=13, color="FFFFFF")
    c.fill  = PatternFill("solid", start_color="065F46", end_color="065F46")
    c.alignment = Alignment(horizontal="center")

    h(ws_fc, 3, ["Linha", "Valor"], cor="065F46")
    saldo_ini  = val(lanc, "saldo_inicial_caixa")
    entradas   = val(lanc, "entradas_caixa")
    saidas     = val(lanc, "saidas_caixa")
    saldo_fin  = saldo_ini + entradas - saidas

    fc_linhas = [
        ("Saldo Inicial", saldo_ini, False),
        ("(+) Entradas",  entradas,  False),
        ("(–) Saídas",    -saidas,   False),
        ("= Saldo Final", saldo_fin, True),
    ]
    for i, (lbl, v, bold_) in enumerate(fc_linhas, start=4):
        c1 = ws_fc.cell(row=i, column=1, value=lbl)
        c2 = ws_fc.cell(row=i, column=2, value=v)
        c2.number_format = 'R$ #,##0.00'
        if bold_:
            c1.font = Font(bold=True, size=10)
            c2.font = Font(bold=True, size=10)
            fill = PatternFill("solid", start_color="D5F5E3", end_color="D5F5E3")
            c1.fill = fill; c2.fill = fill

    # Histórico
    if lancamentos_hist:
        ws_fc.cell(row=9, column=1, value="Histórico (12 meses)").font = Font(bold=True, size=10, color="065F46")
        h(ws_fc, 10, ["Mês/Ano", "Entradas", "Saídas", "Saldo"], cor="065F46")
        ws_fc.column_dimensions["C"].width = 18
        ws_fc.column_dimensions["D"].width = 18
        for i, l in enumerate(lancamentos_hist[-12:], start=11):
            ws_fc.cell(row=i, column=1, value=f"{MESES[l.mes-1]}/{l.ano}")
            for col, campo in [(2,"entradas_caixa"),(3,"saidas_caixa")]:
                c = ws_fc.cell(row=i, column=col, value=val(l, campo))
                c.number_format = 'R$ #,##0.00'
            saldo = val(l,"saldo_inicial_caixa") + val(l,"entradas_caixa") - val(l,"saidas_caixa")
            c = ws_fc.cell(row=i, column=4, value=saldo)
            c.number_format = 'R$ #,##0.00'

    # ── ABA 3: Balanço Patrimonial ───────────────────────────────
    ws_bp = wb.create_sheet("Balanço Patrimonial")
    ws_bp.column_dimensions["A"].width = 35
    ws_bp.column_dimensions["B"].width = 18

    ws_bp.merge_cells("A1:B1")
    c = ws_bp["A1"]
    c.value = f"BALANÇO PATRIMONIAL — {MESES[mes-1]}/{ano}"
    c.font  = Font(name="Calibri", bold=True, size=13, color="FFFFFF")
    c.fill  = PatternFill("solid", start_color="7C3AED", end_color="7C3AED")
    c.alignment = Alignment(horizontal="center")

    ativo_circ = sum(val(lanc,c) for c in ["caixa_equivalentes","contas_receber","estoques","outros_ativo_circ"])
    ativo_total = ativo_circ + val(lanc,"ativo_nao_circulante")
    pass_circ  = sum(val(lanc,c) for c in ["fornecedores","emprestimos_cp","tributos_pagar","outros_passivo_circ"])
    pass_total = pass_circ + val(lanc,"passivo_nao_circulante")
    pl         = val(lanc,"capital_social") + val(lanc,"reservas") + val(lanc,"lucros_acumulados")

    bp_linhas = [
        # (label, valor, bold, cor)
        ("ATIVO",                        None,          True,  "1E293B"),
        ("Ativo Circulante",             ativo_circ,    True,  "334155"),
        ("  Caixa e Equivalentes",       val(lanc,"caixa_equivalentes"),   False, None),
        ("  Contas a Receber",           val(lanc,"contas_receber"),        False, None),
        ("  Estoques",                   val(lanc,"estoques"),              False, None),
        ("  Outros Ativos Circulantes",  val(lanc,"outros_ativo_circ"),     False, None),
        ("Ativo Não Circulante",         val(lanc,"ativo_nao_circulante"),  True,  "334155"),
        ("ATIVO TOTAL",                  ativo_total,   True,  "1E293B"),
        ("",                             None,          False, None),
        ("PASSIVO + PATRIMÔNIO LÍQUIDO", None,          True,  "1E293B"),
        ("Passivo Circulante",           pass_circ,     True,  "334155"),
        ("  Fornecedores",               val(lanc,"fornecedores"),          False, None),
        ("  Empréstimos C/P",            val(lanc,"emprestimos_cp"),        False, None),
        ("  Tributos a Pagar",           val(lanc,"tributos_pagar"),        False, None),
        ("  Outros Passivos Circ.",      val(lanc,"outros_passivo_circ"),   False, None),
        ("Passivo Não Circulante",       val(lanc,"passivo_nao_circulante"),True,  "334155"),
        ("PASSIVO TOTAL",                pass_total,    True,  "1E293B"),
        ("Patrimônio Líquido",           pl,            True,  "334155"),
        ("  Capital Social",             val(lanc,"capital_social"),        False, None),
        ("  Reservas",                   val(lanc,"reservas"),              False, None),
        ("  Lucros Acumulados",          val(lanc,"lucros_acumulados"),     False, None),
        ("PASSIVO + PL",                 pass_total + pl, True, "1E293B"),
    ]
    for i, (lbl, v, bold_, cor_) in enumerate(bp_linhas, start=3):
        c1 = ws_bp.cell(row=i, column=1, value=lbl)
        if v is not None:
            c2 = ws_bp.cell(row=i, column=2, value=v)
            c2.number_format = 'R$ #,##0.00'
            if bold_: c2.font = Font(bold=True, size=10)
        if bold_: c1.font = Font(bold=True, size=10)
        if cor_:
            color = "FFFFFF" if cor_ in ("1E293B","334155") else "000000"
            c1.font = Font(bold=True, size=10, color=color)
            fill = PatternFill("solid", start_color=cor_, end_color=cor_)
            c1.fill = fill
            if v is not None:
                ws_bp.cell(row=i, column=2).fill = fill

    # ── ABA 4: Orçamento vs. Realizado ───────────────────────────
    if orc:
        ws_orc = wb.create_sheet("Orçamento vs. Realizado")
        ws_orc.column_dimensions["A"].width = 35
        for col in ["B","C","D"]:
            ws_orc.column_dimensions[col].width = 18

        ws_orc.merge_cells("A1:D1")
        c = ws_orc["A1"]
        c.value = f"ORÇAMENTO vs. REALIZADO — {MESES[mes-1]}/{ano}"
        c.font  = Font(name="Calibri", bold=True, size=13, color="FFFFFF")
        c.fill  = PatternFill("solid", start_color="6D28D9", end_color="6D28D9")
        c.alignment = Alignment(horizontal="center")

        h(ws_orc, 3, ["Linha", "Orçado", "Realizado", "Desvio %"], cor="6D28D9")

        def dev(orc_v, real_v):
            if orc_v == 0: return None
            return (real_v - orc_v) / abs(orc_v)

        def orc_val(campo): return val(orc, campo)
        def lan_val(campo): return val(lanc, campo)

        orc_rl  = orc_val("receita_bruta") - orc_val("deducoes_receita")
        lan_rl  = lan_val("receita_bruta") - lan_val("deducoes_receita")
        orc_lb  = orc_rl - orc_val("custo_servicos")
        lan_lb  = lan_rl - lan_val("custo_servicos")
        orc_desp= sum(orc_val(c) for c in ["despesas_adm","despesas_comerciais","despesas_financeiras","outras_despesas"])
        lan_desp= sum(lan_val(c) for c in ["despesas_adm","despesas_comerciais","despesas_financeiras","outras_despesas"])
        orc_ll  = orc_lb - orc_desp - orc_val("ir_csll")
        lan_ll  = lan_lb - lan_desp - lan_val("ir_csll")

        orc_rows = [
            ("Receita Bruta",            orc_val("receita_bruta"),        lan_val("receita_bruta"),        False),
            ("(–) Deduções",             orc_val("deducoes_receita"),     lan_val("deducoes_receita"),     False),
            ("= Receita Líquida",        orc_rl,                          lan_rl,                          True),
            ("(–) Custo dos Serviços",   orc_val("custo_servicos"),       lan_val("custo_servicos"),       False),
            ("= Lucro Bruto",            orc_lb,                          lan_lb,                          True),
            ("(–) Despesas Adm.",        orc_val("despesas_adm"),         lan_val("despesas_adm"),         False),
            ("(–) Desp. Comerciais",     orc_val("despesas_comerciais"),  lan_val("despesas_comerciais"),  False),
            ("(–) Desp. Financeiras",    orc_val("despesas_financeiras"), lan_val("despesas_financeiras"), False),
            ("(–) Outras Despesas",      orc_val("outras_despesas"),      lan_val("outras_despesas"),      False),
            ("(–) IR + CSLL",            orc_val("ir_csll"),              lan_val("ir_csll"),              False),
            ("= Lucro Líquido",          orc_ll,                          lan_ll,                          True),
            ("",                         None,                            None,                            False),
            ("Entradas de Caixa",        orc_val("entradas_caixa"),       lan_val("entradas_caixa"),       False),
            ("Saídas de Caixa",          orc_val("saidas_caixa"),         lan_val("saidas_caixa"),         False),
            ("Folha de Pagamento",       orc_val("folha_pagamento"),      lan_val("folha_pagamento"),      False),
        ]

        for i, (lbl, ov, rv, bold_) in enumerate(orc_rows, start=4):
            c1 = ws_orc.cell(row=i, column=1, value=lbl)
            if bold_:
                c1.font = Font(bold=True, size=10)
                fill = PatternFill("solid", start_color="E8E0FF", end_color="E8E0FF")
                c1.fill = fill
            if ov is not None:
                c2 = ws_orc.cell(row=i, column=2, value=ov)
                c2.number_format = 'R$ #,##0.00'
                if bold_: c2.font = Font(bold=True); c2.fill = fill
                c3 = ws_orc.cell(row=i, column=3, value=rv)
                c3.number_format = 'R$ #,##0.00'
                if bold_: c3.font = Font(bold=True); c3.fill = fill
                d = dev(ov, rv)
                c4 = ws_orc.cell(row=i, column=4, value=d)
                if d is not None:
                    c4.number_format = '0.00%'
                    if d < -0.20: c4.font = Font(color="C62828", bold=True)
                    elif d < -0.05: c4.font = Font(color="E65100")
                    else: c4.font = Font(color="1B5E20")

    # ── Salva em memória ─────────────────────────────────────────
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ──────────────────────────────────────────────────────────────────
#  Endpoints
# ──────────────────────────────────────────────────────────────────

@router.get("/excel/{empresa_id}")
def exportar_excel(
    empresa_id: int,
    ano: int,
    mes: int,
    user: models.Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    """
    Gera um arquivo Excel com DRE, Fluxo de Caixa, Balanço Patrimonial
    e (se houver) Orçamento vs. Realizado para o período informado.
    """
    empresa = resolve_empresa_or_403(db, empresa_id, user)

    lanc = db.query(models.LancamentoMensal).filter(
        models.LancamentoMensal.empresa_id == empresa_id,
        models.LancamentoMensal.ano == ano,
        models.LancamentoMensal.mes == mes,
    ).first()

    if not lanc:
        raise HTTPException(status_code=404, detail="Nenhum dado financeiro para este período.")

    orc = db.query(models.OrcamentoMensal).filter(
        models.OrcamentoMensal.empresa_id == empresa_id,
        models.OrcamentoMensal.ano == ano,
        models.OrcamentoMensal.mes == mes,
    ).first()

    hist = db.query(models.LancamentoMensal).filter(
        models.LancamentoMensal.empresa_id == empresa_id,
    ).order_by(
        models.LancamentoMensal.ano.asc(),
        models.LancamentoMensal.mes.asc(),
    ).all()

    conteudo = _gerar_excel_financeiro(empresa, lanc, orc, hist, ano, mes)

    nome_empresa = empresa.nome.replace(" ", "_").replace("/", "-")[:30]
    MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    nome_arquivo = f"Controllo_{nome_empresa}_{MESES[mes-1]}{ano}.xlsx"

    return StreamingResponse(
        io.BytesIO(conteudo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )
