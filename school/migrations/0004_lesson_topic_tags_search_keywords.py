# Generated for editor-managed lesson topic, search phrase and tag metadata.

import django.db.models.functions.text
import django.db.models.deletion
import modelcluster.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0003_alter_lessonpage_body"),
    ]

    operations = [
        migrations.CreateModel(
            name="LessonTopic",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "title",
                    models.CharField(max_length=120, verbose_name="Название темы"),
                ),
                (
                    "slug",
                    models.SlugField(
                        blank=True,
                        editable=False,
                        max_length=160,
                        unique=True,
                        verbose_name="Стабильный slug",
                    ),
                ),
                ("description", models.TextField(blank=True, verbose_name="Описание")),
            ],
            options={
                "verbose_name": "тема урока",
                "verbose_name_plural": "темы уроков",
                "ordering": ["title"],
                "constraints": [
                    models.UniqueConstraint(
                        django.db.models.functions.text.Lower("title"),
                        name="school_topic_title_ci_uniq",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="LessonTag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="name")),
                (
                    "slug",
                    models.SlugField(
                        allow_unicode=True,
                        max_length=100,
                        unique=True,
                        verbose_name="slug",
                    ),
                ),
            ],
            options={
                "verbose_name": "тег урока",
                "verbose_name_plural": "теги уроков",
                "constraints": [
                    models.UniqueConstraint(
                        django.db.models.functions.text.Lower("name"),
                        name="school_lesson_tag_name_ci_uniq",
                    ),
                ],
            },
        ),
        migrations.AddField(
            model_name="lessonpage",
            name="topic",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="lessons",
                to="school.lessontopic",
                verbose_name="Тема",
            ),
        ),
        migrations.AddField(
            model_name="lessonpage",
            name="search_keywords",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "Одна поисковая фраза на строку. Используется для внутреннего поиска; "
                    "содержимое урока автоматически не индексируется."
                ),
                verbose_name="Поисковые фразы",
            ),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="LessonPageTag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tag",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lesson_page_items",
                        to="school.lessontag",
                    ),
                ),
                (
                    "content_object",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tagged_items",
                        to="school.lessonpage",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("content_object", "tag"),
                        name="school_lesson_page_tag_uniq",
                    ),
                ],
            },
        ),
    ]
