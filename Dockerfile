# Portable production image for the Django/Wagtail application.
# It deliberately contains no provider-specific configuration: PostgreSQL,
# persistent media storage, TLS termination, and SMTP are provided by the
# platform chosen later and injected through environment variables.
# See docs/technical/production-deployment-runbook.md.
FROM python:3.13.17-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.production_settings

WORKDIR /app

# The application must not run as root. /srv/media is only the mount point
# for persistent upload storage; the platform MUST back DJANGO_MEDIA_ROOT
# with a persistent volume (see the runbook) or uploads will be lost when
# the container is replaced.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app \
       --shell /usr/sbin/nologin app \
    && mkdir -p /srv/media \
    && chown app:app /srv/media

COPY requirements.txt /app/requirements.txt
RUN python -m pip install -r /app/requirements.txt

COPY --chown=app:app . /app/

# Collect static assets into the image. The values below exist only for
# this build step so the production settings module can be imported; they
# are synthetic, are not usable credentials, and are not present in the
# running container's environment. Real values must be injected at runtime
# or production settings will refuse to start.
RUN DJANGO_SECRET_KEY=build-only-synthetic-key-for-collectstatic-0123456789 \
    DJANGO_ALLOWED_HOSTS=build.invalid \
    WAGTAILADMIN_BASE_URL=https://build.invalid \
    DJANGO_MEDIA_ROOT=/srv/media \
    DB_NAME=build DB_USER=build DB_PASSWORD=build-only DB_HOST=db.invalid \
    DJANGO_EMAIL_HOST=smtp.invalid \
    DJANGO_DEFAULT_FROM_EMAIL=no-reply@build.invalid \
    python manage.py collectstatic --noinput \
    && chown -R app:app /app/staticfiles

USER app

EXPOSE 8000

# Liveness only; readiness (including PostgreSQL) is /health/ready/ and
# should be wired to the platform's readiness mechanism. The Host header
# uses the first configured allowed host so Django accepts the probe.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; host = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')[0].strip() or '127.0.0.1'; req = urllib.request.Request('http://127.0.0.1:8000/health/live/', headers={'Host': host}); urllib.request.urlopen(req, timeout=4).read()"

# Gunicorn is the production WSGI server (never Django's runserver).
# Worker count can be tuned per platform with the standard WEB_CONCURRENCY
# environment variable, which Gunicorn honours natively.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--timeout", "60", "--graceful-timeout", "30", "--access-logfile", "-", "--error-logfile", "-"]
