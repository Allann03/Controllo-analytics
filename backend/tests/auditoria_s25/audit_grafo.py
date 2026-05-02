"""
Audit S25 / Fase 1 — Grafo de Dependencias.

Gera DOIS recortes:

  - "producao": backend/main.py, services/, routers/, data/, scripts/
                (exclui tests/, tests_fase2/, test_parsers.py raiz)
  - "completo": producao + tests/, tests_fase2/, test_parsers.py raiz
                (exclui auditorias antigas e __pycache__)

Entry-points (esperado in-degree=0 por design) sao marcados com flag.

Saidas:
  - grafo_dependencias_producao.json
  - grafo_dependencias_completo.json
  - grafo_dependencias.md (analise comparativa)

Read-only sobre codigo de producao.
"""
from __future__ import annotations

import ast
import json
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"
OUT_DIR = BACKEND_ROOT / "tests" / "auditoria_s25"

# Diretorios cujos .py NUNCA serao mapeados em nenhum recorte
GLOBAL_EXCLUDE = {
    "__pycache__",
    "venv",
    "auditoria_s23",
    "auditoria_s24",
    "auditoria_s25",
    "raw_stone",  # tests/fixtures/raw_stone (PDFs, mas precaucao)
}

# Pastas e arquivos que NAO entram no recorte "producao"
PRODUCAO_EXTRA_EXCLUDE = {
    "tests",
    "tests_fase2",
}
# Arquivo raiz (relativo a backend/) excluido do recorte producao
PRODUCAO_EXCLUDE_FILES_RELATIVE = {
    "test_parsers.py",
}

# Entry-points: in-degree=0 esperado por design
ENTRY_POINTS = {
    "backend/main.py",
    "backend/scripts/seed_empresas_validacao_paralela.py",
    "backend/scripts/validacao_paralela_dre.py",
}

EXTERNAL_PREFIXES = {
    "fastapi", "pydantic", "starlette", "uvicorn", "sqlalchemy",
    "passlib", "jose", "jwt", "bcrypt", "argon2", "zxcvbn",
    "openpyxl", "pandas", "numpy", "pdfplumber", "pdfminer",
    "pytesseract", "PIL", "Pillow", "fitz", "pymupdf",
    "pytest", "pytest_asyncio", "httpx", "requests",
    "dotenv", "boto3", "botocore", "redis", "psycopg2",
    "alembic", "anyio", "sniffio", "click", "typer",
    "datetime", "decimal", "json", "logging", "os", "sys",
    "re", "io", "pathlib", "tempfile", "shutil", "uuid",
    "hashlib", "hmac", "secrets", "base64", "csv", "math",
    "collections", "itertools", "functools", "typing",
    "asyncio", "threading", "multiprocessing", "subprocess",
    "abc", "enum", "dataclasses", "warnings", "traceback",
    "copy", "contextlib", "operator", "string", "textwrap",
    "unicodedata", "calendar", "time", "random", "statistics",
    "concurrent", "queue", "weakref", "inspect", "importlib",
    "ast", "pickle", "tomllib", "platform",
}


def to_node_id(path: Path) -> str:
    rel = path.relative_to(PROJECT_ROOT)
    return rel.as_posix()


def is_internal_module(name: str) -> bool:
    if not name:
        return False
    head = name.split(".")[0]
    if head in EXTERNAL_PREFIXES:
        return False
    return head in {
        "backend", "services", "routers", "data", "core",
        "main", "tests", "scripts", "tests_fase2",
    } or name.startswith(".")


def file_eligible_global(path: Path) -> bool:
    """Filtro global: exclui sempre venv, __pycache__, auditorias antigas."""
    parts = set(path.parts)
    if parts & GLOBAL_EXCLUDE:
        return False
    return True


def file_eligible_producao(path: Path) -> bool:
    """Filtro do recorte producao."""
    if not file_eligible_global(path):
        return False
    parts = set(path.parts)
    if parts & PRODUCAO_EXTRA_EXCLUDE:
        return False
    # Excluir test_parsers.py na raiz de backend/
    try:
        rel = path.relative_to(BACKEND_ROOT).as_posix()
    except ValueError:
        return True
    if rel in PRODUCAO_EXCLUDE_FILES_RELATIVE:
        return False
    return True


def module_to_node_id(module_name: str) -> str | None:
    if module_name.startswith("."):
        return None
    parts = module_name.split(".")
    cf = PROJECT_ROOT.joinpath(*parts).with_suffix(".py")
    if cf.exists():
        return to_node_id(cf)
    cp = PROJECT_ROOT.joinpath(*parts) / "__init__.py"
    if cp.exists():
        return to_node_id(cp)
    if parts[0] != "backend":
        cf2 = BACKEND_ROOT.joinpath(*parts).with_suffix(".py")
        if cf2.exists():
            return to_node_id(cf2)
        cp2 = BACKEND_ROOT.joinpath(*parts) / "__init__.py"
        if cp2.exists():
            return to_node_id(cp2)
    return None


def relative_to_node_id(level: int, module: str | None, src_path: Path) -> str | None:
    base = src_path.parent
    for _ in range(level - 1):
        base = base.parent
    if module:
        for part in module.split("."):
            base = base / part
    cf = base.with_suffix(".py")
    if cf.exists():
        return to_node_id(cf)
    cp = base / "__init__.py"
    if cp.exists():
        return to_node_id(cp)
    return None


def relative_alias_to_node_id(level: int, module: str | None, alias_name: str, src_path: Path) -> str | None:
    """
    Resolve `from .X import Y` ou `from . import Y` no arquivo Y.py
    dentro do pacote relativo.

    Tenta:
      1. caminho_base/alias_name.py (modulo filho)
      2. caminho_base/alias_name/__init__.py (subpacote)
    """
    base = src_path.parent
    for _ in range(level - 1):
        base = base.parent
    if module:
        for part in module.split("."):
            base = base / part
    candidate_file = base / f"{alias_name}.py"
    if candidate_file.exists():
        return to_node_id(candidate_file)
    candidate_pkg = base / alias_name / "__init__.py"
    if candidate_pkg.exists():
        return to_node_id(candidate_pkg)
    return None


def extract_imports(src_path: Path) -> list[str]:
    """
    Extrai imports internos com cobertura completa dos padroes Python.

    Trata especialmente o padrao `from PACOTE import MODULO_FILHO`, onde
    PACOTE/MODULO_FILHO.py existe — adiciona aresta tanto para
    PACOTE/__init__.py quanto para PACOTE/MODULO_FILHO.py (ambas sao reais
    em tempo de execucao).
    """
    try:
        source = src_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    try:
        tree = ast.parse(source, filename=str(src_path))
    except SyntaxError:
        return []
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # Import relativo: from .x.y import z
                # Aresta 1: para o pacote/modulo "x.y"
                t = relative_to_node_id(node.level, node.module, src_path)
                if t:
                    targets.append(t)
                # Aresta 2 (correcao do bug): para cada alias, se for
                # modulo filho, tambem registrar
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    t2 = relative_alias_to_node_id(
                        node.level, node.module, alias.name, src_path
                    )
                    if t2:
                        targets.append(t2)
            elif node.module and is_internal_module(node.module):
                # Import absoluto: from X import Y[, Z]
                # Aresta 1: para X (modulo ou pacote)
                t = module_to_node_id(node.module)
                if t:
                    targets.append(t)
                # Aresta 2 (correcao do bug): se Y e modulo filho de X,
                # adicionar aresta para X/Y.py
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    full = f"{node.module}.{alias.name}"
                    t2 = module_to_node_id(full)
                    if t2:
                        targets.append(t2)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if is_internal_module(alias.name):
                    t = module_to_node_id(alias.name)
                    if t:
                        targets.append(t)
    return sorted(set(targets))


def find_py_files(filter_fn) -> list[Path]:
    files: list[Path] = []
    for path in BACKEND_ROOT.rglob("*.py"):
        if filter_fn(path):
            files.append(path)
    return sorted(files)


def detectar_ciclos(arestas: list[tuple[str, str]]) -> list[list[str]]:
    grafo = defaultdict(set)
    nos = set()
    for de, para in arestas:
        grafo[de].add(para)
        nos.add(de)
        nos.add(para)
    BRANCO, CINZA, PRETO = 0, 1, 2
    cor = {n: BRANCO for n in nos}
    pilha: list[str] = []
    ciclos: list[list[str]] = []

    def dfs(u: str) -> None:
        cor[u] = CINZA
        pilha.append(u)
        for v in sorted(grafo[u]):
            if cor[v] == CINZA:
                if v in pilha:
                    idx = pilha.index(v)
                    ciclo = pilha[idx:] + [v]
                    if ciclo not in ciclos:
                        ciclos.append(ciclo)
            elif cor[v] == BRANCO:
                dfs(v)
        pilha.pop()
        cor[u] = PRETO

    for n in sorted(nos):
        if cor[n] == BRANCO:
            dfs(n)
    return ciclos


def construir_grafo(arquivos: list[Path], escopo: set[str]) -> dict:
    """
    Constroi grafo. arestas so contam quando AMBOS de e para estao em `escopo`.
    Mas se a aresta vai para um node fora do escopo, ainda assim eh contada
    para nao perder visibilidade — vamos manter ambos os comportamentos:
      - in_degree de um node so conta arestas vindas de arquivos no escopo
      - mas nao filtramos arestas que apontam para FORA do escopo (raras)
    """
    nos_set = {to_node_id(p) for p in arquivos}
    arestas: list[tuple[str, str]] = []
    in_degree: dict[str, int] = defaultdict(int)
    out_degree: dict[str, int] = defaultdict(int)
    in_neighbors: dict[str, set[str]] = defaultdict(set)
    out_neighbors: dict[str, set[str]] = defaultdict(set)

    # Garantir 0-init para todos nos
    for n in nos_set:
        in_degree[n] = 0
        out_degree[n] = 0

    for src in arquivos:
        sid = to_node_id(src)
        for did in extract_imports(src):
            arestas.append((sid, did))
            out_degree[sid] = out_degree.get(sid, 0) + 1
            out_neighbors[sid].add(did)
            # in_degree so conta para nodes no escopo
            if did in nos_set:
                in_degree[did] = in_degree.get(did, 0) + 1
                in_neighbors[did].add(sid)

    todos = sorted(nos_set | {de for de, _ in arestas} | {para for _, para in arestas})
    return {
        "nos_escopo": sorted(nos_set),
        "todos_nos": todos,
        "arestas": arestas,
        "in_degree": dict(in_degree),
        "out_degree": dict(out_degree),
        "in_neighbors": {k: sorted(v) for k, v in in_neighbors.items()},
        "out_neighbors": {k: sorted(v) for k, v in out_neighbors.items()},
    }


def serializar_json(grafo: dict, nome_recorte: str) -> Path:
    payload = {
        "recorte": nome_recorte,
        "nos": grafo["nos_escopo"],
        "todos_nos_referenciados": grafo["todos_nos"],
        "arestas": [{"de": d, "para": p} for d, p in grafo["arestas"]],
        "estatisticas": {
            "total_arquivos": len(grafo["nos_escopo"]),
            "total_arestas": len(grafo["arestas"]),
            "in_degree": dict(sorted(grafo["in_degree"].items())),
            "out_degree": dict(sorted(grafo["out_degree"].items())),
        },
        "entry_points": sorted(ENTRY_POINTS),
    }
    out = OUT_DIR / f"grafo_dependencias_{nome_recorte}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def render_md_secao(linhas: list[str], titulo: str, grafo: dict) -> None:
    nos = grafo["nos_escopo"]
    arestas = grafo["arestas"]
    in_deg = grafo["in_degree"]
    out_deg = grafo["out_degree"]
    in_neighbors = grafo["in_neighbors"]

    ciclos = detectar_ciclos(arestas)
    sem_in = sorted([n for n in nos if in_deg.get(n, 0) == 0])
    um_in = sorted([n for n in nos if in_deg.get(n, 0) == 1])
    isolados = sorted([n for n in nos if in_deg.get(n, 0) == 0 and out_deg.get(n, 0) == 0])

    # Marcar entry-points em sem_in
    sem_in_no_ep = [n for n in sem_in if n not in ENTRY_POINTS]

    linhas.append(f"## {titulo}\n")
    linhas.append(f"- Total de arquivos .py mapeados: **{len(nos)}**")
    linhas.append(f"- Total de arestas (imports internos): **{len(arestas)}**")
    linhas.append(f"- Imports circulares detectados: **{len(ciclos)}**")
    linhas.append(f"- Arquivos sem in-degree (orfaos): **{len(sem_in)}**")
    linhas.append(f"  - dos quais entry-points (esperado): **{len(sem_in) - len(sem_in_no_ep)}**")
    linhas.append(f"  - dos quais NAO entry-points (suspeitos): **{len(sem_in_no_ep)}**")
    linhas.append(f"- Arquivos com in-degree=1: **{len(um_in)}**")
    linhas.append(f"- Modulos isolados (in=0 E out=0): **{len(isolados)}**\n")

    top_in = sorted(in_deg.items(), key=lambda x: (-x[1], x[0]))[:10]
    top_out = sorted(out_deg.items(), key=lambda x: (-x[1], x[0]))[:10]

    linhas.append(f"### Top 10 Mais Importados ({titulo})\n")
    linhas.append("| Arquivo | in-degree |")
    linhas.append("| --- | --- |")
    for n, d in top_in:
        linhas.append(f"| `{n}` | {d} |")
    linhas.append("")

    linhas.append(f"### Top 10 Que Mais Importam ({titulo})\n")
    linhas.append("| Arquivo | out-degree |")
    linhas.append("| --- | --- |")
    for n, d in top_out:
        linhas.append(f"| `{n}` | {d} |")
    linhas.append("")

    linhas.append(f"### Imports Circulares ({titulo})\n")
    if not ciclos:
        linhas.append("Nenhum ciclo detectado.\n")
    else:
        for i, c in enumerate(ciclos, 1):
            linhas.append(f"#### Ciclo {i}")
            linhas.append("```")
            for node in c:
                linhas.append(node)
            linhas.append("```\n")

    linhas.append(f"### Arquivos sem In-Degree NAO entry-point ({titulo})\n")
    if not sem_in_no_ep:
        linhas.append("Nenhum.\n")
    else:
        linhas.append("Sao candidatos a dead code (validar em Fase 2/3).\n")
        for n in sem_in_no_ep:
            out = out_deg.get(n, 0)
            linhas.append(f"- `{n}` (out-degree={out})")
        linhas.append("")

    linhas.append(f"### Entry-points reconhecidos ({titulo})\n")
    eps_no_grafo = [n for n in sorted(ENTRY_POINTS) if n in nos]
    for n in eps_no_grafo:
        linhas.append(f"- `{n}` (in-degree={in_deg.get(n, 0)}, out-degree={out_deg.get(n, 0)})")
    linhas.append("")

    linhas.append(f"### Arquivos com In-Degree=1 ({titulo})\n")
    if not um_in:
        linhas.append("Nenhum.\n")
    else:
        for n in um_in:
            importadores = in_neighbors.get(n, [])
            imp_str = ", ".join(f"`{i}`" for i in importadores)
            linhas.append(f"- `{n}` <- {imp_str}")
        linhas.append("")

    linhas.append(f"### Modulos Isolados ({titulo})\n")
    if not isolados:
        linhas.append("Nenhum.\n")
    else:
        for n in isolados:
            linhas.append(f"- `{n}`")
        linhas.append("")


def render_comparativo(linhas: list[str], gp: dict, gc: dict) -> None:
    """Comparativo entre os dois recortes."""
    linhas.append("## Comparativo Producao vs Completo\n")
    linhas.append("Diferenca de in-degree por arquivo do recorte PRODUCAO:")
    linhas.append("quanto o teste/script adiciona aos consumidores do modulo.\n")
    linhas.append("Apenas arquivos onde in-degree(completo) > in-degree(producao)")
    linhas.append("(ou seja, sao consumidos por testes/scripts alem da producao).\n")
    linhas.append("| Arquivo | in-degree producao | in-degree completo | delta |")
    linhas.append("| --- | --- | --- | --- |")

    nos_prod = set(gp["nos_escopo"])
    deltas = []
    for n in sorted(nos_prod):
        ip = gp["in_degree"].get(n, 0)
        ic = gc["in_degree"].get(n, 0)
        if ic > ip:
            deltas.append((n, ip, ic, ic - ip))
    deltas.sort(key=lambda x: (-x[3], x[0]))
    for n, ip, ic, dl in deltas[:30]:
        linhas.append(f"| `{n}` | {ip} | {ic} | +{dl} |")
    if not deltas:
        linhas.append("| (nenhum) | | | |")
    linhas.append("")
    linhas.append(f"Total de arquivos producao com in-degree elevado por testes: **{len(deltas)}**\n")

    # Lista importante: arquivos producao com in-degree=0 NA PRODUCAO mas
    # in-degree>0 no completo (sao "vivos via teste")
    vivos_via_teste = [(n, ic) for n, ip, ic, _ in deltas if ip == 0 and ic > 0]
    linhas.append("### Arquivos Producao Vivos APENAS via Testes/Scripts\n")
    linhas.append("Aparecem orfaos no recorte producao mas sao referenciados no completo.")
    linhas.append("Atencao em Fase 2: NAO sao dead code, sao integration points de teste.\n")
    if not vivos_via_teste:
        linhas.append("Nenhum.\n")
    else:
        for n, ic in vivos_via_teste:
            linhas.append(f"- `{n}` (in-degree completo = {ic})")
        linhas.append("")


def main() -> None:
    arquivos_prod = find_py_files(file_eligible_producao)
    arquivos_compl = find_py_files(file_eligible_global)

    print(f"[audit_grafo] PRODUCAO: {len(arquivos_prod)} arquivos")
    print(f"[audit_grafo] COMPLETO: {len(arquivos_compl)} arquivos")

    gp = construir_grafo(arquivos_prod, escopo={to_node_id(p) for p in arquivos_prod})
    gc = construir_grafo(arquivos_compl, escopo={to_node_id(p) for p in arquivos_compl})

    pj = serializar_json(gp, "producao")
    cj = serializar_json(gc, "completo")
    print(f"[audit_grafo] {pj}")
    print(f"[audit_grafo] {cj}")

    linhas: list[str] = []
    linhas.append("# Grafo de Dependencias — S25 Fase 1\n")
    linhas.append("Gerado por `audit_grafo.py`. Read-only.\n")
    linhas.append("Dois recortes:\n")
    linhas.append("- **producao**: backend/main.py + services/ + routers/ + data/ + scripts/")
    linhas.append("- **completo**: producao + tests/ + tests_fase2/ + test_parsers.py raiz\n")
    linhas.append("Entry-points (in-degree=0 esperado por design):\n")
    for ep in sorted(ENTRY_POINTS):
        linhas.append(f"- `{ep}`")
    linhas.append("")

    render_md_secao(linhas, "Recorte PRODUCAO", gp)
    render_md_secao(linhas, "Recorte COMPLETO", gc)
    render_comparativo(linhas, gp, gc)

    out_md = OUT_DIR / "grafo_dependencias.md"
    out_md.write_text("\n".join(linhas), encoding="utf-8")
    print(f"[audit_grafo] {out_md}")

    print("---")
    print(f"PRODUCAO: {len(gp['nos_escopo'])} nos, {len(gp['arestas'])} arestas")
    print(f"COMPLETO: {len(gc['nos_escopo'])} nos, {len(gc['arestas'])} arestas")
    sem_in_prod_no_ep = [
        n for n in gp["nos_escopo"]
        if gp["in_degree"].get(n, 0) == 0 and n not in ENTRY_POINTS
    ]
    print(f"Producao sem in-degree NAO entry-point: {len(sem_in_prod_no_ep)}")


if __name__ == "__main__":
    main()
