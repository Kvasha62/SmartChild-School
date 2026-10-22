FROM python:3.13.17-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app \
       --shell /usr/sbin/nologin app

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

COPY --chown=app:app . /app/

RUN mkdir -p /app/media /app/staticfiles \
    && chown -R app:app /app/media /app/staticfiles \
    && DJANGO_SECRET_KEY=static-build-only-not-a-production-secret \
       DJANGO_DEBUG=false \
       DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend \
       python manage.py collectstatic --noinput \
    && chown -R app:app /app/staticfiles

USER app

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
