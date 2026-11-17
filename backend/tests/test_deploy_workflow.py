"""The deploy workflow's contract (SPEC-0019).

Read as text, not run: a deploy only runs on a push to main, against the VPS.
What a file can promise is asserted here; the steps on the VPS are proven by
the first deploy of a release (SPEC-0019 §10).
"""

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "deploy.yml"
SECRETS = ("VPS_HOST", "VPS_USER", "VPS_SSH_KEY", "VPS_FINGERPRINT", "VPS_PROJECT_PATH")


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _script() -> str:
    """The commands sent to the VPS, without comments."""
    body = _text().split("script: |", 1)[1]
    lines = (line.strip() for line in body.splitlines())
    return "\n".join(line for line in lines if line and not line.startswith("#"))


def _position(script: str, command: str) -> int:
    index = script.find(command)
    assert index >= 0, f"{command!r} is not in the deploy script"
    return index


def test_AC_0019_01_push_to_main_starts_a_deploy() -> None:
    """AC-0019-01 — A push to main starts the deploy."""
    assert re.search(r"^on:\n  push:\n    branches: \[main\]\n", _text(), re.M)


def test_AC_0019_02_nothing_else_starts_a_deploy() -> None:
    """AC-0019-02 — Only a push to main starts it: no pull request, no dev."""
    trigger = _text().split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    events = re.findall(r"^  (\w+):", trigger, re.M)
    assert events == ["push"]
    assert "dev" not in trigger


def test_AC_0019_03_one_deploy_at_a_time_never_cancelled() -> None:
    """AC-0019-03 — A second deploy waits for the first, which is never cancelled."""
    text = _text()
    assert re.search(r"^concurrency:\n  group: deploy-production\n", text, re.M)
    assert "cancel-in-progress: false" in text


def test_AC_0019_04_token_only_reads_contents() -> None:
    """AC-0019-04 — The run's token only reads the repository's contents."""
    assert re.search(r"^permissions:\n  contents: read\n\n", _text(), re.M)


def test_AC_0019_05_credentials_come_from_secrets() -> None:
    """AC-0019-05 — No address, key or fingerprint is in the file; each comes from a secret."""
    text = _text()
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", text), "an IP address is in the workflow"
    assert "SHA256:" not in text
    assert "PRIVATE KEY" not in text
    for field in ("host", "username", "key", "fingerprint"):
        assert re.search(rf"^\s+{field}: \$\{{\{{ secrets\.VPS_\w+ \}}\}}$", text, re.M), field


def test_AC_0019_05_action_holding_the_key_is_pinned_by_commit() -> None:
    """AC-0019-05 — The action that holds the deploy key is pinned by commit, not by tag."""
    uses = re.findall(r"uses: (\S+)", _text())
    assert uses, "no action is used"
    for action in uses:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", action), action


def test_AC_0019_06_host_key_is_verified() -> None:
    """AC-0019-06 — The connection checks the host's key against the stored fingerprint."""
    assert re.search(r"^\s+fingerprint: \$\{\{ secrets\.VPS_FINGERPRINT \}\}$", _text(), re.M)


def test_AC_0019_07_every_secret_is_checked_before_connecting() -> None:
    """AC-0019-07 — Every secret is checked, and a missing one named, before connecting."""
    text = _text()
    check = text.index("Check the deploy secrets")
    connect = text.index("Deploy over SSH")
    assert check < connect
    checked = text[check:connect]
    for name in SECRETS:
        assert f"{name}: ${{{{ secrets.{name} }}}}" in checked, name
        assert name in checked.split("for name in", 1)[1].splitlines()[0], name
    assert "::error::secret $name is not set" in checked


def test_AC_0019_08_to_10_main_retakes_the_checkout() -> None:
    """AC-0019-08 — The checkout is reset to origin/main, from main, from dev or diverged."""
    script = _script()
    fetch = _position(script, "git fetch origin")
    checkout = _position(script, "git checkout -f main")
    reset = _position(script, "git reset --hard origin/main")
    assert fetch < checkout < reset
    assert "git pull" not in script
    assert "git clean" not in script, ".env.prod is untracked and must survive"


def test_AC_0019_11_production_stack_with_its_env_file() -> None:
    """AC-0019-11 — The production stack is rebuilt with .env.prod and its volumes kept."""
    script = _script()
    assert 'dc="docker compose -f docker-compose.prod.yml --env-file .env.prod"' in script
    assert "$dc up -d --build" in script
    assert re.search(r"\bdown\b|\s-v\b|--volumes|volume (rm|prune)", script) is None


def test_AC_0019_12_missing_env_file_stops_before_the_rebuild() -> None:
    """AC-0019-12 — Without .env.prod the run stops before rebuilding."""
    script = _script()
    guard = _position(script, "if [ ! -f .env.prod ]; then")
    assert guard < _position(script, "$dc up -d --build")
    assert "exit 1" in script[guard : _position(script, "$dc up -d --build")]


def test_AC_0019_13_migrations_after_the_rebuild_as_the_owner() -> None:
    """AC-0019-13 — Migrations run after the rebuild, through the owner connection."""
    script = _script()
    assert _position(script, "$dc up -d --build") < _position(
        script, "$dc exec -T backend alembic upgrade head"
    )
    env = (Path(__file__).resolve().parents[1] / "migrations" / "env.py").read_text("utf-8")
    assert "database_url_admin" in env


def test_AC_0019_14_a_failing_step_ends_the_run() -> None:
    """AC-0019-14 — Any failing step ends the run."""
    assert _script().splitlines()[0] == "set -eu"


def test_AC_0019_15_and_16_health_is_checked_for_60_seconds() -> None:
    """AC-0019-15 — /health is polled for 60 seconds, and the backend's log shown on failure."""
    script = _script()
    migrate = _position(script, "alembic upgrade head")
    probe = _position(script, "http://localhost:8000/health")
    assert migrate < probe
    assert '"$i" -lt 30' in script and "sleep 2" in script
    assert "get('status') == 'ok'" in script
    failure = script[probe:]
    assert failure.index("$dc logs --tail=50 backend") < failure.index("exit 1")


def test_AC_0019_17_only_dangling_images_pruned_after_health() -> None:
    """AC-0019-17 — Only dangling images are pruned, and only after the health check."""
    script = _script()
    prune = _position(script, "docker image prune -f")
    assert _position(script, 'if [ "$healthy" -ne 1 ]; then') < prune
    assert "prune -a" not in script and "system prune" not in script


def test_AC_0019_18_run_names_commit_and_tag() -> None:
    """AC-0019-18 — The log names the commit and tag deployed."""
    script = _script()
    assert "git describe --tags --exact-match" in script
    assert 'echo "deploying $(git rev-parse HEAD) ${tag:-untagged}' in script
