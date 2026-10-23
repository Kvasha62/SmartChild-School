#!/usr/bin/env bash
# Runs only on first initialization of an empty PostgreSQL data directory.
# The official entrypoint sources non-executable *.sh files.
set -Eeuo pipefail

: "${APP_DB_USER:?APP_DB_USER must be set}"
: "${APP_DB_PASSWORD:?APP_DB_PASSWORD must be set}"

if [ "$APP_DB_USER" = "$POSTGRES_USER" ]; then
  echo >&2 "APP_DB_USER must differ from the PostgreSQL bootstrap administrator."
  exit 1
fi

case "$POSTGRES_PASSWORD" in
  *CHANGE_ME*|*change-me*|*change_me*|*changeme*|local-development-only)
    echo >&2 "POSTGRES_PASSWORD is a placeholder; configure a unique bootstrap password."
    exit 1
    ;;
esac

case "$APP_DB_PASSWORD" in
  *CHANGE_ME*|*change-me*|*change_me*|*changeme*|local-development-only)
    echo >&2 "APP_DB_PASSWORD is a placeholder; configure a unique application password."
    exit 1
    ;;
esac

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_user="$APP_DB_USER" \
  --set=app_password="$APP_DB_PASSWORD" <<'SQL'
SELECT format(
    'CREATE ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD %L',
    :'app_user',
    :'app_password'
) \gexec
SELECT format(
    'ALTER DATABASE %I OWNER TO %I',
    current_database(),
    :'app_user'
) \gexec
SQL
