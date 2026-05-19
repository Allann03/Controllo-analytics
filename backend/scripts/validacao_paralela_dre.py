"""
Validacao Paralela DRE -- BLOCO 3B.2 Fase B (recalibrada).

Compara DRE legada vs DRE nova para 3 empresas x 12 meses = 36 comparacoes.
Aplica 5 criterios de categorizacao recalibrados e 6 invariantes matematicas
(INV-P1' a INV-P6') derivadas algebricamente apos descoberta do ALTO-1b.

ALTO-1:  DFin incluida em despesas operacionais (EBIT = LAIR)
ALTO-1b: D&A nunca subtraida na DRE (LL superestimado por D&A)
"""

import os
import sys
from decimal import Decimal
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = ""
os.environ["CONTROLLO_ENV"] = "test"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from data.database.config import Base
from data.database import models
from services.contabil.dre import calcular_dre
from services.contabil.core import money

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "data", "data", "controllo_test.db")
engine = create_engine(f"sqlite:///{os.path.abspath(DB_PATH)}",
                       connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)

EMPRESAS = {
    1: ("Empresa Alpha S/A", "Servicos PME — RB crescente, D&A=1500, DFin=2000"),
    3: ("Empresa Comercio Teste", "Comercio — CMV~60%, sazonalidade, D&A=500, DFin=5000"),
    4: ("Empresa Industria Teste", "Industria — crescimento linear, D&A=20000, DFin=12000"),
}

DRE_CAMPOS = [
    "receita_bruta", "deducoes_receita", "custo_servicos", "despesas_adm",
    "despesas_comerciais", "outras_despesas", "depreciacao_amortizacao",
    "despesas_financeiras", "ir_csll",
]

LINHAS_DRE = [
    "receita_bruta", "deducoes_receita", "receita_liquida", "custo_servicos",
    "lucro_bruto", "despesas_adm", "despesas_comerciais", "outras_despesas",
    "ebit", "ebitda", "despesas_financeiras", "lair", "ir_csll", "lucro_liquido",
]

LINHAS_ATE_LB = {"receita_bruta", "deducoes_receita", "receita_liquida",
                  "custo_servicos", "lucro_bruto", "despesas_adm",
                  "despesas_comerciais", "outras_despesas"}
TOL = 0.02


def _safe(v):
    return v if v is not None else 0


def _to_dec(v):
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def get_legado(lanc):
    rb = _to_dec(lanc.receita_bruta)
    dr = _to_dec(lanc.deducoes_receita)
    cs = _to_dec(lanc.custo_servicos)
    adm = _to_dec(lanc.despesas_adm)
    com = _to_dec(lanc.despesas_comerciais)
    fin = _to_dec(lanc.despesas_financeiras)
    out = _to_dec(lanc.outras_despesas)
    ir = _to_dec(lanc.ir_csll)
    da = _to_dec(getattr(lanc, "depreciacao_amortizacao", 0))
    rl = rb - dr
    lb = rl - cs
    ebit = lb - (adm + com + fin + out)  # BUG: inclui fin, omite da
    ebitda = ebit + da
    ll = ebit - ir
    return {
        "receita_bruta": float(rb), "deducoes_receita": float(dr),
        "receita_liquida": float(rl), "custo_servicos": float(cs),
        "lucro_bruto": float(lb), "despesas_adm": float(adm),
        "despesas_comerciais": float(com), "outras_despesas": float(out),
        "ebit": float(ebit), "ebitda": float(ebitda),
        "despesas_financeiras": float(fin),
        "lair": float(ebit),  # legado: ebit IS lair
        "ir_csll": float(ir), "lucro_liquido": float(ll),
        "depreciacao_amortizacao": float(da),
    }


def get_novo(lanc):
    dados = {col: _safe(getattr(lanc, col, 0)) for col in DRE_CAMPOS}
    res = calcular_dre(dados, f"{lanc.ano}-{lanc.mes:02d}")
    d = res.valor
    return {
        "receita_bruta": float(d.receita_bruta),
        "deducoes_receita": float(d.linhas[1].valor),
        "receita_liquida": float(d.receita_liquida),
        "custo_servicos": float(d.linhas[3].valor),
        "lucro_bruto": float(d.lucro_bruto),
        "despesas_adm": float(d.linhas[5].valor),
        "despesas_comerciais": float(d.linhas[6].valor),
        "outras_despesas": float(d.linhas[7].valor),
        "ebit": float(d.ebit), "ebitda": float(d.ebitda),
        "despesas_financeiras": float(d.despesas_financeiras),
        "lair": float(d.lair),
        "ir_csll": float(d.ir_csll_consolidado if d.ir_csll_consolidado else d.irpj + d.csll),
        "lucro_liquido": float(d.resultado_liquido),
        "depreciacao_amortizacao": float(d.depreciacao_amortizacao),
    }


def categorizar(linha, vl, vn, dfin, da):
    diff = vn - vl
    adiff = abs(diff)
    if adiff <= TOL:
        return "IGUAL"
    if linha == "ebit":
        esperado = dfin - da
        if abs(diff - esperado) <= TOL:
            return "CORRECAO COMBINADA"
    if linha == "ebitda":
        # EBITDA_novo - EBITDA_leg = DFin - D&A
        # (D&A does NOT cancel because legado adds D&A to an EBIT that never subtracted it)
        esperado_ebitda = dfin - da
        if abs(diff - esperado_ebitda) <= TOL:
            return "CORRECAO COMBINADA"
    if linha in ("lair", "lucro_liquido"):
        if abs(diff - (-da)) <= TOL:
            return "CORRECAO ALTO-1b (D&A)"
    return "DIVERGENCIA INVESTIGAR"


def main():
    db = Session()
    out = []
    incidentes = []
    inv_total = 0
    inv_ok = 0
    cat_counts = {}
    empresa_tables = {}

    for emp_id, (nome, perfil) in EMPRESAS.items():
        lancs = (
            db.query(models.LancamentoMensal)
            .filter(models.LancamentoMensal.empresa_id == emp_id)
            .order_by(models.LancamentoMensal.ano, models.LancamentoMensal.mes)
            .all()
        )
        diff_rows = []
        inv_rows = []
        equal_count = 0
        total_count = 0

        for lanc in lancs:
            leg = get_legado(lanc)
            nov = get_novo(lanc)
            dfin = leg["despesas_financeiras"]
            da = leg["depreciacao_amortizacao"]
            mk = f"{lanc.ano}-{lanc.mes:02d}"

            for linha in LINHAS_DRE:
                vl, vn = leg[linha], nov[linha]
                cat = categorizar(linha, vl, vn, dfin, da)
                total_count += 1
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
                if cat == "IGUAL":
                    equal_count += 1
                else:
                    diff_rows.append((mk, linha, vl, vn, round(vn - vl, 2), cat))
                if cat == "DIVERGENCIA INVESTIGAR":
                    incidentes.append(f"{nome} | {mk} | {linha} | leg={vl} | novo={vn} | diff={round(vn-vl,2)}")

            # 6 invariantes
            checks = {}

            # INV-P1': RB ate LB IGUAL
            p1 = all(abs(nov[l] - leg[l]) <= TOL for l in
                     ["receita_bruta", "deducoes_receita", "receita_liquida", "custo_servicos", "lucro_bruto"])
            checks["P1'"] = p1

            # INV-P2': EBIT_novo - EBIT_legado == DFin - D&A
            p2 = abs((nov["ebit"] - leg["ebit"]) - (dfin - da)) <= TOL
            checks["P2'"] = p2

            # INV-P3': EBITDA_novo - EBITDA_legado == DFin - D&A
            # (D&A does NOT cancel: legado adds D&A to EBIT that never subtracted it)
            p3 = abs((nov["ebitda"] - leg["ebitda"]) - (dfin - da)) <= TOL
            checks["P3'"] = p3

            # INV-P4': LAIR_novo - LAIR_legado == -D&A
            p4 = abs((nov["lair"] - leg["lair"]) - (-da)) <= TOL
            checks["P4'"] = p4

            # INV-P5': LL_novo - LL_legado == -D&A
            p5 = abs((nov["lucro_liquido"] - leg["lucro_liquido"]) - (-da)) <= TOL
            checks["P5'"] = p5

            # INV-P6': se D&A=0 entao LAIR e LL iguais
            if da == 0:
                p6 = abs(nov["lair"] - leg["lair"]) <= TOL and abs(nov["lucro_liquido"] - leg["lucro_liquido"]) <= TOL
            else:
                p6 = True  # nao se aplica
            checks["P6'"] = p6

            for k, v in checks.items():
                inv_total += 1
                if v:
                    inv_ok += 1
                else:
                    incidentes.append(f"{nome} | {mk} | {k} FALHOU")

            inv_rows.append((mk, checks))

        empresa_tables[emp_id] = {
            "diff_rows": diff_rows, "inv_rows": inv_rows,
            "equal_count": equal_count, "total_count": total_count,
        }

    db.close()

    # ── Gerar documento ──────────────────────────────────────────────
    L = []
    L.append("# Validacao Paralela DRE -- BLOCO 3B.2 Fase B (recalibrada)")
    L.append(f"\nGerado em: {datetime.now(timezone.utc).isoformat()}")
    L.append("")

    L.append("## Incidente ALTO-1b")
    L.append("")
    L.append("Durante a primeira execucao da Fase B, descobriu-se que a engine legada")
    L.append("nunca subtraia `depreciacao_amortizacao` da DRE (CRITICO-NEW-2).")
    L.append("Criterios recalibrados pelo mandato para refletir dois bugs simultaneos:")
    L.append("ALTO-1 (DFin no EBIT) e ALTO-1b (D&A omitida).")
    L.append("Ref: `docs/debitos-descobertos.md` entry CRITICO-NEW-2.")
    L.append("")

    L.append("## 1. Metodologia")
    L.append("")
    L.append("### Criterios de categorizacao (recalibrados)")
    L.append("| Categoria | Regra |")
    L.append("|---|---|")
    L.append("| IGUAL | Diferenca <= 0.02 |")
    L.append("| CORRECAO COMBINADA (EBITDA) | EBITDA: diff == +DFin - D&A (D&A nao cancela no legado) |")
    L.append("| CORRECAO ALTO-1b (D&A) | LAIR/LL: diff == -depreciacao_amortizacao |")
    L.append("| CORRECAO COMBINADA | EBIT: diff == +DFin - D&A |")
    L.append("| DIVERGENCIA INVESTIGAR | Qualquer outra coisa |")
    L.append("")
    L.append("### Invariantes matematicas (6 novas)")
    L.append("| ID | Formula |")
    L.append("|---|---|")
    L.append("| INV-P1' | RB ate LB: IGUAL em 5 linhas |")
    L.append("| INV-P2' | EBIT_novo - EBIT_leg == DFin - D&A |")
    L.append("| INV-P3' | EBITDA_novo - EBITDA_leg == DFin - D&A |")
    L.append("| INV-P4' | LAIR_novo - LAIR_leg == -D&A |")
    L.append("| INV-P5' | LL_novo - LL_leg == -D&A |")
    L.append("| INV-P6' | Se D&A=0: LAIR e LL iguais |")
    L.append("")

    L.append("## 2. Datasets sinteticos")
    L.append("")
    for emp_id, (nome, perfil) in EMPRESAS.items():
        L.append(f"### {nome} (id={emp_id})")
        L.append(f"- **Perfil:** {perfil}")
        L.append("")

    L.append("## 3. Resultados por empresa")
    L.append("")
    for emp_id, (nome, _) in EMPRESAS.items():
        t = empresa_tables[emp_id]
        L.append(f"### {nome}")
        if t["diff_rows"]:
            L.append("")
            L.append("| Mes | Linha | Legado | Novo | Diferenca | Categoria |")
            L.append("|---|---|---|---|---|---|")
            for mk, linha, vl, vn, diff, cat in t["diff_rows"]:
                L.append(f"| {mk} | {linha} | {vl:.2f} | {vn:.2f} | {diff:+.2f} | {cat} |")
        L.append(f"\nLinhas identicas: {t['equal_count']}/{t['total_count']}")
        L.append("")

    L.append("## 4. Verificacao das 6 invariantes")
    L.append("")
    L.append("| Empresa | Mes | P1' | P2' | P3' | P4' | P5' | P6' |")
    L.append("|---|---|---|---|---|---|---|---|")
    for emp_id, (nome, _) in EMPRESAS.items():
        for mk, checks in empresa_tables[emp_id]["inv_rows"]:
            marks = " | ".join("OK" if checks[f"P{i}'"] else "FALHA" for i in range(1, 7))
            L.append(f"| {nome[:15]} | {mk} | {marks} |")
    L.append(f"\n**Total: {inv_ok}/{inv_total} invariantes atendidas.**")
    L.append("")

    L.append("## 5. Incidentes encontrados")
    L.append("")
    if incidentes:
        for inc in incidentes:
            L.append(f"- {inc}")
    else:
        L.append("Nenhum incidente encontrado.")
    L.append("")

    L.append("## 6. Veredito final")
    L.append("")

    # Criterios
    c1 = all(
        categorizar(l, empresa_tables[eid]["diff_rows"], 0, 0, 0) != "DIVERGENCIA INVESTIGAR"
        for eid in EMPRESAS for l in LINHAS_ATE_LB
    ) if False else cat_counts.get("DIVERGENCIA INVESTIGAR", 0) == 0  # simplified

    todas_ate_lb = all(
        cat != "DIVERGENCIA INVESTIGAR"
        for eid in EMPRESAS
        for mk, linha, vl, vn, diff, cat in empresa_tables[eid]["diff_rows"]
        if linha in LINHAS_ATE_LB
    )
    linhas_ate_lb_sem_diff = not any(
        linha in LINHAS_ATE_LB
        for eid in EMPRESAS
        for mk, linha, vl, vn, diff, cat in empresa_tables[eid]["diff_rows"]
    )

    todas_ebit_ok = all(
        cat in ("CORRECAO COMBINADA", "IGUAL")
        for eid in EMPRESAS
        for mk, linha, vl, vn, diff, cat in empresa_tables[eid]["diff_rows"]
        if linha == "ebit"
    )
    todas_ebitda_ok = all(
        cat in ("CORRECAO COMBINADA", "IGUAL")
        for eid in EMPRESAS
        for mk, linha, vl, vn, diff, cat in empresa_tables[eid]["diff_rows"]
        if linha == "ebitda"
    )
    todas_lair_ok = all(
        cat in ("CORRECAO ALTO-1b (D&A)", "IGUAL")
        for eid in EMPRESAS
        for mk, linha, vl, vn, diff, cat in empresa_tables[eid]["diff_rows"]
        if linha == "lair"
    )
    todas_ll_ok = all(
        cat in ("CORRECAO ALTO-1b (D&A)", "IGUAL")
        for eid in EMPRESAS
        for mk, linha, vl, vn, diff, cat in empresa_tables[eid]["diff_rows"]
        if linha == "lucro_liquido"
    )
    zero_investigar = len(incidentes) == 0
    todas_inv = inv_ok == inv_total

    r1 = "OK" if linhas_ate_lb_sem_diff else "FALHA"
    r2 = "OK" if todas_ebit_ok else "FALHA"
    r3 = "OK" if todas_ebitda_ok else "FALHA"
    r4 = "OK" if todas_lair_ok else "FALHA"
    r5 = "OK" if todas_ll_ok else "FALHA"
    r6 = "OK" if todas_inv else "FALHA"
    r7 = "OK" if zero_investigar else "FALHA"

    aprovado = all(x == "OK" for x in [r1, r2, r3, r4, r5, r6, r7])
    veredito = "APROVADO" if aprovado else "BLOQUEADO"

    L.append(f"- [{r1}] 100% das linhas Receita Bruta ate Lucro Bruto: IGUAL")
    L.append(f"- [{r2}] 100% das linhas EBIT: CORRECAO COMBINADA (ou IGUAL)")
    L.append(f"- [{r3}] 100% das linhas EBITDA: CORRECAO COMBINADA (ou IGUAL)")
    L.append(f"- [{r4}] 100% das linhas LAIR: CORRECAO ALTO-1b (ou IGUAL)")
    L.append(f"- [{r5}] 100% das linhas Resultado Liquido: CORRECAO ALTO-1b (ou IGUAL)")
    L.append(f"- [{r6}] {inv_ok}/{inv_total} invariantes atendidas")
    L.append(f"- [{r7}] Zero DIVERGENCIA INVESTIGAR")
    L.append(f"\n**VEREDITO: {veredito}**")

    L.append("")
    L.append("### Distribuicao de categorias")
    for cat, cnt in sorted(cat_counts.items()):
        L.append(f"- {cat}: {cnt}")

    doc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "docs", "validacao-dre-paralela.md")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))

    print(f"Documento: {doc_path}")
    print(f"Invariantes: {inv_ok}/{inv_total}")
    print(f"Incidentes: {len(incidentes)}")
    print(f"Categorias: {cat_counts}")
    print(f"VEREDITO: {veredito}")
    return veredito


if __name__ == "__main__":
    v = main()
    sys.exit(0 if v == "APROVADO" else 1)
