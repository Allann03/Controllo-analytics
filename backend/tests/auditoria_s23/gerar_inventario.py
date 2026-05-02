"""S23 Fase 1 — Inventario de PDFs.

Lista PDFs em backend/tests/fixtures/pdfs_reais/, captura tamanho e MD5.
Gera inventario_pdfs.csv com colunas: arquivo,tamanho_bytes,md5

Read-only sobre o disco. Nao modifica nenhum PDF.
"""

import csv
import hashlib
import os
from pathlib import Path

PDFS_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "pdfs_reais"
OUT_CSV = Path(__file__).resolve().parent / "inventario_pdfs.csv"


def md5_de_arquivo(caminho: Path) -> str:
    h = hashlib.md5()
    with open(caminho, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if not PDFS_DIR.exists():
        raise SystemExit(f"Pasta nao encontrada: {PDFS_DIR}")

    pdfs = sorted(
        [p for p in PDFS_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"],
        key=lambda p: p.name.lower(),
    )

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["arquivo", "tamanho_bytes", "md5"])
        for p in pdfs:
            w.writerow([p.name, p.stat().st_size, md5_de_arquivo(p)])

    print(f"Total PDFs: {len(pdfs)}")
    print(f"CSV: {OUT_CSV}")


if __name__ == "__main__":
    main()
