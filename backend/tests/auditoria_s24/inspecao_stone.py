"""
S24 — Fase 1: Inspecao read-only dos 10 PDFs Stone.

Acoes:
  1. Para cada um dos 10 PDFs Stone identificados em
     auditoria_s23/resultado_pipeline.csv, calcula MD5.
  2. Extrai texto raw via pdfplumber e salva em
     backend/tests/fixtures/raw_stone/<stem>_raw.txt.
  3. Procura ocorrencias de labels candidatos a saldo inicial e final
     (linha + numero) e produz um JSON resumo em
     backend/tests/auditoria_s24/inspecao_resultado.json.

Nao altera nenhum arquivo de producao. Nao roda parser real.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[3]
S23_CSV = ROOT / "backend" / "tests" / "auditoria_s23" / "resultado_pipeline.csv"
PDFS_DIR = ROOT / "backend" / "tests" / "fixtures" / "pdfs_reais"
RAW_DIR = ROOT / "backend" / "tests" / "fixtures" / "raw_stone"
OUT_JSON = ROOT / "backend" / "tests" / "auditoria_s24" / "inspecao_resultado.json"

LABELS_SI = [
    "saldo anterior",
    "saldo inicial",
    "saldo do dia",
    "saldo em ",
    "saldo bloqueado anterior",
    "saldo da conta no dia",
    "saldo no inicio",
    "saldo do periodo anterior",
]
LABELS_SF = [
    "saldo final",
    "saldo atual",
    "saldo do dia",
    "saldo em ",
    "saldo da conta",
    "saldo no fim",
    "saldo no final",
    "saldo do periodo",
    "saldo apos",
    "saldo total",
]

VALOR_RE = re.compile(r"-?R?\$?\s?-?[\d\.]+,\d{2}")


@dataclass
class HitLine:
    page: int
    lineno: int
    text: str


@dataclass
class PdfReport:
    arquivo: str
    md5: str
    paginas: int = 0
    cabecalho: list[str] = field(default_factory=list)
    si_hits: list[HitLine] = field(default_factory=list)
    sf_hits: list[HitLine] = field(default_factory=list)
    saldo_dia_hits: list[HitLine] = field(default_factory=list)
    menciona_stone_pagamentos: bool = False
    menciona_stone_cripto: bool = False
    menciona_stone_conta: bool = False
    valor_apos_si: list[str] = field(default_factory=list)
    valor_apos_sf: list[str] = field(default_factory=list)
    erro: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stone_files_from_csv() -> list[str]:
    files: list[str] = []
    with S23_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["banco_detectado"] == "stone":
                files.append(row["arquivo"])
    return files


def normalize(s: str) -> str:
    return s.lower().replace("á", "a").replace("ã", "a").replace("é", "e").replace(
        "ê", "e"
    ).replace("í", "i").replace("ó", "o").replace("ô", "o").replace("ú", "u").replace(
        "ç", "c"
    )


def first_value_after(line: str) -> str:
    m = VALOR_RE.search(line)
    return m.group(0) if m else ""


def inspect_pdf(pdf_path: Path) -> PdfReport:
    rep = PdfReport(arquivo=pdf_path.name, md5=md5_of(pdf_path))
    raw_lines: list[str] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            rep.paginas = len(pdf.pages)
            for page_idx, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                lines = text.splitlines()
                if page_idx == 1:
                    rep.cabecalho = lines[:8]
                for lineno, raw in enumerate(lines, 1):
                    raw_lines.append(raw)
                    norm = normalize(raw)
                    if "stone pagamentos" in norm:
                        rep.menciona_stone_pagamentos = True
                    if "stone cripto" in norm:
                        rep.menciona_stone_cripto = True
                    if "stone conta" in norm or "conta stone" in norm:
                        rep.menciona_stone_conta = True
                    for lbl in LABELS_SI:
                        if lbl in norm:
                            hit = HitLine(page=page_idx, lineno=lineno, text=raw.strip())
                            rep.si_hits.append(hit)
                            v = first_value_after(raw)
                            if v:
                                rep.valor_apos_si.append(v)
                            break
                    for lbl in LABELS_SF:
                        if lbl in norm:
                            hit = HitLine(page=page_idx, lineno=lineno, text=raw.strip())
                            if "saldo do dia" in norm or "saldo em " in norm:
                                rep.saldo_dia_hits.append(hit)
                            else:
                                rep.sf_hits.append(hit)
                            v = first_value_after(raw)
                            if v:
                                rep.valor_apos_sf.append(v)
                            break
        out_txt = RAW_DIR / f"{pdf_path.stem}_raw.txt"
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text("\n".join(raw_lines), encoding="utf-8")
    except Exception as e:  # pragma: no cover
        rep.erro = f"{type(e).__name__}: {e}"
    return rep


def main() -> None:
    files = stone_files_from_csv()
    print(f"Stone files: {len(files)}")
    reports: list[PdfReport] = []
    for fname in files:
        pdf_path = PDFS_DIR / fname
        if not pdf_path.exists():
            print(f"NAO ACHEI: {pdf_path}")
            reports.append(PdfReport(arquivo=fname, md5="MISSING"))
            continue
        print(f"  -> {fname}")
        rep = inspect_pdf(pdf_path)
        reports.append(rep)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps([r.to_dict() for r in reports], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"OK -> {OUT_JSON}")


if __name__ == "__main__":
    main()
