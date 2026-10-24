from wagtail import blocks
from wagtailcodeblock.blocks import CodeBlock


class AccordionBlock(blocks.StructBlock):
    title = blocks.CharBlock(
        label="Заголовок раздела",
        max_length=200,
    )
    content = blocks.RichTextBlock(label="Содержимое")

    class Meta:
        label = "Сворачиваемый раздел"
        icon = "collapse-down"
        template = "school/blocks/accordion.html"


class TabItemBlock(blocks.StructBlock):
    title = blocks.CharBlock(
        label="Название вкладки",
        max_length=100,
    )
    content = blocks.RichTextBlock(label="Содержимое вкладки")


class TabsBlock(blocks.StructBlock):
    tabs = blocks.ListBlock(
        TabItemBlock(),
        label="Вкладки",
        min_num=2,
        max_num=8,
    )

    class Meta:
        label = "Вкладки"
        icon = "list-ul"
        template = "school/blocks/tabs.html"


class CalloutBlock(blocks.StructBlock):
    kind = blocks.ChoiceBlock(
        label="Тип заметки",
        choices=[
            ("info", "Информация"),
            ("important", "Важно"),
            ("warning", "Предупреждение"),
        ],
        default="info",
    )
    content = blocks.RichTextBlock(label="Текст заметки")

    class Meta:
        label = "Информационная заметка"
        icon = "info-circle"
        template = "school/blocks/callout.html"


class LessonBodyBlock(blocks.StreamBlock):
    rich_text = blocks.RichTextBlock(
        label="Текст",
        features=[
            "h2",
            "h3",
            "bold",
            "italic",
            "link",
            "ol",
            "ul",
            "blockquote",
            "image",
        ],
    )
    code = CodeBlock(label="Фрагмент кода")
    accordion = AccordionBlock()
    tabs = TabsBlock()
    callout = CalloutBlock()

    class Meta:
        label = "Содержимое урока"
        template = "school/blocks/lesson_body.html"
