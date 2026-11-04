import json
import uuid

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class NestedContentMigrationTests(TransactionTestCase):
    serialized_rollback = True
    migrate_from = ("school", "0005_accordion_stream_content")
    migrate_to = ("school", "0006_alter_lessonpage_body")

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

        self.legacy_body = [
            {
                "type": "tabs",
                "id": "top-tabs",
                "value": {
                    "tabs": [
                        {"title": "Первая", "content": "<p>Первая вкладка</p>"},
                        {"title": "Пустая", "content": ""},
                    ],
                },
            },
            {
                "type": "callout",
                "id": "top-callout",
                "value": {
                    "kind": "info",
                    "content": "",
                },
            },
            {
                "type": "accordion",
                "value": {
                    "title": "Раздел",
                    "content": [
                        {
                            "type": "rich_text",
                            "id": "b9aeb9d7-9e13-4f8a-8e8b-6fcd9f1c6d0a",
                            "value": "<p>Обычный текст</p>",
                        },
                        {
                            "type": "tabs",
                            "id": "nested-tabs",
                            "value": {
                                "tabs": [
                                    {
                                        "title": "Вложенная",
                                        "content": "<p>Вложенный текст</p>",
                                    },
                                    {
                                        "title": "Вложенная пустая",
                                        "content": "",
                                    },
                                ],
                            },
                        },
                        {
                            "type": "callout",
                            "id": "nested-callout",
                            "value": {
                                "kind": "warning",
                                "content": "<p>Вложенная заметка</p>",
                            },
                        },
                        {
                            "type": "code",
                            "id": "existing-code",
                            "value": {
                                "language": "python",
                                "code": "print(1)",
                            },
                        },
                    ],
                },
            },
        ]

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO wagtailcore_page (
                    path, depth, numchild, title, slug, live,
                    has_unpublished_changes, url_path, seo_title,
                    show_in_menus, search_description, expired,
                    content_type_id, locked, draft_title,
                    translation_key, locale_id
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                [
                    "91000001",
                    2,
                    0,
                    "Nested migration test",
                    "nested-migration-test",
                    False,
                    True,
                    "/nested-migration-test/",
                    "",
                    False,
                    "",
                    False,
                    page_content_type.pk,
                    False,
                    "Nested migration test",
                    "00000000-0000-0000-0000-000000000601",
                    locale.pk,
                ],
            )
            self.page_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO school_lessonpage (
                    page_ptr_id, direction, intro, video_embed_url,
                    body, search_keywords
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [
                    self.page_id,
                    "python",
                    "",
                    "",
                    json.dumps(self.legacy_body, ensure_ascii=False),
                    "",
                ],
            )

        revision = Revision.objects.using(database).create(
            created_at=timezone.now(),
            content={
                "title": "Nested migration test",
                "body": self.legacy_body,
            },
            object_id=str(self.page_id),
            content_type_id=lesson_content_type.pk,
            base_content_type_id=lesson_content_type.pk,
            object_str="Nested migration test",
        )
        self.revision_id = revision.pk

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])

    def restore_migrations(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.latest_targets)

    def read_page_body(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT body
                FROM school_lessonpage
                WHERE page_ptr_id = %s
                """,
                [self.page_id],
            )
            row = cursor.fetchone()

        self.assertIsNotNone(row)
        body = row[0]

        if isinstance(body, str):
            return json.loads(body)

        return body

    def get_revision(self, target):
        executor = MigrationExecutor(connection)
        apps = executor.loader.project_state([target]).apps
        Revision = apps.get_model("wagtailcore", "Revision")
        return Revision.objects.using(connection.alias).get(
            pk=self.revision_id
        )

    def test_forward_conversion_uses_index_for_empty_container_ids(self):
        import importlib

        migration = importlib.import_module(
            "school.migrations.0006_alter_lessonpage_body"
        )
        blocks = [
            {
                "type": "callout",
                "id": None,
                "value": {"kind": "info", "content": "<p>Первый</p>"},
            },
            {
                "type": "callout",
                "id": "",
                "value": {"kind": "info", "content": "<p>Второй</p>"},
            },
        ]

        converted, changed = migration.forward_blocks(
            blocks,
            "empty container IDs fixture",
        )

        self.assertTrue(changed)
        first_id = converted[0]["value"]["content"][0]["id"]
        second_id = converted[1]["value"]["content"][0]["id"]

        self.assertNotEqual(first_id, second_id)
        self.assertEqual(str(uuid.UUID(first_id)), first_id)
        self.assertEqual(str(uuid.UUID(second_id)), second_id)
        self.assertEqual(
            [block["value"]["content"][0]["value"] for block in converted],
            ["<p>Первый</p>", "<p>Второй</p>"],
        )

    def test_forward_conversion_enforces_five_container_levels(self):
        import importlib

        migration = importlib.import_module(
            "school.migrations.0006_alter_lessonpage_body"
        )

        def nested_callouts(count):
            content = [{
                "type": "rich_text",
                "id": "leaf",
                "value": "<p>Текст</p>",
            }]

            for level in reversed(range(count)):
                content = [{
                    "type": "callout",
                    "id": f"callout-{level}",
                    "value": {
                        "kind": "info",
                        "content": content,
                    },
                }]

            return content

        # Пять уровней контейнеров должны успешно преобразовываться.
        five_levels = nested_callouts(5)
        converted, _ = migration.forward_blocks(
            five_levels,
            "five-level fixture",
        )
        self.assertEqual(converted, five_levels)

        # Шестой уровень должен быть отклонён.
        with self.assertRaisesRegex(
            ValueError,
            "container nesting exceeds 5 levels",
        ):
            migration.forward_blocks(
                nested_callouts(6),
                "six-level fixture",
            )

    def test_reverse_0005_rejects_multiple_rich_text_children(self):
        import importlib

        migration = importlib.import_module(
            "school.migrations.0005_accordion_stream_content"
        )
        blocks = [{
            "type": "accordion",
            "id": "outer",
            "value": {
                "title": "Раздел",
                "content": [
                    {
                        "type": "rich_text",
                        "id": "first",
                        "value": "<p>Первый фрагмент</p>",
                    },
                    {
                        "type": "rich_text",
                        "id": "second",
                        "value": "<p>Второй фрагмент</p>",
                    },
                ],
            },
        }]

        with self.assertRaisesRegex(RuntimeError, "multiple rich_text blocks"):
            migration.backward_blocks(blocks, "test page")

    def test_forward_migration_converts_pages_and_revisions(self):
        page_body = self.read_page_body()

        top_tabs = page_body[0]["value"]["tabs"]
        self.assertEqual(
            top_tabs[0]["content"][0]["value"],
            "<p>Первая вкладка</p>",
        )
        self.assertEqual(top_tabs[1]["content"][0]["value"], "")

        top_callout = page_body[1]["value"]["content"]
        self.assertEqual(len(top_callout), 1)
        self.assertEqual(top_callout[0]["type"], "rich_text")
        self.assertEqual(top_callout[0]["value"], "")

        accordion_content = page_body[2]["value"]["content"]
        self.assertEqual(
            accordion_content[0]["value"],
            "<p>Обычный текст</p>",
        )

        nested_tabs = accordion_content[1]["value"]["tabs"]
        self.assertEqual(
            nested_tabs[0]["content"][0]["value"],
            "<p>Вложенный текст</p>",
        )
        self.assertEqual(nested_tabs[1]["content"][0]["value"], "")

        nested_callout = accordion_content[2]["value"]["content"]
        self.assertEqual(
            nested_callout[0]["value"],
            "<p>Вложенная заметка</p>",
        )

        self.assertEqual(accordion_content[3]["type"], "code")
        self.assertEqual(
            accordion_content[3]["value"]["code"],
            "print(1)",
        )

        # Every rich-text block must have a valid, unique UUID.
        def collect_rich_text_ids(blocks):
            result = []
            for block in blocks:
                if block["type"] == "rich_text":
                    value = block.get("id")
                    self.assertIsNotNone(value)
                    self.assertEqual(str(uuid.UUID(str(value))), str(value))
                    result.append(str(value))
                elif block["type"] == "tabs":
                    for item in block["value"]["tabs"]:
                        result.extend(collect_rich_text_ids(item["content"]))
                elif block["type"] in ("callout", "accordion"):
                    result.extend(
                        collect_rich_text_ids(block["value"]["content"])
                    )
            return result

        page_rich_text_ids = collect_rich_text_ids(page_body)
        self.assertEqual(
            len(page_rich_text_ids),
            len(set(page_rich_text_ids)),
            "Rich-text UUIDs must be unique within the page.",
        )

        revision = self.get_revision(self.migrate_to)
        self.assertEqual(revision.content["body"], page_body)

        revision_rich_text_ids = collect_rich_text_ids(
            revision.content["body"]
        )
        self.assertEqual(
            revision_rich_text_ids,
            page_rich_text_ids,
            "Page and revision must preserve all corresponding rich-text UUIDs.",
        )

    def test_reverse_migration_restores_original_content(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])

        self.assertEqual(self.read_page_body(), self.legacy_body)

        revision = self.get_revision(self.migrate_from)
        self.assertEqual(revision.content["body"], self.legacy_body)

    def test_reverse_migration_rejects_multiple_rich_text_blocks(self):
        executor = MigrationExecutor(connection)
        apps = executor.loader.project_state([self.migrate_to]).apps
        LessonPage = apps.get_model("school", "LessonPage")

        body = self.read_page_body()
        body[0]["value"]["tabs"][0]["content"] = [
            {
                "type": "rich_text",
                "id": "first-rich-text",
                "value": "<p>Первый фрагмент</p>",
            },
            {
                "type": "rich_text",
                "id": "second-rich-text",
                "value": "<p>Второй фрагмент</p>",
            },
        ]

        LessonPage.objects.using(connection.alias).filter(
            pk=self.page_id
        ).update(body=body)

        with self.assertRaisesRegex(RuntimeError, "without data loss"):
            executor.migrate([self.migrate_from])

        # Failed reverse migration must not partially rewrite the page.
        self.assertEqual(self.read_page_body(), body)

        # The migration must remain applied after the failed reversal.
        current_executor = MigrationExecutor(connection)
        self.assertIn(
            self.migrate_to,
            current_executor.loader.applied_migrations,
        )

    def test_forward_conversion_handles_nested_accordions(self):
        import importlib

        migration = importlib.import_module(
            "school.migrations.0006_alter_lessonpage_body"
        )
        blocks = [{
            "type": "accordion",
            "id": "outer-accordion",
            "value": {
                "title": "Внешний раздел",
                "content": [{
                    "type": "accordion",
                    "id": "inner-accordion",
                    "value": {
                        "title": "Внутренний раздел",
                        "content": [{
                            "type": "callout",
                            "id": "nested-callout",
                            "value": {
                                "kind": "info",
                                "content": "<p>Вложенная заметка</p>",
                            },
                        }],
                    },
                }],
            },
        }]

        converted, changed = migration.forward_blocks(
            blocks,
            "nested accordion fixture",
        )

        self.assertTrue(changed)
        nested_callout = (
            converted[0]["value"]["content"][0]["value"]["content"][0]
        )
        self.assertEqual(nested_callout["type"], "callout")
        self.assertEqual(
            nested_callout["value"]["content"][0]["value"],
            "<p>Вложенная заметка</p>",
        )
        self.assertTrue(
            nested_callout["value"]["content"][0].get("id")
        )

    def test_forward_conversion_handles_nested_tabs(self):
        import importlib

        migration = importlib.import_module(
            "school.migrations.0006_alter_lessonpage_body"
        )
        blocks = [{
            "type": "tabs",
            "id": "outer-tabs",
            "value": {
                "tabs": [{
                    "title": "Внешняя вкладка",
                    "content": [{
                        "type": "tabs",
                        "id": "inner-tabs",
                        "value": {
                            "tabs": [{
                                "title": "Внутренняя вкладка",
                                "content": "<p>Глубокий текст</p>",
                            }],
                        },
                    }],
                }],
            },
        }]

        converted, changed = migration.forward_blocks(
            blocks,
            "nested tabs fixture",
        )

        self.assertTrue(changed)
        inner_tabs = (
            converted[0]["value"]["tabs"][0]["content"][0]
        )
        self.assertEqual(inner_tabs["type"], "tabs")
        inner_content = (
            inner_tabs["value"]["tabs"][0]["content"]
        )
        self.assertEqual(len(inner_content), 1)
        self.assertEqual(inner_content[0]["type"], "rich_text")
        self.assertEqual(
            inner_content[0]["value"],
            "<p>Глубокий текст</p>",
        )
        self.assertTrue(inner_content[0].get("id"))

    def test_reverse_migration_rejects_nested_accordion(self):
        executor = MigrationExecutor(connection)
        apps = executor.loader.project_state([self.migrate_to]).apps
        LessonPage = apps.get_model("school", "LessonPage")

        body = self.read_page_body()
        body[2]["value"]["content"].append({
            "type": "accordion",
            "id": "nested-accordion",
            "value": {
                "title": "Вложенный раздел",
                "content": [{
                    "type": "rich_text",
                    "id": "nested-rich-text",
                    "value": "<p>Вложенный текст</p>",
                }],
            },
        })

        LessonPage.objects.using(connection.alias).filter(
            pk=self.page_id
        ).update(body=body)

        with self.assertRaises(RuntimeError):
            executor.migrate([self.migrate_from])

        self.assertEqual(self.read_page_body(), body)

        current_executor = MigrationExecutor(connection)
        self.assertIn(
            self.migrate_to,
            current_executor.loader.applied_migrations,
        )

    def test_reverse_migration_revision_error_does_not_partially_update_page(self):
        page_body_before = self.read_page_body()
        revision = self.get_revision(self.migrate_to)
        revision_content_before = json.loads(json.dumps(revision.content))

        revision_content = revision.content
        revision_content["body"][0]["value"]["tabs"][0]["content"] = [
            {
                "type": "rich_text",
                "id": "revision-first-rich-text",
                "value": "<p>Первый фрагмент</p>",
            },
            {
                "type": "rich_text",
                "id": "revision-second-rich-text",
                "value": "<p>Второй фрагмент</p>",
            },
        ]

        executor = MigrationExecutor(connection)
        apps = executor.loader.project_state([self.migrate_to]).apps
        Revision = apps.get_model("wagtailcore", "Revision")

        Revision.objects.using(connection.alias).filter(
            pk=self.revision_id
        ).update(content=revision_content)

        with self.assertRaises(RuntimeError):
            executor.migrate([self.migrate_from])

        self.assertEqual(self.read_page_body(), page_body_before)

        revision_after = self.get_revision(self.migrate_to)
        self.assertEqual(
            revision_after.content,
            revision_content,
        )
        self.assertNotEqual(
            revision_after.content,
            revision_content_before,
        )

        current_executor = MigrationExecutor(connection)
        self.assertIn(
            self.migrate_to,
            current_executor.loader.applied_migrations,
        )

    def test_reverse_conversion_rejects_code_inside_tabs_and_callout(self):
        import importlib

        migration = importlib.import_module(
            "school.migrations.0006_alter_lessonpage_body"
        )
        cases = [
            (
                "tabs",
                {
                    "tabs": [{
                        "title": "Вкладка",
                        "content": [{
                            "type": "code",
                            "id": "tabs-code",
                            "value": {
                                "language": "python",
                                "code": "print(1)",
                            },
                        }],
                    }],
                },
            ),
            (
                "callout",
                {
                    "kind": "info",
                    "content": [{
                        "type": "code",
                        "id": "callout-code",
                        "value": {
                            "language": "python",
                            "code": "print(2)",
                        },
                    }],
                },
            ),
        ]

        for block_type, value in cases:
            with self.subTest(block_type=block_type):
                blocks = [{
                    "type": block_type,
                    "id": f"{block_type}-block",
                    "value": value,
                }]

                with self.assertRaisesRegex(
                    RuntimeError,
                    "without data loss",
                ):
                    migration.backward_blocks(
                        blocks,
                        f"{block_type} reverse fixture",
                    )
