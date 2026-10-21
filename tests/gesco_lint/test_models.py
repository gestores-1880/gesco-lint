import ast
import textwrap

from gesco_lint.models import DjangoModelsChecker


def _violations(*, source: str, filename: str = "models.py") -> list[tuple[int, str]]:
    checker = DjangoModelsChecker(tree=ast.parse(textwrap.dedent(source)), filename=filename)
    return [(line, message.split(" ", 1)[0]) for line, _, message, _ in checker.run()]


def test_db_index_true_en_campo():
    source = """
    class Log(models.Model):
        caller = models.CharField(max_length=200, db_index=True)
    """
    assert _violations(source=source) == [(3, "GES211")]


def test_db_index_false_tambien_reporta():
    source = """
    class Log(models.Model):
        caller = models.CharField(max_length=200, db_index=False)
    """
    assert _violations(source=source) == [(3, "GES211")]


def test_indice_en_meta_no_reporta():
    source = """
    class Log(models.Model):
        caller = models.CharField(max_length=200)

        class Meta:
            indexes = [models.Index(fields=["caller"], name="log_caller_idx")]
    """
    assert _violations(source=source) == []


def test_unique_true_en_campo():
    source = """
    class Convenio(models.Model):
        codigo = models.CharField(max_length=20, unique=True)
    """
    assert _violations(source=source) == [(3, "GES221")]


def test_unique_constraint_en_meta_no_reporta():
    source = """
    class Convenio(models.Model):
        codigo = models.CharField(max_length=20)

        class Meta:
            constraints = [
                models.UniqueConstraint(fields=["codigo"], name="convenio_unique_codigo"),
            ]
    """
    assert _violations(source=source) == []


def test_unique_false_no_reporta():
    source = """
    class Convenio(models.Model):
        codigo = models.CharField(max_length=20, unique=False)
    """
    assert _violations(source=source) == []


def test_foreign_key_con_db_index():
    source = """
    class Linea(models.Model):
        pedido = models.ForeignKey("Pedido", on_delete=models.CASCADE, db_index=True)
    """
    assert _violations(source=source) == [(3, "GES211")]


def test_llamada_que_no_es_campo_no_reporta():
    source = """
    def create_user(**kwargs):
        return User.objects.create(unique=True, db_index=True)
    """
    assert _violations(source=source) == []


def test_migracion_no_reporta():
    source = """
    migrations.AlterField(
        model_name="log",
        name="caller",
        field=models.CharField(max_length=200, db_index=True, unique=True),
    )
    """
    assert _violations(source=source, filename="app/migrations/0001_initial.py") == []


def test_ambos_en_el_mismo_campo():
    source = """
    class Log(models.Model):
        codigo = models.CharField(max_length=20, unique=True, db_index=True)
    """
    assert _violations(source=source) == [(3, "GES221"), (3, "GES211")]
