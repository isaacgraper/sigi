# Deploy on a VPS

For showing SIGI to the client. `APP_ENV=staging`: real keys, no development seeds,
mail written to a folder (no SMTP yet, OQ-13).

1. Plain http on the VPS IP, no domain. With a domain: put it in the Caddyfile instead of `:80`, set `SIGI_ORIGIN=https://domain` and `COOKIE_SECURE=true`.
2. VPS (Ubuntu): `curl -fsSL https://get.docker.com | sh`; open ports 80 and 443 only (22 for SSH): `ufw allow 80/tcp && ufw allow 443/tcp`, and in the host panel's firewall if it has one.
3. As the non-root admin user (root login disabled): `git clone https://github.com/isaacgraper/sigi ~/sigi && cd ~/sigi`, on `main`
4. `scripts/gen-prod-env.sh 179.199.146.43`
5. `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build`
6. Migrations: `docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend alembic upgrade head`
7. First gestor: `docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend python -m app.cli bootstrap-gestor --email <email>`
8. Daily notices and summaries: a host cron, once a day:
   `0 7 * * * cd ~/sigi && docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T backend python -m app.cli notificar`

## Automatic deploy (SPEC-0019)

The VPS runs `main`. Every merge of a release PR into `main` deploys it through
`.github/workflows/deploy.yml`: the checkout is reset to `origin/main`, the stack
rebuilt, migrations applied, `/health` checked for 60 seconds, dangling images
pruned. Nothing else deploys, and two deploys never overlap.

**One-off setup**

1. On your machine, a key used only by the workflow:
   `ssh-keygen -t ed25519 -f id_ed25519_github_actions -N "" -C github-actions`
2. Install its public half for the admin user: `ssh-copy-id -i id_ed25519_github_actions.pub <user>@<host>`
3. The host's fingerprint: `ssh-keyscan -t ed25519 <host> 2>/dev/null | ssh-keygen -lf - | awk '{print $2}'`
4. In GitHub, Settings → Environments → `production`, add the secrets:

   | Secret | Value |
   | --- | --- |
   | `VPS_HOST` | the VPS address |
   | `VPS_USER` | the non-root admin user |
   | `VPS_SSH_KEY` | the private key from step 1 |
   | `VPS_FINGERPRINT` | the `SHA256:…` from step 3 |
   | `VPS_PROJECT_PATH` | the checkout's absolute path, e.g. `/home/<user>/sigi` |

A red run is the alarm. A missing secret, a changed host key, a missing
`.env.prod`, a failed migration or a silent `/health` each stop it, with the
reason in the log.

**A demo on `dev`** is a manual checkout. The next deploy discards it, local
changes included, and takes the directory back to `main`. `.env.prod` is
ignored by git and survives.

**Migrations are additive.** There is no dump before migrating; the nearest
restore point is the last backup (RNF11). A migration that drops or rewrites
data ships in a release of its own, after a manual backup.

## Manual update and rollback

These commands keep the database and `.env.prod`.

```bash
cd ~/sigi
git fetch origin
git checkout v1.0.0
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend alembic upgrade head
```

`v1.0.0` pins a version, which is how a bad release is rolled back. A migration
is not reverted. The next merge into `main` takes the directory back to `main`.

Back up the `postgres_data` volume before the client sees real data.
