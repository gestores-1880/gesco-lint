import subprocess
import textwrap

import pytest

from gesco_lint.cli import main

GIT_IDENTITY = ("-c", "user.email=ci@gesco.test", "-c", "user.name=ci")

LEGACY = """\
class Legacy(APIView):
    http_method_names = ["get"]
"""

NEW_CODE = """\


class Nueva(ListAPIView):
    pagination_class = None  # noqa: GES191 catálogo acotado de 12 meses


def alta(request):
    return Response(data=request.data["nombre"], status=201)
"""


def _git(*args: str) -> None:
    subprocess.run(["git", *GIT_IDENTITY, *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PRE_COMMIT_FROM_REF", raising=False)
    _git("init", "-q")
    (tmp_path / "api.py").write_text(LEGACY)
    _git("add", ".")
    _git("commit", "-qm", "base")
    with (tmp_path / "api.py").open("a") as handle:
        handle.write(NEW_CODE)
    return tmp_path


def test_reporta_todo_el_fichero(repo, capsys):
    exit_code = main(argv=["api.py"])

    assert exit_code == 1
    assert capsys.readouterr().out.splitlines() == [
        "api.py:2:5: GES111 http_method_names: los métodos los decide la composición de mixins (API-1)",
        "api.py:10:26: GES131 request.data leído a mano: valida con un serializer (API-3)",
        "api.py:10:57: GES171 código HTTP literal: usa rest_framework.status o http.HTTPStatus (API-7)",
    ]


def test_diff_base_solo_reporta_lineas_nuevas(repo, capsys):
    exit_code = main(argv=["--diff-base", "HEAD", "api.py"])

    assert exit_code == 1
    assert capsys.readouterr().out.splitlines() == [
        "api.py:10:26: GES131 request.data leído a mano: valida con un serializer (API-3)",
        "api.py:10:57: GES171 código HTTP literal: usa rest_framework.status o http.HTTPStatus (API-7)",
    ]


def test_changed_only_toma_el_ref_de_pre_commit(repo, capsys, monkeypatch):
    _git("add", ".")
    _git("commit", "-qm", "nuevo")
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", "HEAD~1")

    exit_code = main(argv=["--changed-only", "api.py"])

    assert exit_code == 1
    assert capsys.readouterr().out.splitlines() == [
        "api.py:10:26: GES131 request.data leído a mano: valida con un serializer (API-3)",
        "api.py:10:57: GES171 código HTTP literal: usa rest_framework.status o http.HTTPStatus (API-7)",
    ]


def test_changed_only_sin_cambios_no_reporta(repo, capsys):
    _git("add", ".")
    _git("commit", "-qm", "nuevo")

    exit_code = main(argv=["--changed-only", "api.py"])

    assert exit_code == 0
    assert capsys.readouterr().out == ""


def test_fichero_limpio(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "api.py").write_text(
        textwrap.dedent(
            """\
            class Conceptos(ListAPIView):
                serializer_class = ConceptoSerializer
            """
        )
    )

    exit_code = main(argv=["api.py"])

    assert exit_code == 0
    assert capsys.readouterr().out == ""
