# TECH-001 — локальный запуск минимального каркаса

## Назначение и границы

Этот каркас проверяет техническую связку Django + Wagtail + PostgreSQL. В нём
нет каталога уроков, учебных материалов, регистрации учеников, пользовательских
функций или выполнения пользовательского кода. Маршруты проверки здоровья
служат только технической диагностике.

## Зафиксированные версии

| Компонент | Версия |
| --- | --- |
| Python | 3.13.17 (см. `.python-version`) |
| Django | 5.2.18 |
| Wagtail | 7.4.3 |
| Psycopg | 3.3.6 |
| PostgreSQL | 18.6 (см. `docker-compose.yml`) |

Проверка по официальной документации выполнена 2026-10-22. Это исходные точные
версии; файл `requirements.txt` фиксирует прямые зависимости. Транзитивные
зависимости пока разрешаются установщиком и должны быть зафиксированы lock-файлом
после первого успешного разрешения пакетов в CI. Поэтому полная побитовая
воспроизводимость окружения на этом этапе ещё не заявляется.

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
Для локальной разработки в `.env` можно оставить `DJANGO_DEBUG=true`.

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
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py migrate --check
python manage.py test
python manage.py runserver
```

После запуска:
- административная панель Wagtail: http://127.0.0.1:8000/cms/;
- проверка процесса: http://127.0.0.1:8000/health/live/;
- проверка готовности с PostgreSQL: http://127.0.0.1:8000/health/ready/.

Маршруты здоровья возвращают только технический статус, не раскрывая детали
исключений и конфигурацию БД. Проверка `live` не проверяет БД; `ready`
выполняет простой запрос к PostgreSQL и возвращает HTTP 503 при ошибке БД.

## Автоматические проверки

CI выполняет те же проверки на Python 3.13.17 и PostgreSQL 18.6:
`manage.py check`, `makemigrations --check --dry-run), миграции,
`manage.py test` и `migrate --check`. Тесты используют синтетическую тестовую
БД, без персональных данных.

До получения результатов CI нельзя считать, что команды уже успешно выполнены.
Результаты и ограничения фиксируются в PR после фактического прогона.

## Остановка

```bash
docker compose stop db
```

Остановка контейнера не удаляет именованный том с локальной базой.
