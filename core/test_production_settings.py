"""Guarantees for the production settings contract and local email.

The production settings module is validated in a subprocess so importing it
can never pollute the settings of the running test suite. All values are
synthetic; no test contacts a real SMTP server or database.
"""
import json
import os
import subprocess
import sys

from django.conf import settings
from django.core import mail
from django.test import SimpleTestCase

# Every environment variable either settings module may read. The
# subprocess starts from a clean slate for these keys.
MANAGED_KEYS = [
    "DJANGO_SECRET_KEY",
    "DJANGO_DEBUG",
    "DJANGO_ALLOWED_HOSTS",
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "DJANGO_STATIC_ROOT",
    "DJANGO_MEDIA_ROOT",
    "DJANGO_EMAIL_BACKEND",
    "DJANGO_DEFAULT_FROM_EMAIL",
    "DJANGO_SERVER_EMAIL",
    "DJANGO_EMAIL_HOST",
    "DJANGO_EMAIL_PORT",
    "DJANGO_EMAIL_USE_TLS",
    "DJANGO_EMAIL_USE_SSL",
    "DJANGO_EMAIL_HOST_USER",
    "DJANGO_EMAIL_HOST_PASSWORD",
    "DJANGO_EMAIL_TIMEOUT",
    "DJANGO_SECURE_SSL_REDIRECT",
    "DJANGO_SECURE_HSTS_SECONDS",
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    "DJANGO_SECURE_HSTS_PRELOAD",
    "DJANGO_TRUST_PROXY_HEADERS",
    "DJANGO_LOG_LEVEL",
    "DJANGO_SETTINGS_MODULE",
    "WAGTAILADMIN_BASE_URL",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "DB_HOST",
    "DB_PORT",
    "DB_CONN_MAX_AGE",
    "DB_SSLMODE",
]

VALID_PRODUCTION_ENV = {
    "DJANGO_SECRET_KEY": "test-production-secret-key-0123456789abcdef-entropy",
    "DJANGO_DEBUG": "false",
    "DJANGO_ALLOWED_HOSTS": "school.example.invalid",
    "WAGTAILADMIN_BASE_URL": "https://school.example.invalid",
    "DJANGO_MEDIA_ROOT": "/srv/smartchild-test-media",
    "DB_NAME": "smartchild_test",
    "DB_USER": "smartchild_test",
    "DB_PASSWORD": "test-db-password",
    "DB_HOST": "db.example.invalid",
    "DB_PORT": "5432",
    "DJANGO_EMAIL_HOST": "smtp.example.invalid",
    "DJANGO_EMAIL_HOST_USER": "mailer@example.invalid",
    "DJANGO_EMAIL_HOST_PASSWORD": "test-mail-password",
    "DJANGO_DEFAULT_FROM_EMAIL": "no-reply@example.invalid",
}


def import_settings(module: str, overrides: dict, remove=()):
    env = {k: v for k, v in os.environ.items() if k not in MANAGED_KEYS}
    env.update(overrides)
    for key in remove:
        env.pop(key, None)
    code = (
        "import json, importlib; s = importlib.import_module(%r); "
        "print(json.dumps({"
        "'DEBUG': s.DEBUG, 'ALLOWED_HOSTS': list(s.ALLOWED_HOSTS), "
        "'EMAIL_BACKEND': s.EMAIL_BACKEND, "
        "'SESSION_COOKIE_SECURE': getattr(s, 'SESSION_COOKIE_SECURE', False), "
        "'CSRF_COOKIE_SECURE': getattr(s, 'CSRF_COOKIE_SECURE', False), "
        "'SECURE_SSL_REDIRECT': getattr(s, 'SECURE_SSL_REDIRECT', False), "
        "'CSRF_TRUSTED_ORIGINS': list(s.CSRF_TRUSTED_ORIGINS), "
        "'WAGTAILADMIN_BASE_URL': s.WAGTAILADMIN_BASE_URL, "
        "'MEDIA_ROOT': str(s.MEDIA_ROOT), "
        "'MIDDLEWARE': list(s.MIDDLEWARE), "
        "'EMAIL_HOST': getattr(s, 'EMAIL_HOST', ''), "
        "'EMAIL_USE_TLS': getattr(s, 'EMAIL_USE_TLS', False), "
        "'DEFAULT_FROM_EMAIL': s.DEFAULT_FROM_EMAIL"
        "}))" % module
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


class ProductionSettingsContractTests(SimpleTestCase):
    def assert_import_fails(self, overrides, *expected_fragments, remove=()):
        env = dict(VALID_PRODUCTION_ENV)
        env.update(overrides)
        result = import_settings("config.production_settings", env, remove=remove)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        for fragment in expected_fragments:
            self.assertIn(fragment, result.stderr)
        return result

    def test_valid_production_env_enables_hardened_settings(self):
        result = import_settings(
            "config.production_settings", dict(VALID_PRODUCTION_ENV)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        values = json.loads(result.stdout)
        self.assertFalse(values["DEBUG"])
        self.assertEqual(values["ALLOWED_HOSTS"], ["school.example.invalid"])
        self.assertEqual(
            values["EMAIL_BACKEND"], "django.core.mail.backends.smtp.EmailBackend"
        )
        self.assertTrue(values["SESSION_COOKIE_SECURE"])
        self.assertTrue(values["CSRF_COOKIE_SECURE"])
        self.assertTrue(values["SECURE_SSL_REDIRECT"])
        self.assertEqual(
            values["CSRF_TRUSTED_ORIGINS"], ["https://school.example.invalid"]
        )
        self.assertEqual(
            values["WAGTAILADMIN_BASE_URL"], "https://school.example.invalid"
        )
        self.assertEqual(values["MEDIA_ROOT"], "/srv/smartchild-test-media")
        self.assertEqual(values["EMAIL_HOST"], "smtp.example.invalid")
        self.assertTrue(values["EMAIL_USE_TLS"])
        self.assertIn(
            "whitenoise.middleware.WhiteNoiseMiddleware", values["MIDDLEWARE"]
        )

    def test_missing_secret_key_is_rejected(self):
        self.assert_import_fails({}, "DJANGO_SECRET_KEY", remove=("DJANGO_SECRET_KEY",))

    def test_placeholder_and_short_secret_keys_are_rejected(self):
        for bad_key in (
            "replace-me-with-a-random-secret",
            "CHANGE_ME_generate_a_random_50_plus_character_secret",
            "short-key",
        ):
            with self.subTest(key_kind=bad_key[:12]):
                self.assert_import_fails(
                    {"DJANGO_SECRET_KEY": bad_key}, "DJANGO_SECRET_KEY"
                )

    def test_debug_true_is_rejected(self):
        self.assert_import_fails({"DJANGO_DEBUG": "true"}, "DJANGO_DEBUG")

    def test_wildcard_allowed_hosts_is_rejected(self):
        self.assert_import_fails(
            {"DJANGO_ALLOWED_HOSTS": "*"}, "DJANGO_ALLOWED_HOSTS"
        )

    def test_empty_database_password_is_rejected(self):
        self.assert_import_fails({"DB_PASSWORD": ""}, "DB_PASSWORD")

    def test_http_admin_base_url_is_rejected(self):
        self.assert_import_fails(
            {"WAGTAILADMIN_BASE_URL": "http://school.example.invalid"},
            "WAGTAILADMIN_BASE_URL",
        )

    def test_missing_media_root_is_rejected(self):
        self.assert_import_fails({}, "DJANGO_MEDIA_ROOT", remove=("DJANGO_MEDIA_ROOT",))

    def test_conflicting_email_tls_and_ssl_are_rejected(self):
        self.assert_import_fails(
            {"DJANGO_EMAIL_USE_TLS": "true", "DJANGO_EMAIL_USE_SSL": "true"},
            "DJANGO_EMAIL_USE_TLS",
        )

    def test_errors_do_not_leak_secret_values(self):
        canary_password = "canary-mail-password-do-not-print"
        result = self.assert_import_fails(
            {
                "DJANGO_EMAIL_HOST_PASSWORD": canary_password,
                "DJANGO_EMAIL_USE_TLS": "true",
                "DJANGO_EMAIL_USE_SSL": "true",
            },
            "DJANGO_EMAIL_USE_TLS",
        )
        self.assertNotIn(canary_password, result.stderr)
        self.assertNotIn(VALID_PRODUCTION_ENV["DJANGO_SECRET_KEY"], result.stderr)
        self.assertNotIn(VALID_PRODUCTION_ENV["DB_PASSWORD"], result.stderr)


class LocalEmailSettingsTests(SimpleTestCase):
    def test_development_settings_default_to_console_email(self):
        result = import_settings(
            "config.settings",
            {"DJANGO_SECRET_KEY": "test-local-secret-key-for-settings-import-only"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        values = json.loads(result.stdout)
        self.assertEqual(
            values["EMAIL_BACKEND"],
            "django.core.mail.backends.console.EmailBackend",
        )

    def test_sending_mail_in_tests_needs_no_smtp_server(self):
        sent = mail.send_mail(
            "Synthetic subject",
            "Synthetic body",
            "no-reply@example.invalid",
            ["editor@example.invalid"],
        )
        self.assertEqual(sent, 1)
        self.assertEqual(len(mail.outbox), 1)
