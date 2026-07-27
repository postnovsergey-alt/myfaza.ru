# Прогресс

Обновляется агентом после каждой завершённой задачи.
Читается в начале каждой сессии — здесь память проекта между запусками.

## Текущий спринт

**Спринт 5 — уведомления. Статус: готов.**

## Сделано

### Спринт 1
- Каркас FastAPI, конфиг на pydantic-settings, ленивый async engine
- 9 моделей БД из раздела 6 ТЗ + начальная миграция `0001_initial`
- Шифрование `daily_logs.note` (AES-256-GCM)
- `/health`, `/health/ready`, docker-compose, Makefile, 12 тестов

### Спринт 2 — аутентификация
- argon2id, JWT HS256, ротация refresh с обнаружением кражи
- Telegram initData (проверка auth_date < 24h)
- 8 эндпоинтов /auth, 21 тест

### Спринт 3 — ядро
- Алгоритм прогноза по разделу 7 ТЗ, 22 юнит-теста
- 10 эндпоинтов (/cycles, /predictions, /logs), 22 HTTP-теста

### Спринт 4 — фронтенд
- Vite + React 18 + TS + Tailwind + PWA-плагин
- 5 экранов + логирование + онбординг, i18n со своим мини-парсером плюралов
- OpenAPI-клиент, платформенный слой TG↔web, тёплая песочная палитра
- Бандл 76 KB gzip, Lighthouse Accessibility 100

### Спринт 5 — уведомления
- `services/notifications.py`: `plan_notifications` материализует
  строки на текущее часовое окно с учётом таймзоны пользователя.
  Дедупликация через `INSERT ON CONFLICT DO NOTHING` по UNIQUE
  `(user_id, type, target_date, channel)` — двойной запуск не создаёт
  дублей (FR-4.8)
- `services/notification_sender.py`: отправка в Telegram (aiogram) и
  Web Push (pywebpush) с обработкой ошибок:
  - Telegram 403 (bot blocked) → переключение канала на web/none
  - Telegram 429 → уважение retry_after
  - Push 404/410 → деактивация подписки
  - Push failure_count ≥ 5 → деактивация
- `bot/texts.py`: тексты для дискретного и обычного режима
  (без слов «менструация», «цикл» в дискретных заголовках)
- Эндпоинты (FR-8.5, ТЗ 8.6):
  - `GET/PATCH /settings` — управление всеми параметрами уведомлений
  - `POST /push/subscribe`, `POST /push/unsubscribe`
  - `GET /push/vapid-key` — публичный ключ для клиентской подписки
  - `POST /push/test` — тестовый пуш, rate limit 1/мин через Redis
- Фронтенд:
  - `sw.ts` — service worker: `push` показывает уведомление,
    `notificationclick` открывает нужный экран или фокусирует таб
  - `pushClient.ts` — subscribe/unsubscribe с корректной подпиской
    через `applicationServerKey` (base64url → Uint8Array)
  - `IosInstallHint` — детекция Safari-iOS-non-standalone,
    инструкция по установке PWA (ТЗ 9.3, обязательное требование)
  - Настройки уведомлений в `SettingsPage`: за сколько дней (1/2/3/5/7),
    канал (telegram/web/both/none), дискретный режим, тестовый пуш
- Тесты (обязательные из ТЗ 9.5):
  - Пользователь в `Asia/Vladivostok` получает пуш в 10:00 по своему
    времени, но не в 10:00 MSK
  - Двойной запуск планировщика — 0 дубликатов
  - `channel=none` не получает ничего
  - `IntegrityError` при попытке вставить дубль вручную
  - `freezegun` мокает время в планировщике

**Итого 89 тестов зелёные**, ruff + mypy чисты, /health/ready → ok.

Метрики фронта (актуальные после SW и push-клиента):
- Bundle JS: 244.73 KB min / **77.65 KB gzip** (бюджет NFR-3: < 250 KB gzip)
- SW: 16.47 KB min / 5.60 KB gzip
- Bundle CSS: 15.67 KB / 4.16 KB gzip

## Следующий шаг

Спринт 6 — личный кабинет + деплой. Разделы FR-8, 8.5, 12 ТЗ. Профиль,
способы входа, сессии, история записей, приватность. docker-compose.prod,
Nginx, CI/CD, чек-лист приёмки (раздел 14).

## Где остановились

—
