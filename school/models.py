import re
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


DIRECTION_CHOICES = [
    ("scratch", "Scratch"),
    ("roblox", "Roblox"),
    ("python", "Python"),
    ("unity", "Unity"),
    ("oge", "ОГЭ"),
    ("ege", "ЕГЭ"),
]


def validate_rutube_embed_url(value):
    """Accept only HTTPS links to Rutube's player embed endpoint."""
    if not value:
        return

    try:
        parsed = urlsplit(value)
        valid_port = parsed.port in (None, 443)
    except ValueError:
        valid_port = False
        parsed = None

    if (
        parsed is None
        or parsed.scheme != "https"
        or parsed.hostname != "rutube.ru"
        or not valid_port
        or parsed.username is not None
        or parsed.password is not None
        or not re.fullmatch(r"/play/embed/[A-Za-z0-9_-]+/?", parsed.path)
        or parsed.fragment
    ):
        raise ValidationError(
            "Укажи HTTPS-ссылку на плеер Rutube вида "
            "https://rutube.ru/play/embed/VIDEO_ID.",
            code="invalid_rutube_embed_url",
        )


class HomePage(Page):
    """Public catalogue and entry point for the learning materials."""

    parent_page_types = ["wagtailcore.Page"]
    subpage_types = ["school.LessonPage"]
    max_count = 1

    content_panels = Page.content_panels

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        lessons = LessonPage.objects.child_of(self).live().public().order_by("title")
        selected_direction = request.GET.get("direction", "").strip()
        valid_directions = {value for value, _label in DIRECTION_CHOICES}

        if selected_direction in valid_directions:
            lessons = lessons.filter(direction=selected_direction)
        else:
            selected_direction = ""

        context.update(
            {
                "lessons": lessons,
                "directions": DIRECTION_CHOICES,
                "selected_direction": selected_direction,
            }
        )
        return context


class LessonPage(Page):
    """A public lesson managed and published through Wagtail."""

    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES)
    intro = models.CharField(
        max_length=300,
        blank=True,
        help_text="Краткое описание для каталога.",
    )
    video_embed_url = models.URLField(
        "Видео Rutube",
        blank=True,
        validators=[validate_rutube_embed_url],
        help_text="Вставь ссылку на плеер Rutube, например https://rutube.ru/play/embed/...",
    )
    body = RichTextField(
        blank=True,
        help_text="Текст урока. Изображения можно вставлять через редактор Wagtail.",
    )

    parent_page_types = ["school.HomePage"]
    subpage_types = []

    content_panels = Page.content_panels + [
        FieldPanel("direction"),
        FieldPanel("intro"),
        FieldPanel("video_embed_url"),
        FieldPanel("body"),
    ]
