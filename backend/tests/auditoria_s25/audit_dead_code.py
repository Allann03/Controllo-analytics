"""
Audit S25 / Fase 2 — Dead code candidatos.

Para cada arquivo do GRUPO A (dead code candidatos genuinos), levanta:
  - Tamanho (linhas)
  - Ultima modificacao git
  - Nomes publicos (classes/funcoes nao-underscore)
  - Referencias por nome do arquivo (sem .py)
  - Referencias por cada nome publico
  - Match em strings (suspeita de importlib/getattr/eval)
  - Match em arquivos .yaml, .json, .md

Tambem processa GRUPO B (vivos apenas em testes) com analise diferente.

Saidas:
  - dead_code_candidatos.md (Grupo A)
  - vivos_apenas_em_testes.md (Grupo B)
  - infraestrutura_python.md (Grupo X — pacotes __init__.py)
"""
from __future__ import annotations

import ast
import json
import subprocess
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"
OUT_DIR = BACKEND_ROOT / "tests" / "auditoria_s25"

# GRUPO A apos correcao do bug do extrator (removidos: indicadores.py,
# importacao_service.py — passaram a ter in-degree>0 com as 5 arestas
# extras detectadas em 'from PACOTE import MODULO_FILHO').
GRUPO_A = [
    "backend/core/config.py",
    "backend/services/parsers/itau_extrato_mensal.py",
    "backend/services/parsers/parser_generico.py",
    "backend/services/parsers/parser_itau_mensal.py",
    "backend/services/parsers/parser_stone.py",
    "backend/test_parsers.py",
]

# GRUPO B apos correcao (removidos: financeiro_service.py,
# simulacao_tributaria_service.py — agora consumidos por routers/, sao
# producao de fato, nao "vivos so via teste").
GRUPO_B = [
    "backend/services/categorias.py",
    "backend/services/contabil/comparador.py",
    "backend/services/contabil/dfc.py",
    "backend/services/contabil/difal.py",
    "backend/services/contabil/icms_st.py",
    "backend/services/contabil/retencoes.py",
    "backend/services/contabil/score_saude.py",
]

GRUPO_X = [
    "backend/routers/__init__.py",
    "backend/services/contabil/tabelas/__init__.py",
    "backend/services/parsers/n2/__init__.py",
    "backend/services/parsers/santander_empresas/__init__.py",
    "backend/services/parsers/bradesco_empresas/__init__.py",
    "backend/services/parsers/__init__.py",
]

EXCLUDE_PARTS = {
    "__pycache__", "venv", "node_modules",
    "auditoria_s23", "auditoria_s24", "auditoria_s25",
}


def to_abs(rel: str) -> Path:
    return PROJECT_ROOT / rel


def extract_public_names(path: Path) -> tuple[list[str], list[str]]:
    """Retorna (classes_publicas, funcoes_publicas)."""
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


def git_last_modified(rel_path: str) -> str:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ci", "--", rel_path],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return (out.stdout or "").strip() or "(sem historico)"
    except Exception as e:
        return f"(erro: {e})"


def list_files_to_search() -> list[Path]:
    """Lista todos arquivos relevantes para grep (codigo + docs)."""
    files: list[Path] = []
    extensions = {".py", ".md", ".yaml", ".yml", ".json", ".toml",
                  ".txt", ".ini", ".cfg", ".sh", ".dockerfile"}
    for p in PROJECT_ROOT.rglob("*"):
        if not p.is_file():
            continue
        parts = set(p.parts)
        if parts & EXCLUDE_PARTS:
            continue
        if p.suffix.lower() in extensions or p.name == "Dockerfile":
            files.append(p)
    return files


def search_term(term: str, files: list[Path], own_path: Path) -> list[tuple[str, int, str]]:
    """
    Busca term em arquivos (exceto own_path). Retorna (rel_path, line_num, line).

    term e tratado como substring literal — case sensitive.
    """
    hits: list[tuple[str, int, str]] = []
    own_resolved = own_path.resolve()
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
        if term not in content:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            if term in line:
                rel = f.relative_to(PROJECT_ROOT).as_posix()
                # Truncar linha
                lt = line.strip()
                if len(lt) > 200:
                    lt = lt[:200] + "..."
                hits.append((rel, i, lt))
                if len(hits) >= 50:
                    return hits
    return hits


def grupo_a_relatorio(files_to_search: list[Path]) -> None:
    linhas: list[str] = []
    linhas.append("# Dead Code Candidatos — GRUPO A (S25 Fase 2)\n")
    linhas.append("Arquivos orfaos em AMBOS os recortes (producao e completo).")
    linhas.append("Validacao via renomear .py.disabled na Fase 3.\n")

    sumario: list[dict] = []

    for rel in GRUPO_A:
        path = to_abs(rel)
        if not path.exists():
            linhas.append(f"## `{rel}`\n")
            linhas.append("**ARQUIVO NAO ENCONTRADO** — listado no protocolo mas inexistente.\n")
            sumario.append({"arquivo": rel, "status": "INEXISTENTE"})
            continue

        # Tamanho
        try:
            n_linhas = sum(1 for _ in path.read_text(encoding="utf-8").splitlines())
        except (UnicodeDecodeError, OSError):
            n_linhas = -1
        last_mod = git_last_modified(rel)
        classes, funcs = extract_public_names(path)
        nome_arquivo = path.stem  # sem .py

        linhas.append(f"## `{rel}`\n")
        linhas.append(f"- Tamanho: **{n_linhas} linhas**")
        linhas.append(f"- Ultima modificacao: {last_mod}")
        linhas.append(f"- Classes publicas ({len(classes)}): {classes if classes else '(nenhuma)'}")
        linhas.append(f"- Funcoes publicas ({len(funcs)}): {funcs if funcs else '(nenhuma)'}")
        linhas.append("")

        # Buscar referencias
        # 1. Por nome do arquivo (sem .py)
        hits_arquivo = search_term(nome_arquivo, files_to_search, path) if nome_arquivo else []
        linhas.append(f"### Referencias por nome do arquivo `{nome_arquivo}` ({len(hits_arquivo)} hits)\n")
        if not hits_arquivo:
            linhas.append("Nenhuma referencia.\n")
        else:
            mostrar = hits_arquivo[:20]
            for f, ln, txt in mostrar:
                linhas.append(f"- `{f}:{ln}` — `{txt}`")
            if len(hits_arquivo) > 20:
                linhas.append(f"- ... +{len(hits_arquivo) - 20} hits adicionais\n")
            linhas.append("")

        # 2. Por nomes publicos
        if classes or funcs:
            linhas.append("### Referencias por nomes publicos\n")
            for nome in classes + funcs:
                hits = search_term(nome, files_to_search, path)
                linhas.append(f"#### `{nome}` ({len(hits)} hits)")
                if not hits:
                    linhas.append("  Nenhuma referencia. **Nome morto.**\n")
                else:
                    for f, ln, txt in hits[:10]:
                        linhas.append(f"  - `{f}:{ln}` — `{txt}`")
                    if len(hits) > 10:
                        linhas.append(f"  - ... +{len(hits) - 10} hits adicionais")
                    linhas.append("")

        # 3. Suspeita de importlib/getattr/eval (busca strings com nome do arquivo)
        suspeitos_dyn: list[str] = []
        for f, ln, txt in hits_arquivo:
            txt_low = txt.lower()
            if any(k in txt_low for k in ["importlib", "import_module", "getattr", "__import__"]):
                suspeitos_dyn.append(f"`{f}:{ln}` — `{txt}`")

        linhas.append(f"### Possiveis chamadas dinamicas ({len(suspeitos_dyn)} hits)\n")
        if not suspeitos_dyn:
            linhas.append("Nenhuma suspeita.\n")
        else:
            for s in suspeitos_dyn:
                linhas.append(f"- {s}")
            linhas.append("")

        # 4. Em arquivos nao-py
        non_py = [(f, ln, txt) for f, ln, txt in hits_arquivo if not f.endswith(".py")]
        linhas.append(f"### Referencias em docs/configs ({len(non_py)} hits)\n")
        if not non_py:
            linhas.append("Nenhuma.\n")
        else:
            for f, ln, txt in non_py[:10]:
                linhas.append(f"- `{f}:{ln}` — `{txt}`")
            linhas.append("")

        # Veredito heuristico
        veredito = "DEAD CANDIDATE — validar Fase 3"
        if hits_arquivo and not all(f.endswith(".py.disabled") for f, _, _ in hits_arquivo):
            # Filtrar self-references via path em test logs
            if non_py:
                veredito = "INVESTIGAR — referencias em docs/configs"
            elif suspeitos_dyn:
                veredito = "INVESTIGAR — possivel chamada dinamica"
        if classes or funcs:
            todos_nomes_mortos = True
            for nome in classes + funcs:
                if search_term(nome, files_to_search, path):
                    todos_nomes_mortos = False
                    break
            if not todos_nomes_mortos:
                veredito = "INVESTIGAR — algum nome publico tem hits"

        linhas.append(f"### Veredito heuristico\n")
        linhas.append(f"**{veredito}**\n")
        linhas.append("---\n")

        sumario.append({
            "arquivo": rel,
            "linhas": n_linhas,
            "ultima_mod": last_mod,
            "classes": len(classes),
            "funcs": len(funcs),
            "hits_nome_arquivo": len(hits_arquivo),
            "hits_dinamicos": len(suspeitos_dyn),
            "hits_nao_py": len(non_py),
            "veredito": veredito,
        })

    # Sumario tabular no topo
    cabecalho = ["# Dead Code Candidatos — GRUPO A (S25 Fase 2)\n",
                 "## Sumario\n",
                 "| Arquivo | linhas | classes | funcs | hits_nome | hits_dyn | hits_nao_py | veredito |",
                 "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for s in sumario:
        if s.get("status") == "INEXISTENTE":
            cabecalho.append(f"| `{s['arquivo']}` | -- | -- | -- | -- | -- | -- | INEXISTENTE |")
        else:
            cabecalho.append(
                f"| `{s['arquivo']}` | {s['linhas']} | {s['classes']} | {s['funcs']} "
                f"| {s['hits_nome_arquivo']} | {s['hits_dinamicos']} | {s['hits_nao_py']} "
                f"| {s['veredito']} |"
            )
    cabecalho.append("")
    out = OUT_DIR / "dead_code_candidatos.md"
    out.write_text("\n".join(cabecalho) + "\n" + "\n".join(linhas[1:]), encoding="utf-8")
    print(f"[audit_dead_code] {out}")


def grupo_b_relatorio(files_to_search: list[Path], grafo_completo_path: Path) -> None:
    """Para cada arquivo GRUPO B, listar testes que importam."""
    grafo = json.loads(grafo_completo_path.read_text(encoding="utf-8"))
    arestas = grafo["arestas"]
    in_neighbors: dict[str, list[str]] = defaultdict(list)
    for a in arestas:
        in_neighbors[a["para"]].append(a["de"])

    linhas: list[str] = []
    linhas.append("# Vivos APENAS via Testes — GRUPO B (S25 Fase 2)\n")
    linhas.append("Arquivos com in-degree=0 no recorte producao mas in-degree>0 no completo.")
    linhas.append("NAO sao dead code para deletar. Sao features sem integracao em endpoints.\n")
    linhas.append("Hipoteses de origem: feature-flag (CONTROLLO_DRE_ENGINE / CONTROLLO_LP_ENGINE),")
    linhas.append("WIP abandonado, helper esquecido.\n")

    for rel in GRUPO_B:
        path = to_abs(rel)
        importadores = sorted(set(in_neighbors.get(rel, [])))
        testes = [i for i in importadores if "/tests/" in i or "/tests_fase2/" in i or i.startswith("backend/tests/")]
        nao_testes = [i for i in importadores if i not in testes]

        # Tamanho e mod
        if path.exists():
            n = sum(1 for _ in path.read_text(encoding="utf-8").splitlines())
        else:
            n = -1
        last_mod = git_last_modified(rel)
        classes, funcs = extract_public_names(path)

        linhas.append(f"## `{rel}`\n")
        linhas.append(f"- Tamanho: {n} linhas")
        linhas.append(f"- Ultima modificacao: {last_mod}")
        linhas.append(f"- Classes publicas ({len(classes)}): {classes}")
        linhas.append(f"- Funcoes publicas ({len(funcs)}): {funcs}")
        linhas.append(f"- Importadores TOTAL: {len(importadores)}")
        linhas.append(f"  - testes: {len(testes)}")
        linhas.append(f"  - nao-testes: {len(nao_testes)}")
        linhas.append("")
        if testes:
            linhas.append("**Testes que importam:**")
            for t in testes:
                linhas.append(f"  - `{t}`")
            linhas.append("")
        if nao_testes:
            linhas.append("**Outros importadores (nao testes):**")
            for n_ in nao_testes:
                linhas.append(f"  - `{n_}`")
            linhas.append("")

        # Buscar feature-flag references no arquivo
        flag_hits: list[str] = []
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                for keyword in ["CONTROLLO_DRE_ENGINE", "CONTROLLO_LP_ENGINE",
                                "FEATURE_FLAG", "feature_flag", "novo", "legado"]:
                    if keyword in content:
                        flag_hits.append(keyword)
            except (UnicodeDecodeError, OSError):
                pass
        linhas.append(f"**Mencoes feature-flag no arquivo:** {flag_hits if flag_hits else '(nenhuma)'}\n")

        # Hipotese
        hip = "WIP / desconectado de producao"
        if any(k in flag_hits for k in ["CONTROLLO_DRE_ENGINE", "CONTROLLO_LP_ENGINE"]):
            hip = "Feature sob flag (sera ativada via env var)"
        elif "novo" in flag_hits or "legado" in flag_hits:
            hip = "Possivel feature sob flag (mencao a 'novo'/'legado')"

        linhas.append(f"**Hipotese:** {hip}\n")
        linhas.append("---\n")

    out = OUT_DIR / "vivos_apenas_em_testes.md"
    out.write_text("\n".join(linhas), encoding="utf-8")
    print(f"[audit_dead_code] {out}")


def grupo_x_relatorio() -> None:
    linhas: list[str] = []
    linhas.append("# Infraestrutura Python — GRUPO X (S25 Fase 2)\n")
    linhas.append("`__init__.py` (vazios ou minimos) que aparecem como orfaos no grafo.")
    linhas.append("**NAO sao dead code** — pacotes Python precisam deles para imports funcionarem.\n")
    linhas.append("Preservar mesmo sem in-degree.\n")

    for rel in GRUPO_X:
        path = to_abs(rel)
        if not path.exists():
            linhas.append(f"- `{rel}` — **inexistente** (nao havia no codebase)")
            continue
        try:
            content = path.read_text(encoding="utf-8")
            n_linhas = sum(1 for _ in content.splitlines())
            non_blank = [l for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
            classes, funcs = extract_public_names(path)
            status = "vazio" if not non_blank else f"{len(non_blank)} linhas com codigo"
            preview = non_blank[0] if non_blank else "(vazio)"
            linhas.append(
                f"- `{rel}` — {n_linhas} linhas, {status}, "
                f"classes={len(classes)}, funcs={len(funcs)} — preview: `{preview[:80]}`"
            )
        except (UnicodeDecodeError, OSError):
            linhas.append(f"- `{rel}` — **erro de leitura**")

    out = OUT_DIR / "infraestrutura_python.md"
    out.write_text("\n".join(linhas), encoding="utf-8")
    print(f"[audit_dead_code] {out}")


def main() -> None:
    print("[audit_dead_code] listando arquivos para grep...")
    files = list_files_to_search()
    print(f"[audit_dead_code] {len(files)} arquivos a serem grepados")

    print("[audit_dead_code] GRUPO A — dead code candidatos...")
    grupo_a_relatorio(files)

    print("[audit_dead_code] GRUPO B — vivos apenas em testes...")
    grafo_completo = OUT_DIR / "grafo_dependencias_completo.json"
    grupo_b_relatorio(files, grafo_completo)

    print("[audit_dead_code] GRUPO X — infraestrutura python...")
    grupo_x_relatorio()

    print("[audit_dead_code] OK")


if __name__ == "__main__":
    main()
