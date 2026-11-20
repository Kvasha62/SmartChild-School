import json
from io import StringIO
from urllib.parse import urlsplit

from django.core.management import call_command
from django.test import TestCase
from wagtail.models import Page, PageViewRestriction

from school.models import HomePage, LessonPage


def public_path(page):
    return urlsplit(page.url or page.url_path).path or "/"


class PublicSeoAuditCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = HomePage.objects.get(slug="smartchild-school")

    def make_lesson(
        self,
        *,
        title,
        slug,
        intro="",
        search_description="",
        body=None,
    ):
        page = self.home.add_child(
            instance=LessonPage(
                title=title,
                slug=slug,
                direction="python",
                intro=intro,
                search_description=search_description,
                body=body or [],
                live=False,
            )
        )
        return page

    def publish(self, page):
        page.save_revision().publish()
        return LessonPage.objects.get(pk=page.pk).specific

    def run_json_audit(self):
        output = StringIO()
        call_command("audit_public_seo", output_format="json", stdout=output)
        return json.loads(output.getvalue())

    def test_excludes_structural_root_from_audit(self):
        root = Page.get_first_root_node()
        expected_page_count = (
            Page.objects.live()
            .public()
            .filter(depth__gt=1)
            .count()
        )

        report = self.run_json_audit()
        self.assertEqual(root.depth, 1)
        self.assertNotIn(root.title, [page["title"] for page in report["pages"]])
        self.assertEqual(report["pages_audited"], expected_page_count)

    def test_reports_lessons_that_use_generic_meta_description_fallback(self):
        lesson = self.make_lesson(
            title="Урок без описания",
            slug="seo-audit-generic-description",
        )
        lesson = self.publish(lesson)

        report = self.run_json_audit()

        self.assertIn(
            public_path(lesson),
            [page["path"] for page in report["pages"]],
        )
        self.assertIn(
            {
                "code": "generic_meta_description_fallback",
                "severity": "review",
                "path": public_path(lesson),
                "detail": (
                    "This lesson has neither an explicit Wagtail SEO description "
                    "nor an intro, so the site-wide generic meta description is used."
                ),
            },
            report["findings"],
        )

    def test_reports_image_embeds_without_contextual_alt_attribute(self):
        lesson = self.make_lesson(
            title="Урок с изображениями для аудита",
            slug="seo-audit-image-alt",
            intro="Описание урока.",
            body=[
                (
                    "rich_text",
                    (
                        '<p>Image without contextual alt.</p>'
                        '<embed embedtype="image" id="987" format="fullwidth" />'
                        '<p>Decorative image.</p>'
                        '<embed embedtype="image" id="988" alt="" format="fullwidth" />'
                        '<p>Image with contextual alt.</p>'
                        '<embed embedtype="image" id="989" alt="Схема переменных" format="fullwidth" />'
                    ),
                ),
            ],
        )
        lesson = self.publish(lesson)

        report = self.run_json_audit()
        page_record = next(page for page in report["pages"] if page["path"] == public_path(lesson))
        findings = [
            finding
            for finding in report["findings"]
            if finding["path"] == public_path(lesson)
        ]

        self.assertEqual(page_record["image_count"], 3)
        image_findings = [
            finding for finding in findings
            if finding["code"] == "image_alt_needs_review"
        ]
        self.assertEqual(len(image_findings), 1)
        self.assertIn("no explicit alt attribute", image_findings[0]["detail"])
        # An explicit empty alt may intentionally mark a decorative image.
        self.assertNotIn('id="988"', image_findings[0]["detail"])

    def test_excludes_drafts_and_login_restricted_pages(self):
        public = self.make_lesson(
            title="Публичный урок для аудита",
            slug="seo-audit-public",
            intro="Краткое описание.",
        )
        public = self.publish(public)

        draft = self.make_lesson(
            title="Черновик для аудита",
            slug="seo-audit-draft",
        )

        restricted = self.make_lesson(
            title="Закрытый урок для аудита",
            slug="seo-audit-restricted",
        )
        restricted = self.publish(restricted)
        PageViewRestriction.objects.create(
            page=restricted,
            restriction_type=PageViewRestriction.LOGIN,
        )

        report = self.run_json_audit()
        paths = [page["path"] for page in report["pages"]]

        self.assertIn(public_path(public), paths)
        self.assertNotIn(public_path(draft), paths)
        self.assertNotIn(public_path(restricted), paths)

    def test_reports_duplicate_explicit_titles_and_descriptions(self):
        description = "Одинаковое редакторское описание для проверки."
        first = self.make_lesson(
            title="Повторяющийся заголовок",
            slug="seo-audit-duplicate-first",
            search_description=description,
        )
        second = self.make_lesson(
            title="Повторяющийся заголовок",
            slug="seo-audit-duplicate-second",
            search_description=description,
        )
        first = self.publish(first)
        second = self.publish(second)

        report = self.run_json_audit()
        duplicate_findings = [
            finding for finding in report["findings"]
            if finding["path"] in {public_path(first), public_path(second)}
        ]

        self.assertTrue(
            any(finding["code"] == "duplicate_effective_title" for finding in duplicate_findings)
        )
        self.assertTrue(
            any(
                finding["code"] == "duplicate_explicit_search_description"
                for finding in duplicate_findings
            )
        )
