.PHONY: setup up up-ollama down logs migrate revision shell venv test lint mcp-stdio

setup:         ## Copy .env files from their examples (if missing)
	@test -f .env || cp .env.example .env
	@test -f api/.env || cp api/.env.example api/.env
	@test -f web/.env || cp web/.env.example web/.env
	@echo ".env files ready"

up:            ## Start PostgreSQL + API + web
	docker compose up -d --build

up-ollama:     ## Start with Ollama in a container as well
	docker compose --profile ollama up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api

logs-web:
	docker compose logs -f web

web-dev:       ## Run the Qwik dev server on the host
	cd web && npm run dev

migrate:       ## Run Alembic migrations
	docker compose exec api alembic upgrade head

revision:      ## Create a new migration: make revision m="add x"
	docker compose exec api alembic revision --autogenerate -m "$(m)"

shell:
	docker compose exec api sh

venv:          ## Create the local venv for api/
	cd api && python3 -m venv .venv && .venv/bin/pip install -q -e ".[dev]"

test:
	cd api && .venv/bin/pytest -q

lint:
	cd api && .venv/bin/ruff check app tests

mcp-stdio:     ## Run the MCP server over stdio (for Claude Desktop/Code)
	cd api && .venv/bin/python -m app.mcp.server
