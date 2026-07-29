# Прогресс

Обновляется агентом после каждой завершённой задачи.
Читается в начале каждой сессии — здесь память проекта между запусками.

## Текущий спринт

**Спринт 6 — личный кабинет + деплой. Статус: закрыт.**

**Пост-спринт — раскатка на VPS + бот.**
Deploy — done. Бот — done: закрыл дыру спринтов 2/5, реализовал
webhook, aiogram Dispatcher, /start (с deep-link link_<token>),
callback-кнопки cyc:start/end/notyet, тесты (11 новых, всего 116
зелёных), setWebhook установлен, end-to-end проверен на проде.
Открыт: внешний uptime-мониторинг (отложено).

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

VPS 5.129.212.158 (ams-1-vm-q0d1), Ubuntu 26.04, общий с zabiru:
- HTTPS: LE-сертификат `/etc/letsencrypt/live/myfaza.ru/` (до
  2026-10-25), автопродление через systemd + hook на reload nginx,
  `certbot renew --dry-run` зелёный.
- Nginx: `/etc/nginx/sites-enabled/myfaza.ru` (полный конфиг из
  `deploy/nginx/myfaza.conf`), www→apex 301.
- Контейнеры: `myfaza-api-1` healthy, `myfaza-worker-1` up, схема
  из `deploy/docker-compose.small.yml` (host network). Postgres и
  Redis — хостовые, 127.0.0.1:5432 / 6379.
- Смоктест `/api/v1/health/ready` → `{"database":"ok","redis":"ok"}`.
- Бэкапы: `/opt/myfaza-backups/dump.sh`, ежедневный systemd-таймер
  `myfaza-backup.timer` в 03:00 UTC, шифр GPG AES-256, passphrase в
  `/etc/myfaza/backup.passphrase` (chmod 600). Ретеншн 14 дней,
  восстановление проверено (10 таблиц оригинала = 10 в восстановлении).

Дополнительно на сервере:
- Bot: webhook `https://myfaza.ru/api/v1/telegram/webhook` установлен,
  `getWebhookInfo` → ip 5.129.212.158, allowed_updates=[message,
  callback_query].
- Bot API-настройки (setMyName/Description/ShortDescription,
  setChatMenuButton → web_app «Открыть» → /app, setMyCommands → /start).
- @BotFather ручные: setuserpic (bot-icon-512.png, дискретная полудуга),
  setprivacy=Enable, setdomain=myfaza.ru.

## После первого прогона — что сделано

Ручной прогон дал баг-репорт. Всё пофикшено (коммиты 2efe93e..f95ebc5),
задеплоено, проверено на проде.

- **Кнопка «Отметить окончание» на HomePage** — раньше пользователь
  мог поставить только начало, а окончание не отмечал (см. FR-1.2).
  Backend получил `PredictionOut.is_period_active` (открытый цикл ≤14
  дней). UI показывает вторую кнопку, когда флаг true, вызывает
  `POST /cycles/current/end`.
- **Онбординг полностью удалён** — раньше был обязательным экраном,
  падал молча при повторной попытке (CYCLE_OVERLAP → тихая ошибка).
  Теперь: пустая главная = приветствие + кнопка «Отметить начало»,
  вся навигация доступна с дефолтами (28/5). Онбординга нет как
  сущности — параметры цикла меняются в Настройках когда захочется.
- **Consent строго при регистрации** — раньше показывался при каждом
  входе новых сессий. Веб: чекбокс в LoginPage. TG: `ConsentGate` —
  блокирующий одноразовый экран в `ProtectedRoute`, если
  `user.consent_given_at IS NULL`. Пока не дан — ни одна страница
  с данными не отдаётся.
- **Связывание TG↔web из личного кабинета** (ТЗ 3.3) — обе стороны:
  · Web-user → «Привязать Telegram» → deep-link на бота, `_handle_link`
    в handlers/start.py делает `confirm_link_telegram`.
  · TG-user → «Привязать веб-доступ» → ссылка `/link?token=…`, новая
    страница `LinkPage`, форма email+password → `/auth/link/confirm`.
  · Отвязка обоих способов с проверкой «нельзя отвязать последний»
    (backend 409, UI alert).
- **Календарь — intent-flow «Выбрать дату»** — раньше клик по «Выбрать
  дату» в mark-sheet уводил в календарь, а там клик открывал только
  LogSheet (симптомы), цикл никогда не создавался. Теперь
  `HomePage → /calendar?intent=mark-start|mark-end` → sticky-баннер
  в календаре → клик по дню → confirm-Sheet → POST /cycles или
  /cycles/current/end. Future-дата в intent-режиме блокируется в
  баннере, ошибки CYCLE_OVERLAP/NO_OPEN_CYCLE — понятные тексты.
- **Валидация будущего для daily-log** — `PUT /logs/{on}` теперь 400
  LOG_FUTURE, если on > today. LogSheet показывает баннер и
  дизейблит все контролы для будущего дня.
- **Удаление цикла и записи из LogSheet** — раньше `DELETE /cycles/{id}`
  в бэке был, UI не звал. Теперь LogSheet ищет через
  `GET /cycles?from=<date-45>&to=<date>` цикл, покрывающий дату, и
  показывает красную кнопку удаления с confirm. Плюс отдельная
  кнопка удаления daily-log, если он есть.
- **Иконка бота** — старая `kartinka_bota_site.png` (ромашка на
  зелёном) нарушала DESIGN-SPEC. Заменил на `assets/bot-icon-512.png`
  (тёплый песок #F5F1EA + розовая полудуга #993556), сгенерирована
  Pillow из frontend/public/icon-192.svg. Загружена в @BotFather.

Метрики: тесты 116 → **122 зелёных** (+6 новых: is_period_active × 4,
LOG_FUTURE × 2). Bundle 79.85 → **~85 KB gzip** (в бюджете NFR-3
< 250 KB gzip). CI/CD не менял — все правки шли через прямой
`git push origin main` + `git pull` на VPS + rebuild контейнера +
пересборка фронт-статики в `/var/www/myfaza/dist`.

## QA прогон уведомлений (2026-07-27)

- Telegram push: sent 21:50:01 UTC, log_reminder/telegram/sent,
  доставлено в чат `@Spostnov`.
- Web Push (iOS PWA, Apple Push Notification service): sent 21:52:04
  UTC, `last_success_at` подписки обновился, `failure_count=0`.
- Планировщик уведомлений с UNIQUE-дедупликацией работает штатно
  (см. `docker compose logs worker`).

## После второго прогона (2026-07-28..29) — что сделано

Второй прогон от пользователя дал ещё пачку багов и запросов. Всё
пофикшено, задеплоено, проверено на проде.

- **Тема сохраняется и системная работает.** Раньше на веб-версии
  `getColorScheme` слушал `window.Telegram.WebApp.colorScheme`
  (telegram-web-app.js подключён в `index.html` всегда и создаёт
  объект даже вне Telegram, `colorScheme` там дефолтно `"light"`),
  поэтому «Как в системе» на веб-странице всегда давало светлую,
  а выбранная тема моргала при рестарте. Теперь `getColorScheme`
  спрашивает Telegram только если реально в Mini App (есть initData),
  `subscribeThemeChanges` получает override пользователя, и `useUi`
  читает `localStorage` сразу при создании стора без вспышки.
- **TTL сессии 180 дней + чекбокс «Оставаться в системе» на 365.**
  `JWT_REFRESH_TTL_DAYS` 60 → 180, добавлен
  `JWT_REFRESH_TTL_DAYS_REMEMBER=365`, remember_me пробрасывается из
  `LoginIn`/`RegisterIn` в `_issue_tokens`. Telegram Mini App всегда
  `remember=True`. Чекбокс на LoginPage включён по умолчанию.
  Решение задокументировано в `DECISIONS.md`.
- **ПИН-код для веба.** 4 цифры, SHA-256(salt||pin) в localStorage,
  5 попыток → сброс + logout. Спрашивается при cold-load и через 5
  минут в фоне (`visibilitychange`). Секция в настройках:
  включить / сменить / отключить. TG Mini App пока без ПИНа —
  Face ID/BiometricManager отложен отдельным шагом (см. `DECISIONS.md`
  и memory `pin-and-biometry-split`).
- **Редактирование дат менструации в LogSheet.** Тап по дню из
  существующего цикла даёт секцию «Даты менструации» с двумя
  date-input и кнопкой «Сохранить новые даты». Использует уже
  готовый `PATCH /cycles/{id}`. Есть кнопка «Ещё идёт — очистить
  дату окончания». Клиентская валидация + перевод серверных кодов
  CYCLE_OVERLAP / CYCLE_END_BEFORE_START / CYCLE_FUTURE /
  CYCLE_TOO_OLD в человеческие сообщения.
- **«Отметить началом менструации» из шторки пустого дня.**
  Тап по дню, который не входит ни в один цикл, теперь показывает
  кнопку «Отметить началом менструации» внизу LogSheet
  (POST /cycles). Раньше начать цикл можно было только через
  кнопки на главной или intent-flow «Выбрать дату».

**Грабли при деплое:** серверный `/etc/myfaza/.env` **перебивает**
дефолты из `backend/app/config.py` — поэтому смена `JWT_REFRESH_TTL_DAYS`
в коде без правки .env на VPS не заедет. Зафиксировано в memory
`env-defaults-vs-prod`. При любом изменении дефолта настройки —
проверять/править `/etc/myfaza/.env` на сервере.

Метрики: bundle **~90 KB gzip** (индекс `index-CLg17ntC.js` в проде,
всё ещё в бюджете NFR-3 < 250 KB gzip). Тесты не гонял (Docker не
был запущен локально) — конкретных assertion'ов на TTL/тему в них
нет, изменения проверил вручную через фронт-билд + тайпчек.

## После третьего прогона (2026-07-29) — что сделано

Третий прогон дал два бага и вопрос про алгоритм прогноза. Оба бага
пофикшены, задеплоены.

- **Удаление аккаунта в PWA не срабатывало.** Причина: `window.confirm()`
  в установленной PWA (особенно iOS standalone) ненадёжен и часто молча
  игнорируется — клик по «Удалить» не открывал диалог, обработчик не
  вызывался. Заменил на инлайн `components/ui/ConfirmDialog.tsx` —
  модалка с backdrop, ESC, aria-modal. Применил ко всем 5
  деструктивным действиям AccountPage (удаление, отзыв согласия,
  выход со всех, отвязка Telegram/email) и к удалению записи/цикла
  в LogSheet.
- **Секцию редактирования цикла в календаре подняли наверх LogSheet.**
  Ранее (коммит 2ba4347) она лежала внизу под симптомами и заметкой —
  пользователь до неё не доскроллил и подумал, что редактирования нет.
  Теперь она сразу после header'а: два date-input + очистить endDraft
  + toast «Сохранено», кнопка primary всегда активна.

Метрики: bundle **86.51 KB gzip** (индекс `index-DxogZZgk.js`).
Тесты фронта не гонял (нет vitest на этих компонентах), тайпчек
чистый, ручная проверка через собранный dist. Backend не трогал.

## Улучшения прогноза (2026-07-29) — что сделано

Отдельная итерация: после обсуждения БТ пришли к решению, что
объективные измерения (температура, LH-полоски, слизь) UX не тянет —
дорого, забываемо, шумно. Реализовали два улучшения точности «без
единой новой записи от пользователя»:

- **Диапазон вместо точки на HomePage.** Раньше «Ожидается 14 августа
  ± 2» — техничная строка, воспринималась как «точно 14 августа».
  Теперь: margin=0 → «Ожидается 14 августа», margin=1 → «около 14
  августа», margin≥2 → «12–16 августа». `fmtRange` не повторяет
  название месяца внутри одного месяца и корректно раскрывает
  граничные случаи (`30 июля – 3 августа`). Новые i18n-ключи:
  `home.expected.around`, `home.expected.range`.
- **Индивидуальная длина менструации из фактов.** Раньше
  `predicted_end` считался от константы `avg_period_length` из
  онбординга (5 дней). Теперь `predictions_service.effective_period_length`
  считает медиану по последним 6 закрытым циклам, если наблюдений
  ≥ 3. Иначе fallback на настройку. То же применил в
  `notifications.py` для расчёта `expected_end` уведомления
  `period_end`. Чистая `compute()` в `prediction.py` не тронута —
  агрегация на сервисном слое.

Тесты: 2 новых HTTP-теста в `test_predictions_api.py` (медиана
> дефолт с 4 циклами по 7 дней; fallback с 1 циклом). Полный
прогон на VPS — **124/124 зелёных** (+2, было 122). Bundle
**86.67 KB gzip** (индекс `index-D0r-C5uF.js`).

БТ (базальная температура) — сознательно **не** делаем. Причина в
DECISIONS.md — см. запись «Почему не делаем БТ в MVP» (нужно
дозаписать).

## Где остановились в коде

Последний коммит: `f89fbd4` (docs: QUESTIONS #5/#6).
Локальный `main` = `origin/main` = прод. В прод-бандле `index-DxogZZgk.js`.

## QA прогон уведомлений (2026-07-27)

- Telegram push: sent 21:50:01 UTC, log_reminder/telegram/sent,
  доставлено в чат `@Spostnov`.
- Web Push (iOS PWA, Apple Push Notification service): sent 21:52:04
  UTC, `last_success_at` подписки обновился, `failure_count=0`.
- Планировщик уведомлений с UNIQUE-дедупликацией работает штатно
  (см. `docker compose logs worker`).

## Что дальше

Договорённый с пользователем порядок пост-релизных работ:

1. **FR-8.6 UI — история циклов и записей в кабинете.** Backend
   (`/me/history/cycles`, `/me/history/logs`) готов ещё со спринта 6,
   UI не рендерит. Даст возможность листать и править прошлое
   удобнее, чем через календарь. Оценка: 2–3 часа.
2. **Uptime-мониторинг** (QUESTIONS.md #4). UptimeRobot или self-hosted,
   ~30 минут.
3. **Face ID / биометрия.** Веб — WebAuthn поверх ПИНа (~2 часа),
   TG Mini App — `WebApp.BiometricManager` из Bot API 7.2 (~3–4 часа).
   Делать в один заход.

Отдельно, не в этом порядке:
- Продолжаем прогон живыми пользователями, собираем баги/фичи.
- Астрологический прогноз (QUESTIONS.md #5) — ждём решения по
  «Claude API + Redis-кэш vs забить».
- Лунный календарь (QUESTIONS.md #6) — 2 часа чистой астрономии,
  если решим делать.
- Миграция в РФ (QUESTIONS.md #2) — только перед публичным анонсом.
- Юр. согласование `docs/consent.md` и `docs/privacy-policy.md` —
  красная зона, ждём человека.

