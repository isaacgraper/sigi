#!/usr/bin/env bash
# Writes .env.prod with fresh secrets. Run once on the VPS: scripts/gen-prod-env.sh sigi.exemplo.com.br
set -euo pipefail
domain="${1:?domain, e.g. sigi.exemplo.com.br}"
[ -e .env.prod ] && { echo ".env.prod already exists" >&2; exit 1; }
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
openssl genrsa -out "$tmp/private.pem" 2048 2>/dev/null
openssl rsa -in "$tmp/private.pem" -pubout -out "$tmp/public.pem" 2>/dev/null
one_line() { awk 'BEGIN{ORS="\\n"} {print}' "$1"; }
umask 077
cat > .env.prod <<ENV
SIGI_DOMAIN=$domain
POSTGRES_PASSWORD=$(openssl rand -hex 24)
APP_DB_PASSWORD=$(openssl rand -hex 24)
HMAC_PEPPER=$(openssl rand -hex 32)
JWT_PRIVATE_KEY="$(one_line "$tmp/private.pem")"
JWT_PUBLIC_KEY="$(one_line "$tmp/public.pem")"
SUPPORT_CONTACT_EMAIL=
ENV
echo ".env.prod written."
