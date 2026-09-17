#!/usr/bin/env python3
"""Enforce the commit convention from CONTRIBUTING.md.

Conventional Commits with an accepted type, an optional scope, and a trailing
``[SPEC-XXXX]`` tag on every type that changes or asserts system behaviour.

Runs as pre-commit's ``commit-msg`` hook, which passes the commit message file
as the single argument. Standard library only, and deliberately so: the hook has
to work on a clone where ``backend/.venv`` does not exist yet.

Usage:
    check_commit_msg.py <path-to-commit-message-file>
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from pathlib import Path

# Exactly the list in CONTRIBUTING.md, "Commit convention". If this needs a
# ninth entry, CONTRIBUTING.md changes first and this file second — the
# convention is the specification, and this is only its enforcement.
TYPES = ("feat", "fix", "chore", "docs", "refactor", "test", "perf", "ci")

# Types that describe the repository rather than the system it implements.
# CONTRIBUTING.md's own worked examples settle this: `chore(ci): add frontend
# lint workflow` and `docs(adr): record CSV import decision` carry no tag, while
# both `feat` and `fix` examples do. Demanding a spec ID from a `chore` teaches
# people to paste an unrelated one, which is worse than no tag — it corrupts the
# traceability record the tag exists to serve.
#
# Everything else either changes behaviour (feat, fix, refactor, perf) or
# asserts it (test), and CLAUDE.md is unambiguous that behaviour does not change
# without a spec changing first.
SPEC_OPTIONAL = frozenset({"chore", "docs", "ci"})

# `<type>(<scope>)!: <subject>` — scope and the breaking-change `!` optional.
HEADER = re.compile(
    r"^(?P<type>[a-z]+)"
    r"(?:\((?P<scope>[^()\r\n]+)\))?"
    r"(?P<breaking>!)?"
    r": (?P<subject>\S.*)$"
)

SPEC_TAG = re.compile(r"\[SPEC-\d{4}\]")

# Messages git composes itself, or that point at another commit rather than
# describing a change of their own.
EXEMPT_PREFIXES = ("merge ", "revert ", "fixup!", "squash!", "amend!")

# Matches [tool.ruff] line-length, so the repository has one width and not two.
MAX_HEADER = 100

# `git commit --verbose` puts the diff below this line, and that diff is not
# comment-prefixed — so it has to be cut before comments are stripped, or a
# `+chore: ...` inside it gets mistaken for the header.
SCISSORS = "# ------------------------ >8 ------------------------"


def read_header(path: Path) -> str:
    """Return the first meaningful line of a commit message file.

    Args:
        path: The commit message file git handed to the hook.

    Returns:
        The header line, or an empty string when the message has no content.
    """
    corpo: list[str] = []
    for linha in path.read_text(encoding="utf-8").splitlines():
        if linha.startswith(SCISSORS):
            break
        if linha.startswith("#"):
            continue
        corpo.append(linha)

    for linha in corpo:
        if linha.strip():
            return linha.rstrip()
    return ""


def reject(header: str, problema: str) -> int:
    """Explain the rejection on stderr and return the hook's exit code.

    The message shows the convention and two worked examples rather than only
    naming the rule: a hook that rejects without showing what it wants is a hook
    people learn to bypass.

    Args:
        header: The offending header line.
        problema: What is wrong with it, as a sentence fragment.

    Returns:
        ``1``, so a caller can ``return reject(...)``.
    """
    print(f"\nCommit message refused:\n\n    {header}\n", file=sys.stderr)
    print(f"  {problema}.\n", file=sys.stderr)
    print("  Shape:  <type>(<scope>): <subject> [SPEC-XXXX]", file=sys.stderr)
    print(f"  Types:  {', '.join(TYPES)}", file=sys.stderr)
    print(f"  No [SPEC-XXXX] needed: {', '.join(sorted(SPEC_OPTIONAL))}", file=sys.stderr)
    print("\n  feat(ne): validate saldo before pré-empenho [SPEC-0004]", file=sys.stderr)
    print("  chore(ci): add frontend lint workflow", file=sys.stderr)
    print("\n  See CONTRIBUTING.md, 'Commit convention'.\n", file=sys.stderr)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    """Validate the commit message file named on the command line.

    Args:
        argv: Arguments after the program name. Defaults to ``sys.argv[1:]``.

    Returns:
        ``0`` if the message is acceptable, ``1`` if it is not, ``2`` on misuse.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: check_commit_msg.py <commit-msg-file>", file=sys.stderr)
        return 2

    header = read_header(Path(args[0]))
    if not header:
        # An empty message aborts the commit in git itself, and git says so more
        # clearly than this hook would. Saying it twice only buries git's line.
        return 0

    if header.lower().startswith(EXEMPT_PREFIXES):
        return 0

    encontrado = HEADER.match(header)
    if encontrado is None:
        return reject(header, "does not match `<type>(<scope>): <subject>`")

    tipo = encontrado.group("type")
    if tipo not in TYPES:
        return reject(header, f"`{tipo}` is not an accepted type")

    if len(header) > MAX_HEADER:
        return reject(
            header,
            f"the header is {len(header)} characters and the limit is {MAX_HEADER}",
        )

    if tipo not in SPEC_OPTIONAL and not SPEC_TAG.search(header):
        return reject(
            header,
            f"a `{tipo}` commit changes or asserts behaviour, so it must "
            "reference its spec as [SPEC-XXXX]",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
