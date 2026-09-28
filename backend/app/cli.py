"""Operator commands, run on the server and never exposed over HTTP.

`python -m app.cli bootstrap-gestor --email ...` creates the first gestor
(AC-0001-34); `seed-dev-admin` creates admin@sc.gov.br / admin, in development
only (AC-0001-39). An HTTP route that could do this would be the most valuable
route in the system to attack, so the only way in is a shell on the server.
"""

from __future__ import annotations

import argparse
import datetime
import getpass
import sys
import uuid
from collections.abc import Callable, Sequence

from app.core.db import session_factory
from app.services import members
from app.services.errors import DomainError


def _read_password(prompt: Callable[[str], str]) -> str:
    # From the terminal, never from an argument: arguments land in shell
    # history and in every process listing on the machine.
    first = prompt("Password: ")
    if first != prompt("Repeat password: "):
        raise SystemExit("PASSWORDS_DIFFER: the two passwords do not match.")
    return first


def bootstrap_gestor(
    email: str, *, no_password: bool, prompt: Callable[[str], str] = getpass.getpass
) -> int:
    """Create the first gestor and report the outcome. Returns an exit code."""
    password = None if no_password else _read_password(prompt)
    with session_factory()() as session:
        try:
            user = members.bootstrap_gestor(
                session,
                email=email,
                password=password,
                at=datetime.datetime.now(datetime.UTC),
                correlation_id=uuid.uuid4(),
            )
            session.commit()
        except DomainError as exc:
            session.rollback()
            print(f"{exc.code}: {exc.message_text}", file=sys.stderr)
            return 1
    print(f"Gestor {user.email} created ({user.id}).")
    return 0


def seed_dev_admin() -> int:
    """Create admin@sc.gov.br / admin on a development install."""
    with session_factory()() as session:
        try:
            user = members.seed_dev_admin(
                session,
                at=datetime.datetime.now(datetime.UTC),
                correlation_id=uuid.uuid4(),
            )
            session.commit()
        except DomainError as exc:
            session.rollback()
            print(f"{exc.code}: {exc.message_text}", file=sys.stderr)
            return 1
    if user is None:
        print(f"{members.DEV_ADMIN_EMAIL} already exists.")
    else:
        print(f"Gestor {members.DEV_ADMIN_EMAIL} created, password '{members.DEV_ADMIN_PASSWORD}'.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Parse the command line and run the chosen command."""
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    bootstrap = commands.add_parser("bootstrap-gestor", help="create the first gestor")
    bootstrap.add_argument("--email", required=True)
    bootstrap.add_argument(
        "--no-password",
        action="store_true",
        help="for an install that logs in only through OIDC",
    )
    commands.add_parser("seed-dev-admin", help="development only: admin@sc.gov.br / admin")
    args = parser.parse_args(argv)
    if args.command == "seed-dev-admin":
        return seed_dev_admin()
    return bootstrap_gestor(args.email, no_password=args.no_password)


if __name__ == "__main__":
    raise SystemExit(main())
