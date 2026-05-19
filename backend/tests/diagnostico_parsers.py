"""
Diagnostico baseline de todos os PDFs em tests/fixtures/pdfs_reais/.
Roda detectar_banco + extrair_extrato para cada PDF e reporta resultados.
"""
import sys
import os
import traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.extrator_pdf import detectar_banco, extrair_extrato

PDF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "pdfs_reais")


def run():
    pdfs = sorted([f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")])
    print(f"Total PDFs: {len(pdfs)}\n")
    print(f"{'Arquivo':<60} {'Banco':<25} {'Tx':>5} {'Ent':>12} {'Said':>12} {'SI':>12} {'SF':>12} {'Gap':>10} {'Conf':>6} {'OK':>4}")
    print("-" * 180)

    resultados = []
    for pdf_name in pdfs:
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        try:
            banco = detectar_banco(pdf_path)
            result = extrair_extrato(pdf_path, banco_id=banco)

            txs = result.get("transacoes", [])
            n_tx = len(txs)
            total_ent = result.get("total_entradas", 0)
            total_said = result.get("total_saidas", 0)
            si = result.get("saldo_inicial")
            sf = result.get("saldo_final")
            verif = result.get("verificacao_saldos", {})
            conf_ok = verif.get("conferencia_ok", None)
            divergencias = verif.get("divergencias", [])
            avisos = result.get("avisos", [])

            # Calcular gap
            gap = None
            if si is not None and sf is not None:
                from decimal import Decimal
                si_d = Decimal(str(si)) if not isinstance(si, Decimal) else si
                sf_d = Decimal(str(sf)) if not isinstance(sf, Decimal) else sf
                ent_d = Decimal(str(total_ent))
                said_d = Decimal(str(total_said))
                gap = sf_d - (si_d + ent_d - said_d)

            si_str = f"{float(si):>12,.2f}" if si is not None else "N/A".rjust(12)
            sf_str = f"{float(sf):>12,.2f}" if sf is not None else "N/A".rjust(12)
            gap_str = f"{float(gap):>10,.2f}" if gap is not None else "N/A".rjust(10)
            conf_str = "OK" if conf_ok else ("FAIL" if conf_ok is False else "N/A")

            nome_curto = pdf_name[:58] if len(pdf_name) > 58 else pdf_name
            print(f"{nome_curto:<60} {banco:<25} {n_tx:>5} {float(total_ent):>12,.2f} {float(total_said):>12,.2f} {si_str} {sf_str} {gap_str} {conf_str:>6} {'Y' if n_tx > 0 else 'N':>4}")

            resultados.append({
                "pdf": pdf_name,
                "banco": banco,
                "n_tx": n_tx,
                "total_ent": float(total_ent),
                "total_said": float(total_said),
                "si": float(si) if si is not None else None,
                "sf": float(sf) if sf is not None else None,
                "gap": float(gap) if gap is not None else None,
                "conf_ok": conf_ok,
                "avisos": avisos,
                "divergencias": divergencias,
            })
        except Exception as e:
            nome_curto = pdf_name[:58] if len(pdf_name) > 58 else pdf_name
            print(f"{nome_curto:<60} ERROR: {str(e)[:100]}")
            resultados.append({
                "pdf": pdf_name,
                "banco": "ERROR",
                "error": str(e),
            })

    # Summary
    print("\n" + "=" * 100)
    total = len(resultados)
    detected = sum(1 for r in resultados if r.get("banco") not in ("desconhecido", "ERROR"))
    with_tx = sum(1 for r in resultados if r.get("n_tx", 0) > 0)
    gap_zero = sum(1 for r in resultados if r.get("gap") is not None and abs(r["gap"]) < 0.02)
    conf_ok_count = sum(1 for r in resultados if r.get("conf_ok") is True)
    errors = sum(1 for r in resultados if r.get("banco") == "ERROR")
    unknown = sum(1 for r in resultados if r.get("banco") == "desconhecido")

    print(f"TOTAL: {total} PDFs")
    print(f"Detectados: {detected}/{total}")
    print(f"Com transacoes: {with_tx}/{total}")
    print(f"Gap ~= 0: {gap_zero}/{total}")
    print(f"Conferencia OK: {conf_ok_count}/{total}")
    print(f"Erros: {errors}")
    print(f"Desconhecido: {unknown}")

    # List problems
    print("\n--- PROBLEMAS ---")
    for r in resultados:
        if r.get("banco") == "ERROR":
            print(f"  ERROR: {r['pdf']}: {r.get('error', '')[:120]}")
        elif r.get("banco") == "desconhecido":
            print(f"  DESCONHECIDO: {r['pdf']}")
        elif r.get("n_tx", 0) == 0:
            print(f"  0 TX: {r['pdf']} (banco={r['banco']})")
        elif r.get("gap") is not None and abs(r["gap"]) >= 0.02:
            print(f"  GAP: {r['pdf']} (banco={r['banco']}, gap={r['gap']:.2f})")
        elif r.get("conf_ok") is False:
            print(f"  CONF FAIL: {r['pdf']} (banco={r['banco']})")


if __name__ == "__main__":
    run()
