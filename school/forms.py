from wagtail.admin.forms.pages import WagtailAdminPageForm
from wagtail.admin.widgets import SlugInput

from school.slug_utils import transliterate_slug


class LessonPageAdminForm(WagtailAdminPageForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].widget = SlugInput(locale="ru-ru")

    def clean_slug(self):
        slug = self.cleaned_data.get("slug", "")

        # Do not change an existing page URL when its slug was left untouched.
        if self.instance.pk and slug == self.instance.slug:
            return slug

        return transliterate_slug(slug)
