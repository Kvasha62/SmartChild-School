import json

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class LessonBodyMigrationTests(TransactionTestCase):
    migrate_from = ("school", "0002_lessonpage_video_embed_url")
    migrate_to = ("school", "0003_alter_lessonpage_body")

    def setUp(self):
        super().setUp()

        executor = MigrationExecutor(connection)
        self.latest_targets = executor.loader.graph.leaf_nodes()
        self.addCleanup(self.restore_migrations)

        executor.migrate([self.migrate_from])

        old_apps = executor.loader.project_state(
            [self.migrate_from]
        ).apps

        database = connection.alias
        Revision = old_apps.get_model("wagtailcore", "Revision")
        ContentType = old_apps.get_model("contenttypes", "ContentType")
        Locale = old_apps.get_model("wagtailcore", "Locale")

        locale, _ = Locale.objects.using(database).get_or_create(
            language_code="ru",
        )

        page_content_type, _ = ContentType.objects.using(
            database
        ).get_or_create(
            app_label="wagtailcore",
            model="page",
            defaults={"name": "page"},
        )

        lesson_content_type, _ = ContentType.objects.using(
            database
        ).get_or_create(
            app_label="school",
            model="lessonpage",
            defaults={"name": "lesson page"},
        )

        self.html = "<p>Старый <strong>HTML</strong></p>"

        def create_lesson(slug, body, path_suffix):
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO wagtailcore_page (
                        path,
                        depth,
                        numchild,
                        title,
                        slug,
                        live,
                        has_unpublished_changes,
                        url_path,
                        seo_title,
                        show_in_menus,
                        search_description,
                        expired,
                        content_type_id,
                        locked,
                        draft_title,
                        translation_key,
                        locale_id
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING id
                    """,
                    [
                        f"9000{path_suffix:04d}",
                        2,
                        0,
                        slug,
                        slug,
                        False,
                        True,
                        f"/{slug}/",
                        "",
                        False,
                        "",
                        False,
                        page_content_type.pk,
                        False,
                        slug,
                        f"00000000-0000-0000-0000-{path_suffix:012d}",
                        locale.pk,
                    ],
                )
                page_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO school_lessonpage (
                        page_ptr_id,
                        direction,
                        intro,
                        video_embed_url,
                        body
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [
                        page_id,
                        "python",
                        "",
                        "",
                        body,
                    ],
                )

            return page_id

        self.lesson_id = create_lesson(
            "migration-test-legacy",
            self.html,
            1,
        )

        self.empty_lesson_id = create_lesson(
            "migration-test-empty",
            "",
            2,
        )

        revision = Revision.objects.using(database).create(
            created_at=timezone.now(),
            content={
                "title": "Legacy lesson",
                "body": self.html,
            },
            object_id=str(self.lesson_id),
            content_type_id=lesson_content_type.pk,
            base_content_type_id=lesson_content_type.pk,
            object_str="Legacy lesson",
        )
        self.revision_id = revision.pk

        # An orphan revision represents a lesson whose page was deleted.
        orphan_revision = Revision.objects.using(database).create(
            created_at=timezone.now(),
            content={
                "title": "Deleted lesson",
                "body": self.html,
            },
            object_id="99999999",
            content_type_id=lesson_content_type.pk,
            base_content_type_id=lesson_content_type.pk,
            object_str="Deleted lesson",
        )
        self.orphan_revision_id = orphan_revision.pk

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])

    def restore_migrations(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.latest_targets)

    def read_raw_body(self, page_id):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT body
                FROM school_lessonpage
                WHERE page_ptr_id = %s
                """,
                [page_id],
            )
            row = cursor.fetchone()

        self.assertIsNotNone(row)
        body = row[0]

        if isinstance(body, str) and body:
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return body

        return body

    def test_forward_migration_preserves_page_revision_and_empty_body(self):
        self.assertEqual(
            self.read_raw_body(self.lesson_id),
            [{"type": "rich_text", "value": self.html}],
        )

        self.assertEqual(
            self.read_raw_body(self.empty_lesson_id),
            [],
        )

        executor = MigrationExecutor(connection)
        new_apps = executor.loader.project_state(
            [self.migrate_to]
        ).apps
        Revision = new_apps.get_model("wagtailcore", "Revision")

        revision = Revision.objects.using(connection.alias).get(
            pk=self.revision_id,
        )

        self.assertEqual(
            revision.content["body"],
            [{"type": "rich_text", "value": self.html}],
        )

        orphan_revision = Revision.objects.using(connection.alias).get(
            pk=self.orphan_revision_id,
        )

        self.assertEqual(
            orphan_revision.content["body"],
            [{"type": "rich_text", "value": self.html}],
        )

    def test_reverse_migration_restores_legacy_html(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])

        self.assertEqual(
            self.read_raw_body(self.lesson_id),
            self.html,
        )

        self.assertEqual(
            self.read_raw_body(self.empty_lesson_id),
            "",
        )

        old_apps = executor.loader.project_state(
            [self.migrate_from]
        ).apps
        Revision = old_apps.get_model("wagtailcore", "Revision")

        revision = Revision.objects.using(connection.alias).get(
            pk=self.revision_id,
        )

        self.assertEqual(
            revision.content["body"],
            self.html,
        )

        orphan_revision = Revision.objects.using(connection.alias).get(
            pk=self.orphan_revision_id,
        )

        self.assertEqual(
            orphan_revision.content["body"],
            self.html,
        )

    def test_reverse_migration_refuses_to_lose_non_rich_text_blocks(self):
        executor = MigrationExecutor(connection)
        new_apps = executor.loader.project_state(
            [self.migrate_to]
        ).apps
        LessonPage = new_apps.get_model("school", "LessonPage")

        code_block = [
            {
                "type": "code",
                "value": {
                    "language": "python",
                    "code": "print(1)",
                },
            }
        ]

        LessonPage.objects.using(connection.alias).filter(
            pk=self.lesson_id,
        ).update(body=code_block)

        with self.assertRaisesRegex(RuntimeError, "non-rich_text"):
            executor.migrate([self.migrate_from])

        # A failed reverse migration must leave the original StreamField data.
        executor = MigrationExecutor(connection)
        current_apps = executor.loader.project_state(
            [self.migrate_to]
        ).apps
        LessonPage = current_apps.get_model("school", "LessonPage")

        page = LessonPage.objects.using(connection.alias).get(
            pk=self.lesson_id,
        )

        self.assertEqual(len(page.body.raw_data), 1)
        self.assertEqual(page.body.raw_data[0]["type"], "code")
        self.assertEqual(
            page.body.raw_data[0]["value"]["code"],
            "print(1)",
        )
        self.assertEqual(
            page.body.raw_data[0]["value"]["language"],
            "python",
        )
