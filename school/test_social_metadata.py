from django.test import TestCase

from school.models import HomePage, LessonPage


class SocialMetadataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = HomePage.objects.get(slug="smartchild-school")

    def publish_lesson(
        self,
        *,
        title,
        slug,
        intro="",
        search_description="",
        seo_title="",
    ):
        lesson = self.home.add_child(
            instance=LessonPage(
                title=title,
                slug=slug,
                direction="python",
                intro=intro,
                search_description=search_description,
                seo_title=seo_title,
                body=[],
                live=False,
            )
        )
        lesson.save_revision().publish()
        return LessonPage.objects.get(pk=lesson.pk).specific

    def test_catalogue_has_basic_social_metadata_without_absolute_url_fields(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<meta property="og:type" content="website">')
        self.assertContains(response, '<meta property="og:site_name" content="SmartChild-School">')
        self.assertContains(response, '<meta name="twitter:card" content="summary">')
        self.assertContains(
            response,
            '<meta name="description" content="Учебные материалы SmartChild-School по программированию и подготовке к ОГЭ и ЕГЭ.">',
        )
        self.assertContains(
            response,
            '<meta property="og:description" content="Учебные материалы SmartChild-School по программированию и подготовке к ОГЭ и ЕГЭ.">',
        )
        self.assertNotContains(response, 'property="og:url"')
        self.assertNotContains(response, 'rel="canonical"')

    def test_social_metadata_prefers_explicit_wagtail_seo_fields(self):
        lesson = self.publish_lesson(
            title="Основы переменных",
            slug="social-meta-explicit",
            intro="Вступление для карточки урока.",
            search_description="Редакторское описание для социальных превью.",
            seo_title="SEO-заголовок переменных",
        )

        response = self.client.get(lesson.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<meta property="og:title" content="SEO-заголовок переменных — SmartChild-School">',
        )
        self.assertContains(
            response,
            '<meta name="twitter:title" content="SEO-заголовок переменных — SmartChild-School">',
        )
        self.assertContains(
            response,
            '<meta name="description" content="Редакторское описание для социальных превью.">',
        )
        self.assertContains(
            response,
            '<meta property="og:description" content="Редакторское описание для социальных превью.">',
        )
        self.assertContains(
            response,
            '<meta name="twitter:description" content="Редакторское описание для социальных превью.">',
        )

    def test_social_metadata_falls_back_to_lesson_intro(self):
        description = "Вступление урока, подходящее для краткого превью."
        lesson = self.publish_lesson(
            title="Переменные в Python",
            slug="social-meta-intro-fallback",
            intro=description,
        )

        response = self.client.get(lesson.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'<meta name="description" content="{description}">',
        )
        self.assertContains(
            response,
            f'<meta property="og:description" content="{description}">',
        )
        self.assertContains(
            response,
            f'<meta name="twitter:description" content="{description}">',
        )
