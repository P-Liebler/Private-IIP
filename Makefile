COMPOSE := docker compose

.PHONY: up down build logs test lint format typecheck migrate smoke config create-user reset-totp sources source-review source-enable source-disable

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f --tail=100

config:
	$(COMPOSE) config

test:
	$(COMPOSE) run --rm api pytest -q

lint:
	$(COMPOSE) run --rm api ruff check .
	$(COMPOSE) run --rm web npm run lint

format:
	$(COMPOSE) run --rm api ruff format .

typecheck:
	$(COMPOSE) run --rm api mypy app
	$(COMPOSE) run --rm web npm run typecheck

migrate:
	$(COMPOSE) run --rm api alembic upgrade head

smoke:
	$(COMPOSE) exec -T api python -m app.jobs.smoke
	$(COMPOSE) exec -T api python -m app.core.storage_smoke

create-user:
	$(COMPOSE) exec api python -m app.auth.cli create-user

reset-totp:
	$(COMPOSE) exec api python -m app.auth.cli reset-totp

sources:
	$(COMPOSE) exec -T api python -m app.sources.cli list

source-review:
	$(COMPOSE) exec -T api python -m app.sources.cli review $(ARGS)

source-enable:
	$(COMPOSE) exec -T api python -m app.sources.cli enable $(SOURCE)

source-disable:
	$(COMPOSE) exec -T api python -m app.sources.cli disable $(SOURCE)
