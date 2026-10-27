# Отчёт независимого аудита SEO и frontend: публичный каталог и страница урока (Issue #62)

## 1. Контекст

| Поле | Значение |
|------|----------|
| Issue | [#62 SEO и frontend: аудит публичного каталога и страницы урока](https://github.com/Kvasha62/SmartChild-School/issues/62) |
| Задание | Этап 1 Arena: независимый аудит только на чтение, оценка PR #72, предложение следующего узкого PR. Функциональные изменения не вносятся. |
| Базовая ветка | `main` |
| SHA базы (контрольная точка задания) | `85a490df774ff5404ced5483b976dac60f362832` |
| Проверенная версия | `origin/main` = `85a490df774ff5404ced5483b976dac60f362832` (коммит `test: cover public 404 and Wagtail redirects`) |
| Время фиксации SHAs | 2026-10-27 11:09 UTC |
| Источники SHA | `git fetch origin`, `git rev-parse origin/main`, GitHub API (`/repos/Kvasha62/SmartChild-School/pulls/72`, `/compare/...`) |
| Окружение проверки | Python 3.11.2 (среда CI использует 3.13.17), venv с зависимостями из `requirements.txt` на дату проверки (`Django==5.2.18`, `wagtail==7.4.3` и т.д.), нет PostgreSQL, нет 공개 production-домена, нет запущенного приложения |
| Выполнено в среде проверки | `python manage.py check` — ошибок не выявлено; `python manage.py makemigrations --check --dry-run` — «No changes detected» |
| Не выполнено (ограничение окружения) | полный набор `manage.py test` (требуется PostgreSQL), HTTP-проверки `/sitemap.xml`, `/robots.txt`, отрисованных meta-тегов, проверка на реальных браузерах и устройствах |

## 2. Проверенное состояние `main` на SHA `85a490d`

Ниже — observations, сверенные с текущими файлами на SHA `85a490d` (не с текстом Issue #62 на момент открытия; устаревшие наблюдения начального аудита перепроверены).

### Таблица фактов

| Область | Наблюдение | Доказательство (путь:строки, SHA) | Вид проверки | Статус |
|---------|------------|-----------------------------------|--------------|--------|
| Sitemap | Маршрут `/sitemap.xml` подключён через штатный Wagtail view `wagtail.contrib.sitemaps.views.sitemap` **до** catch-all `wagtail.urls`; приложение `django.contrib.sitemaps` в `INSTALLED_APPS` | `config/urls.py:8-9,19-20`; `config/settings.py:58` [blob](https://github.com/Kvasha62/SmartChild-School/blob/85a490df774ff5404ced5483b976dac60f362832/config/urls.py) [blob](https://github.com/Kvasha62/SmartChild-School/blob/85a490df774ff5404ced5483b976dac60f362832/config/settings.py) | Исходники | Подтверждено |
| robots.txt | Файла и маршрута `robots.txt` в дереве нет | `git ls-tree -r --name-only 85a490d` — отсутствует; `config/urls.py` — без маршрута | Исходники | Подтверждено (отсутствие) |
| Canonical | `<link rel="canonical">` не выводится на страницах | `school/templates/school/base.html` — нет canonical-тега [blob](https://github.com/Kvasha62/SmartChild-School/blob/85a490df774ff5404ced5483b976dac60f362832/school/templates/school/base.html) | Исходники | Подтверждено (отсутствие) |
| SEO title | `page.seo_title | default:page.title` + « — SmartChild-School» | `base.html:11` | Исходники | Подтверждено |
| Meta description | Приоритет у явного `page.search_description`; иначе `page.intro` до 170 символов; иначе общий сайтовый фолбэк | `school/templates/school/includes/description_meta.html` [blob](https://github.com/Kvasha62/SmartChild-School/blob/85a490df774ff5404ced5483b976dac60f362832/school/templates/school/includes/description_meta.html) | Исходники | Подтверждено |
| Социальная мета (OG/Twitter) | `og:type`, `og:site_name`, `og:title`, `og:description`, `twitter:card`, `twitter:title`, `twitter:description` подключены через `school/includes/social_metadata.html` | `base.html:10`; `social_metadata.html` | Исходники | Подтверждено (частично — см. риски) |
| `noindex` для URL поиска/фильтра | При `?q` и/или `?direction` в каталоге выводится `<meta name="robots" content="noindex,follow">` (`catalogue_noindex`) | `school/templates/school/home_page.html:5` [blob](https://github.com/Kvasha62/SmartChild-School/blob/85a490df774ff5404ced5483b976dac60f362832/school/templates/school/home_page.html) | Исходники | Подтверждено |
| Поиск каталога | Регистронезависимый частичный поиск по `title`, `intro`, `search_keywords`; `body` исключён; пустой `q` не фильтрует; фильтр `direction` сохраняется; выдача ограничена `live().public()` | `school/models.py` `HomePage.get_context` | Исходники | Подтверждено |
| Смежные материалы | Блок «Похожие материалы» на странице урока: сначала общая тема, потом общие теги, максимум 3, без текущего урока и дублей, только `live().public()` дочерних того же каталога | `school/models.py` `LessonPage.get_related_lessons`; `lesson_page.html` | Исходники | Подтверждено |
| Темы, теги, ключевые фразы | Справочник `LessonTopic` (snippet), урок → одна тема, поле `search_keywords` с нормализацией, теги через `LessonClusterTaggableManager` + через-модель `LessonPageTag`, изолированный пул тегов уроков | `school/models.py`; миграции `0003_alter_lessonpage_body.py`, `0004_lesson_topic_tags_search_keywords.py` | Исходники | Подтверждено |
| 404 на неизвестный URL | Нет файлов `404.html`/`500.html`; обработка через Wagtail; тест проверяет 404 | `school/tests.py:184` `test_unknown_public_url_returns_404` | Исходники + тест | Подтверждено |
| Редиректы | Подключён `RedirectMiddleware`; тесты постоянного редиректа для старого URL и защиты существующего URL | MIDDLEWARE в `config/settings.py`; `school/tests.py:188,204` | Исходники + тест | Подтверждено |
| Заголовки безопасности | `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS = "SAMEORIGIN"`, `SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"`, HSTS/SSL-редирект настраиваются через env | `config/settings.py` | Исходники | Подтверждено |
| Заголовки страниц | Один `h1` на каталоге и уроке; ожидаемые `h2`/`h3` в rich-тексте урока | `school/tests.py:340` `test_catalogue_and_lesson_use_single_h1` | Тест | Подтверждено |
| Внутренние ссылки | Ссылка на урок из каталога и на связанный урок со страницы урока — HTTP 200 через test client | `school/tests.py` (раздел PR #75) | Тест | Подтверждено |
| Черновики/закрытые страницы | Не попадают в каталог, sitemap, поиск, выдачу смежных материалов; прямой URL черновика — 404; ограниченная страница — 302/403 | `school/tests.py` (множественные тесты) | Тест | Подтверждено |

### Проверки, выполненные в окружении проверки

| Команда | Результат | Примечание |
|---------|-----------|------------|
| `python manage.py check` (Django 5.2.18, Wagtail 7.4.3 из `requirements.txt`) | `System check identified no issues (0 silenced)` | Запущено с `DJANGO_SECRET_KEY` синтетическим; без подключения к БД |
| `python manage.py makemigrations --check --dry-run` | `No changes detected` | Состояние миграций соответствует моделям; предупреждение о недоступности PostgreSQL ожидаемо |
| Сравнение базы PR #72 с `main` через GitHub compare API | База PR #72 `4b5b6a269cdff0260331087d4da0a1b85c0de181` **является предком** `main`; `main` опережает на 1 коммит; `mergeable: true` | Конфликтов с текущим `main` не ожидается (PR #72 только добавляет новые файлы) |

Не выполнено в среде проверки (отмечено явно, без заявления об успехе):
- Полный запуск `python manage.py test` — в sandbox нет PostgreSQL сервера (подключение к `127.0.0.1:5432` отказано); тестовая БД не развернута.
- HTTP-проверки работающего приложения: ответы `/sitemap.xml`, `/robots.txt`, наличие `noindex`/`canonical` в отрисованном HTML, коды 404/редиректов.
- Проверка на реальных устройствах/браузерах и на公開 production-домене (домен не согласован владельцем).

Примечание по среде: Python sandbox 3.11.2, тогда как CI собирает 3.13.17; пакет `soupsieve==3.0.4` установлен с `--ignore-requires-python` (маркер требует >=3.11.5). Это не повлияло на статические проверки Django, но отличает окружение от CI.

## 3. Оценка PR #72 «tools: add read-only audit for public SEO content»

| Атрибут | Значение |
|---------|----------|
| Состояние | открыт, Draft, не слит |
| Голова (head) | `e007fac496e73c496b88838ca4e976d5599d2081`, ветка `feature/audit-public-seo-content` |
| База (base) | `4b5b6a269cdff0260331087d4da0a1b85c0de181` (предок текущего `main`) |
| Изменения | 4 файла добавлено, 415 строк, 0 удалений: `school/management/__init__.py`, `school/management/commands/__init__.py`, `school/management/commands/audit_public_seo.py`, `school/test_seo_audit.py` |
| Mergeable | `true` (GitHub API) |
| CI на голове | пройден (согласно комментариям Issue #62, run #155) |

### Что делает команда (по коду на голове PR #72)

`audit_public_seo` — read-only команда управления:
- обходит только `Page.objects.live().public().specific()` — опубликованные общедоступные страницы; черновики и страницы с ограничением доступа исключаются;
- не меняет модели, миграции, настройки, URL и контент;
- выводит инвентаризацию страниц и находки в текстовом или JSON-формате (`--format json`);
- детерминирован: инвентарь и находки сортируются; ключи нормализуются (пробелы, casefold);
- код не содержит вызовов записи, сетевых запросов или обращения к production-данным.

### Находки команды

- `generic_meta_description_fallback` — урок без явного SEO-описания и без intro;
- `image_alt_needs_review` — изображения/эмбеды без контекстуального `alt` в rich text lessons;
- `duplicate_effective_title` / `duplicate_explicit_search_description` — повторяющиеся значения между страницами;
- 심각ность находок: `review` (рекомендация к проверке, а не блокирующая ошибка).

### Тесты (`school/test_seo_audit.py`)

Покрывают: попадание страницы в инвентарь и находку фолбэка generic description; эмбеды изображения без `alt` (явно пустой `alt` считается декоративным и не флажится); исключение черновиков и страниц с `PageViewRestriction.LOGIN` из аудита; duplicate títulos и описаний. Все тесты используют синтетические данные.

### Ограничения команды (очевидны из кода, не дефекты)

- не аудирует sitemap, robots.txt, canonical, social-мета, h1, внутренние ссылки — это вне заявленного объема команды;
- `page.url` зависит от настроенного Wagtail Site; без публичного origin пути остаются сайт-относительными;
- не заменяет проверку реального production-контента (синтетические тесты не показывают дубликаты SEO-полей на боевой базе CMS).

### Вердикт по PR #72

**Положительный.** PR #72 — узкий, аддитивный (только новые файлы), read-only инструмент с тестами, не меняющий публичное поведение. База PR является предком текущего `main`; конфликтов при слиянии не ожидается (GitHub: `mergeable: true`). Команда не закрывает все пробелы SEO-аудита (sitemap/robots/canonical require отдельного решения по домену), но не претендует на это. Рекомендуется к принятию владельцем как следующий独立й шаг после Issue #62 этапа 1 — см. раздел 6.

## 4. Таблица наблюдений, рисков, рекомендаций и критериев приёмки

| # | Наблюдение | Доказательство | Риск / приоритет | Рекомендация | Критерий приёмки |
|---|------------|----------------|------------------|--------------|------------------|
| 1 | Sitemap подключён и покрыт тестом; кэширование sitemap не вводилось | `config/urls.py:19`; `tests.py:300` | Низкий | Оставить без изменений; кэш только после проверки инвалидации при публикации/снятии | Изменений не требуется |
| 2 | `robots.txt` отсутствует; директива Sitemap не может быть выдана без подтверждённого домена | отсутствие файла/маршрута | Средний | Не подставлять выдуманный домен; после согласования публичного origin добавить маршрут и тест | Решение владельца по домену; маршрут + тест |
| 3 | `canonical` отсутствует; корректный origin не согласован | `base.html` без canonical | Средний | Не подставлять `localhost`/`WAGTAILADMIN_BASE_URL` автоматически; отдельный PR после решения по домену | Владелец подтвердил canonical origin |
| 4 | OG/Twitter мета presentes, но нет `og:url`, канонических абсолютных URL и абсолютных URL изображений | `social_metadata.html` | Низкий/средний | Ввести после подтверждения origin (PR #73 уже подготовлен upstream, зависит от #71) | Владелец принял решение по домену |
| 5 | `noindex,follow` для URL каталога с `q` и/или `direction` — политика реализована, но требует одобрения владельца | `home_page.html:5`; `tests.py:722` | Средний | Оставить текущее поведение до явного решения: индексировать или нет фильтрующие URL | Владелец утвердил политику индексации |
| 6 | `404.html`/`500.html` отсутствуют; Wagtail обрабатывает 404; тесты фиксируют фактические статусы | `tests.py:184,188,204` | Низкий | Документировать ожидаемые статусы; пока не менять | Тесты зелёны в CI |
| 7 | Черновики и закрытые страницы исключены из公開 представлений | `tests.py` (множественные тесты) | Низкий | Поддерживать при любых изменениях sitemap/поиска | Тесты на исключение проходят |
| 8 | Публичный поиск ограничен `title`, `intro`, `search_keywords`; `body` не индексируется | `models.py` `HomePage.get_context` | Низкий | Не расширять поиск на тело урока без отдельного решения | Контракт поиска не расширен |
| 9 | Вёрстка: один `h1`, семантический `article`,ビデо с `title` у iframe, адаптивная сетка | `lesson_page.html`, `home_page.html`, CSS | Низкий | Сохранить при рефакторингах | Тесты заголовков и ссылок проходят |

## 5. Вопросы, требующие решения владельца (не утверждены в этом отчёте)

1. **Канонический публичный origin** — какой домен считать каноническим и откуда приложение должно брать hostname для Wagtail Site / production-конфигурации. `smartchild-school.com` не подставлять как реальный домен без подтверждения.
2. **Политика индексации URL поиска/фильтрации** — должны ли `/`?`q=` и `?direction=` индексироваться. Текущее поведение `noindex,follow` требует утверждения.
3. **Политика снятых/удалённых URL** — 410 только при явной политике (по §H, не автоматически); согласованные 301 при equivalents, не массовый редирект на главную.
4. **`og:url` и абсолютные URL изображений** — возможны только после подтверждения HTTPS origin.

Нижеизложенные architectural предложения (`docs/technical/TECH-DESIGN-001.md`, раздел H, и ранний текст Issue #62) считаются **предложениями**, а не утверждёнными требованиями.

## 6. Предложенный следующий узкий PR (не начат)

**Предложение:** принять (замержить) Draft PR #72 `tools: add read-only audit for public SEO content` в `main` после отдельной приёмки владельцем.

**Обоснование:**
- Только чтение и только новые файлы — не меняет модели, миграции, настройки, URL, шаблоны и публичное поведение;
- База PR является предком `main` (main опережает на 1 коммит); `mergeable: true`, конфликтов не ожидается;
- CI на голове PR прошёл успешно (запуски, указанные в Issue #62);
- Даёт редактору и CI инструмент инвентаризации опубликованного SEO-контента (дубли títulos/описаний, фолбэк generic description, изображения без alt), независимо от pending-решений по домену и canonical;
- Не конфликтует с запретами задания: код, тесты, модели, миграции, настройки и контент не меняются в рамках этого отчёта.

**Тесты PR #72 (уже в ветке PR):** fallback generic meta description; изображения без контекстуального `alt`; исключение черновиков и закрытых страниц; дубли títulos и описаний.

**Критерии приёмки следующего PR:**
1. Владелец явно принял PR #72;
2. `python manage.py check` без ошибок на целевом SHA;
3. `python manage.py makemigrations --check --dry-run` — без изменений;
4. Полный набор автоматических тестов (`school/tests.py`, `school/test_social_metadata.py`, `school/test_migrations.py`, `school/test_seo_audit.py`) — зелёный;
5. `python manage.py migrate --check` — чистое состояние миграций;
6. Нет изменений публичного поведения, URL, моделей или контента.

**Альтернатива (уже подготовлена upstream):** PR #73 «seo: add domain-independent social metadata» — зависит от принятого #71; требует retarget на `main` после слияния #71 и повторной проверки CI. Может следовать сразу после PR #72.

## 7. Что не входит в этот отчёт

- Функциональные изменения кода, тестов, моделей, миграций, настроек, контента Wagtail;
- Деплой, публикация страниц, изменение production/DNS;
- Реализация canonical, robots.txt, изменения индексации;
- Автоматическое создание страниц тем/тегов.

---

Файл отчёта: `docs/reviews/issue-62-seo-frontend-audit-85a490d.md`, commit будет выполнен в ветке `arena/311bc9b1-smartchild-school` отдельным Draft PR, содержащим только этот отчёт. SHA отчёта будет указан в ответе после коммита.
