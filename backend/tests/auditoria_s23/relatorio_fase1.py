"""S23 Fase 1 — Relatorio executivo do inventario.

Gera resumo agrupado por banco (heuristica do brief), top 5 maiores e
duplicatas via MD5. NAO modifica producao.
"""

import csv
from collections import defaultdict
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent / "inventario_pdfs.csv"


def banco_por_nome(nome: str) -> str:
    n = nome.lower()
    # Casos prioritarios — ordem importa.
    # "Internet Banking" no nome Santander NAO e Inter.
    if "santander" in n:
        return "santander"
    if "bradesco" in n:
        return "bradesco"
    if "itau" in n or "itaú" in n or "ita�" in n:
        return "itau"
    if "nubank" in n:
        return "nubank"
    if "inter" in n:
        # ja excluimos santander acima
        return "inter"
    if "btg" in n:
        return "btg"
    if "bb" in n or "banco do brasil" in n:
        return "bb"
    if "caixa" in n:
        return "caixa"
    if "safra" in n:
        return "safra"
    if "bs2" in n or "b2s" in n:
        return "bs2"
    if "c6" in n:
        return "c6"
    if "stone" in n:
        return "stone"
    if "sicredi" in n:
        return "sicredi"
    if "sumup" in n:
        return "sumup"
    if "pagbank" in n or "pagseguro" in n:
        return "pagbank"
    if "mercado pago" in n or "mercadopago" in n or " mp " in f" {n} ":
        return "mp"
    if "xp" in n:
        return "xp"
    if "cora" in n:
        return "cora"
    if "extrato" in n:
        return "desconhecido_por_nome"
    return "desconhecido_por_nome"


def main() -> None:
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    print(f"Total de PDFs: {len(rows)}")
    print()

    # Agrupar por banco
    por_banco: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        por_banco[banco_por_nome(r["arquivo"])].append(r)

    print("Tabela: banco_por_nome | quantidade")
    print("-" * 50)
    for banco in sorted(por_banco.keys(), key=lambda b: -len(por_banco[b])):
        print(f"  {banco:30s} | {len(por_banco[banco])}")
    print()

    # Top 5 maiores
    top5 = sorted(rows, key=lambda r: -int(r["tamanho_bytes"]))[:5]
    print("Top 5 PDFs maiores em bytes:")
    print("-" * 50)
    for r in top5:
        mb = int(r["tamanho_bytes"]) / 1024 / 1024
        print(f"  {mb:6.2f} MB  {r['arquivo']}")
    print()

    # Duplicatas via MD5
    md5_para_arqs: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        md5_para_arqs[r["md5"]].append(r["arquivo"])
    duplicatas = {h: arqs for h, arqs in md5_para_arqs.items() if len(arqs) > 1}

    print(f"Duplicatas via MD5: {len(duplicatas)} grupos")
    print("-" * 50)
    if not duplicatas:
        print("  (nenhuma)")
    else:
        for h, arqs in duplicatas.items():
            print(f"  {h[:8]}...  ->  {arqs}")
    print()

    print(f"Commit atual: 02a753c860011f5d7a5521462a00b3b07f25f940")


if __name__ == "__main__":
    main()
