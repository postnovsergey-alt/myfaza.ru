# Деплой myfaza.ru в прод

Пошаговая инструкция первого разворота. Читать сверху вниз, не пропускать.
Ссылки на файлы конфига — от корня репозитория.

Легенда:
- 👤 — делаете вы (или подтверждаете, что уже сделано)
- 🤖 — делает агент, после того как вы дали данные

---

## Шаг 1. GitHub-репозиторий

**👤 Что сделать:**

1. Создайте пустой репозиторий на GitHub, например `sergeypostnov/myfaza`.
   Приватный или публичный — на ваш выбор. Не инициализируйте README,
   `.gitignore`, лицензию — репозиторий должен быть пустой.
2. Пришлите мне URL: `git@github.com:owner/repo.git` или https-вариант.

**🤖 Что сделаю я после этого:**

- `git remote add origin ...`
- Переименую ветку `master` → `main` (у нас 6 коммитов, стандартное имя
  для GitHub).
- `git push -u origin main`.

---

## Шаг 2. Сервер (общий с zabiru)

**👤 Что мне нужно узнать про сервер:**

1. IP-адрес.
2. SSH-порт (обычно 22).
3. Пользователь для SSH (не root — обычный юзер с sudo и правами на docker).
4. Куда именно кладём проект (например `/opt/myfaza` — по умолчанию
   в моём `release.yml`).
5. Установлен ли Docker на этом сервере (для zabiru должен быть).
6. Установлен ли Nginx на хосте, или проксирует контейнер?
   — Если на хосте: наш nginx-контейнер конфликтует, надо будет
     развести порты и, возможно, отдать TLS хостовому Nginx.
   — Если контейнер: то как zabiru его использует?

**👤 Приготовьте отдельный SSH-ключ для деплоя:**

```
ssh-keygen -t ed25519 -f ~/.ssh/myfaza_deploy -C deploy@myfaza
```

Публичную часть (`~/.ssh/myfaza_deploy.pub`) добавьте в
`~/.ssh/authorized_keys` того пользователя на сервере.
Приватную (`~/.ssh/myfaza_deploy`) сохраните — она пойдёт в GitHub-секреты.

**🤖 Что я сделаю потом:**

- Проверю, что могу без прав `root` на сервере разложить проект в
  `/opt/myfaza`, поднять контейнеры и открыть 8000-й порт внутри
  сети Docker.
- Подготовлю финальную версию `deploy/docker-compose.prod.yml` под
  вашу схему (хостовой Nginx vs контейнер).

---

## Шаг 3. DNS

**👤 На регистраторе домена `myfaza.ru`:**

1. Добавьте A-запись: `myfaza.ru` → IP-адрес сервера, TTL 300.
2. Добавьте A-запись: `www.myfaza.ru` → тот же IP.
3. Подождите распространение (обычно 5–30 минут). Проверить:
   ```
   dig +short myfaza.ru
   ```
   должно вернуть ваш IP.

⚠️ Домен на этом этапе фиксируется навсегда. Если сейчас указать не тот —
push-подписки и установленные PWA потом придётся выбрасывать.

---

## Шаг 4. Секреты

Готовим два набора: на сервере и на GitHub.

### 4.1. На сервере — файл `/etc/myfaza/.env`

**👤 На сервере (я подскажу команду, когда будет SSH):**

```bash
sudo mkdir -p /etc/myfaza
sudo chmod 700 /etc/myfaza
sudo tee /etc/myfaza/.env <<'EOF'
APP_ENV=production
PUBLIC_DOMAIN=myfaza.ru
SECRET_KEY=<openssl rand -hex 32>
FIELD_ENCRYPTION_KEY=<openssl rand -hex 32>

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=myfaza
POSTGRES_USER=myfaza
POSTGRES_PASSWORD=<openssl rand -hex 24>

REDIS_URL=redis://redis:6379/0

BOT_TOKEN=<от @BotFather для @moyafaza_bot>
BOT_USERNAME=moyafaza_bot
WEBHOOK_SECRET=<openssl rand -hex 32>

VAPID_PUBLIC_KEY=<см. ниже>
VAPID_PRIVATE_KEY=<см. ниже>
VAPID_SUBJECT=mailto:privacy@myfaza.ru

JWT_ACCESS_TTL_MINUTES=30
JWT_REFRESH_TTL_DAYS=60

SENTRY_DSN=
EOF
sudo chmod 600 /etc/myfaza/.env
```

**Генерация VAPID:**

```bash
docker run --rm python:3.12-slim sh -c "pip install py-vapid && python -c 'from py_vapid import Vapid01; v=Vapid01(); v.generate_keys(); print(v.public_key_urlsafe_base64()); print(v.private_key_urlsafe_base64())'"
```

Первое значение — VAPID_PUBLIC_KEY, второе — VAPID_PRIVATE_KEY.

### 4.2. На GitHub — Settings → Secrets and variables → Actions

**👤 Добавить репозиторные секреты:**

| Имя | Значение |
|---|---|
| `DEPLOY_HOST` | IP или домен сервера |
| `DEPLOY_USER` | SSH-пользователь |
| `DEPLOY_KEY` | приватный SSH-ключ (весь файл `myfaza_deploy`) |

Больше ничего в GitHub-секретах не нужно — прод-секреты живут
только на сервере, в GitHub не улетают.

---

## Шаг 5. Первый разворот на общем VPS

Мы деплоимся рядом с zabiru/musorstop, хостовой nginx уже держит 80/443.
Поэтому оригинальный сценарий с временным docker-nginx на 80-м не годится —
он бы конфликтовал с соседями. Идём через webroot существующего nginx.

### 5.1. Клонируем репозиторий и ставим пакеты

**👤 На сервере:**

```bash
sudo mkdir -p /opt/myfaza
sudo chown $USER:$USER /opt/myfaza
git clone https://github.com/<owner>/<repo>.git /opt/myfaza

sudo apt-get update
sudo apt-get install -y certbot
sudo mkdir -p /var/www/certbot
```

### 5.2. Bootstrap-конфиг nginx (только для ACME)

Полный `deploy/nginx/myfaza.conf` не подходит на этом шаге: он ссылается
на сертификаты, которых ещё нет, и nginx откажется грузиться. Ставим
временный `myfaza.acme.conf` — там только HTTP-порт с ACME challenge.

**👤 На сервере:**

```bash
sudo cp /opt/myfaza/deploy/nginx/myfaza.acme.conf /etc/nginx/sites-available/myfaza.ru
sudo ln -sf /etc/nginx/sites-available/myfaza.ru /etc/nginx/sites-enabled/myfaza.ru
sudo nginx -t && sudo systemctl reload nginx
```

Проверить, что домен реально прилетает на наш nginx:
```bash
curl -I http://myfaza.ru/
# ожидаем 200 OK и тело "myfaza.ru bootstrap"
```

Если 200 не пришло — либо DNS ещё не обновился (`dig +short myfaza.ru`
должен вернуть IP сервера), либо в основном `/etc/nginx/nginx.conf`
нет `include /etc/nginx/sites-enabled/*.conf;`. Дальше не идём, пока
bootstrap не отдаёт 200.

### 5.3. Выдача сертификата

**👤 На сервере:**

```bash
sudo certbot certonly --webroot -w /var/www/certbot \
  -d myfaza.ru -d www.myfaza.ru \
  --email privacy@myfaza.ru --agree-tos --no-eff-email
```

Ожидаемый результат: `Successfully received certificate.` и путь
`/etc/letsencrypt/live/myfaza.ru/fullchain.pem`.

Проверяем:
```bash
sudo ls -l /etc/letsencrypt/live/myfaza.ru/
# fullchain.pem и privkey.pem должны быть на месте
```

### 5.4. Подмена на полный конфиг

Теперь bootstrap заменяем на боевой `myfaza.conf` — уже с 443, HSTS,
CSP, проксированием `/api/` в контейнер api и статикой фронта.

**👤 На сервере:**

```bash
sudo cp /opt/myfaza/deploy/nginx/myfaza.conf /etc/nginx/sites-available/myfaza.ru
sudo nginx -t && sudo systemctl reload nginx
```

Проверяем:
```bash
curl -I https://myfaza.ru/
# 200 или 404 (статика фронта ещё не выложена — это нормально)
curl -I http://myfaza.ru/
# 301 → https://myfaza.ru/
```

Если `nginx -t` ругается — не reload'им, разбираемся. При проблеме
можно откатиться на bootstrap: `sudo cp .../myfaza.acme.conf ... &&
sudo systemctl reload nginx`.

### 5.5. Автопродление

Пакет certbot в Debian/Ubuntu уже ставит systemd-таймер `certbot.timer`,
который два раза в сутки пробует продлить. Проверить:
```bash
systemctl list-timers | grep certbot
sudo certbot renew --dry-run
```

Хук на reload nginx после продления:
```bash
sudo mkdir -p /etc/letsencrypt/renewal-hooks/deploy
sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'EOF'
#!/bin/sh
systemctl reload nginx
EOF
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

### 5.6. Первый запуск бэкенда

Фронт-статика и API-контейнер отдельно от TLS-части; сюда переходим,
когда `curl https://myfaza.ru/` уже возвращает от нашего nginx хоть
что-то (пусть 404 — важно, что цепочка TLS + reverse proxy жива).

**👤 На сервере:**

```bash
cd /opt/myfaza
# Собрать фронт (нужен node 20+) и разложить в /var/www/myfaza/dist
cd frontend && npm ci && npm run build
sudo mkdir -p /var/www/myfaza
sudo rm -rf /var/www/myfaza/dist
sudo cp -r dist /var/www/myfaza/
sudo chown -R www-data:www-data /var/www/myfaza
cd ..

# Поднять api + worker
cd deploy
sudo docker compose -f docker-compose.small.yml up -d --build
```

Смоктест:
```bash
curl -s https://myfaza.ru/api/v1/health
# {"status":"ok"}
curl -sI https://myfaza.ru/
# 200 OK + index.html
```

Alembic-миграции при первом старте — руками, чтобы точно применились:
```bash
sudo docker compose -f docker-compose.small.yml exec api alembic upgrade head
```

### 5.7. Пуш тега для CI (когда всё работает вручную)

Локально:
```bash
git tag v0.1.0
git push origin v0.1.0
```

**🤖 Что сделает CI:**

1. Соберёт `myfaza-api` и `myfaza-frontend` образы, запушит в GHCR.
2. Через SSH зайдёт на сервер, сделает `docker compose pull && up -d`,
   `alembic upgrade head`, дождётся `/health/ready`.
3. При провале — откатится (насколько сможет; в первом деплое отката
   нет).

---

## Шаг 6. Настройка Telegram-бота

**👤 У @BotFather:**

| Команда | Значение |
|---|---|
| `/setname` | Моя фаза |
| `/setdomain` | myfaza.ru |
| `/setmenubutton` | `https://myfaza.ru/app` |
| `/setprivacy` | Enabled |

**👤 Установите webhook (одноразово):**

```bash
curl "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=https://myfaza.ru/api/v1/telegram/webhook&secret_token=${WEBHOOK_SECRET}"
```

---

## Шаг 7. Уведомление Роскомнадзора

**👤 Красная зона — юридическая часть:**

Подать уведомление об обработке ПДн до фактического приёма первого
пользователя. Реестр Роскомнадзора: pd.rkn.gov.ru. Тексты в
`docs/consent.md` и `docs/privacy-policy.md` — черновики, юрист
согласовывает окончательные формулировки.

---

## Чек-лист «релиз состоялся»

- [ ] `https://myfaza.ru/api/v1/health/ready` возвращает `{"status":"ok"}`.
- [ ] `https://myfaza.ru/` открывает главную страницу приложения.
- [ ] `https://myfaza.ru/privacy` доступна без авторизации.
- [ ] Bot `@moyafaza_bot` отвечает на `/start`.
- [ ] Тестовый пуш из `/settings` → «Отправить тестовое» доходит
      в Chrome и в PWA на iOS 16.4+.
- [ ] Ежедневный бэкап Postgres настроен, восстановление проверено.
- [ ] Uptime-мониторинг (UptimeRobot или аналог) отслеживает `/health/ready`.
- [ ] Все 13 пунктов из `docs/acceptance-checklist.md` закрыты.
