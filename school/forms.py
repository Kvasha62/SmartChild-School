from wagtail.admin.forms.pages import WagtailAdminPageForm
from django.core.validators import MaxLengthValidator

from school.slug_utils import transliterate_slug


class LessonPageAdminForm(WagtailAdminPageForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Let server-side transliteration handle Russian consistently, regardless
        # of Wagtail's client-side locale map. Truncate before model validation.
        slug_field = self.fields.get("slug")
        if slug_field is not None:
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

        return transliterate_slug(slug)
