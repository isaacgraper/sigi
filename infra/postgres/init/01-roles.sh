#!/bin/sh
# Creates the application role. Runs once, when the data directory is empty —
# the official postgres image only executes this directory on first init.
#
# Why two roles at all: ADR-0004 makes the audit trail append-only with
# REVOKE UPDATE, DELETE plus a trigger. Both are void if the application
# connects as the table owner, because an owner can ALTER TABLE ... DISABLE
# TRIGGER, TRUNCATE, and re-GRANT itself UPDATE. So POSTGRES_USER stays the
# owner and migration role, and the application gets a role that can do
# nothing but read and write rows.
#
# Table-level grants are NOT here: the tables do not exist yet. The migration
# applies them, and refuses to run if this role is missing.
set -eu

: "${APP_DB_ROLE:?APP_DB_ROLE is required}"
: "${APP_DB_PASSWORD:?APP_DB_PASSWORD is required}"

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname "$POSTGRES_DB" \
     -v role="$APP_DB_ROLE" \
     -v password="$APP_DB_PASSWORD" <<'EOSQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L NOINHERIT', :'role', :'password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'role') \gexec

-- Connect and see the schema. Nothing else: no CREATE, so the role cannot
-- add a table and then own it.
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'role') \gexec
SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'role') \gexec
SELECT format('REVOKE CREATE ON SCHEMA public FROM %I', :'role') \gexec

-- PostgreSQL 15+ already removes the world-writable public schema, but say it
-- explicitly rather than depending on the server's major version.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
EOSQL

echo "application role '$APP_DB_ROLE' ready (no table privilege yet; the migration grants it)"
