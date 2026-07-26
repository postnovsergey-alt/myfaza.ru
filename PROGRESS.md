# Прогресс

Обновляется агентом после каждой завершённой задачи.
Читается в начале каждой сессии — здесь память проекта между запусками.

## Текущий спринт

**Спринт 2 — аутентификация. Статус: готов.**

## Сделано

### Спринт 1
- Каркас FastAPI, конфиг на pydantic-settings, ленивый async engine
- 9 моделей БД из раздела 6 ТЗ + начальная миграция `0001_initial`
- Шифрование `daily_logs.note` (AES-256-GCM)
- Скрабинг чувствительных полей для логов и Sentry
- `/health`, `/health/ready`
- docker-compose, Makefile, 12 тестов

### Спринт 2 — аутентификация
- `app/core/security.py`: argon2id для паролей, JWT HS256, генерация и SHA-256
  хеширование refresh-токенов, соль+хеш IP
- `app/services/auth_service.py`: регистрация, логин, Telegram-логин, ротация
  refresh с обнаружением кражи (компрометация → отзыв всех сессий), logout,
  фиксация согласия, создание и подтверждение link-токенов TG↔web
- `app/services/telegram_auth.py`: валидация initData через
  `aiogram.utils.web_app.safe_parse_webapp_init_data` + обязательная проверка
  `auth_date < 24h` (раздел 10.1 ТЗ, п.6)
- `app/api/deps.py`: `get_current_user` из Bearer-токена, `client_ip`, `device_label`
- `app/api/v1/auth.py`: 8 эндпоинтов из раздела 8.1 ТЗ
  (`/telegram`, `/register`, `/login`, `/refresh`, `/logout`, `/consent`,
  `/link/create`, `/link/confirm`)
- `app/schemas/auth.py`: DTO с EmailStr, форматом ответа `{access_token,
  refresh_token, expires_in, user}`
- 21 тест на все обязательные сценарии: initData валидный/протухший/битый
  hash/чужой токен; логин/регистрация/argon2-хеш; ротация refresh,
  обнаружение кражи, истёкший refresh, logout; consent требует авторизации;
  link-токен одноразовый, TTL 15 мин, направление проверяется
- Тесты изолируются truncate'ом перед каждым тестом; для asyncpg подключён
  `NullPool` в тестовом режиме — иначе pytest-asyncio ловит
  "Event loop is closed"

### Инфраструктура
- В `.env` BOT_TOKEN шёл вместе с trailing-комментарием — в conftest.py
  принудительное задание тестового значения (см. `DECISIONS.md`)
- `NullPool` в engine при `USE_NULL_POOL=1` или под pytest — чтобы соединения
  asyncpg не пересекали event loop'ы

### Дизайн
- Палитра «Тёплый песок» утверждена, значения в OKLCH зафиксированы
  в `docs/DESIGN-SPEC.md` (2.1), светлая и тёмная темы
- Язык движения, бюджет производительности, критерии приёмки — там же
- MCP настроены в `.mcp.json`: chrome-devtools, playwright, figma

## Следующий шаг

Спринт 3 — ядро: CRUD циклов, дневные логи, алгоритм прогноза + тесты
из раздела 7.7 ТЗ. Промпт в `CLAUDE.md`, раздел 15.

## Где остановились

—
