# TECH-001 — локальный запуск минимального каркаса

## Назначение и границы

Этот каркас проверяет техническую связку Django + Wagtail + PostgreSQL. На
момент создания каркаса в нём не было каталога уроков и учебных материалов;
первый публичный учебный сценарий (каталог и страницы уроков Wagtail) позже
предложен отдельным PR #45 на базе этого каркаса. Регистрации учеников,
пользовательских функций и выполнения пользовательского кода по-прежнему
нет. Маршруты проверки здоровья служат только технической диагностике.

Локальная почта по умолчанию использует консольный backend Django: письма
Wagtail (уведомления модерации, сброс пароля) печатаются в терминал
`runserver`, настоящий SMTP-сервер для локальной разработки не нужен и
подключение к нему не выполняется. Production-конфигурация и порядок
будущего развёртывания описаны отдельно в
[production-runbook](production-deployment-runbook.md).

## Зафиксированные версии

| Компонент | Версия |
| --- | --- |
| Python | 3.13.17 (см. `.python-version`) |
| Django | 5.2.18 |
| Wagtail | 7.4.3 |
| Psycopg | 3.3.6 |
| PostgreSQL | 18.6 (см. `docker-compose.yml`) |
| Gunicorn (только production-запуск) | 26.2.0 |
| WhiteNoise (статика в production) | 6.12.0 |

Проверка по официальной документации выполнена 2026-10-22. Прямые зависимости
заданы в `requirements.in`; `requirements.txt` — lock со всеми прямыми и
транзитивными пакетами, закреплёнными точными версиями. Он сформирован по
фактическому успешному разрешению пакетов в CI на Python 3.13.17 и PostgreSQL
18.6 2026-10-22. Версии пакетов зафиксированы, но хеши артефактов не указаны,
поэтому не заявляется побитовая идентичность всех возможных установок.

При обновлении зависимостей изменяйте `requirements.in`, заново разрешайте
пакеты в чистом окружении Python 3.13.17, обновляйте lock целиком и повторяйте
все проверки CI. Не редактируйте транзитивные версии выборочно без проверки.

Источники:
- [Python 3.13.17](https://www.python.org/downloads/release/python-31317/)
- [Django 5.2.18](https://docs.djangoproject.com/en/5.2/releases/5.2.18/)
- [Матрица совместимости Wagtail 7.4](https://docs.wagtail.org/en/stable-7.4.x/releases/upgrading.html)
- [Wagtail releases](https://github.com/wagtail/wagtail/releases)
- [Psycopg install and supported versions](https://www.psycopg.org/psycopg3/docs/basic/install.html)
- [Psycopg on PyPI](https://pypi.org/project/psycopg/)
- [PostgreSQL 18.6](https://www.postgresql.org/docs/release/18.6/)

## Требования

- Python 3.13.17;
- Docker Engine with Docker Compose plugin (для PostgreSQL);
- доступ к PyPI для установки Python-пакетов.

## Подготовка конфигурации

В корне репозитория выполните:

```bash
cp .env.example .env
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Скопируйте выведенное случайное значение в `DJANGO_SECRET_KEY` в локальном
файле `.env`. Не коммитьте `.env`: он исключён через `.gitignore`.
Для локального запуска через `runserver` обязательно установите `DJANGO_DEBUG=true` в `.env`: при `DEBUG=false` Django не раздаёт статические файлы через встроенный сервер. В `DEBUG=true` этот каркас раздаёт статические файлы и медиа локально; это предназначено только для разработки, не для production.

## Запуск PostgreSQL

```bash
set -a
. ./.env
set +a
docker compose up -d db
docker compose ps
```

Дождитесь состояния `healthy` для сервиса `db`.

## Установка и запуск Django/Wagtail

```bash
# В каждой новой оболочке заново загрузите локальные переменные окружения.
set -a
. ./.env
set +a

python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py migrate --check
python manage.py test
python manage.py createsuperuser
python manage.py runserver
```

Команда `createsuperuser` интерактивно создаёт локальную учётную запись
администратора для входа в Wagtail CMS. Используйте отдельный локальный пароль;
не переносите его в репозиторий и не используйте пароль от других сервисов.

После запуска:
- административная панель Wagtail: http://127.0.0.1:8000/cms/;
- проверка процесса: http://127.0.0.1:8000/health/live/;
- проверка готовности с PostgreSQL: http://127.0.0.1:8000/health/ready/.

Маршруты здоровья возвращают только технический статус, не раскрывая детали
исключений и конфигурацию БД. Проверка `live` не проверяет БД; `ready`
выполняет простой запрос к PostgreSQL и возвращает HTTP 503 при ошибке БД.

## Автоматические проверки

CI устанавливает закреплённый lock из `requirements.txt` и выполняет проверки
на Python 3.13.17 и PostgreSQL 18.6: `pip check`, `manage.py check`,
`makemigrations --check --dry-run`, миграции, `manage.py test` и
`migrate --check`. Тесты используют синтетическую тестовую БД, без персональных
данных.

По состоянию на 2026-10-22 CI успешно завершил сборку Python 3.13.17, установку закреплённых зависимостей, проверки Django и миграций, применение миграций PostgreSQL, автоматические тесты и `migrate --check`. Этот результат относится к конкретному commit SHA, указанному в PR, и должен быть перепроверен после следующих изменений.

## Остановка

```bash
docker compose stop db
```

Остановка контейнера не удаляет именованный том с локальной базой.
