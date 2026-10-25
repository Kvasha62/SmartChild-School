import importlib
from types import SimpleNamespace

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from wagtail.models import PageViewRestriction, Site

from school.models import DIRECTION_CHOICES, HomePage, LessonPage


class PublicLearningFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = HomePage.objects.get(slug="smartchild-school")

    def make_lesson(
        self,
        *,
        title,
        slug,
        direction,
        intro="",
        body=None,
        video_embed_url="",
    ):
        if isinstance(body, str):
            body = [("rich_text", body)] if body else []

        return self.home.add_child(
            instance=LessonPage(
                title=title,
                slug=slug,
                direction=direction,
                intro=intro,
                body=body or [],
                video_embed_url=video_embed_url,
                live=False,
            )
        )

    def publish(self, page):
        page.save_revision().publish()
        return page.specific

    def test_homepage_shows_all_six_directions_without_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Scratch")
        self.assertContains(response, "Roblox")
        self.assertContains(response, "Python")
        self.assertContains(response, "Unity")
        self.assertContains(response, "ОГЭ")
        self.assertContains(response, "ЕГЭ")

    def test_draft_is_not_listed_or_publicly_accessible(self):
        draft = self.make_lesson(
            title="Черновик Python",
            slug="draft-python",
            direction="python",
            intro="Не должен появиться публично",
        )

        catalogue = self.client.get("/")
        self.assertNotContains(catalogue, "Черновик Python")
        detail = self.client.get(draft.url)
        self.assertEqual(detail.status_code, 404)

    def test_published_lesson_appears_in_catalogue_and_opens_publicly(self):
        lesson = self.make_lesson(
            title="Первый шаг в Python",
            slug="pervyi-shag-python",
            direction="python",
            intro="Знакомимся с Python.",
            body="<p>Это синтетический учебный пример.</p>",
        )
        lesson = self.publish(lesson)

        catalogue = self.client.get("/")
        self.assertEqual(catalogue.status_code, 200)
        self.assertContains(catalogue, "Первый шаг в Python")
        self.assertContains(catalogue, "Знакомимся с Python.")

        detail = self.client.get(lesson.url)
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Это синтетический учебный пример.")
        self.assertContains(detail, "Python")
        self.assertNotContains(detail, "<iframe")

    def test_valid_rutube_embed_url_is_rendered_in_lesson(self):
        embed_url = "https://rutube.ru/play/embed/abc123_XYZ-9/"
        lesson = self.make_lesson(
            title="Урок с видео",
            slug="urok-s-video",
            direction="python",
            video_embed_url=embed_url,
        )
        lesson = self.publish(lesson)

        response = self.client.get(lesson.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<iframe src="' + embed_url + '"')
        self.assertContains(response, "allowfullscreen")

    def test_rutube_embed_url_validator_accepts_only_expected_https_player_urls(self):
        field = LessonPage._meta.get_field("video_embed_url")
        valid_url = "https://rutube.ru/play/embed/abc123_XYZ-9/"
        self.assertEqual(field.clean(valid_url, None), valid_url)
        self.assertEqual(field.clean("", None), "")

        invalid_urls = [
            "http://rutube.ru/play/embed/abc123",
            "https://example.com/play/embed/abc123",
            "https://rutube.ru.evil.example/play/embed/abc123",
            "https://rutube.ru/video/abc123",
            "https://rutube.ru@evil.example/play/embed/abc123",
            "https://rutube.ru:8443/play/embed/abc123",
            "https://rutube.ru/play/embed/abc123#fragment",
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValidationError):
                    field.clean(url, None)

    def test_each_direction_filter_only_shows_matching_published_lessons(self):
        lessons = {}
        for direction, label in DIRECTION_CHOICES:
            lesson = self.make_lesson(
                title=f"Тестовый урок {label}",
                slug=f"test-lesson-{direction}",
                direction=direction,
            )
            lessons[direction] = self.publish(lesson)

        for direction, _label in DIRECTION_CHOICES:
            with self.subTest(direction=direction):
                response = self.client.get(f"/?direction={direction}")
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, lessons[direction].title)
                for other_direction, other_lesson in lessons.items():
                    if other_direction != direction:
                        self.assertNotContains(response, other_lesson.title)

    def test_unknown_direction_filter_falls_back_to_all_published_materials(self):
        lesson = self.make_lesson(
            title="Опубликованный урок",
            slug="published-lesson",
            direction="python",
        )
        self.publish(lesson)

        response = self.client.get("/?direction=not-a-direction")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Опубликованный урок")

    def test_restricted_lesson_is_not_listed_or_open_to_anonymous_visitors(self):
        lesson = self.make_lesson(
            title="Закрытый урок",
            slug="closed-lesson",
            direction="unity",
        )
        lesson = self.publish(lesson)
        PageViewRestriction.objects.create(
            page=lesson,
            restriction_type=PageViewRestriction.LOGIN,
        )

        catalogue = self.client.get("/")
        self.assertNotContains(catalogue, "Закрытый урок")
        detail = self.client.get(lesson.url)
        self.assertIn(detail.status_code, (302, 403))

    def test_homepage_migration_can_be_reversed_and_reapplied(self):
        migration = importlib.import_module("school.migrations.0001_initial")
        site = Site.objects.get(is_default_site=True)
        parent_id = self.home.get_parent().pk
        schema_editor = SimpleNamespace(connection=connection)

        migration.delete_homepage(django_apps, schema_editor)
        self.assertFalse(HomePage.objects.filter(slug="smartchild-school").exists())
        site.refresh_from_db()
        self.assertEqual(site.root_page_id, parent_id)

        migration.create_homepage(django_apps, schema_editor)
        recreated_home = HomePage.objects.get(slug="smartchild-school")
        site.refresh_from_db()
        self.assertEqual(site.root_page_id, recreated_home.pk)

    def test_russian_lesson_title_generates_latin_slug_on_server(self):
        form_class = LessonPage.get_edit_handler().get_form_class()
        form = form_class(
            data={
                "title": "Условия и циклы",
                "slug": "",
                "direction": "python",
                "body-count": "0",
                "body": "",
            }
        )

        # The field intentionally has no Wagtail w-slug JS handler; server-side
        # generation must not depend on Wagtail's client-side transliteration map.
        self.assertNotIn("w-slug", form.fields["slug"].widget.attrs.get("class", ""))
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.cleaned_data["slug"], "usloviya-i-tsikly")

    def test_lesson_slug_with_russian_title_and_data(self):
        form_class = LessonPage.get_edit_handler().get_form_class()
        form = form_class(
            data={
                "title": "Переменные и типы данных",
                "slug": "",
                "direction": "python",
                "body-count": "0",
                "body": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(
            form.cleaned_data["slug"],
            "peremennye-i-tipy-dannykh",
        )

    def test_very_long_russian_title_generates_saveable_slug(self):
        form_class = LessonPage.get_edit_handler().get_form_class()
        title = "Щ" * 240
        form = form_class(
            data={
                "title": title,
                "slug": "",
                "direction": "python",
                "body-count": "0",
                "body": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        generated_slug = form.cleaned_data["slug"]
        self.assertEqual(len(generated_slug), 255)
        self.assertFalse(generated_slug.endswith("-"))

        lesson = LessonPage(
            title=title,
            slug=generated_slug,
            direction="python",
            live=False,
        )
        lesson.full_clean()
        saved_lesson = self.home.add_child(instance=lesson)
        saved_lesson.refresh_from_db()
        self.assertEqual(saved_lesson.slug, generated_slug)
        self.assertEqual(len(saved_lesson.slug), 255)
        self.assertFalse(saved_lesson.slug.endswith("-"))
        self.assertIn(saved_lesson.slug, saved_lesson.url_path)

    def test_custom_latin_lesson_slug_is_preserved(self):
        form_class = LessonPage.get_edit_handler().get_form_class()
        form = form_class(
            data={
                "title": "Условия и циклы",
                "slug": "my-custom-lesson",
                "direction": "python",
                "body-count": "0",
                "body": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.cleaned_data["slug"], "my-custom-lesson")

    def test_existing_lesson_slug_is_preserved_when_unchanged(self):
        lesson = self.make_lesson(
            title="Условия и циклы",
            slug="usloviya-i-tsikly",
            direction="python",
        )
        form_class = LessonPage.get_edit_handler().get_form_class()
        form = form_class(
            instance=lesson,
            data={
                "title": "Условия и циклы — обновлённый урок",
                "slug": "usloviya-i-tsikly",
                "direction": "python",
                "body-count": "0",
                "body": "",
            },
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.cleaned_data["slug"], "usloviya-i-tsikly")

    def test_wagtail_editor_can_open_lesson_creation_form(self):
        user = get_user_model().objects.create_superuser(
            username="editor-smoke-test",
            email="editor@example.invalid",
            password="test-only-password",
        )
        self.client.force_login(user)

        add_url = reverse(
            "wagtailadmin_pages:add",
            args=["school", "lessonpage", self.home.pk],
        )
        response = self.client.get(add_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "direction")
        self.assertContains(response, "intro")
        self.assertContains(response, "body")

    def test_lesson_renders_all_rich_content_blocks(self):
        lesson = self.make_lesson(
            title="Урок со всеми блоками",
            slug="lesson-all-content-blocks",
            direction="python",
            body=[
                ("rich_text", "<p>Основной текст блока</p>"),
                (
                    "code",
                    {
                        "language": "python",
                        "code": "print('hello')",
                    },
                ),
                (
                    "accordion",
                    {
                        "title": "Дополнительный раздел",
                        "content": "<p>Содержимое аккордеона</p>",
                    },
                ),
                (
                    "tabs",
                    {
                        "tabs": [
                            {
                                "title": "Первая вкладка",
                                "content": "<p>Содержимое первой вкладки</p>",
                            },
                            {
                                "title": "Вторая вкладка",
                                "content": "<p>Содержимое второй вкладки</p>",
                            },
                        ],
                    },
                ),
                (
                    "callout",
                    {
                        "kind": "important",
                        "content": "<p>Важное сообщение</p>",
                    },
                ),
            ],
        )
        lesson = self.publish(lesson)

        response = self.client.get(lesson.url)

        self.assertEqual(response.status_code, 200)

        for content in (
            "Основной текст блока",
            "print",
            "hello",
            "Дополнительный раздел",
            "Содержимое аккордеона",
            "Первая вкладка",
            "Вторая вкладка",
            "Содержимое первой вкладки",
            "Содержимое второй вкладки",
            "Важное сообщение",
        ):
            with self.subTest(content=content):
                self.assertContains(response, content)

        self.assertContains(response, "lesson-accordion")
        self.assertContains(response, "lesson-tabs")
        self.assertContains(response, "lesson-callout--important")
        self.assertContains(response, 'role="tablist"')
        self.assertContains(response, 'role="tabpanel"')
