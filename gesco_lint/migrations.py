"""Familia GES3: convenciones de migraciones Django.

Detecta `RunPython` sin keyword `elidable=` y imports del modelo real dentro
de funciones usadas por `RunPython` (django-migrations).
"""

import ast
from collections.abc import Iterator
from importlib.metadata import version
from pathlib import Path

RUNPYTHON_ELIDABLE = (
    "GES311 RunPython sin elidable=: pasa elidable=False "
    "(o True solo si es relleno elidable en squash) (django-migrations)"
)
RUNPYTHON_MODEL_IMPORT = "GES321 import de modelo real en RunPython: usa apps.get_model (django-migrations)"


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _is_migration(*, filename: str) -> bool:
    return "migrations" in Path(filename).parts


def _has_elidable_keyword(node: ast.Call) -> bool:
    return any(keyword.arg == "elidable" for keyword in node.keywords)


def _is_models_import(node: ast.Import | ast.ImportFrom) -> bool:
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        return module == "models" or module.endswith(".models") or ".models." in module
    return any(alias.name == "models" or alias.name.endswith(".models") for alias in node.names)


def _runpython_callable_names(node: ast.Call) -> list[str]:
    names: list[str] = []
    for arg in node.args[:2]:
        if isinstance(arg, ast.Name):
            names.append(arg.id)
    for keyword in node.keywords:
        if keyword.arg in {"code", "reverse_code"} and isinstance(keyword.value, ast.Name):
            names.append(keyword.value.id)
    return names


class DjangoMigrationsVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.found: list[tuple[ast.AST, str]] = []
        self._functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self._runpython_callables: set[str] = set()

    def _add(self, *, node: ast.AST, message: str) -> None:
        self.found.append((node, message))

    def visit_Module(self, node: ast.Module) -> None:
        for statement in node.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._functions[statement.name] = statement
        self.generic_visit(node)
        self._check_model_imports()

    def visit_Call(self, node: ast.Call) -> None:
        if _call_name(node=node) == "RunPython":
            if not _has_elidable_keyword(node=node):
                self._add(node=node, message=RUNPYTHON_ELIDABLE)
            self._runpython_callables.update(_runpython_callable_names(node=node))
        self.generic_visit(node)

    def _check_model_imports(self) -> None:
        for name in self._runpython_callables:
            function = self._functions.get(name)
            if function is None:
                continue
            for child in ast.walk(function):
                if isinstance(child, (ast.Import, ast.ImportFrom)) and _is_models_import(node=child):
                    self._add(node=child, message=RUNPYTHON_MODEL_IMPORT)


class DjangoMigrationsChecker:
    name = "gesco-lint-migrations"
    version = version("gesco-lint")

    def __init__(self, tree: ast.AST, filename: str) -> None:
        self.tree = tree
        self.filename = filename

    def run(self) -> Iterator[tuple[int, int, str, type]]:
        if not _is_migration(filename=self.filename):
            return
        visitor = DjangoMigrationsVisitor()
        visitor.visit(self.tree)
        for node, message in visitor.found:
            yield node.lineno, node.col_offset, message, type(self)
