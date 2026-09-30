import re
import subprocess
from pathlib import Path

HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,(?P<count>\d+))? @@")


def changed_lines(*, path: Path, base: str) -> set[int]:
    diff = subprocess.run(  # noqa: S603
        ["git", "diff", "--no-color", "-U0", base, "--", str(path)],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    lines: set[int] = set()
    for text in diff.splitlines():
        match = HUNK_HEADER.match(text)
        if match is None:
            continue
        start = int(match.group("start"))
        count = int(match.group("count") or "1")
        lines.update(range(start, start + count))
    return lines
