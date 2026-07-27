# Второй АРМ под Windows — как поднять окружение

Инструкция, чтобы на Windows-машине можно было работать с проектом
как на основном Mac: коммитить, гонять тесты, деплоить на прод.

Все шаги делаются один раз. Дальше — обычный `git pull` / `git push`
и работа как везде.

---

## 1. Ставим базовый софт

- **Git for Windows** — https://git-scm.com/download/win. Ставится
  «Git Bash» — удобно для команд из этой инструкции.
- **Docker Desktop** с WSL2 backend — https://www.docker.com/products/docker-desktop.
  Обязательно включить «Use WSL 2 based engine» в настройках.
  Локальная разработка через `docker compose` — как на Mac.
- **Node.js 20 LTS** — https://nodejs.org (или через `winget install
  OpenJS.NodeJS.LTS`). Фронтенд собирается локально `npm run build`,
  этого достаточно.
- **VS Code** — https://code.visualstudio.com. Плюс расширения
  «Docker», «ESLint», «Python» (если хочется запускать тесты вне
  контейнера).
- **Claude Code** — `npm install -g @anthropic-ai/claude-code`
  (нужен свежий Node). Авторизуйся один раз командой `claude`,
  подхватит API key.

Python не обязателен: все backend-тесты гоняются через
`docker compose exec api pytest`, локальный Python вне контейнера
не нужен.

---

## 2. Настраиваем git

В Git Bash или PowerShell:

```bash
git config --global core.autocrlf input
git config --global core.longpaths true
git config --global user.name  "Сергей Постнов"
git config --global user.email "postnov.sergey@gmail.com"
```

- `autocrlf input` — Windows не превратит `\n` в `\r\n` при коммите
  (иначе будут ложные diff'ы у файлов, которые я редактирую с Mac).
- `longpaths true` — некоторые пути в `node_modules` длиннее 260
  символов, без этого падает клон.

---

## 3. SSH-ключ на прод-сервер

На Mac уже есть `~/.ssh/id_ed25519`, его публичка добавлена в
`authorized_keys` у `root@5.129.212.158`. Два варианта:

**A) Скопировать существующий ключ с Mac.**
Файлы `id_ed25519` и `id_ed25519.pub` из `~/.ssh/` на Mac положить
в `%USERPROFILE%\.ssh\`. Правильно проставить права:
```powershell
icacls "%USERPROFILE%\.ssh\id_ed25519" /inheritance:r /grant:r "%username%:(R)"
```

**B) Сгенерировать новый ключ на Windows и добавить его на сервер.**
```bash
ssh-keygen -t ed25519 -C "postnov-windows"
# приватный в C:\Users\<you>\.ssh\id_ed25519, публичный .pub рядом
cat ~/.ssh/id_ed25519.pub
# скопировать вывод и с mac'а добавить в authorized_keys:
#   ssh root@5.129.212.158 'cat >> ~/.ssh/authorized_keys' < win.pub
```

Проверить:
```bash
ssh root@5.129.212.158 hostname
# → ams-1-vm-q0d1
```

Если первый раз соединения нет — в `~/.ssh/known_hosts` появится
запись с fingerprint (см. **[[deploy-cert-flow]]** — фингерпринт
сервера мы уже сверяли; можно попросить агента проверить сходство).

---

## 4. Клонируем репозиторий

Куда угодно, но выбирай короткий путь без пробелов и русских букв,
чтобы Docker и Node.js не капризничали:

```bash
mkdir -p /c/projects
cd /c/projects
git clone https://github.com/postnovsergey-alt/myfaza.ru.git myfaza
cd myfaza
```

Если для push нужен HTTPS-токен — GitHub давно не пускает по паролю,
используй Personal Access Token (Settings → Developer settings →
Tokens (classic), scope `repo`). Или переключи remote на SSH:
```bash
git remote set-url origin git@github.com:postnovsergey-alt/myfaza.ru.git
```
и добавь тот же SSH-ключ в GitHub → Settings → SSH keys.

---

## 5. Локальный `.env`

Файл `backend/.env` (или корневой `.env`, если compose его читает)
в git не лежит — берётся с Mac или генерируется. Для локальной
разработки достаточно тестовых значений — реальные секреты не
нужны, всё крутится в docker-compose:

```bash
# в корне репозитория:
cat > .env <<'EOF'
APP_ENV=local
PUBLIC_DOMAIN=localhost
SECRET_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
FIELD_ENCRYPTION_KEY=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=myfaza
POSTGRES_USER=myfaza
POSTGRES_PASSWORD=local-dev-only

REDIS_URL=redis://redis:6379/0

BOT_TOKEN=123456:TESTBOTTOKENFORFAKEUSE
BOT_USERNAME=moyafaza_bot
WEBHOOK_SECRET=local-test-secret

VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=

JWT_ACCESS_TTL_MINUTES=30
JWT_REFRESH_TTL_DAYS=60
EOF
```

Реальные секреты живут только в `/etc/myfaza/.env` на проде — сюда
не тащим.

---

## 6. Поднимаем локально

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api pytest -q      # должно быть 122 passed
```

Фронтенд:
```bash
cd frontend
npm ci
npm run dev            # dev-сервер на http://localhost:5173
# или
npm run build          # прод-сборка в dist/
```

- API: http://localhost:8000/api/v1/health
- Docs (когда APP_ENV=local): http://localhost:8000/api/docs

---

## 7. Deploy — та же схема, что с Mac

Смотри `docs/DEPLOY.md` и memory-заметку про ручной деплой:

```bash
# после git push origin main
ssh root@5.129.212.158 '
cd /opt/myfaza && git pull --ff-only origin main
cd deploy && docker compose -f docker-compose.small.yml up -d --build api worker

# если фронт менялся:
cd /opt/myfaza/frontend && npm run build
sudo rm -rf /var/www/myfaza/dist
sudo cp -r dist /var/www/myfaza/
sudo chown -R www-data:www-data /var/www/myfaza
sudo systemctl reload nginx
'
```

Никаких Vercel и GitHub Actions авто-деплоев — только руками.
Причины подробно описаны в memory-заметке `deploy_manual.md` (см.
шаг 9 ниже).

---

## 8. Инструменты Claude Code при работе с проектом

Всё, что нужно агенту при старте, лежит в самом репозитории:

- `CLAUDE.md` — быстрый вход в проект, ссылки на разделы ТЗ.
- `docs/AGENT-PROTOCOL.md` — правила автономной работы, красные зоны.
- `PROGRESS.md` — где остановились в прошлой сессии.
- `QUESTIONS.md` — открытые вопросы к человеку.
- `DECISIONS.md` — журнал жёлто-зоновых решений.

При открытии проекта в Claude Code этот контекст читается автоматически,
так что с Windows-машины первая же сессия увидит весь фон проекта.

---

## 9. Память проекта Claude Code (опционально)

На Mac у Claude есть локальный memory-каталог
`~/.claude/projects/<slug>/memory/` с заметками про:

- `prod_server.md` — доступ, что развёрнуто, `/etc/myfaza/*`.
- `deploy_cert_flow.md` — как выдавали TLS на общем VPS.
- `bot_setup.md` — реальные значения BotFather-настроек.
- `deploy_manual.md` — ручной цикл деплоя.
- `ux_contract.md` — контракт после багфиксов.
- `aiogram_test_bot_patch.md` — техническая заметка про тесты бота.
- `MEMORY.md` — индекс.

Они **не в git** (личный контекст агента). Если хочется, чтобы
Windows-агент видел то же самое:

**A) Скопировать вручную.**
Каталог с Mac `~/.claude/projects/-Users-sergeypostnov---...-myfaza-ru/memory/`
на Windows положить в `%USERPROFILE%\.claude\projects\<slug>\memory\`.
Slug у Claude Code вычисляется из абсолютного пути к репо; проще
всего один раз запустить Claude в клонированном репо, увидеть какой
slug создался, и туда положить файлы.

**B) Не копировать.** Все важные факты уже есть в `PROGRESS.md`,
`DECISIONS.md`, `QUESTIONS.md`, `docs/DEPLOY.md`. Агент прочитает
их при старте и получит 90% контекста. Технические ловушки типа
aiogram-теста в git не лежат — Windows-агент про них не узнает,
но при первой же встрече заново разберётся и добавит в свою память.

Рекомендую вариант B — проще, не тащим потенциальные IP-адреса в
локальные Windows-файлы.

---

## 10. Windows-специфика, о чём помнить

- **Line endings** — если увидишь diff'ы вида «весь файл изменился»,
  проверь, что `autocrlf=input` (шаг 2). Один раз пересохранить
  файл в UTF-8 без BOM решает это же.
- **Docker Desktop CPU/RAM** — по умолчанию берёт немного, для
  нашего compose (postgres + redis + api) хватает; если тормозит —
  выделить 4–6 GB в Settings → Resources.
- **Пути с кириллицей** — не клонируй в `C:\Users\...\Документы\...`,
  Docker Desktop иногда не может замаунтить такой путь. `C:\projects`
  или `D:\projects` — надёжно.
- **Права на файл** — если после клонирования репо `chmod +x` не
  сохраняется у скриптов из `deploy/`, это не страшно: на VPS они
  всё равно запускаются под нужными правами.
- **Firewall** — при первом `docker compose up` Windows спросит
  разрешение на входящие для докера; разрешить только Private.

---

## 11. Быстрый чек-лист

- [ ] Git for Windows + Docker Desktop + Node 20 + VS Code + Claude Code
- [ ] `git config core.autocrlf=input`, `core.longpaths=true`, user/email
- [ ] SSH-ключ работает: `ssh root@5.129.212.158 hostname` возвращает `ams-1-vm-q0d1`
- [ ] Репо клонирован в короткий путь без кириллицы (`C:\projects\myfaza`)
- [ ] `.env` создан с тестовыми значениями
- [ ] `docker compose up -d --build` — сервисы healthy
- [ ] `docker compose exec api pytest -q` — 122 passed
- [ ] `curl http://localhost:8000/api/v1/health` — `{"status":"ok"}`
- [ ] `cd frontend && npm ci && npm run dev` — открывается http://localhost:5173

После этого можно работать так же, как с Mac.
