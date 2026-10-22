# Production deployment: Django + Wagtail

## Status and limits

This is a deployment template for review, not an assertion that SmartChild is
already deployed. The stack uses the project's pinned Python/Django/Wagtail and
PostgreSQL versions, a non-root Gunicorn application container, WhiteNoise for
collected static files, Caddy for HTTPS, a separate PostgreSQL administrator
and restricted application role, and persistent database/media volumes.

Hosting provider, region/jurisdiction, public domain, budget, SMTP provider,
traffic assumptions and RPO/RTO are not selected here. No real deployment,
DNS change, paid operation, production secret or backup schedule is performed
by these files. Do not call this production-ready until the checklist below
has been completed on the chosen host.

## 1. Host and DNS prerequisites

- A supported Linux host with Docker Engine and Docker Compose v2 installed.
- DNS A/AAAA records for `PUBLIC_DOMAIN` point to this host. Do not publish an
  AAAA record unless IPv6 is actually routed to the host.
- Inbound TCP ports 80 and 443 are allowed; UDP 443 is optional for HTTP/3.
  PostgreSQL is not published on a host port.
- Agree where backups will be stored outside the application host and who is
  responsible for testing restores before launching production.

Caddy obtains and renews HTTPS certificates automatically when the domain
resolves to this host and its validation ports are reachable.

## 2. Prepare secrets and environment

From a checked-out release on the host:

```bash
cp .env.production.example .env.production
chmod 600 .env.production
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Use the generated value for `DJANGO_SECRET_KEY`. Generate separate, long random
passwords for `DB_PASSWORD` (the application role) and
`POSTGRES_ADMIN_PASSWORD` (the database administrator); they must not be the
same. Replace every `example.org`, `example.com`, and `REPLACE_...` or
`replace-with-...` placeholder with real, owner-approved values.

Important variable rules:

- `PUBLIC_DOMAIN`: hostname only, without scheme or path.
- `DJANGO_ALLOWED_HOSTS`: comma-separated hostnames, without `https://`.
- `DJANGO_CSRF_TRUSTED_ORIGINS` and `WAGTAILADMIN_BASE_URL`: include the
  HTTPS scheme.
- `DB_USER` must differ from `POSTGRES_ADMIN_USER`. The web application uses
  only the restricted `DB_USER` account.
- `EMAIL_HOST` and `DEFAULT_FROM_EMAIL` are required for SMTP. Keep SMTP
  passwords in `.env.production`, not in GitHub, screenshots, logs or PRs.
- Never copy a production secret into `.env.example` or this documentation.

The Compose commands below always use `--env-file .env.production`. Compose
uses this file for interpolation, while the application container receives only
the environment variables it needs.

## 3. Validate before starting

```bash
docker compose --env-file .env.production -f compose.production.yml config --quiet
docker compose --env-file .env.production -f compose.production.yml build --pull
```

Before enabling HTTPS redirects, confirm the real domain and DNS. Start the
database and run Django's deployment checks against the intended production
environment:

```bash
docker compose --env-file .env.production -f compose.production.yml up -d db
docker compose --env-file .env.production -f compose.production.yml run --rm web python manage.py check --deploy
```

Read every warning. HSTS subdomain/preload warnings must not be “fixed” by
turning on `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` or
`DJANGO_SECURE_HSTS_PRELOAD` until all affected hostnames are confirmed to
support HTTPS. A short HSTS value is intentionally provided for cutover; raise
it to a long duration after the HTTPS redirects and admin/login flows have been
verified.

## 4. First deployment

After replacing all placeholders and confirming DNS/firewall access:

```bash
docker compose --env-file .env.production -f compose.production.yml run --rm web python manage.py migrate --noinput
docker compose --env-file .env.production -f compose.production.yml run --rm web python manage.py createsuperuser
docker compose --env-file .env.production -f compose.production.yml up -d
docker compose --env-file .env.production -f compose.production.yml ps
docker compose --env-file .env.production -f compose.production.yml logs --tail=100 web caddy db
```

The PostgreSQL init script creates the application role only when the database
volume is initialized for the first time. If a volume already exists, changing
the init script will not rerun it. Do not delete an existing volume to force
initialization; create/grant the role deliberately with a reviewed SQL
procedure instead.

After the site is reachable:

1. Open `/cms/` over HTTPS and sign in with the superuser created above.
2. In Wagtail **Settings → Sites**, set the default site's hostname to
   `PUBLIC_DOMAIN` (hostname only, no scheme or port), preserving the intended
   home-page root.
3. Confirm the public homepage, lesson publication, images, admin static assets,
   password/session behavior and SMTP notification flow over HTTPS.
4. Check `/health/live/` (process) and `/health/ready/` (database) without
   exposing secrets in the response or logs.
5. Confirm public files are served correctly. Caddy directly serves only
   `/media/images/*`; document downloads continue through Wagtail's
   `/documents/` view instead of exposing the entire media directory.
6. Confirm the host firewall and cloud firewall do not expose PostgreSQL or
   Gunicorn directly to the Internet.

## 5. Release/update procedure

Use a reviewed commit SHA; do not deploy an unreviewed working tree.

```bash
git fetch origin
git checkout <reviewed-release-tag-or-sha>
docker compose --env-file .env.production -f compose.production.yml build --pull
docker compose --env-file .env.production -f compose.production.yml run --rm web python manage.py check --deploy
docker compose --env-file .env.production -f compose.production.yml run --rm web python manage.py migrate --noinput
docker compose --env-file .env.production -f compose.production.yml up -d
docker compose --env-file .env.production -f compose.production.yml ps
```

Back up PostgreSQL and media before schema changes. Migrations can be
irreversible or incompatible with an older image; verify the migration plan and
rollback strategy for each release. Do not use `down -v`: that deletes named
data volumes.

## 6. Manual backup and restore smoke test

The following is a manual starting point, not an agreed backup SLA. Create
encrypted, access-controlled copies outside this host and define retention,
frequency, RPO/RTO and an owner before launch. Database and media copies must
represent a consistent point in time; schedule a maintenance window or use a
snapshot procedure that prevents uploads/publication while the pair is copied.

Backup:

```bash
set -eu
umask 077
mkdir -p backups
stamp=$(date -u +%Y%m%dT%H%M%SZ)
docker compose --env-file .env.production -f compose.production.yml exec -T db sh -ec 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "backups/db-$stamp.dump"
docker compose --env-file .env.production -f compose.production.yml exec -T web tar -czf - -C /app/media . > "backups/media-$stamp.tar.gz"
sha256sum "backups/db-$stamp.dump" "backups/media-$stamp.tar.gz" > "backups/SHA256SUMS-$stamp"
```

Test restore on an isolated staging database and media volume before production.
Never test restore by overwriting the only live copy. A database restore command
for a deliberately selected empty/recovery database is:

```bash
docker compose --env-file .env.production -f compose.production.yml exec -T db sh -ec 'pg_restore --no-owner --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' < backups/db-<selected-stamp>.dump
```

Restore media into the matching recovery volume using the approved restore
procedure, then verify image/document references and representative pages.
The example above is not a complete safe in-place recovery recipe; existing
objects, roles, migration versions and point-in-time consistency must be
considered before any restore against a non-empty database.

## 7. Production checklist

- [ ] Provider, region/jurisdiction, domain, budget, capacity assumptions and
      operational owner approved.
- [ ] Separate high-entropy Django, application-DB, database-admin and SMTP
      credentials provisioned and stored outside Git with restricted access.
- [ ] DNS, firewall, certificate issuance and HTTPS redirects verified.
- [ ] `manage.py check --deploy` reviewed; no unexplained warnings.
- [ ] Wagtail Site hostname/root and editor permissions checked.
- [ ] PostgreSQL and media persistence verified across container recreation.
- [ ] Off-host encrypted backup plus a successful restore drill completed.
- [ ] RPO/RTO, retention, monitoring/alerting, dependency updates and incident
      response owner agreed.
- [ ] SMTP is verified end to end; failed mail delivery is monitored.
- [ ] Public policy/legal requirements and content/image/video rights reviewed.

## 8. What this template does not provide

This does not add student accounts, execute submitted Python, choose an
external video provider, automate backup retention, set up a monitoring vendor,
create a domain, or provision a hosting account. Those are separate product or
operations decisions. A running container is not by itself proof of production
readiness.
