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
