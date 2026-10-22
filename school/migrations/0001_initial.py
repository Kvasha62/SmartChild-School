import django.db.models.deletion
from django.db import migrations, models
import wagtail.fields


DIRECTION_CHOICES = [
    ("scratch", "Scratch"),
    ("roblox", "Roblox"),
    ("python", "Python"),
    ("unity", "Unity"),
    ("oge", "ОГЭ"),
    ("ege", "ЕГЭ"),
]


def create_homepage(apps, schema_editor):
    # Wagtail's treebeard methods are not present on historical models.
    # Use runtime page models for tree operations, but historical Site model.
    from school.models import HomePage
    from wagtail.models import Page

    Site = apps.get_model("wagtailcore", "Site")
    database = schema_editor.connection.alias

    site = Site.objects.using(database).filter(is_default_site=True).first()
    if site is None:
        return

    home = HomePage.objects.using(database).filter(slug="smartchild-school").first()
    if home is None:
        root = Page.objects.using(database).get(depth=1)
        home = HomePage(
            title="SmartChild — блог-школа программирования",
            slug="smartchild-school",
            live=True,
            show_in_menus=True,
        )
        root.add_child(instance=home)

    Site.objects.using(database).filter(pk=site.pk).update(root_page_id=home.pk)


def delete_homepage(apps, schema_editor):
    """Undo only the homepage created by this migration and detach the Site."""
    from wagtail.models import Page

    Site = apps.get_model("wagtailcore", "Site")
    database = schema_editor.connection.alias

    site = Site.objects.using(database).filter(is_default_site=True).first()
    home = Page.objects.using(database).filter(slug="smartchild-school").first()

    if home is None:
        return

    # The forward migration creates the homepage directly under the Wagtail
    # tree root. Restore that parent before deleting the page, so Site never
    # points to a page that is being removed.
    parent_id = home.get_parent().pk
    if site is not None and site.root_page_id == home.pk:
        Site.objects.using(database).filter(pk=site.pk).update(root_page_id=parent_id)

    home.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("wagtailcore", "0097_baselogentry_uuid_action_timestamp_indexes"),
        # Creating a Wagtail Page triggers search-index hooks; ensure the
        # indexentry table exists before the data migration inserts the home page.
        ("wagtailsearch", "0010_add_text_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomePage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
            ],
            options={"abstract": False},
            bases=("wagtailcore.page",),
        ),
        migrations.CreateModel(
            name="LessonPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "direction",
                    models.CharField(choices=DIRECTION_CHOICES, max_length=20),
                ),
                (
                    "intro",
                    models.CharField(
                        blank=True,
                        help_text="Краткое описание для каталога.",
                        max_length=300,
                    ),
                ),
                (
                    "body",
                    wagtail.fields.RichTextField(
                        blank=True,
                        help_text="Текст урока. Изображения можно вставлять через редактор Wagtail.",
                    ),
                ),
            ],
            options={"abstract": False},
            bases=("wagtailcore.page",),
        ),
        migrations.RunPython(create_homepage, delete_homepage),
    ]
