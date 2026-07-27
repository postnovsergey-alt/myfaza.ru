# Прогресс

Обновляется агентом после каждой завершённой задачи.
Читается в начале каждой сессии — здесь память проекта между запусками.

## Текущий спринт

**Спринт 6 — личный кабинет + деплой. Статус: готов.**

## Сделано

### Спринт 1 — каркас
FastAPI, 9 моделей БД, миграции, шифрование `daily_logs.note`,
`/health`, docker-compose, 12 тестов.

### Спринт 2 — аутентификация
argon2id, JWT + ротация refresh с обнаружением кражи, Telegram initData
с проверкой `auth_date`, привязка аккаунтов, /auth-эндпоинты, 21 тест.

### Спринт 3 — ядро
Алгоритм прогноза по разделу 7 (22 юнит-теста), CRUD /cycles с
валидацией FR-1.5, /predictions/next и /calendar, /logs с шифрованным
`note`. 22 HTTP-теста.

### Спринт 4 — фронтенд
Vite + React 18 + TS + Tailwind + PWA. 5 экранов + логирование +
онбординг. Свой мини-парсер ICU-плюралов, OpenAPI-клиент, платформенный
слой TG↔web. Бандл 76 KB gzip, Lighthouse A11y 100.

### Спринт 5 — уведомления
Планировщик с UNIQUE-дедупликацией, Telegram+Web Push отправка с
обработкой ошибок, service worker с injectManifest, iOS-инструкция,
эндпоинты /settings и /push/*. 8 обязательных тестов.

### Спринт 6 — личный кабинет + деплой
- **Backend, личный кабинет (FR-8, ТЗ 8.5):**
  - `GET /me` — сводка (auth_methods, consent, cycle_status)
  - `PATCH /me` — display_name, timezone, locale
  - `POST /me/email` — привязка/смена email
  - `POST /me/password` — с проверкой current_password
  - `DELETE /me/telegram`, `DELETE /me/email` — с запретом отвязки последнего способа входа
  - `GET/DELETE /me/sessions[/{id}]` — список и завершение
  - `GET /push/subscriptions` — активные подписки
  - `GET /me/history/cycles`, `/me/history/logs` — пагинация 1..100, фильтр по симптому
  - `GET /me/consent` — принятый текст
  - `GET /export?format=csv|json` — весь дата-дамп в CSV или JSON
  - `POST /account/consent/revoke`, `DELETE /account` — hard delete
  - `GET /stats` — FR-6: среднее, σ, регулярность, мягкое предупреждение
- **Backend, тесты:** 16 HTTP-тестов личного кабинета, включая проверку
  hard delete прямыми запросами к БД. **Всего 105 зелёных.**
- **Deploy (ТЗ 12.3, 12.4):**
  - `deploy/docker-compose.prod.yml` — api/bot/worker/postgres/redis/frontend/nginx
  - `deploy/nginx/prod.conf` — TLS, HSTS, CSP, gzip, X-Forwarded-*
  - `frontend/Dockerfile` — multi-stage: build → nginx с SPA-fallback
  - `backend/app/workers/entrypoint.py` — APScheduler 5 мин, план+отправка
- **CI/CD:**
  - `.github/workflows/ci.yml` — на PR: postgres+redis сервисы,
    alembic upgrade, ruff, mypy, pytest, tsc, build фронта,
    проверка бандла < 256 KB
  - `.github/workflows/release.yml` — на тег `v*`: build+push ghcr,
    ssh-деплой, migrate, smoke, rollback при провале
- **Документы:**
  - `docs/privacy-policy.md`, `docs/consent.md` — черновики,
    красная зона: юрист согласовывает
- **Frontend:**
  - `AccountPage` — профиль, способы входа, сессии, приватность,
    экспорт, удаление, отзыв согласия. Ссылка из `SettingsPage`.
  - `PrivacyPage` — публичная политика конфиденциальности `/privacy`
- **Чек-лист приёмки MVP:** `docs/acceptance-checklist.md` —
  11 из 13 пунктов готовы полностью, 2 требуют прод-деплоя (красная
  зона).

### Метрики фронта
- Bundle JS: 253 KB min / **79.85 KB gzip** (бюджет NFR-3: 250 KB gzip ✓)
- Service Worker: 5.60 KB gzip
- CSS: 4.17 KB gzip

## Следующий шаг

MVP готов технически. Дальнейшие действия — красная зона, требуют
человека:
1. Юрист согласует `docs/consent.md` и `docs/privacy-policy.md`.
2. VPS + GitHub-секреты + первый тег `v0.1.0` → прод-деплой.
3. Ручной прогон нового пользователя на реальном телефоне.

После этих трёх шагов — все 13 пунктов чек-листа закрыты, и можно
объявлять релиз v0.1.

## Где остановились

—
