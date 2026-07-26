#!/usr/bin/env bash
# Разворачивает окружение проекта «Моя фаза» с нуля.
# Идемпотентен: можно запускать сколько угодно раз, ничего не сломается.
# Запуск:  bash scripts/setup.sh

set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

G='\033[0;32m'; Y='\033[0;33m'; R='\033[0;31m'; B='\033[1m'; N='\033[0m'
ok(){   printf "${G}  ok${N}  %s\n" "$1"; }
warn(){ printf "${Y}  ..${N}  %s\n" "$1"; }
err(){  printf "${R}  !!${N}  %s\n" "$1"; }
step(){ printf "\n${B}%s${N}\n" "$1"; }

FAILED=0
MANUAL=()

# ---------------------------------------------------------------- 1. система
step "1/7  Проверка инструментов"

case "$ROOT" in
  *[![:ascii:]]*|*" "*)
    warn "в пути к проекту есть пробелы или кириллица:"
    printf "        %s\n" "$ROOT"
    warn "это поддерживается, но команды в терминале набирайте в кавычках"
    ;;
esac

OS="$(uname -s)"
HAS_BREW=0
command -v brew >/dev/null 2>&1 && HAS_BREW=1

need_brew_note(){
  MANUAL+=("Установите Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
}

if command -v git >/dev/null 2>&1; then ok "git $(git --version | awk '{print $3}')"
else
  if [ "$HAS_BREW" = 1 ]; then warn "ставлю git"; brew install git >/dev/null 2>&1 && ok "git установлен" || { err "git не установился"; FAILED=1; }
  else err "git не найден"; need_brew_note; FAILED=1; fi
fi

if command -v node >/dev/null 2>&1; then ok "node $(node -v)"
else
  if [ "$HAS_BREW" = 1 ]; then warn "ставлю node"; brew install node >/dev/null 2>&1 && ok "node установлен" || { err "node не установился"; FAILED=1; }
  else err "node не найден"; need_brew_note; FAILED=1; fi
fi

command -v openssl >/dev/null 2>&1 && ok "openssl" || { err "openssl не найден"; FAILED=1; }

# ---------------------------------------------------------------- 2. docker
step "2/7  Docker"

if ! command -v docker >/dev/null 2>&1; then
  if [ "$HAS_BREW" = 1 ] && [ "$OS" = "Darwin" ]; then
    warn "ставлю Docker Desktop (несколько минут)"
    brew install --cask docker >/dev/null 2>&1 \
      && ok "Docker Desktop установлен" \
      || { err "не установился"; FAILED=1; }
    MANUAL+=("Запустите Docker Desktop из Программ и дождитесь, пока значок кита перестанет мигать")
  else
    err "docker не найден"
    MANUAL+=("Установите Docker Desktop: https://docker.com/products/docker-desktop")
    FAILED=1
  fi
else
  ok "docker $(docker --version | awk '{print $3}' | tr -d ,)"
fi

if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    ok "демон запущен"
  else
    if [ "$OS" = "Darwin" ] && [ -d "/Applications/Docker.app" ]; then
      warn "демон не отвечает, запускаю Docker Desktop"
      open -a Docker 2>/dev/null || true
      for i in $(seq 1 60); do
        docker info >/dev/null 2>&1 && break
        sleep 3
      done
      docker info >/dev/null 2>&1 && ok "демон поднялся" || {
        err "демон так и не ответил"
        MANUAL+=("Запустите Docker Desktop вручную и повторите: bash scripts/setup.sh")
        FAILED=1
      }
    else
      err "демон Docker не запущен"
      MANUAL+=("Запустите Docker Desktop и повторите: bash scripts/setup.sh")
      FAILED=1
    fi
  fi
fi

# ---------------------------------------------------------------- 3. git
step "3/7  Репозиторий"

if [ -d .git ]; then ok "git-репозиторий уже есть"
else
  git init -q
  git config user.name  >/dev/null 2>&1 || git config user.name  "myfaza"
  git config user.email >/dev/null 2>&1 || git config user.email "dev@myfaza.ru"
  git add -A >/dev/null 2>&1
  git commit -qm "chore: каркас проекта, спринт 1" >/dev/null 2>&1 \
    && ok "репозиторий создан, первый коммит сделан" \
    || warn "репозиторий создан, коммит не потребовался"
fi

# ---------------------------------------------------------------- 4. .env
step "4/7  Секреты"

gen(){ openssl rand -hex 32; }

if [ -f .env ]; then
  ok ".env уже существует, не трогаю"
  for k in SECRET_KEY FIELD_ENCRYPTION_KEY WEBHOOK_SECRET POSTGRES_PASSWORD; do
    v="$(grep -E "^${k}=" .env | cut -d= -f2-)"
    [ -z "$v" ] && { warn "$k пуст — заполните вручную"; }
  done
else
  cp .env.example .env
  SK="$(gen)"; FK="$(gen)"; WS="$(gen)"; PW="$(openssl rand -hex 16)"
  if [ "$OS" = "Darwin" ]; then SED=(sed -i ''); else SED=(sed -i); fi
  "${SED[@]}" "s|^SECRET_KEY=.*|SECRET_KEY=${SK}|"                     .env
  "${SED[@]}" "s|^FIELD_ENCRYPTION_KEY=.*|FIELD_ENCRYPTION_KEY=${FK}|" .env
  "${SED[@]}" "s|^WEBHOOK_SECRET=.*|WEBHOOK_SECRET=${WS}|"             .env
  "${SED[@]}" "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${PW}|"       .env
  ok ".env создан, секреты сгенерированы"

  mkdir -p "$HOME/.myfaza-backup"
  cp .env "$HOME/.myfaza-backup/env-$(date +%Y%m%d-%H%M%S).txt"
  chmod 600 "$HOME/.myfaza-backup/"* 2>/dev/null || true
  ok "копия секретов: ~/.myfaza-backup/"
fi

# ---------------------------------------------------------------- 5. сборка
step "5/7  Контейнеры"

if docker info >/dev/null 2>&1; then
  docker compose up -d --build 2>&1 | tail -3
  for i in $(seq 1 40); do
    docker compose exec -T postgres pg_isready -q 2>/dev/null && break
    sleep 2
  done
  docker compose ps --format "  {{.Service}}: {{.State}}" 2>/dev/null || true
  ok "контейнеры подняты"
else
  err "пропускаю: docker недоступен"
  FAILED=1
fi

# ---------------------------------------------------------------- 6. миграции
step "6/7  Миграции"

if docker info >/dev/null 2>&1; then
  if docker compose exec -T api alembic upgrade head 2>&1 | tail -2; then
    ok "схема применена"
  else
    err "миграция не прошла"; FAILED=1
  fi
fi

# ---------------------------------------------------------------- 7. проверка
step "7/7  Проверка"

if docker info >/dev/null 2>&1; then
  docker compose exec -T api pytest -q 2>&1 | tail -3
  sleep 2
  H="$(curl -fsS http://localhost:8000/api/v1/health/ready 2>/dev/null || echo '')"
  if echo "$H" | grep -q '"status":"ok"'; then ok "API отвечает: $H"
  else err "API не отвечает или деградирован: ${H:-нет ответа}"; FAILED=1; fi
fi

# ---------------------------------------------------------------- итог
printf "\n${B}Итог${N}\n"
if [ "$FAILED" = 0 ] && [ ${#MANUAL[@]} -eq 0 ]; then
  printf "${G}Окружение готово.${N}\n\n"
  printf "  API           http://localhost:8000/api/v1/health\n"
  printf "  Документация  http://localhost:8000/api/docs\n\n"
  printf "  Дальше:  claude   →   /sprint 2\n\n"
else
  [ "$FAILED" != 0 ] && printf "${Y}Есть незакрытые пункты.${N}\n"
  if [ ${#MANUAL[@]} -gt 0 ]; then
    printf "\n  ${B}Сделайте руками:${N}\n"
    for m in "${MANUAL[@]}"; do printf "   • %s\n" "$m"; done
    printf "\n  Затем повторите: bash scripts/setup.sh\n\n"
  fi
fi

exit 0
