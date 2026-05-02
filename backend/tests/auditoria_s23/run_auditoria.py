"""S23 Fase 2 — Roda o pipeline em todos os 96 PDFs.

Estrategia:
- Le inventario_pdfs.csv.
- Para cada PDF, chama processar_com_pipeline com timeout de 60s
  via ThreadPoolExecutor.
- Try/except envolvendo CADA chamada — exception de 1 PDF nao para o loop.
- Captura: banco_detectado, usou_ocr, n_transacoes, si, sf, gap, nivel,
  diagnostico, tempo, erro.
- Salva em resultado_pipeline.csv.

Read-only sobre producao. Nao modifica parsers, pipeline, ou qualquer .py
fora desta pasta.
"""

import csv
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path

# Garante que backend/ esteja no sys.path para importar services
ROOT = Path(__file__).resolve().parent.parent.parent.parent  # repo root
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services.pipeline_extracao import processar_com_pipeline  # noqa: E402

PDFS_DIR = BACKEND / "tests" / "fixtures" / "pdfs_reais"
INVENTARIO_CSV = Path(__file__).resolve().parent / "inventario_pdfs.csv"
RESULTADO_CSV = Path(__file__).resolve().parent / "resultado_pipeline.csv"
TIMEOUT_S = 60


def calcular_gap(si, sf, total_entradas, total_saidas):
    if si is None or sf is None:
        return None
    try:
        return round(sf - (si + total_entradas - total_saidas), 2)
    except (TypeError, ValueError):
        return None


def processar_um_pdf(caminho: Path) -> dict:
    """Processa 1 PDF com timeout de TIMEOUT_S. Retorna dict pronto pra CSV."""
    t0 = time.time()
    arquivo = caminho.name
    base = {
        "arquivo": arquivo,
        "banco_detectado": "",
        "usou_ocr": "nao",
        "n_transacoes": 0,
        "si_extraido": "",
        "sf_extraido": "",
        "gap": "",
        "nivel_validador": "",
        "diagnostico": "",
        "tempo_segundos": 0.0,
        "erro": "",
    }

    def _run():
        return processar_com_pipeline(str(caminho))

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_run)
            try:
                r = future.result(timeout=TIMEOUT_S)
            except FuturesTimeoutError:
                base["erro"] = "timeout"
                base["tempo_segundos"] = round(time.time() - t0, 2)
                return base
    except Exception as e:
        base["erro"] = str(e)[:200]
        base["tempo_segundos"] = round(time.time() - t0, 2)
        return base

    base["tempo_segundos"] = round(time.time() - t0, 2)

    try:
        base["banco_detectado"] = getattr(r, "banco", "") or "desconhecido"
        base["usou_ocr"] = "sim" if getattr(r, "requer_ocr", False) else "nao"
        base["n_transacoes"] = len(getattr(r, "transacoes", []) or [])
        si = getattr(r, "saldo_inicial", None)
        sf = getattr(r, "saldo_final", None)
        base["si_extraido"] = "" if si is None else f"{float(si):.2f}"
        base["sf_extraido"] = "" if sf is None else f"{float(sf):.2f}"
        te = getattr(r, "total_entradas", 0.0) or 0.0
        ts = getattr(r, "total_saidas", 0.0) or 0.0
        gap = calcular_gap(si, sf, te, ts)
        base["gap"] = "" if gap is None else f"{gap:.2f}"
        base["nivel_validador"] = getattr(r, "nivel_confianca", "") or "INDETERMINADO"
        diag = getattr(r, "diagnostico", "") or ""
        base["diagnostico"] = (diag[:80]) if diag else ""
        if getattr(r, "erro", None):
            err = r.erro or ""
            base["erro"] = str(err)[:200]
    except Exception as e:
        base["erro"] = f"erro_pos_processamento: {str(e)[:180]}"

    return base


def main() -> None:
    rows_inv = list(csv.DictReader(open(INVENTARIO_CSV, encoding="utf-8")))
    total = len(rows_inv)
    print(f"Iniciando auditoria de {total} PDFs (timeout {TIMEOUT_S}s/PDF)")
    print(f"Pipeline: services.pipeline_extracao.processar_com_pipeline")
    print()

    inicio_global = time.time()
    resultados: list[dict] = []

    for i, inv in enumerate(rows_inv, 1):
        nome = inv["arquivo"]
        caminho = PDFS_DIR / nome
        print(f"[{i:3d}/{total}] {nome[:70]}", flush=True)
        if not caminho.is_file():
            resultados.append({
                "arquivo": nome, "banco_detectado": "", "usou_ocr": "nao",
                "n_transacoes": 0, "si_extraido": "", "sf_extraido": "",
                "gap": "", "nivel_validador": "", "diagnostico": "",
                "tempo_segundos": 0.0, "erro": "arquivo_inexistente",
            })
            continue
        r = processar_um_pdf(caminho)
        resultados.append(r)

    duracao = time.time() - inicio_global

    fieldnames = [
        "arquivo", "banco_detectado", "usou_ocr", "n_transacoes",
        "si_extraido", "sf_extraido", "gap", "nivel_validador",
        "diagnostico", "tempo_segundos", "erro",
    ]
    with open(RESULTADO_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in resultados:
            w.writerow(r)

    print()
    print(f"Auditoria concluida em {duracao:.1f}s")
    print(f"CSV: {RESULTADO_CSV}")
    print(f"Total processados: {len(resultados)}")
    com_erro = sum(1 for r in resultados if r["erro"])
    print(f"Com erro: {com_erro}")


if __name__ == "__main__":
    main()
