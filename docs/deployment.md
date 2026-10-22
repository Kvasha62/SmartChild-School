# Развёртывание Wagtail

Этот документ описывает воспроизводимый контейнерный запуск приложения, а не
выбор хостинг-провайдера и не разрешение на публикацию сайта в Интернете.
До реального production-релиза отдельно нужны домен, TLS, инфраструктура
резервного копирования и восстановление, выбранное место размещения и проверка
производительности/безопасности.

## Что входит в контейнерный контур

- Gunicorn запускает WSGI-приложение вместо Django `runserver`.
- WhiteNoise и `CompressedManifestStaticFilesStorage` обслуживают версионированные
  статические файлы Wagtail; `collectstatic` выполняется при сборке образа.
- PostgreSQL доступен только во внутренней Docker-сети; данные хранятся в
  именованном томе.
- Загруженные медиа находятся в отдельном постоянном томе. Nginx отдаёт только
  производные изображения из `/media/images/`; `/media/original_images/` и
  другие пути `/media/` не публикуются. Документы продолжают обслуживаться
  Wagtail через `/documents/`, где сохраняется проверка разрешений.
- `/health/live/` проверяет процесс приложения, а `/health/ready/` — доступность
  PostgreSQL.
- Настройки читаются из переменных окружения. В `DEBUG=True` письма выводятся
  в консоль; production по умолчанию использует SMTP и отклоняет локальную
  конфигурацию с демонстрационными секретами.

## Локальная разработка

Для ежедневной разработки используй обычные settings, console email и локальный
PostgreSQL. Django не загружает файл `.env` автоматически:

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
nano .env
set -a
source .env
set +a
docker compose up -d db
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Сайт: [http://127.0.0.1:8000/](http://127.0.0.1:8000/), CMS:
[http://127.0.0.1:8000/cms/](http://127.0.0.1:8000/cms/). В локальной
разработке Wagtail выводит email-уведомления в терминал вместо попытки
подключиться к реальному SMTP-серверу.

## Production/staging Compose

`compose.production.yml` всегда запускает `config.production_settings` и
не предназначен для обхода production-проверок локальными значениями. Для
staging скопируй `.env.production.example` в приватный `.env`, замени все
`CHANGE_ME` значения и укажи настоящий домен, SMTP и постоянный том media.
Не добавляй этот файл в Git и не используй значения CI:

```bash
cp .env.production.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
nano .env
docker compose -f compose.production.yml config --quiet
docker compose -f compose.production.yml build
docker compose -f compose.production.yml run --rm app python manage.py migrate --noinput
docker compose -f compose.production.yml up -d
docker compose -f compose.production.yml ps
```

Перед запуском приложения команда `run ... migrate` выполняет миграции
явно; приложение не запускает миграции при старте. PostgreSQL не публикует
порт на host. Reverse proxy по умолчанию доступен только через
`127.0.0.1:8080`; внешний TLS ingress должен завершать HTTPS, перезаписывать
`X-Forwarded-Proto` и передавать трафик этому proxy. Не выставляй Nginx
напрямую в Интернет и не включай доверие к forwarded-заголовку, если
приложение доступно в обход доверенного ingress.

## Обязательная production-конфигурация

Перед запуском контейнера с `config.production_settings` в защищённом `.env` укажи реальные
значения (сам файл не добавляй в Git):

- `DJANGO_SECRET_KEY`: уникальный случайный секрет не короче 50 символов.
- `DJANGO_DEBUG=false`.
- `DJANGO_ALLOWED_HOSTS`: только домены сайта, без `*`, `localhost` и
  `testserver`.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: HTTPS origins, если они нужны для используемого
  домена/панели.
- `WAGTAILADMIN_BASE_URL`: публичный HTTPS URL сайта; Wagtail использует его
  при формировании абсолютных ссылок.
- `DB_PASSWORD`: уникальный пароль PostgreSQL; замени локальный пример.
- `DJANGO_EMAIL_HOST`, `DJANGO_DEFAULT_FROM_EMAIL` и при необходимости SMTP
  credentials. При порте 587 используется TLS по умолчанию. Для порта 465 задай
  `DJANGO_EMAIL_USE_TLS=false` и `DJANGO_EMAIL_USE_SSL=true`.
- Если PostgreSQL требует TLS, установи `DB_SSLMODE=require`. `DB_ADMIN_USER` и `DB_ADMIN_PASSWORD` используются только контейнером и bootstrap-скриптом PostgreSQL; приложение получает лишь ограниченную роль `DB_USER`/`DB_PASSWORD`. Production требует `DJANGO_EMAIL_HOST_USER` и `DJANGO_EMAIL_HOST_PASSWORD`.

Production-конфигурация отклоняет запуск с DEBUG, демонстрационными значениями,
неограниченным `ALLOWED_HOSTS`, небезопасными cookies/redirect, HTTP URL CMS
или отключённой/консольной почтой. Проверь итоговую конфигурацию до релиза:

```bash
python manage.py check --deploy --settings=config.production_settings
```

Предупреждение об HSTS остаётся до тех пор, пока HSTS не включён. Сначала
убедись, что HTTPS работает для всех доменов и нет HTTP-only поддоменов, затем
задай `DJANGO_SECURE_HSTS_SECONDS=31536000`. Не включай
`DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` или `DJANGO_SECURE_HSTS_PRELOAD`, пока
все поддомены и долгосрочные последствия не проверены.

`check --deploy` может также предупреждать о `X_FRAME_OPTIONS=SAMEORIGIN`:
это сохраняет возможность встраивания страниц в iframe только с того же origin,
но слабее глобального `DENY`. Значение не меняется молча в этой задаче: на
staging проверь работу preview/админки и только после проверки принимай решение
о более строгом `DENY`. Ожидаемое предупреждение HSTS до настройки домена и TLS
не должно скрывать любые новые warnings/errors — читай полный вывод `check --deploy`.

## TLS ingress / reverse proxy

Compose-профиль поднимает HTTP reverse proxy и по умолчанию публикует его
только на `127.0.0.1:8080`. TLS должен завершаться на доверенном входном proxy
или балансировщике; выбери его при утверждении места размещения. Для production
укажи `DJANGO_TRUST_PROXY_SSL_HEADER=true` только если приложение недоступно
напрямую, а доверенный ingress перезаписывает `X-Forwarded-Proto`. Не доверяй
этому заголовку от произвольного клиента: иначе можно ослабить HTTPS-защиту и
CSRF-проверку. Ограничь сетевой доступ к порту Nginx; для локального reverse
proxy по умолчанию оставь bind на loopback.

Nginx-конфигурация временно ограничивает запросы тела до 20 MiB. Этот потолок
действует и для документов; до запуска публичного сайта нужно согласовать
допустимый размер загрузок и изменить `client_max_body_size` соответственно.
Крайне важно не публиковать весь `MEDIA_ROOT`: открыты только сгенерированные
изображения, а оригиналы и документы не отдаются как обычные статические файлы.

## Порядок релиза

1. Выбери хостинг/регион и способ TLS, базу и постоянное файловое хранилище.
2. Создай секреты вне репозитория; настрой домены, SMTP и разрешённые origins.
3. Собери конкретный образ и выполни `python manage.py check --deploy --settings=config.production_settings`.
4. Перед миграциями создай и проверь восстановление резервной копии PostgreSQL
   и файлового тома. План хранения и RPO/RTO ещё должны быть утверждены.
5. Запусти миграции одноразовой командой `docker compose ... run --rm app
   python manage.py migrate --noinput`, затем разверни приложение и proxy.
6. Проверь анонимный каталог/урок, вход в `/cms/`, публикацию, почтовое
   уведомление, изображения, документы, health endpoints, HTTP→HTTPS redirect,
   корректные cookies и доступность после перезапуска.
7. Только после проверок включай HSTS и открывай сайт публичному трафику.

Не запускать Django `runserver` в production. Не запускать пользовательский
Python-код на сервере сайта: runner в MVP не входит.


## Least-privilege PostgreSQL и существующие тома

На пустом PostgreSQL volume init-скрипт
`deploy/postgres/10-create-app-role.sh` создаёт отдельную роль приложения с
`NOSUPERUSER NOCREATEDB NOCREATEROLE` и передаёт ей владение целевой БД.
Bootstrap-учётная запись `DB_ADMIN_USER` нужна только PostgreSQL service и
не передаётся приложению. CI проверяет, что роль приложения не имеет
суперпользовательских и административных атрибутов.

**Init-скрипты PostgreSQL исполняются только при инициализации пустого data
directory.** Если volume уже создан старой конфигурацией, изменение
`POSTGRES_USER` и добавление init-скрипта автоматически не создадут роли.
До переключения существующей базы на новую конфигурацию создай отдельную
роль вручную от текущего администратора, введи пароль интерактивно и передай
ей владение базой:

```sql
CREATE ROLE smartchild_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
\password smartchild_app
ALTER DATABASE smartchild OWNER TO smartchild_app;
```

Имена БД и роли выше — пример; замени их значениями своего окружения.
Сначала исполни процедуру на копии БД и убедись, что миграции и чтение/запись
контента работают. Не удаляй существующий volume для «повторной
инициализации»: это уничтожит данные.

## Файловая система контейнера и media

Процесс Wagtail работает с uid/gid `10001:10001`, корневая файловая система
контейнера только для чтения; writable-пути — `/tmp` (tmpfs) и явно
смонтированный постоянный `DJANGO_MEDIA_ROOT=/srv/media`. Код и статика
в образе не должны изменяться работающим приложением. Не добавляй общий
volume на `/app` и не запускай `collectstatic` во время старта.

Nginx публикует только `/media/images/` (производные изображения).
Проверка приватности должна использовать **существующие тестовые файлы**, а
не только ожидать 404 на несуществующем пути: seeded original из
`/media/original_images/` и файл из `/media/documents/` обязаны возвращать
404 через публичный proxy; seeded rendition из `/media/images/` — доступна.
Это не решает автоматически вопрос, можно ли публично показывать rendition
изображения, пока исходная Wagtail-страница является черновиком. Приватность
renditions черновиков требует отдельного решения до размещения чувствительных
изображений.

## Резервное копирование, восстановление и откат

До staging/production выпуска должны существовать копии **и PostgreSQL, и
media** вне узла/тома приложения. Пример команд; учётные данные берутся из
защищённого окружения или `.pgpass`, а не задаются открытым аргументом:

```bash
pg_dump --format=custom --no-owner --host="$DB_HOST" \
  --username="$DB_ADMIN_USER" --dbname="$DB_NAME" \
  --file="smartchild-db-$(date -u +%Y%m%dT%H%M%SZ).dump"

tar --create --gzip --file="smartchild-media-$(date -u +%Y%m%dT%H%M%SZ).tar.gz" \
  --directory="$DJANGO_MEDIA_ROOT" .
```

Восстанавливай пару БД + media сначала на отдельном test/staging окружении:

```bash
pg_restore --clean --if-exists --no-owner --host="$DB_HOST" \
  --username="$DB_ADMIN_USER" --dbname="$DB_NAME" smartchild-db.dump
tar --extract --gzip --file=smartchild-media.tar.gz --directory="$DJANGO_MEDIA_ROOT"
docker compose -f compose.production.yml run --rm app python manage.py migrate --check
```

На production восстановление требует окна обслуживания и отдельного
утверждения. Периодичность копий, retention, off-site хранение, RPO/RTO,
ответственный и подтверждённое учение восстановления пока не выбраны —
поэтому SLA/готовность к публичному запуску не заявляются. Откат приложения
в первую очередь означает возврат к предыдущему immutable image tag; откат
схемы БД допустим только после проверки обратной совместимости миграций.

## Проверки и оставшиеся блокеры

CI проверяет production settings на синтетических значениях, миграции и тесты
на Python 3.13.17/PostgreSQL 18.6, `check --deploy`, manifest статики,
сборку образа и Compose smoke: роль БД не является администратором, `/app`
не writable, health endpoints и CMS доступны, статика загружается, существующая
rendition доступна, original и документ закрыты, а media переживает рестарт
приложения.

CI **не** подтверждает рабочую почту, настоящий DNS/TLS/HTTPS ingress,
восстановление backup, нагрузку, мониторинг/алерты или приватность renditions
черновиков. До публичного запуска остаются решения о хостинге/регионе,
домене/TLS, SMTP и SPF/DKIM/DMARC, лимитах загрузок, storage/backup/RPO/RTO,
мониторинге, MFA и политике доступа редакторов, staging и реестре образов.
