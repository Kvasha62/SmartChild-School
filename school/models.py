import re
from urllib.parse import urlsplit

from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.db import models, router
from django.db.models.functions import Lower
from modelcluster.contrib.taggit import ClusterTaggableManager, _ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import ItemBase, TagBase
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.snippets.models import register_snippet

from school.blocks import LessonBodyBlock
from school.forms import LessonPageAdminForm
from school.metadata import normalize_search_keywords
from school.slug_utils import transliterate_slug


DIRECTION_CHOICES = [
    ("scratch", "Scratch"),
    ("roblox", "Roblox"),
    ("python", "Python"),
    ("unity", "Unity"),
    ("oge", "ОГЭ"),
    ("ege", "ЕГЭ"),
]



class _LessonClusterTaggableManager(_ClusterTaggableManager):
    """Resolve tag names case-insensitively only for the lesson tag pool."""

    def _to_tag_model_instances(self, tags, tag_kwargs=None):
        if tag_kwargs is None:
            tag_kwargs = {}

        database = router.db_for_write(self.through, instance=self.instance)
        tag_model = self.through.tag_model()
        manager = tag_model._default_manager.using(database)
        result = []
        seen = set()

        for value in tags:
            if isinstance(value, tag_model):
                tag = value
            elif isinstance(value, str):
                name = " ".join(value.split())
                if not name:
                    continue

                lookup = {"name__iexact": name, **tag_kwargs}
                tag = manager.filter(**lookup).order_by("pk").first()
                if tag is None:
                    try:
                        tag, _created = manager.get_or_create(
                            **lookup,
                            defaults={"name": name},
                        )
                    except MultipleObjectsReturned:
                        tag = manager.filter(**lookup).order_by("pk").first()
            else:
                raise ValueError(
                    f"Cannot add {value} ({type(value)}). "
                    f"Expected {tag_model} or str."
                )

            identity = (
                ("pk", tag.pk)
                if tag.pk is not None
                else ("name", tag.name.casefold())
            )
            if identity not in seen:
                seen.add(identity)
                result.append(tag)

        return result


class LessonClusterTaggableManager(ClusterTaggableManager):
    """Cluster tag manager whose case-insensitive behavior is lesson-scoped."""

    def __get__(self, instance, model):
        return _LessonClusterTaggableManager(
            through=self.through,
            model=model,
            instance=instance,
            prefetch_cache_name=self.name,
        )


@register_snippet
class LessonTopic(models.Model):
    """Controlled topic taxonomy for lessons; topics are not public pages."""

    title = models.CharField("Название темы", max_length=120)
    slug = models.SlugField(
        "Стабильный slug",
        max_length=160,
        unique=True,
        blank=True,
        editable=False,
    )
    description = models.TextField("Описание", blank=True)

    panels = [
        FieldPanel("title"),
        FieldPanel("description"),
    ]

    class Meta:
        ordering = ["title"]
        verbose_name = "тема урока"
        verbose_name_plural = "темы уроков"
        constraints = [
            models.UniqueConstraint(
                Lower("title"),
                name="school_topic_title_ci_uniq",
            ),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        self.title = " ".join((self.title or "").split())

    def save(self, *args, **kwargs):
        self.title = " ".join((self.title or "").split())
        if not self.slug and self.title:
            base = transliterate_slug(self.title)[:150].rstrip("-") or "topic"
            candidate = base
            suffix = 2
            topics = type(self).objects.all()
            if self.pk is not None:
                topics = topics.exclude(pk=self.pk)

            while topics.filter(slug=candidate).exists():
                suffix_text = f"-{suffix}"
                candidate = f"{base[:160 - len(suffix_text)].rstrip('-')}{suffix_text}"
                suffix += 1

            self.slug = candidate

        return super().save(*args, **kwargs)


@register_snippet
class LessonTag(TagBase):
    """Lesson-only tag pool, separate from Wagtail image/document tags."""

    panels = [FieldPanel("name")]

    class Meta:
        verbose_name = "тег урока"
        verbose_name_plural = "теги уроков"
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="school_lesson_tag_name_ci_uniq",
            ),
        ]

    def save(self, *args, **kwargs):
        self.name = " ".join((self.name or "").split())
        return super().save(*args, **kwargs)

    def slugify(self, tag, i=None):
        base = transliterate_slug(tag) or "tag"
        if i is not None:
            suffix = f"_{i}"
            return f"{base[:100 - len(suffix)].rstrip('-_')}{suffix}"
        return base[:100].rstrip("-")


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

    base_form_class = LessonPageAdminForm

    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES)
    topic = models.ForeignKey(
        LessonTopic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lessons",
        verbose_name="Тема",
    )
    search_keywords = models.TextField(
        "Поисковые фразы",
        blank=True,
        help_text=(
            "Одна поисковая фраза на строку. Используется для внутреннего поиска; "
            "содержимое урока автоматически не индексируется."
        ),
    )
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
    body = StreamField(
        LessonBodyBlock(),
        blank=True,
        use_json_field=True,
        help_text=(
        "Собери урок из текста, кода, вкладок, заметок "
        "и сворачиваемых разделов."
        ),
    )
    tags = LessonClusterTaggableManager(
        through="school.LessonPageTag",
        blank=True,
        verbose_name="Теги",
    )

    def clean(self):
        super().clean()
        self.search_keywords = normalize_search_keywords(self.search_keywords)

    parent_page_types = ["school.HomePage"]
    subpage_types = []

    content_panels = Page.content_panels + [
        FieldPanel("direction"),
        FieldPanel("intro"),
        FieldPanel("video_embed_url"),
        FieldPanel("body"),
    ]

    promote_panels = Page.promote_panels + [
        MultiFieldPanel(
            [
                FieldPanel("topic"),
                FieldPanel("search_keywords"),
                FieldPanel("tags"),
            ],
            heading="Тематические метаданные и поиск",
        ),
    ]


class LessonPageTag(ItemBase):
    tag = models.ForeignKey(
        LessonTag,
        on_delete=models.CASCADE,
        related_name="lesson_page_items",
    )
    content_object = ParentalKey(
        "school.LessonPage",
        on_delete=models.CASCADE,
        related_name="tagged_items",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("content_object", "tag"),
                name="school_lesson_page_tag_uniq",
            ),
        ]
