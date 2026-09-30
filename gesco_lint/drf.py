"""Familia GES1: convenciones de API Django REST Framework.

Cada código cita el default que incumple (API-n). Detecta solo lo que es mecánico en el AST; la
salida con serializers (API-4), el uso del framework antes que mecanismos propios (API-6) y la
carga de relaciones (API-8) se revisan en el plan y en la review.
"""

import ast
from collections.abc import Iterator
from importlib.metadata import version
from pathlib import Path

DNI_CONTROL_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
QUERY_PARAMS_ALLOWED_MODULES = ("filters", "pagination")
RESPONSE_CLASS_SUFFIX = "Response"
IN_LOOKUP_SUFFIX = "__in"

HTTP_METHOD_NAMES = "GES111 http_method_names: los métodos los decide la composición de mixins (API-1)"
QUERY_PARAMS = "GES121 query_params leído a mano: declara un FilterSet (API-2)"
REQUEST_DATA = "GES131 request.data leído a mano: valida con un serializer (API-3)"
DNI_TABLE = "GES151 tabla de letras de control del DNI: usa la librería validators (API-5)"
STATUS_LITERAL = "GES171 código HTTP literal: usa rest_framework.status o http.HTTPStatus (API-7)"
METHOD_LITERAL = "GES172 método HTTP literal: usa http.HTTPMethod o SAFE_METHODS (API-7)"
MATERIALIZED_IN = "GES181 colección materializada en un lookup __in: compón querysets (API-8)"
PAGINATION_NONE = "GES191 pagination_class = None: pagina o declara la excepción con noqa y motivo (API-9)"


def _is_int_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and type(node.value) is int


def _is_str_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _is_str_collection(node: ast.AST) -> bool:
    if not isinstance(node, (ast.Tuple, ast.List, ast.Set)) or not node.elts:
        return False
    return all(_is_str_literal(node=element) for element in node.elts)


def _is_attribute(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == name


def _is_request_data(node: ast.AST) -> bool:
    if not _is_attribute(node=node, name="data"):
        return False
    owner = node.value
    return (isinstance(owner, ast.Name) and owner.id == "request") or _is_attribute(node=owner, name="request")


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _assigned_names(node: ast.stmt) -> list[str]:
    if isinstance(node, ast.Assign):
        return [target.id for target in node.targets if isinstance(target, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


def _assigns_none(node: ast.stmt) -> bool:
    if not isinstance(node, (ast.Assign, ast.AnnAssign)):
        return False
    return isinstance(node.value, ast.Constant) and node.value.value is None


class DrfApiVisitor(ast.NodeVisitor):
    def __init__(self, *, check_query_params: bool) -> None:
        self.check_query_params = check_query_params
        self.found: list[tuple[ast.AST, str]] = []

    def _add(self, *, node: ast.AST, message: str) -> None:
        self.found.append((node, message))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for statement in node.body:
            names = _assigned_names(node=statement)
            if "http_method_names" in names:
                self._add(node=statement, message=HTTP_METHOD_NAMES)
            if "pagination_class" in names and _assigns_none(node=statement):
                self._add(node=statement, message=PAGINATION_NONE)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        operands = [node.left, *node.comparators]
        if any(_is_attribute(node=operand, name="status_code") for operand in operands) and any(
            _is_int_literal(node=operand) for operand in operands
        ):
            self._add(node=node, message=STATUS_LITERAL)
        if any(_is_attribute(node=operand, name="method") for operand in operands) and any(
            _is_str_literal(node=operand) or _is_str_collection(node=operand) for operand in operands
        ):
            self._add(node=node, message=METHOD_LITERAL)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        is_response = _call_name(node=node).endswith(RESPONSE_CLASS_SUFFIX)
        for keyword in node.keywords:
            if is_response and keyword.arg == "status" and _is_int_literal(node=keyword.value):
                self._add(node=keyword.value, message=STATUS_LITERAL)
            if keyword.arg is None or not keyword.arg.endswith(IN_LOOKUP_SUFFIX):
                continue
            if isinstance(keyword.value, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
                self._add(node=keyword.value, message=MATERIALIZED_IN)
        if _is_attribute(node=node.func, name="get") and _is_request_data(node=node.func.value):
            self._add(node=node, message=REQUEST_DATA)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if _is_request_data(node=node.value):
            self._add(node=node, message=REQUEST_DATA)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if self.check_query_params and node.attr == "query_params":
            self._add(node=node, message=QUERY_PARAMS)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if node.value == DNI_CONTROL_LETTERS:
            self._add(node=node, message=DNI_TABLE)


class DrfApiChecker:
    name = "gesco-lint-drf"
    version = version("gesco-lint")

    def __init__(self, tree: ast.AST, filename: str) -> None:
        self.tree = tree
        self.filename = filename

    def run(self) -> Iterator[tuple[int, int, str, type]]:
        stem = Path(self.filename).stem
        visitor = DrfApiVisitor(check_query_params=not any(module in stem for module in QUERY_PARAMS_ALLOWED_MODULES))
        visitor.visit(self.tree)
        for node, message in visitor.found:
            yield node.lineno, node.col_offset, message, type(self)
