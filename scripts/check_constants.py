#!/usr/bin/env python3
"""Refuse an UPPER_CASE constant outside `backend/app/constants/`.

`docs/process/coding-standards.md` §7: a fixed value lives in
`app/constants/<domain>.py`, and a value an operator may tune is a `Settings`
field in `app/core/config.py`. The frontend half of the rule is an ESLint
`no-restricted-syntax` selector; ruff has no rule that knows where a name is
allowed to live, so the backend half is this script.

It reads the syntax tree, not the text, so a name in a string, a comment or a
docstring is never mistaken for a declaration. Any depth counts: a constant
declared inside a function is a constant rebuilt on every call.

Usage:
    check_constants.py                  # every module under backend/app
    check_constants.py <file> [<file>]  # only these, as pre-commit passes them
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "backend" / "app"
ALLOWED = APP / "constants"
CONSTANT = re.compile(r"^[A-Z][A-Z0-9_]+$")


def _names(target: ast.expr) -> Iterator[ast.Name]:
    if isinstance(target, ast.Name):
        yield target
    elif isinstance(target, ast.Tuple | ast.List):
        for element in target.elts:
            yield from _names(element)


def violations(path: Path) -> list[str]:
    """Every UPPER_CASE name the module assigns, as `path:line: name`."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            for name in _names(target):
                if CONSTANT.match(name.id):
                    found.append(f"{path.resolve().relative_to(ROOT)}:{name.lineno}: {name.id}")
    return found


def in_scope(path: Path) -> bool:
    """A Python module of the application, outside `app/constants/`."""
    resolved = path.resolve()
    return (
        resolved.suffix == ".py"
        and resolved.is_relative_to(APP)
        and not resolved.is_relative_to(ALLOWED)
    )


def main(argv: Sequence[str]) -> int:
    """Print every misplaced constant; exit 1 when there is one."""
    paths = [Path(arg) for arg in argv] if argv else sorted(APP.rglob("*.py"))
    found = [line for path in paths if in_scope(path) for line in violations(path)]
    for line in found:
        print(line)
    if found:
        print(
            "\nConstants live in backend/app/constants/<domain>.py "
            "(docs/process/coding-standards.md §7).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
