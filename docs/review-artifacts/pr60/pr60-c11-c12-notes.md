# PR #60 — исправления C11 и C12 (передача владельцу)

**Дата:** 2026-10-25, 19:25Z—19:45Z (UTC)
**Проверенный HEAD PR:** `5defe9c65bc038e8b4825f9d8485a4dde927dc38` (не менялся)
**База:** `dc73430`
**CI на HEAD:** run `40224552913` — success

## Что сделано

Изменены два файла (патч: `pr60-c11-c12.patch`, полные версии — в `pr60-c11-c12-files/`):

| Файл | Строки | Изменение |
| --- | --- | --- |
| `school/forms.py` | 28—44 | C11: пустой результат транслитерации теперь ошибка валидации поля `slug`; ранний возврат для существующего слага срабатывает только для непустого значения |
| `school/tests.py` | 204—240 | C12: вакуумная проверка CSS-класса заменена проверкой `data-controller`/`w-slug`; добавлен регрессионный тест на непереводимые заголовки |

### C11

```python
        # Do not change an existing page URL when its slug was left untouched.
        if self.instance.pk and slug and slug == self.instance.slug:
            return slug
        ...
        slug = transliterate_slug(slug)
        if not slug:
            raise forms.ValidationError(
                "Не удалось сформировать slug из заголовка. "
                "Введите slug вручную."
            )
        return slug
```

- `🎉`, `Ъ`, `ь`, `!!!`, `ъь` → `form.is_valid() == False`, ошибка на поле `slug`;
- черновик с пустым слагом больше не создаётся; Wagtail не подставляет кириллицу для `ъь`;
- ручной слаг для «непереводимого» заголовка работает (`🎉` + `party-time` → `party-time`);
- оба обязательных примера, ручной латинский слаг, неизменённый существующий слаг и длинный заголовок не затронуты.

### C12

```python
    def test_slug_field_has_no_client_side_slug_controller(self):
        form = form_class()

        self.assertNotIn("data-controller", form.fields["slug"].widget.attrs)
        self.assertNotIn("data-w-slug-allow-unicode-value", form.fields["slug"].widget.attrs)

        rendered = str(form["slug"])
        self.assertNotIn("data-controller", rendered)
        self.assertNotIn("w-slug", rendered)
```

Проверено, что при возврате `SlugInput` тест падает: у `SlugInput()` есть `data-controller`, а его отрендеренный HTML содержит `w-slug`.

Добавлен тест `test_untransliterable_title_is_rejected_by_slug_validation` (5 заголовков, проверка ошибки и отсутствия страниц с пустым/кириллическим слагом).

## Проверки

| Проверка | Результат |
| --- | --- |
| `manage.py check` | 0 issues |
| `manage.py test school.tests` | **18/18 OK** (было 16) |
| `manage.py test` | **47/47 OK** (было 45) |
| `manage.py makemigrations --check --dry-run` | No changes detected |
| `git diff --check` | чисто |
| Оба обязательных примера | `usloviya-i-tsikly`, `peremennye-i-tipy-dannykh` |
| То же при `WAGTAIL_ALLOW_UNICODE_SLUGS=False` | `peremennye-i-tipy-dannykh` |
| Ручной и существующий slug | сохраняются |
| Заголовок 240 × «Щ» | 255 символов, без дефиса, сохранение и `full_clean` проходят |
| Дубликат слага | отклоняется формой |

Окружение: Python 3.11.2, Django 5.2.18, Wagtail 7.4.3, SQLite вместо PostgreSQL (переопределение в `/tmp`, файлы репозитория не менялись). CI для этих изменений не запускался: они не отправлены в ветку PR.

## Как применить

```bash
git fetch origin feature/issue-59-latin-slugs
git switch feature/issue-59-latin-slugs
git apply patches/pr60-c11-c12.patch
git add school/forms.py school/tests.py
git commit -m "fix: reject empty transliterated lesson slugs and harden widget test"
git push origin feature/issue-59-latin-slugs
```

Патч сгенерирован против `5defe9c65bc038e8b4825f9d8485a4dde927dc38`; при неизменной голове применяется без конфликтов (проверено `git apply --check --reverse` в worktree).

## Ограничения и остаточные риски

- Ветка PR не является веткой этой сессии, поэтому изменения переданы патчем; в `feature/issue-59-latin-slugs` они не отправлялись.
- Браузер не запускался: поведение проверено на серверном слое (формы, `save_revision`, отрендеренный HTML).
- Не проверялись PostgreSQL, Python 3.13, `check --deploy`, compose.
- Сохраняются замечания прошлых раундов: C4 (нормализация `_` в ручном слаге), C5 (ручной `Урок 1.2` отклоняется валидатором), C7 (транслитерация только в админ-форме), C9 (молчаливая обрезка ручных слагов >255).
