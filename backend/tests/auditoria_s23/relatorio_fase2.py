"""S23 Fase 2 — Relatorio executivo do resultado do pipeline."""

import csv
from collections import defaultdict
from pathlib import Path

CSV = Path(__file__).resolve().parent / "resultado_pipeline.csv"


def main() -> None:
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    total = len(rows)
    com_erro = [r for r in rows if r["erro"]]
    desconhecido = [r for r in rows if r["banco_detectado"] in ("desconhecido", "")]
    timeouts = [r for r in rows if r["erro"] == "timeout"]
    com_ocr = [r for r in rows if r["usou_ocr"] == "sim"]

    print(f"Total processados: {total}")
    print(f"Com erro: {len(com_erro)} (timeouts: {len(timeouts)})")
    print(f"Banco=desconhecido: {len(desconhecido)}")
    print(f"OCR usado: {len(com_ocr)}")
    tempo_total = sum(float(r["tempo_segundos"]) for r in rows)
    print(f"Tempo total auditoria: {tempo_total:.1f}s")
    print()

    # Tabela por banco_detectado
    grupos: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        b = r["banco_detectado"] or "desconhecido"
        grupos[b].append(r)

    print(
        f"{'banco':<28} {'tot':>4} {'VRD':>4} {'AML':>4} {'VML':>4} "
        f"{'IND':>4} {'ERR':>4} {'OCR':>4}"
    )
    print("-" * 70)
    for banco in sorted(grupos.keys(), key=lambda b: -len(grupos[b])):
        rs = grupos[banco]
        tot = len(rs)
        vrd = sum(1 for r in rs if r["nivel_validador"] == "VERDE")
        aml = sum(1 for r in rs if r["nivel_validador"] == "AMARELO")
        vml = sum(1 for r in rs if r["nivel_validador"] == "VERMELHO")
        ind = sum(1 for r in rs if r["nivel_validador"] in ("", "INDETERMINADO"))
        err = sum(1 for r in rs if r["erro"])
        ocr = sum(1 for r in rs if r["usou_ocr"] == "sim")
        print(
            f"{banco:<28} {tot:>4} {vrd:>4} {aml:>4} {vml:>4} "
            f"{ind:>4} {err:>4} {ocr:>4}"
        )

    print()
    print(f"PDFs com banco=desconhecido ({len(desconhecido)}):")
    print("-" * 70)
    for r in desconhecido:
        print(f"  {r['arquivo']}")

    print()
    print(f"PDFs com erro ({len(com_erro)}):")
    print("-" * 70)
    for r in com_erro:
        print(f"  {r['arquivo'][:50]:<50}  | {r['erro'][:80]}")

    print()
    print(f"PDFs que usaram OCR ({len(com_ocr)}):")
    print("-" * 70)
    for r in com_ocr:
        print(f"  {r['arquivo'][:50]:<50}  | banco={r['banco_detectado']} | nivel={r['nivel_validador']}")

    # Top 10 mais lentos
    print()
    rs_sorted = sorted(rows, key=lambda r: -float(r["tempo_segundos"]))[:10]
    print("Top 10 mais lentos:")
    print("-" * 70)
    for r in rs_sorted:
        print(f"  {float(r['tempo_segundos']):>6.1f}s  {r['arquivo'][:55]}")


if __name__ == "__main__":
    main()
