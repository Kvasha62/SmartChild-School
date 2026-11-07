from wagtail import blocks
from wagtailcodeblock.blocks import CodeBlock


RICH_TEXT_FEATURES = [
    "h2", "h3", "bold", "italic", "link",
    "ol", "ul", "blockquote", "image",
]

MAX_CONTENT_DEPTH = 5


def make_content_stream(depth=0):
    children = [
        (
            "rich_text",
            blocks.RichTextBlock(
                label="Текст",
            ),
        ),
        ("code", CodeBlock(label="Фрагмент кода")),
    ]

    if depth < MAX_CONTENT_DEPTH:
        children.extend([
            ("callout", make_callout_block(depth + 1)),
            ("accordion", make_accordion_block(depth + 1)),
            ("tabs", make_tabs_block(depth + 1)),
        ])

    return blocks.StreamBlock(
        children,
        label="Содержимое",
        template="school/blocks/lesson_body.html",
    )


def make_tab_item_block(depth):
    return blocks.StructBlock(
        [
            (
                "title",
                blocks.CharBlock(
                    label="Название вкладки",
                    max_length=100,
                ),
            ),
            (
                "content",
                make_content_stream(depth),
            ),
        ],
        label="Вкладка",
    )


def make_tabs_block(depth):
    return blocks.StructBlock(
        [
            (
                "tabs",
                blocks.ListBlock(
                    make_tab_item_block(depth),
                    label="Вкладки",
                    min_num=2,
                    max_num=8,
                ),
            ),
        ],
        label="Вкладки",
        icon="list-ul",
        template="school/blocks/tabs.html",
    )


def make_callout_block(depth):
    return blocks.StructBlock(
        [
            (
                "kind",
                blocks.ChoiceBlock(
                    label="Тип заметки",
                    choices=[
                        ("info", "Информация"),
                        ("important", "Важно"),
                        ("warning", "Предупреждение"),
                    ],
                    default="info",
                ),
            ),
            (
                "content",
                make_content_stream(depth),
            ),
        ],
        label="Информационная заметка",
        icon="info-circle",
        template="school/blocks/callout.html",
    )


def make_accordion_block(depth):
    return blocks.StructBlock(
        [
            (
                "title",
                blocks.CharBlock(
                    label="Заголовок раздела",
                    max_length=200,
                ),
            ),
            (
                "content",
                make_content_stream(depth),
            ),
        ],
        label="Сворачиваемый раздел",
        icon="collapse-down",
        template="school/blocks/accordion.html",
    )


class LessonBodyBlock(blocks.StreamBlock):
    rich_text = blocks.RichTextBlock(
        label="Текст",
        features=RICH_TEXT_FEATURES,
    )
    code = CodeBlock(label="Фрагмент кода")
    callout = make_callout_block(1)
    accordion = make_accordion_block(1)
    tabs = make_tabs_block(1)

    class Meta:
        label = "Содержимое урока"
        template = "school/blocks/lesson_body.html"
