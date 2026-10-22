import ast
import textwrap

from gesco_lint.migrations import DjangoMigrationsChecker


def _violations(*, source: str, filename: str = "app/migrations/0001_data.py") -> list[tuple[int, str]]:
    checker = DjangoMigrationsChecker(tree=ast.parse(textwrap.dedent(source)), filename=filename)
    return [(line, message.split(" ", 1)[0]) for line, _, message, _ in checker.run()]


def test_runpython_sin_elidable_reporta():
    source = """
    operations = [
        migrations.RunPython(populate, migrations.RunPython.noop),
    ]
    """
    assert _violations(source=source) == [(3, "GES311")]


def test_runpython_con_elidable_false_no_reporta():
    source = """
    operations = [
        migrations.RunPython(populate, migrations.RunPython.noop, elidable=False),
    ]
    """
    assert _violations(source=source) == []


def test_runpython_con_elidable_true_no_reporta():
    source = """
    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop, elidable=True),
    ]
    """
    assert _violations(source=source) == []


def test_runpython_importado_sin_elidable_reporta():
    source = """
    from django.db.migrations import RunPython

    operations = [
        RunPython(populate, RunPython.noop),
    ]
    """
    assert _violations(source=source) == [(5, "GES311")]


def test_fuera_de_migrations_no_reporta():
    source = """
    migrations.RunPython(populate, migrations.RunPython.noop)
    """
    assert _violations(source=source, filename="app/management/commands/seed.py") == []


def test_import_modelo_en_runpython_reporta():
    source = """
    def populate(apps, schema_editor):
        from myapp.models import CustomField
        CustomField.objects.all()

    operations = [
        migrations.RunPython(populate, migrations.RunPython.noop, elidable=False),
    ]
    """
    assert _violations(source=source) == [(3, "GES321")]


def test_import_modelo_relativo_en_runpython_reporta():
    source = """
    def backfill(apps, schema_editor):
        from .models import Invoice
        Invoice.objects.filter(active=True)

    operations = [
        migrations.RunPython(code=backfill, reverse_code=migrations.RunPython.noop, elidable=False),
    ]
    """
    assert _violations(source=source) == [(3, "GES321")]


def test_apps_get_model_no_reporta():
    source = """
    def populate(apps, schema_editor):
        CustomField = apps.get_model("myapp", "CustomField")
        CustomField.objects.all()

    operations = [
        migrations.RunPython(populate, migrations.RunPython.noop, elidable=False),
    ]
    """
    assert _violations(source=source) == []


def test_import_modelo_fuera_de_runpython_no_reporta():
    source = """
    from myapp.models import CustomField

    def populate(apps, schema_editor):
        CustomField = apps.get_model("myapp", "CustomField")
        CustomField.objects.all()

    operations = [
        migrations.RunPython(populate, migrations.RunPython.noop, elidable=False),
    ]
    """
    assert _violations(source=source) == []


def test_import_modelo_en_reverse_tambien_reporta():
    source = """
    def forwards(apps, schema_editor):
        Model = apps.get_model("myapp", "Thing")
        Model.objects.all()

    def backwards(apps, schema_editor):
        from myapp.models import Thing
        Thing.objects.all()

    operations = [
        migrations.RunPython(forwards, backwards, elidable=False),
    ]
    """
    assert _violations(source=source) == [(7, "GES321")]
