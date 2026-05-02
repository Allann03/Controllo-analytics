"""
Audit S25 / Fase 4 — Codigo Duplicado.

Detecta:
  1. Funcoes com nome identico em arquivos diferentes (do mesmo dominio
     ou nao)
  2. Blocos de >=10 linhas identicos entre arquivos (compare normalizado:
     strip + ignorar comentarios/docstrings/whitespace excedente)
  3. Constantes/regex/strings literais duplicadas entre parsers
  4. Imports identicos repetidos em multiplos arquivos (sinaliza heranca
     comum candidata a base.py)

Saida: codigo_duplicado.md
"""
from __future__ import annotations

import ast
import hashlib
import re
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"
OUT_DIR = BACKEND_ROOT / "tests" / "auditoria_s25"

EXCLUDE_PARTS = {
    "__pycache__", "venv", "node_modules",
    "auditoria_s23", "auditoria_s24", "auditoria_s25",
    "tests_fase2",
}

PARSERS_DIR = BACKEND_ROOT / "services" / "parsers"


def list_py_files(include_tests: bool = False) -> list[Path]:
    files: list[Path] = []
    for path in BACKEND_ROOT.rglob("*.py"):
        parts = set(path.parts)
        if parts & EXCLUDE_PARTS:
            continue
        if not include_tests and ("tests" in parts or "tests_fase2" in parts):
            continue
        files.append(path)
    return sorted(files)


def to_rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def extract_function_defs(path: Path) -> list[tuple[str, int, int, str]]:
    """
    Retorna [(nome_funcao, linha_inicio, linha_fim, hash_corpo)] para
    cada funcao publica + privada do arquivo.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    if not source.strip():
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out: list[tuple[str, int, int, str]] = []
    lines = source.splitlines()

    def walk(node, klass: str | None = None) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = child.lineno
                end = child.end_lineno or start
                body_lines = lines[start - 1:end]
                normalized = normalize_body(body_lines)
                h = hashlib.md5(normalized.encode("utf-8")).hexdigest()
                full_name = f"{klass}.{child.name}" if klass else child.name
                out.append((full_name, start, end, h))
                walk(child, klass)
            elif isinstance(child, ast.ClassDef):
                walk(child, child.name)
            else:
                walk(child, klass)

    walk(tree)
    return out


def normalize_body(lines: list[str]) -> str:
    """
    Normaliza corpo de funcao: remove docstring, comments, whitespace
    excedente. Resultado: hash robusto a reformatacoes triviais.
    """
    cleaned: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        # tira inline comment
        idx = s.find("#")
        if idx > 0:
            # mas cuidado com hash em string — heuristica: se tiver aspas antes do #
            quote_count = s[:idx].count("'") + s[:idx].count('"')
            if quote_count % 2 == 0:
                s = s[:idx].rstrip()
        cleaned.append(s)
    # Tirar docstring se for primeira linha apos def
    if len(cleaned) >= 2:
        # heuristica: se segunda linha (apos def) for triple-string, considerar docstring
        body = "\n".join(cleaned)
        # nao removeremos docstring de fato — apenas normalizacao basica
    return "\n".join(cleaned)


def find_duplicate_functions(files: list[Path]) -> dict:
    """
    Retorna duas estruturas:
      - same_name: nome -> [(arquivo, linha_inicio, linha_fim, hash)]
      - same_body: hash -> [(arquivo, nome, linha_inicio, linha_fim)]
    """
    by_name: dict[str, list[tuple[str, int, int, str]]] = defaultdict(list)
    by_hash: dict[str, list[tuple[str, str, int, int]]] = defaultdict(list)

    for f in files:
        rel = to_rel(f)
        for nome, ini, fim, h in extract_function_defs(f):
            by_name[nome].append((rel, ini, fim, h))
            by_hash[h].append((rel, nome, ini, fim))

    duplicates_name = {n: locs for n, locs in by_name.items() if len(locs) > 1}
    duplicates_body = {h: locs for h, locs in by_hash.items() if len(locs) > 1}
    return {"by_name": duplicates_name, "by_body": duplicates_body}


def find_constant_duplicates(files: list[Path]) -> dict:
    """
    Detecta constantes/regex/strings literais duplicadas.

    Heuristica:
      - Linhas que casam r'^([A-Z_][A-Z0-9_]*)\\s*=' (constantes ALL-CAPS)
      - Capturar valor literal e nome
      - Agrupar por valor
    """
    pattern_const = re.compile(r"^([A-Z_][A-Z0-9_]*)\s*[:=]\s*(.+)$")
    by_value: dict[str, list[tuple[str, str, int]]] = defaultdict(list)

    for f in files:
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for i, raw in enumerate(lines, 1):
            line = raw.strip()
            m = pattern_const.match(line)
            if not m:
                continue
            name, val = m.group(1), m.group(2).strip()
            # Filtrar valores triviais
            if len(val) < 4:
                continue
            if val.startswith("(") or val.startswith("[") or val.startswith("{"):
                # estrutura — skip (multilinha em geral)
                continue
            by_value[val].append((to_rel(f), name, i))

    duplicates = {v: locs for v, locs in by_value.items() if len(locs) > 1}
    return duplicates


def hash_block(lines: list[str]) -> str:
    return hashlib.md5("\n".join(lines).encode("utf-8")).hexdigest()


def find_duplicate_blocks(files: list[Path], min_lines: int = 10) -> dict:
    """
    Procura blocos de >=min_lines linhas identicas entre arquivos.

    Implementacao naive: para cada arquivo, gerar todas as janelas de
    `min_lines` linhas (apos normalizacao basica), agrupar por hash.
    """
    by_hash: dict[str, list[tuple[str, int, int]]] = defaultdict(list)

    for f in files:
        try:
            raw = f.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        # Normalizar: strip + ignorar linhas em branco + tirar comentarios
        normalized: list[tuple[int, str]] = []
        for i, l in enumerate(raw, 1):
            s = l.strip()
            if not s or s.startswith("#"):
                continue
            normalized.append((i, s))

        for j in range(0, len(normalized) - min_lines + 1):
            window = normalized[j:j + min_lines]
            content = "\n".join(s for _, s in window)
            # filtros para evitar ruido:
            if content.count("\n") < min_lines - 1:
                continue
            # se mais de metade das linhas e vazia/comentario, skip (ja cuidado por filtro)
            h = hash_block([s for _, s in window])
            ini = window[0][0]
            fim = window[-1][0]
            by_hash[h].append((to_rel(f), ini, fim))

    # Pegar so onde ha pelo menos 2 arquivos diferentes
    duplicates: dict[str, list[tuple[str, int, int]]] = {}
    for h, locs in by_hash.items():
        arquivos_distintos = {l[0] for l in locs}
        if len(arquivos_distintos) >= 2:
            duplicates[h] = locs
    return duplicates


def find_parser_specific_duplicates() -> dict:
    """
    Analise focada em backend/services/parsers/ — busca patterns que
    poderiam ser extraidos para base.py:
      - Regexes no topo do arquivo (REGEX_*, RE_*, _RE_*, etc)
      - Constantes de meses, formatos de data, etc
    """
    parsers_files = [p for p in list_py_files() if PARSERS_DIR in p.parents]
    regex_pattern = re.compile(r"^(_?[A-Z_][A-Z0-9_]*)\s*=\s*re\.compile\((.+)\)")
    by_regex_pattern: dict[str, list[tuple[str, str, int]]] = defaultdict(list)

    for f in parsers_files:
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for i, raw in enumerate(lines, 1):
            line = raw.strip()
            m = regex_pattern.match(line)
            if not m:
                continue
            name, val = m.group(1), m.group(2).strip()
            by_regex_pattern[val].append((to_rel(f), name, i))

    return {v: locs for v, locs in by_regex_pattern.items() if len(locs) > 1}


def main() -> None:
    files = list_py_files(include_tests=False)
    print(f"[audit_duplicado] {len(files)} arquivos producao")

    print("[audit_duplicado] funcoes duplicadas...")
    dup_funcs = find_duplicate_functions(files)
    print(f"  - mesmo nome em arquivos diferentes: {len(dup_funcs['by_name'])}")
    print(f"  - mesmo corpo (hash MD5): {len(dup_funcs['by_body'])}")

    print("[audit_duplicado] constantes duplicadas...")
    dup_consts = find_constant_duplicates(files)
    print(f"  - constantes com mesmo valor: {len(dup_consts)}")

    print("[audit_duplicado] blocos identicos (>=10 linhas)...")
    dup_blocks = find_duplicate_blocks(files, min_lines=10)
    print(f"  - blocos: {len(dup_blocks)}")

    print("[audit_duplicado] regex duplicadas em parsers...")
    dup_regex = find_parser_specific_duplicates()
    print(f"  - regex compartilhadas: {len(dup_regex)}")

    # ========= Markdown =========
    linhas: list[str] = []
    linhas.append("# Codigo Duplicado — S25 Fase 4\n")
    linhas.append("Audit estrutural sobre `backend/` (exceto tests/, venv, auditorias antigas).\n")

    # Sumario
    linhas.append("## Sumario\n")
    linhas.append(f"- Total arquivos producao analisados: **{len(files)}**")
    linhas.append(f"- Funcoes com mesmo nome em arquivos diferentes: **{len(dup_funcs['by_name'])}**")
    linhas.append(f"- Funcoes com corpo identico (hash MD5): **{len(dup_funcs['by_body'])}**")
    linhas.append(f"- Constantes ALL-CAPS com mesmo valor: **{len(dup_consts)}**")
    linhas.append(f"- Blocos >=10 linhas identicas: **{len(dup_blocks)}**")
    linhas.append(f"- Regex compartilhadas entre parsers: **{len(dup_regex)}**\n")

    # 1. Funcoes mesmo nome
    linhas.append("## 1. Funcoes com Mesmo Nome em Arquivos Diferentes\n")
    if not dup_funcs["by_name"]:
        linhas.append("Nenhuma.\n")
    else:
        # Filtrar nomes triviais (dunders, _init_, etc)
        triviais = {"__init__", "__repr__", "__str__", "__eq__", "__hash__",
                    "extrair", "extrair_transacoes", "salvar", "main"}
        relevantes = {n: locs for n, locs in dup_funcs["by_name"].items() if n not in triviais}
        linhas.append("(Filtrando metodos comuns como `__init__`, `extrair`, `main`.)\n")
        linhas.append(f"Total relevante: **{len(relevantes)}**\n")
        for nome in sorted(relevantes.keys()):
            locs = relevantes[nome]
            # Marcador: se hash do corpo coincide entre todos, e copy-paste literal
            hashes = {l[3] for l in locs}
            marca = "**[CORPO IDENTICO]**" if len(hashes) == 1 else "(corpos diferentes)"
            linhas.append(f"- `{nome}` {marca}")
            for arq, ini, fim, h in locs:
                linhas.append(f"  - `{arq}:{ini}-{fim}`")
        linhas.append("")

    # 2. Funcoes mesmo corpo
    linhas.append("## 2. Funcoes com Corpo Identico (hash MD5)\n")
    if not dup_funcs["by_body"]:
        linhas.append("Nenhuma.\n")
    else:
        # Filtrar bodies triviais (1-2 linhas)
        for h, locs in sorted(dup_funcs["by_body"].items()):
            if len(locs) < 2:
                continue
            # Pega tamanho do corpo (uma das ocorrencias) — calcular via primeira
            arq, nome, ini, fim = locs[0]
            tamanho = fim - ini + 1
            if tamanho < 5:
                continue  # filtrar funcoes muito pequenas
            linhas.append(f"### Hash `{h[:8]}` — {tamanho} linhas")
            for arq, nome, ini, fim in locs:
                linhas.append(f"- `{arq}:{ini}-{fim}` — funcao `{nome}`")
            linhas.append("")

    # 3. Constantes
    linhas.append("## 3. Constantes ALL-CAPS Duplicadas\n")
    if not dup_consts:
        linhas.append("Nenhuma.\n")
    else:
        # Mostrar apenas top 30
        items = sorted(dup_consts.items(), key=lambda x: -len(x[1]))[:30]
        for val, locs in items:
            preview = val[:80] + ("..." if len(val) > 80 else "")
            linhas.append(f"### Valor: `{preview}`")
            for arq, name, lin in locs:
                linhas.append(f"- `{arq}:{lin}` — `{name}`")
            linhas.append("")

    # 4. Blocos
    linhas.append("## 4. Blocos >=10 Linhas Identicas Entre Arquivos\n")
    if not dup_blocks:
        linhas.append("Nenhum.\n")
    else:
        # Reduzir: blocos overlap entre si dao muito ruido. Pegar os UNICOS
        # com no minimo 2 arquivos diferentes.
        # Mostrar top 20.
        items = sorted(dup_blocks.items(), key=lambda x: -len(x[1]))[:20]
        for h, locs in items:
            arquivos = sorted({l[0] for l in locs})
            if len(arquivos) < 2:
                continue
            linhas.append(f"### Bloco `{h[:8]}` — {len(arquivos)} arquivos")
            for arq, ini, fim in locs[:6]:
                linhas.append(f"- `{arq}:{ini}-{fim}`")
            if len(locs) > 6:
                linhas.append(f"- ... +{len(locs) - 6} ocorrencias")
            linhas.append("")

    # 5. Regex parsers
    linhas.append("## 5. Regex Compartilhadas Entre Parsers\n")
    if not dup_regex:
        linhas.append("Nenhuma.\n")
    else:
        for val, locs in sorted(dup_regex.items(), key=lambda x: -len(x[1])):
            preview = val[:100] + ("..." if len(val) > 100 else "")
            linhas.append(f"### Padrao: `{preview}`")
            for arq, name, lin in locs:
                linhas.append(f"- `{arq}:{lin}` — `{name}`")
            linhas.append("")

    # 6. Recomendacoes
    linhas.append("## 6. Recomendacoes (analise manual)\n")
    linhas.append("Para cada caso acima, decisao:")
    linhas.append("- **EXTRAIR**: mover para utilitario comum (ex: `parsers/base.py`)")
    linhas.append("- **MANTER**: especializacao por banco que parece igual mas vai divergir")
    linhas.append("- **INVESTIGAR**: caso ambiguo, decisao manual\n")
    linhas.append("Estas recomendacoes serao refinadas apos analise dos achados acima.\n")

    out_md = OUT_DIR / "codigo_duplicado.md"
    out_md.write_text("\n".join(linhas), encoding="utf-8")
    print(f"[audit_duplicado] {out_md}")


if __name__ == "__main__":
    main()
