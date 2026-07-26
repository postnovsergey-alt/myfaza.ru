# Спринт 1 — что сделано и что проверить

## Готово

| Пункт | Файл |
|---|---|
| Конфиг из окружения | `backend/app/config.py` |
| Async engine, сессии, миксины | `backend/app/db/base.py` |
| Перечисления из ТЗ | `backend/app/db/enums.py` |
| users, user_settings | `backend/app/db/models/user.py` |
| cycles, daily_logs | `backend/app/db/models/cycle.py` |
| push_subscriptions, notifications | `backend/app/db/models/notification.py` |
| sessions, account_link_tokens, audit_log | `backend/app/db/models/session.py` |
| Шифрование поля note (AES-256-GCM) | `backend/app/core/crypto.py` |
| Скрабинг чувствительных полей | `backend/app/core/logging.py` |
| /health, /health/ready | `backend/app/api/v1/health.py` |
| Начальная миграция | `backend/alembic/versions/0001_initial.py` |
| Docker Compose, Makefile | `docker-compose.yml`, `Makefile` |
| Тесты (12 шт.) | `backend/tests/` |

## Проверить на своей машине

- [ ] `make up` — контейнеры поднялись, healthcheck зелёный
- [ ] `make migrate` — миграция прошла без ошибок
- [ ] `\dt` в psql показывает 9 таблиц + `alembic_version`
- [ ] `\dT` показывает 9 enum-типов, метки в нижнем регистре
- [ ] `curl /api/v1/health/ready` возвращает `database: ok, redis: ok`
- [ ] `make test` — 12 тестов зелёные

## Известные ограничения

Начальная миграция написана через `op.execute()` с готовым DDL, а не через
`op.create_table()`. Причина: DDL сгенерирован напрямую из моделей, поэтому
гарантированно им соответствует. Следующие миграции делайте обычным
автогенератором: `make revision m="описание"`.

`/health/ready` тестами не покрыт — нужна живая БД. Проверяется руками
по чек-листу выше.

## Не делалось намеренно

Бизнес-логика, аутентификация, API циклов, алгоритм прогноза, бот,
уведомления, фронтенд. Это спринты 2–6, промпты — в разделе 15 ТЗ.

## Что проверено при сборке

- `ruff check app tests` — чисто
- 12 тестов зелёные
- DDL миграции сгенерирован из моделей, синтаксис проверен

Тесты прогонялись в окружении с Python 3.10, поэтому `enums.py` на время
прогона подменялся эквивалентом `(str, Enum)`. В поставке — `StrEnum`,
как положено для 3.12. Прогоните `make test` у себя на 3.12 первым делом.
