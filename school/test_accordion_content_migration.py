import importlib

from django.test import TestCase


class AccordionContentMigrationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.migration = importlib.import_module(
            "school.migrations.0005_accordion_stream_content"
        )

    def test_forward_and_backward_conversion_preserve_legacy_content(self):
        original_html = '<p>Старое содержимое</p><pre>print("ok")</pre>'
        original = [{
            "type": "accordion",
            "id": "outer-block-id",
            "value": {
                "title": "Заголовок",
                "content": original_html,
                "custom": "preserve-me",
            },
        }, {
            "type": "rich_text",
            "id": "following-block-id",
            "value": "<p>Обычный блок</p>",
        }]

        converted, changed = self.migration.forward_blocks(
            original, "test page"
        )

        self.assertTrue(changed)
        self.assertEqual(converted[0]["id"], "outer-block-id")
        self.assertEqual(converted[0]["value"]["title"], "Заголовок")
        self.assertEqual(converted[0]["value"]["custom"], "preserve-me")
        self.assertEqual(
            converted[0]["value"]["content"][0]["type"], "rich_text"
        )
        self.assertEqual(
            converted[0]["value"]["content"][0]["value"], original_html
        )
        self.assertTrue(converted[0]["value"]["content"][0]["id"])
        self.assertEqual(converted[1], original[1])

        restored, changed_back = self.migration.backward_blocks(
            converted, "test page"
        )

        self.assertTrue(changed_back)
        self.assertEqual(restored, original)

    def test_forward_conversion_leaves_non_accordion_blocks_unchanged(self):
        original = [{
            "type": "rich_text",
            "id": "text-id",
            "value": "<p>Текст</p>",
        }]

        converted, changed = self.migration.forward_blocks(
            original, "test page"
        )

        self.assertFalse(changed)
        self.assertEqual(converted, original)

    def test_forward_conversion_rejects_unexpected_legacy_content(self):
        original = [{
            "type": "accordion",
            "id": "outer-id",
            "value": {"title": "Заголовок", "content": []},
        }]

        with self.assertRaisesRegex(ValueError, "unexpected content"):
            self.migration.forward_blocks(original, "test page")

    def test_reverse_conversion_rejects_non_rich_text_children(self):
        for child_type in ("code", "tabs", "callout"):
            with self.subTest(child_type=child_type):
                blocks = [{
                    "type": "accordion",
                    "id": "outer-id",
                    "value": {
                        "title": "Заголовок",
                        "content": [{
                            "type": child_type,
                            "id": "nested-id",
                            "value": {},
                        }],
                    },
                }]

                with self.assertRaisesRegex(RuntimeError, "without data loss"):
                    self.migration.backward_blocks(blocks, "test page")
