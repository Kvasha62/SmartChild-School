from django import forms
from django.core.validators import MaxLengthValidator
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
            slug_field.widget = forms.TextInput()
            slug_field.required = False
            # Normalize/truncate before model validation applies max_length.
            slug_field.validators = [
                validator
                for validator in slug_field.validators
                if not isinstance(validator, MaxLengthValidator)
            ]

    def clean_slug(self):
        slug = self.cleaned_data.get("slug", "")

        # Do not change an existing page URL when its slug was left untouched.
        if self.instance.pk and slug == self.instance.slug:
            return slug

        # With the client-side w-slug handler disabled, an empty field means
        # the editor accepted automatic generation from the page title.
        if not slug:
            slug = self.cleaned_data.get("title", "")

        return transliterate_slug(slug)
