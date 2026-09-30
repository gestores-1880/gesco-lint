"""CLI `gesco-lint`: flake8 limitado a los códigos GES, con modo solo-diff.

Reutiliza flake8 para que `# noqa: GESnnn`, `per-file-ignores` y `exclude` del proyecto se apliquen
como en cualquier otro plugin. Con --diff-base (o --changed-only en pre-commit) solo reporta las
líneas añadidas o modificadas, para adoptar el linter en repos con código previo.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from gesco_lint.git_diff import changed_lines

CODE_PREFIX = "GES"
PRE_COMMIT_FROM_REF_ENV = "PRE_COMMIT_FROM_REF"
DEFAULT_DIFF_BASE = "HEAD"
OUTPUT_FORMAT = "%(path)s:%(row)d:%(col)d: %(code)s %(text)s"
VIOLATION_LINE = re.compile(r"^(?P<path>.+?):(?P<row>\d+):(?P<col>\d+): (?P<code>GES\d+) ")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gesco-lint", description="Linters de convenciones de Gesco (códigos GES)")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--diff-base", default=None, help="Solo líneas cambiadas respecto a este ref de git")
    scope.add_argument(
        "--changed-only",
        action="store_true",
        help=f"Como --diff-base, con el ref de {PRE_COMMIT_FROM_REF_ENV} o {DEFAULT_DIFF_BASE}",
    )
    parser.add_argument("paths", nargs="*", default=["."])
    return parser


def _run_flake8(*, paths: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "flake8", f"--select={CODE_PREFIX}", f"--format={OUTPUT_FORMAT}", *paths],
        capture_output=True,
        text=True,
        check=False,
    )


def _in_scope(*, line: str, diff_base: str | None, cache: dict[str, set[int]]) -> bool:
    if diff_base is None:
        return True
    match = VIOLATION_LINE.match(line)
    if match is None:
        return True
    path = match.group("path")
    if path not in cache:
        cache[path] = changed_lines(path=Path(path), base=diff_base)
    return int(match.group("row")) in cache[path]


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    diff_base = os.environ.get(PRE_COMMIT_FROM_REF_ENV, DEFAULT_DIFF_BASE) if args.changed_only else args.diff_base
    result = _run_flake8(paths=args.paths)
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    cache: dict[str, set[int]] = {}
    violations = [
        line for line in result.stdout.splitlines() if line and _in_scope(line=line, diff_base=diff_base, cache=cache)
    ]
    for line in violations:
        print(line)
    if violations:
        return 1
    flake8_failed = result.returncode not in (0, 1) or (result.returncode == 1 and not result.stdout.strip())
    return 1 if flake8_failed else 0


if __name__ == "__main__":
    sys.exit(main())
