COMPOSE := docker compose

.PHONY: up down exec lint lint-fix test int-test

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

exec:
	$(COMPOSE) exec worker bash

lint:
	$(COMPOSE) exec worker ruff check .
	$(COMPOSE) exec worker mypy app

lint-fix:
	$(COMPOSE) exec worker ruff check --fix .

test:
	$(COMPOSE) exec worker pytest tests/unit -v

int-test:
	$(COMPOSE) exec worker pytest tests/integration -v
