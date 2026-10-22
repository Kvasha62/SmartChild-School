"""Production Django + Wagtail settings for SmartChild-School.

Use with ``DJANGO_SETTINGS_MODULE=config.production_settings``.

This module layers a fail-fast production contract on top of the local
development settings in ``config.settings``. It never falls back to
development secrets or hosts: every mandatory value must come from the
environment, and configuration errors name the offending variable without
echoing secret values.

See ``docs/technical/production-deployment-runbook.md`` for the full
variable reference, release procedure, and the operational decisions that
are still open (hosting, domain, SMTP provider, persistent media storage,
backups, monitoring). Nothing in this module selects a hosting provider.
"""
import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

# Fail with a production-specific message before the development settings
# are imported (they already require some secret key, but their guidance
# points at a local .env file).
if not os.environ.get("DJANGO_SECRET_KEY", "").strip():
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is required in production. Generate a random "
        "value of at least 50 characters and provide it through the "
        "environment; never commit it to the repository."
    )

from config.settings import *  # noqa: F401,F403,E402
from config.settings import BASE_DIR, DATABASES, MIDDLEWARE  # noqa: E402
from config.settings import env_bool, env_list  # noqa: E402


def _require_env(names: list[str]) -> None:
    """Raise one error listing every missing variable name (never values)."""
    missing = [name for name in names if not os.environ.get(name, "").strip()]
    if missing:
        raise ImproperlyConfigured(
            "Missing required production environment variable(s): "
            + ", ".join(missing)
            + ". See docs/technical/production-deployment-runbook.md."
        )


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ImproperlyConfigured(
            f"{name} must be an integer between {minimum} and {maximum}."
        ) from None
    if not minimum <= value <= maximum:
        raise ImproperlyConfigured(
            f"{name} must be an integer between {minimum} and {maximum}."
        )
    return value


# ---------------------------------------------------------------------------
# Core safety contract
# ---------------------------------------------------------------------------

if env_bool("DJANGO_DEBUG", False):
    raise ImproperlyConfigured(
        "DJANGO_DEBUG must not be enabled with production settings. "
        "Unset it or set it to false."
    )
DEBUG = False

_require_env(
    [
        "DJANGO_ALLOWED_HOSTS",
        "WAGTAILADMIN_BASE_URL",
        "DJANGO_MEDIA_ROOT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
        "DJANGO_EMAIL_HOST",
        "DJANGO_DEFAULT_FROM_EMAIL",
    ]
)

# SECRET_KEY is imported from the base settings (sourced from
# DJANGO_SECRET_KEY); enforce production strength without printing it.
_KNOWN_PLACEHOLDERS = {
    "replace-me-with-a-random-secret",
    "local-development-only",
    "ci-only-not-a-production-secret",
    "ci-only-password",
}
_secret_lower = SECRET_KEY.strip().lower()  # noqa: F405
if (
    len(SECRET_KEY) < 50  # noqa: F405
    or len(set(SECRET_KEY)) < 5  # noqa: F405
    or _secret_lower in _KNOWN_PLACEHOLDERS
    or _secret_lower.startswith("django-insecure-")
    or "replace-me" in _secret_lower
    or "replace_me" in _secret_lower
    or "change-me" in _secret_lower
    or "change_me" in _secret_lower
    or "changeme" in _secret_lower
):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is too weak or is a known placeholder. Use a "
        "random value of at least 50 characters generated for this "
        "deployment only."
    )

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must list the exact production host name(s); "
        "the '*' wildcard is not accepted in production."
    )

# ---------------------------------------------------------------------------
# Public base URL and CSRF origins
# ---------------------------------------------------------------------------

WAGTAILADMIN_BASE_URL = os.environ["WAGTAILADMIN_BASE_URL"].strip().rstrip("/")
_base_url = urlparse(WAGTAILADMIN_BASE_URL)
if _base_url.scheme != "https" or not _base_url.netloc:
    raise ImproperlyConfigured(
        "WAGTAILADMIN_BASE_URL must be the public https origin of the site, "
        "for example https://school.example.org (no path is required)."
    )
if _base_url.username or _base_url.password or _base_url.query or _base_url.fragment:
    raise ImproperlyConfigured(
        "WAGTAILADMIN_BASE_URL must not contain credentials, a query "
        "string, or a fragment."
    )

if os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").strip():
    CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
    if any(not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS):
        raise ImproperlyConfigured(
            "Every DJANGO_CSRF_TRUSTED_ORIGINS entry must start with "
            "https:// in production."
        )
else:
    # Single-origin deployment: the admin and the public site share the
    # WAGTAILADMIN_BASE_URL origin. Set DJANGO_CSRF_TRUSTED_ORIGINS
    # explicitly if additional https origins must be trusted.
    CSRF_TRUSTED_ORIGINS = [f"https://{_base_url.netloc}"]

# ---------------------------------------------------------------------------
# Database (PostgreSQL only)
# ---------------------------------------------------------------------------

if "change_me" in os.environ["DB_PASSWORD"].lower() or "change-me" in os.environ[
    "DB_PASSWORD"
].lower():
    raise ImproperlyConfigured(
        "DB_PASSWORD still contains the template placeholder from "
        ".env.production.example; set the real database password."
    )

DATABASES["default"].update(
    NAME=os.environ["DB_NAME"].strip(),
    USER=os.environ["DB_USER"].strip(),
    PASSWORD=os.environ["DB_PASSWORD"],
    HOST=os.environ["DB_HOST"].strip(),
    PORT=str(_env_int("DB_PORT", 5432, minimum=1, maximum=65535)),
    CONN_MAX_AGE=_env_int("DB_CONN_MAX_AGE", 60, minimum=0, maximum=3600),
)
# Optional transport security towards a managed PostgreSQL service, e.g.
# DB_SSLMODE=require. The hosting decision determines whether this is
# needed; it stays unset until the platform is chosen.
_sslmode = os.environ.get("DB_SSLMODE", "").strip()
if _sslmode:
    DATABASES["default"].setdefault("OPTIONS", {})["sslmode"] = _sslmode

# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------

STATIC_ROOT = Path(
    os.environ.get("DJANGO_STATIC_ROOT", BASE_DIR / "staticfiles")
)

# Uploaded Wagtail images/documents must live on persistent storage provided
# by the platform (mounted volume or, after a separate owner decision,
# object storage). Requiring an explicit absolute path prevents silently
# writing uploads to an ephemeral container filesystem.
MEDIA_ROOT = Path(os.environ["DJANGO_MEDIA_ROOT"].strip())
if not MEDIA_ROOT.is_absolute():
    raise ImproperlyConfigured(
        "DJANGO_MEDIA_ROOT must be an absolute path to persistent storage "
        "mounted into the application environment."
    )

# WhiteNoise serves collected static files from the application process.
# Rationale: the current architecture is a single small Wagtail site with
# no chosen CDN/object-storage provider; compressed, hashed assets with
# long-lived caching are sufficient and keep deployment portable. Media
# uploads are NOT served by WhiteNoise and still need a web server or
# platform file-serving decision at the chosen MEDIA_ROOT (see runbook).
MIDDLEWARE = [
    MIDDLEWARE[0],  # SecurityMiddleware stays first
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],
]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# HTTPS, cookies, HSTS, trusted reverse proxy
# ---------------------------------------------------------------------------
# These settings assume TLS is terminated either in front of the app (a
# trusted reverse proxy / platform load balancer) or by a web server on the
# same host. They are intentionally NOT applied by the development
# settings, where plain http on localhost is used.

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
# Liveness/readiness probes typically call the container over plain http on
# a private network. These two paths return no content beyond a status
# word, so they are exempted from the https redirect; every other path,
# including the Wagtail admin, still redirects.
SECURE_REDIRECT_EXEMPT = [r"^health/live/$", r"^health/ready/$"]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
# Wagtail's page preview and image chooser run in same-origin iframes, so
# DENY would break the admin. SAMEORIGIN still blocks embedding by other
# sites; `check --deploy` reports this as warning W019 by design.
X_FRAME_OPTIONS = "SAMEORIGIN"

# Start HSTS conservatively (1 hour). Raise DJANGO_SECURE_HSTS_SECONDS
# (e.g. to 31536000) only after HTTPS and the final domain layout are
# verified; enable subdomains/preload only by explicit owner decision.
SECURE_HSTS_SECONDS = _env_int(
    "DJANGO_SECURE_HSTS_SECONDS", 3600, minimum=0, maximum=63072000
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
if SECURE_HSTS_PRELOAD and not SECURE_HSTS_INCLUDE_SUBDOMAINS:
    raise ImproperlyConfigured(
        "DJANGO_SECURE_HSTS_PRELOAD requires "
        "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=true."
    )

# Only enable DJANGO_TRUST_PROXY_HEADERS when a trusted reverse proxy in
# front of the app always overwrites X-Forwarded-Proto and the app port is
# not reachable directly from the internet. Otherwise clients could spoof
# the header and defeat the https redirect and secure-cookie logic.
if env_bool("DJANGO_TRUST_PROXY_HEADERS", False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# Email (SMTP) and Wagtail notifications
# ---------------------------------------------------------------------------
# The provider is chosen by the project owner; only the transport contract
# is fixed here. Credentials arrive via the environment and are never
# logged by this configuration.

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ["DJANGO_EMAIL_HOST"].strip()
EMAIL_PORT = _env_int("DJANGO_EMAIL_PORT", 587, minimum=1, maximum=65535)
EMAIL_USE_TLS = env_bool("DJANGO_EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("DJANGO_EMAIL_USE_SSL", False)
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured(
        "DJANGO_EMAIL_USE_TLS and DJANGO_EMAIL_USE_SSL are mutually "
        "exclusive; enable at most one (TLS on port 587 or SSL on 465)."
    )
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", "")
if "change_me" in EMAIL_HOST_PASSWORD.lower() or "change-me" in EMAIL_HOST_PASSWORD.lower():
    raise ImproperlyConfigured(
        "DJANGO_EMAIL_HOST_PASSWORD still contains the template "
        "placeholder from .env.production.example; set the real SMTP "
        "password."
    )
if bool(EMAIL_HOST_USER.strip()) != bool(EMAIL_HOST_PASSWORD):
    raise ImproperlyConfigured(
        "DJANGO_EMAIL_HOST_USER and DJANGO_EMAIL_HOST_PASSWORD must be "
        "provided together (or both omitted for an unauthenticated relay "
        "on a private network)."
    )
EMAIL_TIMEOUT = _env_int("DJANGO_EMAIL_TIMEOUT", 10, minimum=1, maximum=120)
DEFAULT_FROM_EMAIL = os.environ["DJANGO_DEFAULT_FROM_EMAIL"].strip()
SERVER_EMAIL = os.environ.get("DJANGO_SERVER_EMAIL", "").strip() or DEFAULT_FROM_EMAIL

# ---------------------------------------------------------------------------
# Logging: structured-enough plain text to stderr, no secrets, no files.
# The platform (once chosen) owns collection and retention.
# ---------------------------------------------------------------------------

_LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO").strip().upper()
if _LOG_LEVEL not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
    raise ImproperlyConfigured(
        "DJANGO_LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR, "
        "CRITICAL."
    )

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {"handlers": ["console"], "level": _LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": _LOG_LEVEL, "propagate": False},
        "wagtail": {"handlers": ["console"], "level": _LOG_LEVEL, "propagate": False},
    },
}
