from django.test import TestCase
from wagtail.models import PageViewRestriction

from school.models import DIRECTION_CHOICES, HomePage, LessonPage


class PublicLearningFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = HomePage.objects.get(slug="smartchild-school")

    def make_lesson(self, *, title, slug, direction, intro="", body=""):
        return self.home.add_child(
            instance=LessonPage(
                title=title,
                slug=slug,
                direction=direction,
                intro=intro,
                body=body,
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
