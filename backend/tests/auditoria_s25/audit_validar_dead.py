"""
Audit S25 / Fase 3 — Validacao de Dead Code (protocolo LOTE).

Para cada arquivo do GRUPO A (apos [1/6] ja feito):
  1. PRE-CHECK granular: grep nome arquivo, classes publicas, funcoes
     publicas, PARSERS/_FALLBACK_PARSERS/_ASSINATURAS/_NOME_BANCO_EXIBICAO
     em extrator_pdf, docs/yamls/jsons/md/toml.
  2. Se PRE-CHECK tem match nao-trivial -> marca INVESTIGAR, pula.
  3. Se LIMPO:
     a. Renomeia arquivo.py -> arquivo.py.disabled
     b. Roda pytest, compara com baseline
     c. Renomeia de volta
     d. Roda pytest CONFIRMACAO (deve voltar ao baseline)
     e. Se nao voltar -> PARAR, reportar
  4. Acumula resultados.

Saida: dead_code_validado.md + dead_code_validado.json
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"
OUT_DIR = BACKEND_ROOT / "tests" / "auditoria_s25"

# [1/6] core/config.py ja foi validado em execucao anterior — resultado fixado
RESULTADO_INICIAL = [{
    "indice": "1/6",
    "arquivo": "backend/core/config.py",
    "pre_check": "LIMPO (referencias todas falsos positivos genericos em docs)",
    "acao": "VALIDADO",
    "pytest_pos_disabled": "1 failed, 912 passed, 1 skipped, 1 warning, 2 errors in 308.18s",
    "pytest_pos_disabled_ok": True,
    "pytest_pos_revert": "(implicita via pytest do [2/6] que foi interrompido)",
    "pytest_pos_revert_ok": None,  # nao re-confirmado nesta sessao
    "veredito": "DEAD CONFIRMED",
    "elapsed": 310.6,
}]

# [2/6] a [6/6]
GRUPO_A_RESTANTE = [
    ("2/6", "backend/services/parsers/itau_extrato_mensal.py"),
    ("3/6", "backend/services/parsers/parser_generico.py"),
    ("4/6", "backend/services/parsers/parser_itau_mensal.py"),
    ("5/6", "backend/services/parsers/parser_stone.py"),
    ("6/6", "backend/test_parsers.py"),
]

ZXCVBN_TEST_NAME = "test_t8_senhas_comuns_rejeita_via_zxcvbn"

EXTRATOR_PDF = BACKEND_ROOT / "services" / "extrator_pdf.py"

EXTENSOES_DOCS = {".md", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg"}
EXCLUDE_DIRS = {"__pycache__", "venv", "node_modules", ".next",
                "auditoria_s23", "auditoria_s24", "auditoria_s25",
                ".pytest_cache", ".git"}


def file_relevant_for_grep(p: Path) -> bool:
    parts = set(p.parts)
    if parts & EXCLUDE_DIRS:
        return False
    if p.suffix == ".py":
        return True
    if p.suffix.lower() in EXTENSOES_DOCS:
        return True
    return False


def listar_arquivos_grep() -> list[Path]:
    out: list[Path] = []
    for p in PROJECT_ROOT.rglob("*"):
        if p.is_file() and file_relevant_for_grep(p):
            out.append(p)
    return out


def grep_word(termo: str, files: list[Path], own: Path,
              max_hits: int = 30) -> list[tuple[str, int, str]]:
    """Busca termo (substring case-sensitive). Exclui own."""
    own_resolved = own.resolve()
    hits: list[tuple[str, int, str]] = []
    for f in files:
        try:
            if f.resolve() == own_resolved:
                continue
        except OSError:
            pass
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if termo not in content:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            if termo in line:
                rel = f.relative_to(PROJECT_ROOT).as_posix()
                lt = line.strip()
                if len(lt) > 200:
                    lt = lt[:200] + "..."
                hits.append((rel, i, lt))
                if len(hits) >= max_hits:
                    return hits
    return hits


def is_trivial_doc_hit(hit: tuple[str, int, str]) -> bool:
    """
    Heuristica: hit e trivial se vem de doc/audit retrospectivo
    (mencao em arquitetura, sumario etc) ou de log/cache.
    """
    arq, _, _ = hit
    if arq.endswith(".md"):
        return True
    if "AUDITORIA" in arq.upper():
        return True
    if ".next/" in arq or ".pytest_cache/" in arq:
        return True
    if arq.startswith(".claude/"):
        return True
    return False


def extract_public_names(path: Path) -> tuple[list[str], list[str]]:
    """Retorna (classes_publicas, funcoes_publicas) top-level."""
    import ast
    if not path.exists():
        return [], []
    try:
        source = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return [], []
    if not source.strip():
        return [], []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [], []
    classes, funcs = [], []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                funcs.append(node.name)
    return sorted(classes), sorted(funcs)


def pre_check_arquivo(rel: str, files: list[Path]) -> dict:
    """
    Executa PRE-CHECK granular do arquivo.
    Retorna {"limpo": bool, "detalhes": [...], "summary": "..."}.
    """
    path = PROJECT_ROOT / rel
    nome = path.stem
    classes, funcs = extract_public_names(path)
    detalhes: list[str] = []

    # 1. Nome do arquivo
    hits_nome = grep_word(nome, files, path)
    nao_triviais_nome = [h for h in hits_nome if not is_trivial_doc_hit(h)]
    detalhes.append(f"nome_arquivo `{nome}`: {len(hits_nome)} hits "
                    f"({len(nao_triviais_nome)} nao-triviais)")

    # 2. Classes publicas
    hits_classes: dict[str, list[tuple[str, int, str]]] = {}
    for c in classes:
        h = grep_word(c, files, path)
        nt = [x for x in h if not is_trivial_doc_hit(x)]
        hits_classes[c] = nt
        detalhes.append(f"classe `{c}`: {len(h)} hits ({len(nt)} nao-triviais)")

    # 3. Funcoes publicas
    hits_funcs: dict[str, list[tuple[str, int, str]]] = {}
    for fn in funcs:
        h = grep_word(fn, files, path)
        nt = [x for x in h if not is_trivial_doc_hit(x)]
        hits_funcs[fn] = nt
        detalhes.append(f"funcao `{fn}`: {len(h)} hits ({len(nt)} nao-triviais)")

    # 4. Em extrator_pdf (PARSERS, _FALLBACK_PARSERS, _ASSINATURAS, _NOME_BANCO_EXIBICAO)
    extrator_hits: list[str] = []
    if EXTRATOR_PDF.exists():
        try:
            extrator_content = EXTRATOR_PDF.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            extrator_content = ""
        # Verificar se nome do arquivo aparece no dict PARSERS, FALLBACK_PARSERS, _ASSINATURAS, _NOME_BANCO_EXIBICAO
        for keyword in ["PARSERS", "FALLBACK_PARSERS", "_ASSINATURAS", "_NOME_BANCO_EXIBICAO"]:
            if nome in extrator_content:
                # Ja capturado por hits_nome
                pass
        # Buscar classes do arquivo no extrator
        for c in classes:
            if c in extrator_content:
                # Descobrir linha
                for i, l in enumerate(extrator_content.splitlines(), 1):
                    if c in l:
                        extrator_hits.append(f"backend/services/extrator_pdf.py:{i} — `{l.strip()[:120]}`")
                        break
    detalhes.append(f"extrator_pdf — classes referenciadas: {len(extrator_hits)}")

    # Decidir limpo
    limpo = (
        len(nao_triviais_nome) == 0
        and all(len(v) == 0 for v in hits_classes.values())
        and all(len(v) == 0 for v in hits_funcs.values())
        and len(extrator_hits) == 0
    )

    # Excecao: se classe e referenciada APENAS no extrator pelo nome dela como import
    # estatico (ex: `from .parsers.X import ParserY`), isso JA seria capturado pelo
    # grafo. Aqui nao deveria estar pois entrou na lista A. Mas permitir match em
    # docs.

    summary = "LIMPO" if limpo else "INVESTIGAR"

    return {
        "limpo": limpo,
        "summary": summary,
        "detalhes": detalhes,
        "hits_nome_nt": [f"{a}:{i} — {t}" for a, i, t in nao_triviais_nome[:10]],
        "hits_classes_nt": {k: [f"{a}:{i} — {t}" for a, i, t in v[:10]] for k, v in hits_classes.items() if v},
        "hits_funcs_nt": {k: [f"{a}:{i} — {t}" for a, i, t in v[:10]] for k, v in hits_funcs.items() if v},
        "hits_extrator": extrator_hits,
        "classes_total": len(classes),
        "funcs_total": len(funcs),
    }


def rodar_pytest(label: str) -> dict:
    print(f"    > pytest {label} (~5min)...", flush=True)
    t0 = time.time()
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--tb=no", "-q"],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        timeout=900,
    )
    elapsed = time.time() - t0
    text = (out.stdout or "") + (out.stderr or "")
    lines = [l for l in text.splitlines() if l.strip()]
    last = lines[-1] if lines else "(vazio)"
    res = {"raw": last, "elapsed": round(elapsed, 1)}
    for keyword, key in [("passed", "passed"), ("failed", "failed"),
                         ("skipped", "skipped"), ("error", "errors")]:
        m = re.search(rf"(\d+)\s+{keyword}", last)
        res[key] = int(m.group(1)) if m else 0
    print(f"    < {last} (em {res['elapsed']}s)", flush=True)
    return res


def baseline_ok(res: dict) -> tuple[bool, str]:
    p = res.get("passed", 0)
    f = res.get("failed", 0)
    s = res.get("skipped", 0)
    e = res.get("errors", 0)
    passed_ok = p in (912, 913)
    failed_ok = f in (0, 1)
    skipped_ok = s == 1
    errors_ok = e == 2
    ok = passed_ok and failed_ok and skipped_ok and errors_ok
    motivo = (f"passed={p} (esperado 912/913), failed={f} (esperado 0/1), "
              f"skipped={s} (=1), errors={e} (=2)")
    return ok, motivo


def desabilitar(rel: str) -> Path:
    src = PROJECT_ROOT / rel
    dst = src.with_name(src.name + ".disabled")
    src.rename(dst)
    return dst


def reabilitar(rel: str) -> Path:
    disabled = PROJECT_ROOT / (rel + ".disabled")
    target = PROJECT_ROOT / rel
    disabled.rename(target)
    return target


def main() -> None:
    print("=== Fase 3 LOTE — listando arquivos para grep... ===")
    files = listar_arquivos_grep()
    print(f"    {len(files)} arquivos elegiveis para grep")
    print()

    resultados: list[dict] = list(RESULTADO_INICIAL)
    parar = False

    for indice, rel in GRUPO_A_RESTANTE:
        if parar:
            resultados.append({
                "indice": indice,
                "arquivo": rel,
                "pre_check": "(nao executado)",
                "acao": "PULADO_PARADA_ANTERIOR",
                "veredito": "PENDENTE",
            })
            continue

        print(f"\n=== [{indice}] {rel} ===")
        path = PROJECT_ROOT / rel
        if not path.exists():
            print("  ! arquivo inexistente")
            resultados.append({
                "indice": indice,
                "arquivo": rel,
                "pre_check": "INEXISTENTE",
                "acao": "PULADO",
                "veredito": "INEXISTENTE",
            })
            continue

        # PRE-CHECK
        print("  PRE-CHECK...")
        pre = pre_check_arquivo(rel, files)
        for d in pre["detalhes"]:
            print(f"    - {d}")
        if pre["hits_extrator"]:
            for h in pre["hits_extrator"][:3]:
                print(f"    ! extrator_pdf: {h}")
        print(f"  -> PRE-CHECK: {pre['summary']}")

        if not pre["limpo"]:
            resultados.append({
                "indice": indice,
                "arquivo": rel,
                "pre_check": pre["summary"],
                "pre_check_detalhes": pre["detalhes"],
                "hits_nome_nt": pre["hits_nome_nt"],
                "hits_classes_nt": pre["hits_classes_nt"],
                "hits_funcs_nt": pre["hits_funcs_nt"],
                "hits_extrator": pre["hits_extrator"],
                "acao": "BLOQUEADO",
                "veredito": "INVESTIGAR",
            })
            print("  ! BLOQUEADO — pulando para proximo")
            continue

        # Renomear .disabled
        try:
            d_path = desabilitar(rel)
            print(f"  > {d_path.name}")
        except OSError as e:
            resultados.append({
                "indice": indice,
                "arquivo": rel,
                "pre_check": pre["summary"],
                "acao": "ERRO_RENOMEAR",
                "veredito": "ERRO",
                "erro": str(e),
            })
            continue

        # pytest com .disabled
        res_disabled = rodar_pytest("pos-disabled")
        ok_disabled, motivo_disabled = baseline_ok(res_disabled)
        veredito = "DEAD CONFIRMED" if ok_disabled else "DEAD NEGADO"
        print(f"  -> pytest pos-disabled: {motivo_disabled}")
        print(f"  -> veredito disabled: {veredito}")

        # Reverter
        reabilitar(rel)
        print("  > revertido para .py")

        # pytest pos-revert (CONFIRMACAO)
        res_revert = rodar_pytest("pos-revert")
        ok_revert, motivo_revert = baseline_ok(res_revert)
        print(f"  -> pytest pos-revert: {motivo_revert}")

        resultados.append({
            "indice": indice,
            "arquivo": rel,
            "pre_check": pre["summary"],
            "pre_check_detalhes": pre["detalhes"],
            "acao": "VALIDADO",
            "pytest_pos_disabled": res_disabled.get("raw"),
            "pytest_pos_disabled_ok": ok_disabled,
            "pytest_pos_disabled_elapsed": res_disabled.get("elapsed"),
            "pytest_pos_revert": res_revert.get("raw"),
            "pytest_pos_revert_ok": ok_revert,
            "pytest_pos_revert_elapsed": res_revert.get("elapsed"),
            "veredito": veredito,
        })

        if not ok_revert:
            print(f"\n  !!! pytest pos-revert NAO VOLTOU AO BASELINE — PARANDO LOTE")
            parar = True

    # ========= Salvar =========
    out_json = OUT_DIR / "dead_code_validado.json"
    out_json.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")

    linhas: list[str] = []
    linhas.append("# Dead Code Validado — S25 Fase 3 (LOTE)\n")
    linhas.append("Validacao via renomeacao temporaria + pytest baseline.\n")
    linhas.append("Baseline aceitavel: 912-913 passed / 0-1 failed (zxcvbn) / 1 skipped / 2 errors\n")

    linhas.append("## Sumario\n")
    linhas.append("| Indice | Arquivo | PRE-CHECK | Acao | pos-disabled | pos-revert | Veredito |")
    linhas.append("| --- | --- | --- | --- | --- | --- | --- |")
    for r in resultados:
        pos_d = "OK" if r.get("pytest_pos_disabled_ok") else (
            "FAIL" if r.get("pytest_pos_disabled_ok") is False else "-"
        )
        pos_r = "OK" if r.get("pytest_pos_revert_ok") else (
            "FAIL" if r.get("pytest_pos_revert_ok") is False else "-"
        )
        linhas.append(
            f"| {r['indice']} | `{r['arquivo']}` | {r['pre_check']} "
            f"| {r['acao']} | {pos_d} | {pos_r} | {r['veredito']} |"
        )
    linhas.append("")

    linhas.append("## Detalhes por Arquivo\n")
    for r in resultados:
        linhas.append(f"### [{r['indice']}] `{r['arquivo']}` — {r['veredito']}")
        linhas.append(f"- **PRE-CHECK**: {r['pre_check']}")
        if r.get("pre_check_detalhes"):
            linhas.append("  - Greps:")
            for d in r["pre_check_detalhes"]:
                linhas.append(f"    - {d}")
        if r.get("hits_nome_nt"):
            linhas.append("  - **Hits nome (nao-triviais)**:")
            for h in r["hits_nome_nt"]:
                linhas.append(f"    - `{h}`")
        if r.get("hits_classes_nt"):
            linhas.append("  - **Hits classes (nao-triviais)**:")
            for k, lst in r["hits_classes_nt"].items():
                for h in lst:
                    linhas.append(f"    - `{k}` em `{h}`")
        if r.get("hits_funcs_nt"):
            linhas.append("  - **Hits funcoes (nao-triviais)**:")
            for k, lst in r["hits_funcs_nt"].items():
                for h in lst:
                    linhas.append(f"    - `{k}` em `{h}`")
        if r.get("hits_extrator"):
            linhas.append("  - **Hits em extrator_pdf**:")
            for h in r["hits_extrator"]:
                linhas.append(f"    - `{h}`")
        if r.get("acao") == "VALIDADO":
            linhas.append(f"- pytest pos-disabled: `{r.get('pytest_pos_disabled')}`")
            linhas.append(f"- pytest pos-revert: `{r.get('pytest_pos_revert')}`")
        linhas.append("")

    out_md = OUT_DIR / "dead_code_validado.md"
    out_md.write_text("\n".join(linhas), encoding="utf-8")
    print(f"\n[Fase 3] {out_md}")
    print(f"[Fase 3] {out_json}")

    # Sumario stdout
    n_dead = sum(1 for r in resultados if r["veredito"] == "DEAD CONFIRMED")
    n_negado = sum(1 for r in resultados if r["veredito"] == "DEAD NEGADO")
    n_invest = sum(1 for r in resultados if r["veredito"] == "INVESTIGAR")
    print(f"DEAD CONFIRMED: {n_dead}")
    print(f"DEAD NEGADO: {n_negado}")
    print(f"INVESTIGAR (bloqueado): {n_invest}")
    if parar:
        print("PARADO no meio devido a pytest pos-revert nao voltar ao baseline")


if __name__ == "__main__":
    main()
