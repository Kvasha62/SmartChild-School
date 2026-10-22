# Production Wagtail image: production settings are the default, without a
# DJANGO_ENV/development-mode fallback.
FROM python:3.13.17-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.production_settings \
    HOME=/tmp \
    TMPDIR=/tmp

WORKDIR /app

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /tmp \
       --shell /usr/sbin/nologin app \
    && mkdir -p /srv/media /tmp \
    && chown app:app /srv/media \
    && chmod 1777 /tmp

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

# Source and generated static assets remain root-owned and non-writable by app.
# User uploads live on the explicitly mounted /srv/media volume.
COPY --chown=root:root . /app/

# Synthetic build-only environment; these values are not Docker ENV settings
# and do not survive into the runtime container.
RUN DJANGO_SECRET_KEY=build-only-synthetic-key-for-collectstatic-0123456789abcdef \
    DJANGO_DEBUG=false \
    DJANGO_ALLOWED_HOSTS=build.example.invalid \
    WAGTAILADMIN_BASE_URL=https://build.example.invalid \
    DJANGO_MEDIA_ROOT=/srv/media \
    DB_NAME=build DB_USER=build_app DB_PASSWORD=build-only-app-password DB_HOST=build.invalid \
    DJANGO_EMAIL_HOST=mail.build.invalid \
    DJANGO_EMAIL_HOST_USER=mailer@build.invalid \
    DJANGO_EMAIL_HOST_PASSWORD=build-only-mail-password \
    DJANGO_DEFAULT_FROM_EMAIL=no-reply@build.invalid \
    DJANGO_TRUST_PROXY_SSL_HEADER=true \
    python manage.py collectstatic --noinput \
    && chown -R root:root /app \
    && chmod -R a-w /app

USER 10001:10001

EXPOSE 8000

# Host is required because production ALLOWED_HOSTS deliberately rejects '*'.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; host = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')[0].strip() or '127.0.0.1'; req = urllib.request.Request('http://127.0.0.1:8000/health/live/', headers={'Host': host}); urllib.request.urlopen(req, timeout=4).read()"

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--graceful-timeout", "30", "--worker-tmp-dir", "/tmp", "--access-logfile", "-", "--error-logfile", "-"]
