#!/bin/sh
# PostgreSQL's official entrypoint sources non-executable .sh init files.
# This runs once, only when the database volume is first initialized.
set -eu

if [ "${DB_USER}" = "${POSTGRES_USER}" ]; then
    echo "DB_USER must differ from POSTGRES_ADMIN_USER." >&2
    exit 1
fi

psql --set ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'EOSQL'
\getenv app_user DB_USER
\getenv app_password DB_PASSWORD
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'app_user') \gexec
GRANT USAGE, CREATE ON SCHEMA public TO :"app_user";
EOSQL
