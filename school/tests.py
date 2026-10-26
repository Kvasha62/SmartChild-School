import importlib
from types import SimpleNamespace

from django.conf import settings
from urllib.parse import urlsplit
from xml.etree import ElementTree

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from wagtail.models import PageViewRestriction, Site

from school.models import DIRECTION_CHOICES, HomePage, LessonPage, LessonTopic


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
        topic=None,
        search_keywords="",
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
                topic=topic,
                search_keywords=search_keywords,
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

    def test_public_templates_load_external_frontend_assets(self):
        catalogue = self.client.get("/")
        self.assertEqual(catalogue.status_code, 200)
        self.assertContains(catalogue, '/static/school/css/site.css')
        self.assertContains(catalogue, '/static/school/js/lesson-tabs.js')
        self.assertNotContains(catalogue, "<style>")
        self.assertNotContains(catalogue, "<script>")

        lesson = self.make_lesson(
            title="Урок для проверки frontend-ресурсов",
            slug="frontend-assets-lesson",
            direction="python",
            body=[
                (
                    "tabs",
                    {
                        "tabs": [
                            {"title": "Вкладка 1", "content": "<p>Текст 1</p>"},
                            {"title": "Вкладка 2", "content": "<p>Текст 2</p>"},
                        ],
                    },
                ),
            ],
        )
        lesson = self.publish(lesson)
        detail = self.client.get(lesson.url)
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, '/static/school/css/site.css')
        self.assertContains(detail, '/static/school/js/lesson-tabs.js')
        self.assertContains(detail, "data-lesson-tabs")

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

    def test_search_keyword_form_normalizes_and_deduplicates_lines(self):
        form_class = LessonPage.get_edit_handler().get_form_class()
        form = form_class(
            data={
                "title": "Метаданные Python",
                "slug": "metadata-python",
                "direction": "python",
                "search_keywords": (
                    "  Переменные   в Python  \n"
                    "переменные в python\n"
                    " Создать\tпеременную Python "
                ),
                "body-count": "0",
                "body": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(
            form.cleaned_data["search_keywords"],
            "Переменные в Python\nСоздать переменную Python",
        )

    def test_topic_tags_and_search_keywords_survive_revision_publish(self):
        # Case-insensitive lookup is scoped to LessonTag, not global Taggit pools.
        self.assertFalse(getattr(settings, "TAGGIT_CASE_INSENSITIVE", False))

        topic = LessonTopic.objects.create(
            title="Основы Python",
            description="Начальные понятия языка.",
        )
        self.assertEqual(topic.slug, "osnovy-python")

        lesson = self.make_lesson(
            title="Метаданные урока",
            slug="lesson-metadata",
            direction="python",
            topic=topic,
            search_keywords=(
                "Переменные в Python\n"
                "переменные в python\n"
                "создать   переменную"
            ),
        )
        lesson.full_clean()
        self.assertEqual(
            lesson.search_keywords,
            "Переменные в Python\nсоздать переменную",
        )

        # Case variants should reuse the existing lesson tag.
        lesson.tags.add("Переменные")
        lesson.tags.add("переменные")
        lesson.tags.add("Python")
        self.assertEqual(lesson.tags.count(), 2)

        self.publish(lesson)
        published = LessonPage.objects.get(pk=lesson.pk).specific
        self.assertEqual(published.topic_id, topic.pk)
        self.assertEqual(
            published.search_keywords,
            "Переменные в Python\nсоздать переменную",
        )
        self.assertSetEqual(set(published.tags.names()), {"Переменные", "Python"})

        public_page = self.client.get(published.url)
        self.assertEqual(public_page.status_code, 200)
        self.assertNotContains(public_page, "создать переменную")
        self.assertNotContains(public_page, "Переменные")

    def test_sitemap_lists_only_published_public_pages(self):
        draft = self.make_lesson(
            title="Черновик для sitemap",
            slug="draft-sitemap-lesson",
            direction="python",
        )
        published = self.make_lesson(
            title="Опубликованный материал для sitemap",
            slug="published-sitemap-lesson",
            direction="python",
        )
        published = self.publish(published)

        restricted = self.make_lesson(
            title="Закрытый материал для sitemap",
            slug="restricted-sitemap-lesson",
            direction="python",
        )
        restricted = self.publish(restricted)
        PageViewRestriction.objects.create(
            page=restricted,
            restriction_type=PageViewRestriction.LOGIN,
        )

        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"].split(";")[0], "application/xml")

        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        root = ElementTree.fromstring(response.content)
        locations = [
            urlsplit(node.text).path
            for node in root.findall(".//sm:loc", namespace)
            if node.text
        ]

        self.assertIn(published.url, locations)
        self.assertNotIn(draft.url, locations)
        self.assertNotIn(restricted.url, locations)

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
        self.assertNotContains(detail, "Похожие материалы")

    def test_related_lessons_prioritize_shared_topic_then_tags(self):
        topic = LessonTopic.objects.create(title="Основы связанных уроков")
        current = self.make_lesson(
            title="Текущий урок связей",
            slug="related-current-lesson",
            direction="python",
            topic=topic,
        )
        current.tags.add("общая метка")
        current = self.publish(current)

        topic_and_tag = self.make_lesson(
            title="A. Та же тема и тег",
            slug="related-topic-and-tag",
            direction="python",
            topic=topic,
        )
        topic_and_tag.tags.add("общая метка")
        topic_and_tag = self.publish(topic_and_tag)

        topic_only = self.make_lesson(
            title="B. Только та же тема",
            slug="related-topic-only",
            direction="python",
            topic=topic,
        )
        topic_only = self.publish(topic_only)

        tag_only = self.make_lesson(
            title="C. Только общий тег",
            slug="related-tag-only",
            direction="python",
        )
        tag_only.tags.add("общая метка")
        tag_only = self.publish(tag_only)

        unrelated = self.make_lesson(
            title="D. Нет тематической связи",
            slug="related-unrelated",
            direction="python",
            body="<p>Общая метка</p>",
        )
        unrelated = self.publish(unrelated)

        related = current.get_related_lessons()
        self.assertEqual(
            [lesson.pk for lesson in related],
            [topic_and_tag.pk, topic_only.pk, tag_only.pk],
        )
        self.assertNotIn(current.pk, [lesson.pk for lesson in related])
        self.assertNotIn(unrelated.pk, [lesson.pk for lesson in related])

        response = self.client.get(current.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Похожие материалы")
        self.assertContains(response, topic_and_tag.title)
        self.assertContains(response, topic_only.title)
        self.assertContains(response, tag_only.title)
        self.assertNotContains(response, unrelated.title)

    def test_related_lessons_exclude_drafts_and_restricted_pages(self):
        current = self.make_lesson(
            title="Урок для проверки границ доступа",
            slug="related-access-current",
            direction="python",
        )
        current.tags.add("общая метка доступа")
        current = self.publish(current)

        public_related = self.make_lesson(
            title="Публичный связанный урок",
            slug="related-access-public",
            direction="python",
        )
        public_related.tags.add("общая метка доступа")
        public_related = self.publish(public_related)

        draft = self.make_lesson(
            title="Черновик связанного урока",
            slug="related-access-draft",
            direction="python",
        )
        draft.tags.add("общая метка доступа")

        restricted = self.make_lesson(
            title="Закрытый связанный урок",
            slug="related-access-restricted",
            direction="python",
        )
        restricted.tags.add("общая метка доступа")
        restricted = self.publish(restricted)
        PageViewRestriction.objects.create(
            page=restricted,
            restriction_type=PageViewRestriction.LOGIN,
        )

        related = current.get_related_lessons()
        self.assertEqual([lesson.pk for lesson in related], [public_related.pk])
        self.assertNotIn(draft.pk, [lesson.pk for lesson in related])
        self.assertNotIn(restricted.pk, [lesson.pk for lesson in related])

        response = self.client.get(current.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, public_related.title)
        self.assertNotContains(response, draft.title)
        self.assertNotContains(response, restricted.title)

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

    def test_catalogue_search_matches_title_intro_and_keywords_but_not_body(self):
        title_match = self.make_lesson(
            title="Оператор распаковки аргументов",
            slug="search-title-match",
            direction="python",
        )
        intro_match = self.make_lesson(
            title="Краткое описание материала",
            slug="search-intro-match",
            direction="python",
            intro="Оператор распаковки аргументов",
        )
        keyword_match = self.make_lesson(
            title="Другой учебный материал",
            slug="search-keyword-match",
            direction="python",
            search_keywords="Оператор распаковки аргументов\nраспаковка параметров",
        )
        body_only_match = self.make_lesson(
            title="Материал без совпадения в метаданных",
            slug="search-body-only-match",
            direction="python",
            body="<p>Оператор распаковки аргументов</p>",
        )

        for lesson in (title_match, intro_match, keyword_match, body_only_match):
            self.publish(lesson)

        response = self.client.get("/", {"q": "оператор распаковки"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, title_match.title)
        self.assertContains(response, intro_match.title)
        self.assertContains(response, keyword_match.title)
        self.assertNotContains(response, body_only_match.title)
        self.assertContains(response, 'name="q"')
        self.assertContains(response, 'value="оператор распаковки"')

    def test_catalogue_search_combines_with_direction_filter(self):
        python_lesson = self.make_lesson(
            title="Поиск в Python",
            slug="search-python-direction",
            direction="python",
            search_keywords="специальный запрос",
        )
        unity_lesson = self.make_lesson(
            title="Поиск в Unity",
            slug="search-unity-direction",
            direction="unity",
            search_keywords="специальный запрос",
        )
        self.publish(python_lesson)
        self.publish(unity_lesson)

        response = self.client.get(
            "/",
            {"q": "специальный запрос", "direction": "python"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, python_lesson.title)
        self.assertNotContains(response, unity_lesson.title)
        self.assertContains(response, 'name="direction" value="python"')
        self.assertContains(response, "?direction=unity&amp;q=")

    def test_blank_catalogue_search_keeps_all_published_materials(self):
        first = self.make_lesson(
            title="Первый доступный материал",
            slug="blank-search-first",
            direction="python",
        )
        second = self.make_lesson(
            title="Второй доступный материал",
            slug="blank-search-second",
            direction="unity",
        )
        self.publish(first)
        self.publish(second)

        response = self.client.get("/", {"q": "   "})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, first.title)
        self.assertContains(response, second.title)
        self.assertEqual(response.context["search_query"], "")

    def test_catalogue_search_never_lists_drafts_or_restricted_lessons(self):
        draft = self.make_lesson(
            title="Секретный запрос в черновике",
            slug="search-draft-secret",
            direction="python",
        )
        restricted = self.make_lesson(
            title="Секретный запрос в закрытом уроке",
            slug="search-restricted-secret",
            direction="python",
        )
        self.publish(restricted)
        PageViewRestriction.objects.create(
            page=restricted,
            restriction_type=PageViewRestriction.LOGIN,
        )

        response = self.client.get("/", {"q": "секретный запрос"})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, draft.title)
        self.assertNotContains(response, restricted.title)
        self.assertContains(response, "ничего не найдено")

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

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.cleaned_data["slug"], "usloviya-i-tsikly")

    def test_slug_field_has_no_client_side_slug_controller(self):
        form_class = LessonPage.get_edit_handler().get_form_class()
        form = form_class()

        self.assertNotIn("data-controller", form.fields["slug"].widget.attrs)
        self.assertNotIn(
            "data-w-slug-allow-unicode-value",
            form.fields["slug"].widget.attrs,
        )

        rendered = str(form["slug"])
        self.assertNotIn("data-controller", rendered)
        self.assertNotIn("w-slug", rendered)

    def test_untransliterable_title_is_rejected_by_slug_validation(self):
        form_class = LessonPage.get_edit_handler().get_form_class()

        for title in ["🎉", "Ъ", "ь", "!!!", "ъь"]:
            with self.subTest(title=title):
                form = form_class(
                    data={
                        "title": title,
                        "slug": "",
                        "direction": "python",
                        "body-count": "0",
                        "body": "",
                    }
                )

                self.assertFalse(form.is_valid())
                self.assertIn("slug", form.errors)
                self.assertIn("Введите slug вручную", form.errors["slug"][0])

        self.assertFalse(LessonPage.objects.filter(slug="").exists())
        self.assertFalse(LessonPage.objects.filter(slug="ъь").exists())

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
        saved_lesson = self.home.add_child(instance=lesson)
        saved_lesson.full_clean()
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

    def test_manual_ascii_slug_with_underscores_is_preserved(self):
        form_class = LessonPage.get_edit_handler().get_form_class()
        form = form_class(
            data={
                "title": "Условия и циклы",
                "slug": "my_custom_slug",
                "direction": "python",
                "body-count": "0",
                "body": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.cleaned_data["slug"], "my_custom_slug")

    def test_manual_cyrillic_slug_is_transliterated_before_validation(self):
        form_class = LessonPage.get_edit_handler().get_form_class()
        form = form_class(
            data={
                "title": "Урок",
                "slug": "Урок 1.2",
                "direction": "python",
                "body-count": "0",
                "body": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.cleaned_data["slug"], "urok-1-2")

    def test_overlong_manual_slug_is_rejected_without_truncation(self):
        form_class = LessonPage.get_edit_handler().get_form_class()
        form = form_class(
            data={
                "title": "Урок",
                "slug": "a" * 300,
                "direction": "python",
                "body-count": "0",
                "body": "",
            }
        )

        self.assertEqual(form.fields["slug"].widget.attrs["maxlength"], "255")
        self.assertIn('maxlength="255"', str(form["slug"]))
        self.assertFalse(form.is_valid())
        self.assertIn("slug", form.errors)
        self.assertNotIn("slug", form.cleaned_data)

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
                (
                    "tabs",
                    {
                        "tabs": [
                            {
                                "title": "Третья вкладка",
                                "content": "<p>Содержимое третьей вкладки</p>",
                            },
                            {
                                "title": "Четвёртая вкладка",
                                "content": "<p>Содержимое четвёртой вкладки</p>",
                            },
                        ],
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
            "Третья вкладка",
            "Четвёртая вкладка",
            "Содержимое третьей вкладки",
            "Содержимое четвёртой вкладки",
        ):
            with self.subTest(content=content):
                self.assertContains(response, content)

        self.assertContains(response, "lesson-accordion")
        self.assertContains(response, "lesson-tabs")
        self.assertContains(response, "lesson-callout--important")
        self.assertContains(response, 'role="tablist"')
        self.assertContains(response, 'role="tabpanel"')
        self.assertContains(
            response,
            f'id="lesson-tab-{lesson.pk}-4-0"',
        )
        self.assertContains(
            response,
            f'aria-controls="lesson-tab-panel-{lesson.pk}-4-0"',
        )
        self.assertContains(
            response,
            f'id="lesson-tab-panel-{lesson.pk}-4-0"',
        )
        self.assertContains(
            response,
            f'aria-labelledby="lesson-tab-{lesson.pk}-4-0"',
        )
        self.assertContains(
            response,
            f'id="lesson-tab-{lesson.pk}-6-0"',
        )
        self.assertContains(
            response,
            f'aria-controls="lesson-tab-panel-{lesson.pk}-6-0"',
        )
        self.assertContains(
            response,
            f'id="lesson-tab-panel-{lesson.pk}-6-0"',
        )
        self.assertContains(
            response,
            f'aria-labelledby="lesson-tab-{lesson.pk}-6-0"',
        )
