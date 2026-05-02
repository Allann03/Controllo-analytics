"""S23 Fase 3 — Captura diagnostico completo dos VERMELHOS suspeitos.

Re-roda pipeline so para PDFs flagged como Stone, c6bank, BB, sicredi,
itau_empresas, safra, pagbank, btg, santander_empresas, e os 5 Itau
mensal VERMELHO. Captura diagnostico/validacao completos sem truncar.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services.pipeline_extracao import processar_com_pipeline  # noqa: E402

PDFS_DIR = BACKEND / "tests" / "fixtures" / "pdfs_reais"
RESULTADO_CSV = Path(__file__).resolve().parent / "resultado_pipeline.csv"
OUT_JSON = Path(__file__).resolve().parent / "detalhes_vermelhos.json"


def main() -> None:
    rows = list(csv.DictReader(open(RESULTADO_CSV, encoding="utf-8")))
    bancos_alvo = {
        "stone", "c6bank", "bb", "sicredi", "itau_empresas",
        "safra", "pagbank", "btg", "santander_empresas",
    }
    alvos = [r for r in rows
             if r["nivel_validador"] == "VERMELHO"
             and (r["banco_detectado"] in bancos_alvo
                  or r["banco_detectado"] == "itau")]

    print(f"Re-rodando {len(alvos)} PDFs VERMELHO para capturar diagnostico full...")

    detalhes: list[dict] = []
    for i, r in enumerate(alvos, 1):
        nome = r["arquivo"]
        caminho = PDFS_DIR / nome
        print(f"[{i}/{len(alvos)}] {nome[:60]}", flush=True)
        try:
            res = processar_com_pipeline(str(caminho))
        except Exception as e:
            detalhes.append({
                "arquivo": nome,
                "banco": "ERRO",
                "diagnostico_full": f"exception: {str(e)[:200]}",
            })
            continue
        d = {
            "arquivo": nome,
            "banco": getattr(res, "banco", ""),
            "si": getattr(res, "saldo_inicial", None),
            "sf": getattr(res, "saldo_final", None),
            "n_tx": len(getattr(res, "transacoes", []) or []),
            "total_entradas": getattr(res, "total_entradas", 0),
            "total_saidas": getattr(res, "total_saidas", 0),
            "gap": getattr(res, "gap", None),
            "reconciliacao": getattr(res, "reconciliacao", ""),
            "nivel": getattr(res, "nivel_confianca", ""),
            "diagnostico_full": getattr(res, "diagnostico", ""),
            "validacao": getattr(res, "validacao", {}),
            "checkpoints_total": getattr(res, "checkpoints_total", 0),
            "checkpoints_ok": getattr(res, "checkpoints_ok", 0),
            "warnings_count": len(getattr(res, "warnings", []) or []),
            "erro": getattr(res, "erro", None),
        }
        detalhes.append(d)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(detalhes, f, indent=2, default=str, ensure_ascii=False)

    # Imprime tabela
    print()
    print(f"{'arquivo':<50} {'banco':<22} {'si':>10} {'sf':>10} {'gap':>10} {'#tx':>4}")
    print("-" * 120)
    for d in detalhes:
        si = "" if d.get("si") is None else f"{d['si']:.2f}"
        sf = "" if d.get("sf") is None else f"{d['sf']:.2f}"
        gap = "" if d.get("gap") is None else f"{d['gap']:.2f}"
        print(f"{d['arquivo'][:50]:<50} {d['banco'][:22]:<22} {si:>10} {sf:>10} {gap:>10} {d.get('n_tx', 0):>4}")
        diag = d.get("diagnostico_full", "")
        if diag:
            print(f"  diag: {diag}")
    print(f"\nJSON: {OUT_JSON}")


if __name__ == "__main__":
    main()
