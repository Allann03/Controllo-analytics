"""
Teste ad-hoc do extrator de imports do audit_grafo.py.

Cria um mini-projeto em tempfile, roda extract_imports e valida que os
4 cenarios criticos sao detectados:

  1. from PACOTE import MODULO_FILHO    -> aresta para MODULO_FILHO.py
  2. from PACOTE.MODULO import simbolo  -> aresta para MODULO.py
  3. lazy import dentro de funcao       -> aresta detectada
  4. from . import X (relativo)         -> aresta detectada

Uso: python backend/tests/auditoria_s25/audit_grafo_test.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path


# Importar o modulo audit_grafo via path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_grafo  # noqa: E402


def assert_contains(targets: list[str], substr: str, label: str) -> None:
    if not any(substr in t for t in targets):
        print(f"  FAIL [{label}]: '{substr}' nao encontrado em {targets}")
        sys.exit(1)
    print(f"  OK   [{label}]: contem '{substr}'")


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Estrutura
        (root / "services").mkdir()
        (root / "services" / "__init__.py").write_text("", encoding="utf-8")
        (root / "services" / "foo.py").write_text(
            "def hello(): return 1\n", encoding="utf-8"
        )
        (root / "services" / "bar.py").write_text(
            "from services import foo\n", encoding="utf-8"
        )
        (root / "main.py").write_text(
            "from services.foo import hello\n", encoding="utf-8"
        )
        (root / "lazy.py").write_text(
            "def func():\n    from services import foo\n    return foo.hello()\n",
            encoding="utf-8",
        )
        # Pacote relativo
        (root / "pkg").mkdir()
        (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (root / "pkg" / "x.py").write_text("def y(): pass\n", encoding="utf-8")
        (root / "pkg" / "consumer.py").write_text(
            "from . import x\n", encoding="utf-8"
        )

        # Hack: temporariamente apontar audit_grafo para esse root
        original_root = audit_grafo.PROJECT_ROOT
        original_backend = audit_grafo.BACKEND_ROOT
        audit_grafo.PROJECT_ROOT = root
        audit_grafo.BACKEND_ROOT = root  # mesma raiz para testes

        # Permitir que o filtro is_internal_module aceite "services" e "pkg"
        # (ja aceita pelo conjunto fixo no extractor)

        try:
            print("Cenario 1: from services import foo (modulo filho)")
            t = audit_grafo.extract_imports(root / "services" / "bar.py")
            print(f"  imports detectados: {t}")
            assert_contains(t, "services/foo.py", "modulo filho")

            print("Cenario 2: from services.foo import hello")
            t = audit_grafo.extract_imports(root / "main.py")
            print(f"  imports detectados: {t}")
            assert_contains(t, "services/foo.py", "from X.Y import Z")

            print("Cenario 3: lazy import dentro de funcao")
            t = audit_grafo.extract_imports(root / "lazy.py")
            print(f"  imports detectados: {t}")
            assert_contains(t, "services/foo.py", "lazy import")

            print("Cenario 4: from . import x (relativo)")
            t = audit_grafo.extract_imports(root / "pkg" / "consumer.py")
            print(f"  imports detectados: {t}")
            assert_contains(t, "pkg/x.py", "relativo")
        finally:
            audit_grafo.PROJECT_ROOT = original_root
            audit_grafo.BACKEND_ROOT = original_backend

    print("\n[audit_grafo_test] TODOS OS CENARIOS PASSARAM")


if __name__ == "__main__":
    main()
