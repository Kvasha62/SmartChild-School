import re

from django import forms
from django.core.validators import validate_slug
from wagtail.admin.forms.pages import WagtailAdminPageForm

from school.slug_utils import transliterate_slug


class LessonPageAdminForm(WagtailAdminPageForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Do not attach Wagtail's client-side w-slug handler: its transliteration
        # map can differ from the server's. Generate the slug from the title on
        # submission when the editor has not supplied one.
        slug_field = self.fields.get("slug")
        if slug_field is not None:
            slug_field.widget = forms.TextInput(
                attrs={"maxlength": str(slug_field.max_length or 255)}
            )
            slug_field.required = False
            # Normalize manually entered Cyrillic/punctuation before Wagtail's
            # ASCII-only slug validator would reject it. Keep the max-length
            # validator so overlong manual values are rejected, not truncated.
            slug_field.validators = [
                validator
                for validator in slug_field.validators
                if validator is not validate_slug
            ]

    def clean_slug(self):
        slug = self.cleaned_data.get("slug", "")

        # Do not change an existing page URL when its slug was left untouched.
        if self.instance.pk and slug and slug == self.instance.slug:
            return slug

        # Preserve valid manually supplied ASCII slugs exactly, including
        # underscores and intentional capitalization.
        if slug and slug.isascii() and re.fullmatch(r"[-a-zA-Z0-9_]+", slug):
            return slug

        # With the client-side w-slug handler disabled, an empty field means
        # the editor accepted automatic generation from the page title.
        if not slug:
            slug = self.cleaned_data.get("title", "")

        # Normalize manual Cyrillic or punctuation too (e.g. "Урок 1.2").
        slug = transliterate_slug(slug)
        if not slug:
            raise forms.ValidationError(
                "Не удалось сформировать slug из заголовка. "
                "Введите slug вручную."
            )

        return slug
