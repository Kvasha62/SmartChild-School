import json

import wagtail.fields
from django.db import migrations


def _decode_streamfield_blocks(value):
    """Decode StreamField JSON or wrap legacy HTML in a rich_text block."""
    if value is None or value == "":
        return []

    if isinstance(value, list):
        blocks = value
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return [{"type": "rich_text", "value": value}]

        if not isinstance(parsed, list):
            return [{"type": "rich_text", "value": value}]

        # A legacy text value may itself contain valid JSON.
        # Treat it as StreamField data only if every item is a valid block.
        if not all(
            isinstance(block, dict)
            and isinstance(block.get("type"), str)
            and "value" in block
            for block in parsed
        ):
            return [{"type": "rich_text", "value": value}]

        blocks = parsed
    else:
        raise ValueError(
            f"Unexpected LessonPage.body value: {type(value).__name__}"
        )

    for block in blocks:
        if (
            not isinstance(block, dict)
            or not isinstance(block.get("type"), str)
            or "value" not in block
        ):
            raise ValueError(
                "Invalid StreamField block encountered in LessonPage.body."
            )

    return blocks


def _to_streamfield_blocks(value):
    return _decode_streamfield_blocks(value)


def _get_lesson_revisions(apps, database):
    """Include revisions of lessons whose pages have been deleted."""
    Revision = apps.get_model("wagtailcore", "Revision")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type = (
        ContentType.objects.using(database)
        .filter(app_label="school", model="lessonpage")
        .first()
    )

    if content_type is None:
        return Revision.objects.using(database).none()

    return Revision.objects.using(database).filter(
        content_type_id=content_type.pk,
    )


def _get_revision_content(revision):
    content = revision.content
    was_string = isinstance(content, str)

    if was_string:
        content = json.loads(content)

    if not isinstance(content, dict):
        return None, was_string

    return content, was_string


def _encode_revision_content(content, was_string):
    if was_string:
        return json.dumps(content, ensure_ascii=False)
    return content


def forwards_convert_lesson_bodies(apps, schema_editor):
    """Convert legacy HTML in pages and all saved LessonPage revisions."""
    database = schema_editor.connection.alias
    LessonPage = apps.get_model("school", "LessonPage")

    converted_pages = []

    for page in (
        LessonPage.objects.using(database)
        .only("pk", "body")
        .iterator()
    ):
        blocks = _to_streamfield_blocks(page.body)
        encoded = json.dumps(blocks, ensure_ascii=False)

        if page.body != encoded:
            converted_pages.append((page.pk, encoded))

    converted_revisions = []

    for revision in _get_lesson_revisions(apps, database).iterator():
        content, was_string = _get_revision_content(revision)

        if content is None or "body" not in content:
            continue

        content["body"] = _to_streamfield_blocks(content["body"])
        converted_revisions.append(
            (
                revision.pk,
                _encode_revision_content(content, was_string),
            )
        )

    # Validate all data before writing any converted values.
    for page_id, encoded in converted_pages:
        LessonPage.objects.using(database).filter(pk=page_id).update(
            body=encoded
        )

    Revision = apps.get_model("wagtailcore", "Revision")

    for revision_id, content in converted_revisions:
        Revision.objects.using(database).filter(pk=revision_id).update(
            content=content
        )


def backwards_convert_lesson_bodies(apps, schema_editor):
    """Restore HTML, refusing to discard non-rich_text block content."""
    database = schema_editor.connection.alias
    LessonPage = apps.get_model("school", "LessonPage")

    def to_html(value):
        blocks = _decode_streamfield_blocks(value)

        unsupported_types = sorted({
            block["type"]
            for block in blocks
            if block["type"] != "rich_text"
        })

        if unsupported_types:
            names = ", ".join(unsupported_types)
            raise RuntimeError(
                "Cannot reverse LessonPage.body migration without losing "
                f"non-rich_text StreamField blocks: {names}."
            )

        return "".join(str(block["value"]) for block in blocks)

    converted_pages = []

    for page in (
        LessonPage.objects.using(database)
        .only("pk", "body")
        .iterator()
    ):
        converted_pages.append((page.pk, to_html(page.body)))

    converted_revisions = []

    for revision in _get_lesson_revisions(apps, database).iterator():
        content, was_string = _get_revision_content(revision)

        if content is None or "body" not in content:
            continue

        content["body"] = to_html(content["body"])
        converted_revisions.append(
            (
                revision.pk,
                _encode_revision_content(content, was_string),
            )
        )

    # No writes occur until all page and revision bodies validate.
    for page_id, html in converted_pages:
        LessonPage.objects.using(database).filter(pk=page_id).update(
            body=html
        )

    Revision = apps.get_model("wagtailcore", "Revision")

    for revision_id, content in converted_revisions:
        Revision.objects.using(database).filter(pk=revision_id).update(
            content=content
        )


class Migration(migrations.Migration):

    dependencies = [
        ('school', '0002_lessonpage_video_embed_url'),
    ]

    operations = [
        migrations.RunPython(
            forwards_convert_lesson_bodies,
            backwards_convert_lesson_bodies,
        ),
        migrations.AlterField(
            model_name='lessonpage',
            name='body',
            field=wagtail.fields.StreamField([('rich_text', 0), ('code', 3), ('accordion', 6), ('tabs', 11), ('callout', 14)], blank=True, block_lookup={0: ('wagtail.blocks.RichTextBlock', (), {'features': ['h2', 'h3', 'bold', 'italic', 'link', 'ol', 'ul', 'blockquote', 'image'], 'label': 'Текст'}), 1: ('wagtail.blocks.ChoiceBlock', [], {'choices': [('bash', 'Bash/Shell'), ('css', 'CSS'), ('diff', 'diff'), ('html', 'HTML'), ('javascript', 'Javascript'), ('json', 'JSON'), ('python', 'Python'), ('scss', 'SCSS'), ('yaml', 'YAML')], 'help_text': 'Coding language', 'identifier': 'language', 'label': 'Language'}), 2: ('wagtail.blocks.TextBlock', (), {'identifier': 'code', 'label': 'Code'}), 3: ('wagtail.blocks.StructBlock', [[('language', 1), ('code', 2)]], {'label': 'Фрагмент кода'}), 4: ('wagtail.blocks.CharBlock', (), {'label': 'Заголовок раздела', 'max_length': 200}), 5: ('wagtail.blocks.RichTextBlock', (), {'label': 'Содержимое'}), 6: ('wagtail.blocks.StructBlock', [[('title', 4), ('content', 5)]], {}), 7: ('wagtail.blocks.CharBlock', (), {'label': 'Название вкладки', 'max_length': 100}), 8: ('wagtail.blocks.RichTextBlock', (), {'label': 'Содержимое вкладки'}), 9: ('wagtail.blocks.StructBlock', [[('title', 7), ('content', 8)]], {}), 10: ('wagtail.blocks.ListBlock', (9,), {'label': 'Вкладки', 'max_num': 8, 'min_num': 2}), 11: ('wagtail.blocks.StructBlock', [[('tabs', 10)]], {}), 12: ('wagtail.blocks.ChoiceBlock', [], {'choices': [('info', 'Информация'), ('important', 'Важно'), ('warning', 'Предупреждение')], 'label': 'Тип заметки'}), 13: ('wagtail.blocks.RichTextBlock', (), {'label': 'Текст заметки'}), 14: ('wagtail.blocks.StructBlock', [[('kind', 12), ('content', 13)]], {})}, help_text='Собери урок из текста, кода, вкладок, заметок и сворачиваемых разделов.'),
        ),
    ]
