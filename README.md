# Handwritten

Гар бичмэл таних төслийн monorepo.

```
handwritten/
├── api/                 FastAPI + SQLAlchemy (async) + Alembic + FastMCP + Ollama client
│   ├── app/
│   │   ├── api/routes/  health, documents (CRUD), llm (generate / chat / ocr)
│   │   ├── core/        config (pydantic-settings), db (async engine)
│   │   ├── mcp/         MCP сервер (FastMCP) — /mcp дээр mount, эсвэл stdio
│   │   ├── models/      SQLAlchemy моделиуд
│   │   ├── schemas/     Pydantic схемүүд
│   │   └── services/    Ollama async client
│   ├── alembic/         Миграциуд
│   ├── tests/
│   ├── .env.example
│   ├── Dockerfile
│   └── pyproject.toml
├── web/                 Frontend (framework сонгогдоогүй — web/README.md харах)
│   └── .env.example
├── docker-compose.yml   db (PostgreSQL 17) + api (+ сонголттой ollama)
├── .env.example         compose-ийн дэд бүтцийн хувьсагчид
└── Makefile
```

## Эхлүүлэх

```bash
make setup          # .env, api/.env, web/.env файлуудыг example-аас хуулна
make up             # PostgreSQL + API (миграци автоматаар ажиллана)
make logs
```

| Хаяг | Юу |
|------|----|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/api/v1/health/ready | DB + Ollama холболтын төлөв |
| http://localhost:8000/mcp | MCP сервер (Streamable HTTP) |

## Ollama

Default-аар API контейнер **хост машин дээр ажиллаж буй Ollama**-г
`http://host.docker.internal:11434` хаягаар дуудна. Хост дээр `ollama serve`
ажиллаж, `ollama pull gemma3:4b` хийсэн байх хэрэгтэй.

Ollama-г контейнерт ажиллуулах бол:

```bash
make up-ollama                       # --profile ollama
docker compose exec ollama ollama pull gemma3:4b
# root .env:  OLLAMA_BASE_URL_DOCKER=http://ollama:11434
```

Endpoint-ууд: `POST /api/v1/llm/generate`, `POST /api/v1/llm/chat`,
`POST /api/v1/llm/ocr` (зураг + vision модель), `GET /api/v1/llm/models`.

## MCP сервер

[FastMCP](https://gofastmcp.com) ашигласан. Tools: `list_documents`,
`get_document`, `create_document`, `search_documents`, `ask_ollama`,
`ollama_models`. Resource: `handwritten://config`. Prompt: `transcribe_prompt`.

**HTTP** — API асаалттай үед Claude Code-д холбох:

```bash
claude mcp add --transport http handwritten http://localhost:8000/mcp
```

**stdio** — Claude Desktop гэх мэт:

```bash
make venv
make mcp-stdio      # cd api && .venv/bin/python -m app.mcp.server
```

## Локал хөгжүүлэлт (Docker-гүй API)

```bash
docker compose up -d db
make venv
cd api && .venv/bin/alembic upgrade head
cd api && .venv/bin/uvicorn app.main:app --reload
make test
make lint
```

## Миграци

```bash
make revision m="add users table"
make migrate
```
