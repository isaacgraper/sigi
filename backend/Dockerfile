FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=2.3.3 \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry-cache \
    # Installs into the interpreter's own prefix — /usr/local here — instead of
    # creating a project virtualenv. Same destination UV_PROJECT_ENVIRONMENT
    # used to name, which is why CMD can still call a bare `uvicorn`.
    # An environment variable rather than a config file, because it has to win
    # over backend/poetry.toml, which `COPY . .` brings into the image.
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

COPY pyproject.toml poetry.lock ./

# One layer, deliberately. Poetry installs into a virtualenv of its own so that
# its dependency tree never reaches the image's site-packages, and it is deleted
# here rather than in a later RUN — a file removed in a later layer still ships
# inside the image. Nothing at runtime needs Poetry.
#
#   --only main : no dev group (was --no-dev)
#   --no-root   : implied by package-mode = false; stated so the intent survives
#   --compile   : was UV_COMPILE_BYTECODE=1. Unaffected by PYTHONDONTWRITEBYTECODE,
#                 which only suppresses implicit writes at import time.
#
# A stale poetry.lock aborts the build rather than being re-resolved quietly,
# which is the same guarantee `uv sync --frozen` gave.
RUN python -m venv /opt/poetry \
 && /opt/poetry/bin/pip install --no-cache-dir "poetry==${POETRY_VERSION}" \
 && /opt/poetry/bin/poetry install --only main --no-root --compile \
 && rm -rf /opt/poetry "${POETRY_CACHE_DIR}" /root/.cache

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
