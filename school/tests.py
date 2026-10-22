from django.test import TestCase

from school.models import HomePage, LessonPage


class PublicLearningFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = HomePage.objects.get(slug="home")

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

    def test_direction_filter_only_shows_matching_published_lessons(self):
        python_lesson = self.make_lesson(
            title="Python: переменные",
            slug="python-peremennye",
            direction="python",
        )
        scratch_lesson = self.make_lesson(
            title="Scratch: первый проект",
            slug="scratch-first-project",
            direction="scratch",
        )
        self.publish(python_lesson)
        self.publish(scratch_lesson)

        response = self.client.get("/?direction=python")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python: переменные")
        self.assertNotContains(response, "Scratch: первый проект")

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
