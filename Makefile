.PHONY: up down logs migrate revision test lint fmt shell

up:            ## Поднять всё локально
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api

migrate:       ## Применить миграции
	docker compose exec api alembic upgrade head

revision:      ## make revision m="описание"
	docker compose exec api alembic revision --autogenerate -m "$(m)"

test:
	docker compose exec api pytest -q

lint:
	docker compose exec api ruff check app tests
	docker compose exec api mypy app

fmt:
	docker compose exec api ruff format app tests
	docker compose exec api ruff check --fix app tests

shell:
	docker compose exec api python
