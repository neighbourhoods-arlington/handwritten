.PHONY: setup up up-ollama down logs build migrate revision shell test lint mcp-stdio

setup:         ## .env файлуудыг example-аас хуулах (байхгүй бол)
	@test -f .env || cp .env.example .env
	@test -f api/.env || cp api/.env.example api/.env
	@test -f web/.env || cp web/.env.example web/.env
	@echo ".env файлууд бэлэн"

up:            ## PostgreSQL + API-г асаах
	docker compose up -d --build

up-ollama:     ## Ollama-г хамт асаах
	docker compose --profile ollama up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api

migrate:       ## Alembic миграци ажиллуулах
	docker compose exec api alembic upgrade head

revision:      ## Шинэ миграци үүсгэх: make revision m="add x"
	docker compose exec api alembic revision --autogenerate -m "$(m)"

shell:
	docker compose exec api sh

venv:          ## api/ локал venv үүсгэх
	cd api && python3 -m venv .venv && .venv/bin/pip install -q -e ".[dev]"

test:
	cd api && .venv/bin/pytest -q

lint:
	cd api && .venv/bin/ruff check app tests

mcp-stdio:     ## MCP серверийг stdio горимд (Claude Desktop/Code-д) ажиллуулах
	cd api && .venv/bin/python -m app.mcp.server
