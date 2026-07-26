# Прогресс

Обновляется агентом после каждой завершённой задачи.
Читается в начале каждой сессии — здесь память проекта между запусками.

## Текущий спринт

**Спринт 3 — ядро (циклы, логи, прогноз). Статус: готов.**

## Сделано

### Спринт 1
- Каркас FastAPI, конфиг на pydantic-settings, ленивый async engine
- 9 моделей БД из раздела 6 ТЗ + начальная миграция `0001_initial`
- Шифрование `daily_logs.note` (AES-256-GCM)
- Скрабинг чувствительных полей для логов и Sentry
- `/health`, `/health/ready`
- docker-compose, Makefile, 12 тестов

### Спринт 2 — аутентификация
- `app/core/security.py`: argon2id, JWT HS256, refresh-токены
- `app/services/auth_service.py`: регистрация, логин, Telegram-логин, ротация
  refresh с обнаружением кражи, logout, consent, link-токены TG↔web
- `app/services/telegram_auth.py`: валидация initData через aiogram + auth_date
- 8 эндпоинтов /auth, 21 тест

### Спринт 3 — ядро продукта
- `app/services/prediction.py`: чистая функция `compute` по разделу 7 ТЗ,
  дополнительно `classify_regularity` для 7.5. Взвешенное среднее по последним
  6, отсечение выбросов по [21,45] и >2σ от медианы, овуляция и фертильное
  окно от конца цикла (7.4)
- `app/services/predictions_service.py`: обёртка над `compute` для БД,
  сборка календаря на месяц с состояниями period_actual/period_predicted/
  fertile/ovulation/normal
- `app/services/cycles_service.py`: CRUD циклов + автоматический пересчёт
  cycle_length у предыдущего цикла и переоценка is_anomaly при изменениях;
  валидация FR-1.5 (пересечения блокируем, границы вне [15,90]/[1,14]
  сохраняются с флагом is_anomaly)
- `app/services/logs_service.py`: upsert/delete/list дневных записей
- 5 новых эндпоинтов /cycles + 2 /predictions + 3 /logs = 10 (раздел 8.2–8.4)
- 22 юнит-теста алгоритма (все 7 обязательных из ТЗ 7.7 + краевые),
  22 HTTP-теста /cycles, /predictions, /logs

Всего: **77 тестов зелёные, ruff и mypy чисты**, миграций новых
не потребовалось (спринт использует существующие таблицы cycles и daily_logs).

### Дизайн
- Палитра «Тёплый песок» утверждена, значения в OKLCH зафиксированы
  в `docs/DESIGN-SPEC.md`
- MCP настроены в `.mcp.json`: chrome-devtools, playwright, figma

## Следующий шаг

Спринт 4 — фронтенд. Онбординг, главный экран, календарь, логирование,
настройки. Строго по `docs/DESIGN-SPEC.md`. Клиент API — из OpenAPI.
Обязательный «замкнутый цикл»: экран → MCP chrome-devtools → скриншот
→ сверка со спекой → починка.

## Где остановились

—
