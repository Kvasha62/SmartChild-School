from unittest.mock import patch

from django.db import DatabaseError, InterfaceError, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase
from django.urls import reverse


class HealthEndpointTests(TestCase):
    def test_live_endpoint_is_available(self):
        response = self.client.get(reverse("health-live"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_live_endpoint_does_not_depend_on_database(self):
        with patch("core.views.connection.cursor", side_effect=InterfaceError("connection closed")):
            response = self.client.get(reverse("health-live"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_ready_endpoint_checks_database(self):
        response = self.client.get(reverse("health-ready"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_ready_endpoint_returns_503_and_logs_database_errors(self):
        errors = (
            DatabaseError("database unavailable"),
            InterfaceError("connection closed"),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                with patch("core.views.connection.cursor", side_effect=error):
                    with self.assertLogs("core.views", level="WARNING") as logs:
                        response = self.client.get(reverse("health-ready"))
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json(), {"status": "unavailable"})
                self.assertTrue(any("Readiness check failed" in entry for entry in logs.output))

    def test_database_query_succeeds(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            self.assertEqual(cursor.fetchone()[0], 1)


class MigrationStateTests(TestCase):
    def test_all_migrations_are_applied(self):
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        self.assertEqual(plan, [])
