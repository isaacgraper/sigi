# Deploy on a VPS

For showing SIGI to the client. `APP_ENV=staging`: real keys, no development seeds,
mail written to a folder (no SMTP yet, OQ-13).

1. DNS: an A record for the domain pointing at the VPS IP.
2. VPS (Ubuntu): `curl -fsSL https://get.docker.com | sh`; open ports 80 and 443 only.
3. `git clone https://github.com/isaacgraper/sigi && cd sigi && git checkout dev`
4. `scripts/gen-prod-env.sh sigi.exemplo.com.br`
5. `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build`
6. Migrations: `docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend alembic upgrade head`
7. First gestor: `docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend python -m app.cli bootstrap-gestor <email>`
8. Daily notices and summaries: a host cron, once a day:
   `0 7 * * * cd /root/sigi && docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T backend python -m app.cli notificar`

Update: `git pull`, step 5, step 6. Back up the `postgres_data` volume before the client sees real data.
