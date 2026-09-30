import ast
import textwrap

from gesco_lint.drf import DrfApiChecker


def _violations(*, source: str, filename: str = "api.py") -> list[tuple[int, str]]:
    checker = DrfApiChecker(tree=ast.parse(textwrap.dedent(source)), filename=filename)
    return [(line, message.split(" ", 1)[0]) for line, _, message, _ in checker.run()]


def test_http_method_names_en_clase():
    source = """
    class ConceptoView(APIView):
        http_method_names = ["get", "post"]
    """
    assert _violations(source=source) == [(3, "GES111")]


def test_query_params_en_vista():
    source = """
    def get(self, request):
        return request.query_params.get("estado")
    """
    assert _violations(source=source) == [(3, "GES121")]


def test_query_params_pasados_al_serializer_no_reporta():
    source = """
    def get(self, request):
        filtros = DiarioFiltrosSerializer(data=request.query_params, context={"empresa": empresa})
        otros = MayorFiltrosSerializer(self.request.query_params)
    """
    assert _violations(source=source) == []


def test_query_params_por_clave_junto_al_serializer():
    source = """
    def get(self, request):
        filtros = DiarioFiltrosSerializer(data=request.query_params, context={"empresa": empresa})
        asiento = request.query_params.get("asiento")
        estado = self.request.query_params["estado"]
    """
    assert _violations(source=source) == [(4, "GES121"), (5, "GES121")]


def test_query_params_en_modulo_de_filtros_no_reporta():
    source = """
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(estado=request.query_params.get("estado"))
    """
    assert _violations(source=source, filename="contabilidad/asientos/filters.py") == []


def test_request_data_subscript_y_get():
    source = """
    def post(self, request):
        nombre = request.data["nombre"]
        codigo = self.request.data.get("codigo")
    """
    assert _violations(source=source) == [(3, "GES131"), (4, "GES131")]


def test_serializer_con_request_data_no_reporta():
    source = """
    def post(self, request):
        serializer = ConceptoSerializer(data=request.data)
    """
    assert _violations(source=source) == []


def test_tabla_de_letras_del_dni():
    source = """
    LETRAS = "TRWAGMYFPDXBNJZSQVHLCKE"
    """
    assert _violations(source=source) == [(2, "GES151")]


def test_status_code_literal_en_comparacion():
    source = """
    def test_alta(client):
        assert client.post("/api/").status_code == 201
    """
    assert _violations(source=source) == [(3, "GES171")]


def test_status_code_con_constante_no_reporta():
    source = """
    def test_alta(client):
        assert client.post("/api/").status_code == status.HTTP_201_CREATED
    """
    assert _violations(source=source) == []


def test_status_literal_en_response():
    source = """
    def post(self, request):
        return Response(data={}, status=201)
    """
    assert _violations(source=source) == [(3, "GES171")]


def test_status_en_filtro_del_orm_no_reporta():
    source = """
    Pedido.objects.filter(status=1)
    """
    assert _violations(source=source) == []


def test_method_literal_y_coleccion_de_metodos():
    source = """
    def get_permissions(self):
        if self.request.method == "POST":
            return []
        if self.request.method in ("PUT", "PATCH"):
            return []
    """
    assert _violations(source=source) == [(3, "GES172"), (5, "GES172")]


def test_method_con_safe_methods_no_reporta():
    source = """
    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return []
    """
    assert _violations(source=source) == []


def test_lookup_in_con_coleccion_materializada():
    source = """
    Empresa.objects.filter(id__in=[empresa.id for empresa in empresas])
    """
    assert _violations(source=source) == [(2, "GES181")]


def test_lookup_in_con_queryset_no_reporta():
    source = """
    Empresa.objects.filter(id__in=Empresa.objects.filter(gestoria=gestoria).values("id"))
    """
    assert _violations(source=source) == []


def test_pagination_class_none():
    source = """
    class EmpresaListView(ListAPIView):
        pagination_class = None
    """
    assert _violations(source=source) == [(3, "GES191")]


def test_pagination_class_con_clase_no_reporta():
    source = """
    class EmpresaListView(ListAPIView):
        pagination_class = LimitOffsetPagination
    """
    assert _violations(source=source) == []
