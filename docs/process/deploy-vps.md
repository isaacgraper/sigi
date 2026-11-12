# Deploy on a VPS

For showing SIGI to the client. `APP_ENV=staging`: real keys, no development seeds,
mail written to a folder (no SMTP yet, OQ-13).

1. Plain http on the VPS IP, no domain. With a domain: put it in the Caddyfile instead of `:80`, set `SIGI_ORIGIN=https://domain` and `COOKIE_SECURE=true`.
2. VPS (Ubuntu): `curl -fsSL https://get.docker.com | sh`; open ports 80 and 443 only (22 for SSH): `ufw allow 80/tcp && ufw allow 443/tcp`, and in the host panel's firewall if it has one.
3. `git clone https://github.com/isaacgraper/sigi && cd sigi && git checkout dev`
4. `scripts/gen-prod-env.sh 179.199.146.43`
5. `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build`
6. Migrations: `docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend alembic upgrade head`
7. First gestor: `docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend python -m app.cli bootstrap-gestor --email <email>`
8. Daily notices and summaries: a host cron, once a day:
   `0 7 * * * cd /root/sigi && docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T backend python -m app.cli notificar`

## Update and release

The VPS runs `dev` for testing. These commands keep the database and `.env.prod`.

Update `dev`:

```bash
cd ~/sigi
git checkout dev
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend alembic upgrade head
```

Run `main`, the released version: the same commands with `git checkout main`. To pin a version, use `git checkout v1.0.0`.

Back up the `postgres_data` volume before the client sees real data.
