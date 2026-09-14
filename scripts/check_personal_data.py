#!/usr/bin/env python3
"""Refuse to commit the personal data CLAUDE.md forbids committing.

CLAUDE.md: *"Do not commit real CPF, SIAPE numbers, e-mails or tokens. The RFC
appendix contains a live prototype JWT: it must not be copied into this
repository."* `docs/security/lgpd.md` depends on that holding, and git keeps what
it is given — by the time a reviewer notices, the value is in the history of
every clone. So the rule runs before the commit, not after.

This is deliberately **not** a general-purpose secret scanner. `gitleaks` runs in
CI and is better at API keys than anything written here. What a generic scanner
does not know is what a CPF is, what a SIAPE number is, or which e-mail domain
belongs to the entity — and those are the three things this repository is most
likely to leak, because they are what the stakeholder workbooks are full of.

Same idea as ``DadoPessoalNoHistorico`` in ``app/services/auditoria.py``: the
rule already exists in prose, and prose decays.

Usage:
    check_personal_data.py <file> [<file> ...]
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from pathlib import Path

# The institutional domains. An address at one of these is a real person unless
# it is plainly synthetic — see ENDERECO_INSTITUCIONAL.
DOMINIOS_INSTITUCIONAIS = ("sc.gov.br", "saude.sc.gov.br")

#: A CPF is eleven digits, written with or without punctuation.
#:
#: The boundaries exclude `.` and `,`, not just digits, and that is not
#: over-engineering — the first run of this hook against the tree flagged
#: `46213.70138888889` in `data-sources.md`, an Excel date serial whose
#: fractional part is exactly eleven digits. `\b` or a plain `(?<!\d)` matches
#: it. The trailing `[.,]\d` guard does the same for the other side, so a
#: number like `12345678901.5` is not read as a CPF followed by a full stop,
#: while a CPF that genuinely ends a sentence still is.
CPF = re.compile(r"(?<![\d.,])(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})(?!\d|[.,]\d)")

#: SIAPE registration, seven digits, and only when the line says so. Seven bare
#: digits alone are far too common to flag.
SIAPE = re.compile(r"(?i)\bsiape\b[^\n\r]{0,20}?(?<!\d)\d{7}(?!\d)")

#: A JWT's header always begins `eyJ` — base64 of `{"`. This is OQ-17: the live
#: prototype token published in the RFC appendix, which must never be copied in.
JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")

#: An institutional address whose local part contains a dot.
#:
#: The dot is what separates a real person from a fixture. The entity issues
#: `nome.sobrenome@sc.gov.br` — sigi: dado-pessoal-ok, that is the shape being
#: described and not anybody's address — while every synthetic address in this
#: repository is a single token: `ana@`, `outro@`, `naoexiste@`. Blocking the
#: domain outright would reject every authentication test there is, and a hook
#: that fires on correct code is a hook people disable.
#:
#: The line above is also the escape hatch demonstrating itself. It is the first
#: thing this rule flagged, on its own source.
ENDERECO_INSTITUCIONAL = re.compile(
    r"\b[A-Za-z0-9_%+-]+\.[A-Za-z0-9._%+-]+@(?:" + "|".join(
        d.replace(".", r"\.") for d in DOMINIOS_INSTITUCIONAIS
    ) + r")\b"
)

REGRAS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("CPF", CPF, "CLAUDE.md proíbe CPF no repositório; a OQ-10 decidiu não coletá-lo"),
    ("SIAPE", SIAPE, "matrícula SIAPE identifica um servidor"),
    ("JWT", JWT, "token no repositório; ver OQ-17, o JWT de protótipo do RFC"),
    (
        "e-mail institucional",
        ENDERECO_INSTITUCIONAL,
        "endereço com nome.sobrenome parece de uma pessoa real; "
        "fixtures usam um token só, como ana@sc.gov.br",
    ),
)

#: Binary and lock files: no personal data is authored there, and a lock file
#: full of hashes is where the unpunctuated-CPF pattern would false-positive.
EXTENSOES_IGNORADAS = frozenset({".lock", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".svg"})

#: The line that tells this hook to stand down, for the case it judges wrongly.
#: Deliberately verbose: an escape hatch nobody can find is an escape hatch that
#: gets replaced by `--no-verify`, which disables every other hook too.
ESCAPE = "sigi: dado-pessoal-ok"


def achados(caminho: Path) -> list[str]:
    """Return one message per suspected value in the file.

    Args:
        caminho: The file to scan.

    Returns:
        Human-readable findings, each naming the file, line and rule.
    """
    if caminho.suffix.lower() in EXTENSOES_IGNORADAS:
        return []
    try:
        texto = caminho.read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
        # Unreadable as text means no authored personal data to find. A binary
        # blob that really does carry some is gitleaks' problem, not this hook's.
        return []

    encontrados: list[str] = []
    for numero, linha in enumerate(texto.splitlines(), start=1):
        if ESCAPE in linha:
            continue
        for rotulo, padrao, porque in REGRAS:
            achado = padrao.search(linha)
            if achado is not None:
                encontrados.append(
                    f"{caminho}:{numero}: {rotulo} — {porque}\n"
                    f"    {achado.group(0)[:60]}"
                )
    return encontrados


def main(argv: Sequence[str] | None = None) -> int:
    """Scan every file named on the command line.

    Args:
        argv: Paths to scan. Defaults to ``sys.argv[1:]``.

    Returns:
        ``0`` when nothing was found, ``1`` otherwise.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    encontrados = [linha for arg in args for linha in achados(Path(arg))]
    if not encontrados:
        return 0

    print("\nDado pessoal aparente nos arquivos em stage:\n", file=sys.stderr)
    for linha in encontrados:
        print(f"  {linha}", file=sys.stderr)
    print(
        "\n  O git guarda o que recebe: depois do commit o valor está no"
        "\n  histórico de todo clone. Troque por um valor sintético, ou use o"
        f"\n  HMAC de app/core/segredos.py se o que você quer é correlacionar."
        f"\n\n  Se este achado estiver errado, escreva `{ESCAPE}` na linha."
        "\n  Ver CLAUDE.md e docs/security/lgpd.md.\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
