# SIGI — Sistema Integrado de Governança de Insumos

Plataforma web para rastrear o ciclo administrativo de insumos em entidades
governamentais estaduais, da ATA à conclusão do fornecimento.

![Status](https://img.shields.io/badge/status-em%20progresso-yellow)
![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20Next.js-informational)

## Sobre

O SIGI substitui planilhas e e-mails dispersos por uma plataforma auditável:
acompanha cada insumo da ATA de Registro de Preços, pelo fluxo de Notas de
Empenho, até as Notas Fiscais e o encerramento do fornecimento. O histórico é
imutável e exportável para prestação de contas.

| Camada | Tecnologia |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Banco | PostgreSQL 16 |
| Frontend | Next.js, React, TypeScript, Tailwind |
| Execução | Docker Compose |

```
backend/    API FastAPI, migrações e testes (pytest)
frontend/   Aplicação Next.js e testes (Vitest, Playwright)
docs/       Specs, ADRs, requisitos e processo
infra/      Scripts do banco (papéis e permissões)
```

## Rodando com Docker

Pré-requisito: [Docker](https://docs.docker.com) com Docker Compose.

```bash
git clone https://github.com/isaacgraper/sigi.git
cd sigi
cp .env.example .env
docker compose up --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.cli seed-dev-admin
```

Abra <http://localhost:3000> e entre com `admin@sc.gov.br` / `admin`. Esse
gestor só existe em desenvolvimento (`APP_ENV=development`); em produção o
primeiro gestor é criado com `python -m app.cli bootstrap-gestor`.

## Desenvolvimento

Pré-requisitos: Python 3.12, [Poetry](https://python-poetry.org) 2.x,
Node.js 22 e um PostgreSQL 16 (o do Docker Compose serve).

### Backend

```bash
cd backend
poetry sync --all-groups
poetry run pre-commit install --install-hooks \
    --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

| Tarefa | Comando |
| --- | --- |
| Testes | `poetry run pytest` |
| Testes de um critério | `poetry run pytest -k AC_0001_07` |
| Cobertura (mínimo 70%) | `poetry run pytest --cov=app --cov-fail-under=70` |
| Lint e formatação | `poetry run ruff check .` · `poetry run ruff format .` |
| Todas as verificações | `poetry run pre-commit run --all-files` |

Os testes usam um PostgreSQL real: exporte `TEST_DATABASE_URL_ADMIN` apontando
para um servidor, ou deixe sem definir para o `testcontainers` subir um com
Docker.

### Frontend

```bash
cd frontend
npm ci
npm run dev        # http://localhost:3000, com a API em http://localhost:8000
```

| Tarefa | Comando |
| --- | --- |
| Lint | `npm run lint` |
| Testes unitários | `npm run test` |
| Testes ponta a ponta | `npm run test:e2e` (com a API e o frontend rodando) |
| Build | `npm run build` |

## Documentação

- [`docs/specs/`](docs/specs) — especificações com critérios de aceite; nada é
  implementado sem uma spec aprovada
- [`docs/architecture/adr/`](docs/architecture/adr) — decisões de arquitetura
- [`DESIGN.md`](DESIGN.md) — identidade visual e padrões de tela
- [`docs/GETTING-STARTED.md`](docs/GETTING-STARTED.md) — configuração de
  implantação: primeiro gestor, contato de suporte, proxy

## Contribuição

Nenhuma mudança entra em produção sem Pull Request revisado. `main` recebe
apenas releases; todo o trabalho é integrado em `dev`.

1. Parta de `dev` atualizada (`git checkout dev && git pull origin dev`)
2. Crie sua branch (`git checkout -b add/minha-feature-spec-0001`)
3. Faça commits atômicos (`git commit -m "feat: minha feature [SPEC-0001]"`)
4. Envie a branch (`git push -u origin HEAD`)
5. Abra um Pull Request **para `dev`**, nunca para `main`

Leia o [guia de contribuição](CONTRIBUTING.md) antes do primeiro PR. O modelo de
branches e o processo de release estão em
[`docs/process/branching-and-releases.md`](docs/process/branching-and-releases.md).

**Isaac Kleimmann Graper** · 2026
