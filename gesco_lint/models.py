"""Familia GES2: convenciones de modelos Django.

Detecta `db_index` en el campo (índices van en Meta.indexes) y `unique=True` en el campo
(unicidad va en Meta.constraints con UniqueConstraint).
"""

import ast
from collections.abc import Iterator
from importlib.metadata import version
from pathlib import Path

DB_INDEX = "GES211 db_index en el campo: declara el índice en Meta.indexes (django-model-indexes)"
UNIQUE_FIELD = "GES221 unique=True en el campo: declara UniqueConstraint en Meta.constraints (django-models)"


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _is_field_call(node: ast.Call) -> bool:
    name = _call_name(node=node)
    return name.endswith("Field") or name == "ForeignKey"


def _is_migration(*, filename: str) -> bool:
    return "migrations" in Path(filename).parts


class DjangoModelsVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.found: list[tuple[ast.AST, str]] = []

    def _add(self, *, node: ast.AST, message: str) -> None:
        self.found.append((node, message))

    def visit_Call(self, node: ast.Call) -> None:
        if not _is_field_call(node=node):
            self.generic_visit(node)
            return
        for keyword in node.keywords:
            if (
                keyword.arg == "db_index"
                and isinstance(keyword.value, ast.Constant)
                and type(keyword.value.value) is bool
            ):
                self._add(node=keyword.value, message=DB_INDEX)
            if keyword.arg == "unique" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                self._add(node=keyword.value, message=UNIQUE_FIELD)
        self.generic_visit(node)


class DjangoModelsChecker:
    name = "gesco-lint-models"
    version = version("gesco-lint")

    def __init__(self, tree: ast.AST, filename: str) -> None:
        self.tree = tree
        self.filename = filename

    def run(self) -> Iterator[tuple[int, int, str, type]]:
        if _is_migration(filename=self.filename):
            return
        visitor = DjangoModelsVisitor()
        visitor.visit(self.tree)
        for node, message in visitor.found:
            yield node.lineno, node.col_offset, message, type(self)
