# Handwritten

Monorepo for the Handwritten project: a FastAPI backend with PostgreSQL, an MCP server
exposing domain tools, and an Ollama-powered agent that calls those tools.

```
handwritten/
├── api/                 FastAPI + SQLAlchemy (async) + Alembic + FastMCP + Ollama
│   ├── app/
│   │   ├── api/routes/  health, documents (CRUD), llm (generate/chat/ocr), agent
│   │   ├── core/        config (pydantic-settings), db (async engine)
│   │   ├── mcp/         MCP server (FastMCP) — mounted at /mcp, or run via stdio
│   │   ├── models/      SQLAlchemy models
│   │   ├── schemas/     Pydantic schemas
│   │   └── services/    ollama_client, mcp_client, agent (Ollama → MCP loop)
│   ├── alembic/         Migrations
│   ├── tests/
│   ├── .env.example
│   ├── Dockerfile
│   └── pyproject.toml
├── web/                 Qwik City frontend (Vite, SSR) — see web/README.md
│   ├── src/routes/      Pages (index shows API status + documents)
│   ├── src/lib/api.ts   Typed client for the backend
│   ├── .env.example
│   └── Dockerfile
├── docker-compose.yml   db (PostgreSQL 17) + api + web (+ optional ollama profile)
├── .env.example         Infrastructure variables for docker-compose
└── Makefile
```

## Quick start

```bash
make setup          # copy .env, api/.env, web/.env from their examples
make up             # start PostgreSQL + API + web (migrations run automatically)
make logs
```

| URL | What |
|-----|------|
| http://localhost:5173 | Web app (Qwik) |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/api/v1/health/ready | DB + Ollama connectivity |
| http://localhost:8000/mcp | MCP server (Streamable HTTP) |

## Architecture: Ollama agent → MCP server

```
POST /api/v1/agent/chat
        │
        ▼
 app/services/agent.py ──(chat + tools)──▶ Ollama (llama3.2 ...)
        │  ▲                                   │
        │  └──── tool_calls ◀──────────────────┘
        ▼
 fastmcp.Client ──▶ MCP server (app/mcp/server.py)
                      donors / gifts / notes / imports / documents (20 tools)
                                │
                                ▼
                           PostgreSQL
```

The Ollama model acts as the agent and decides which MCP tools to call. By default the
agent connects to the project's own MCP server **in-process**. Set `MCP_CLIENT_URL` to
connect over HTTP instead (to this server's `/mcp` or to any external MCP server).

```bash
curl -X POST localhost:8000/api/v1/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Is there a document mentioning eggs? If not, create one."}'
```

The response contains `content` (final answer), `steps`, and `tool_calls` (which tool
was called with which arguments and what it returned). `GET /api/v1/agent/tools` lists
the tools visible to the agent. Tools tagged `staff` (`approve_note`, `mark_note_sent`,
`import_gifts_csv`) are hidden from the agent: a person has to approve and send notes.

## Ollama

By default the API container talks to **Ollama running on the host machine** at
`http://host.docker.internal:11434`. Make sure `ollama serve` is running on the host.

| Variable | Default | Notes |
|----------|---------|-------|
| `OLLAMA_MODEL` | `llama3.2` | Agent/chat model. **Must support tool calling** (llama3.2, qwen3, mistral, ...). gemma3 does not. |
| `OLLAMA_VISION_MODEL` | `gemma3:4b` | Used by `/llm/ocr` to read images |

```bash
ollama pull llama3.2
ollama pull gemma3:4b
```

To run Ollama inside Docker instead:

```bash
make up-ollama                       # enables the "ollama" compose profile
docker compose exec ollama ollama pull llama3.2
# root .env:  OLLAMA_BASE_URL_DOCKER=http://ollama:11434
```

Endpoints: `POST /api/v1/llm/generate`, `POST /api/v1/llm/chat`,
`POST /api/v1/llm/ocr` (image + vision model), `GET /api/v1/llm/models`.

## MCP server

Built with [FastMCP](https://gofastmcp.com). 20 tools in five groups (donors, gifts,
thank-you notes, imports, documents), prompts `thank_you_note_prompt` and
`transcribe_prompt`, resource `handwritten://config`.
**Full tool reference: [docs/mcp-tools.md](docs/mcp-tools.md).**

Besides the Ollama agent, any other MCP client (e.g. Claude) can connect to the same server.

**HTTP** — with the API running, add it to Claude Code:

```bash
claude mcp add --transport http handwritten http://localhost:8000/mcp
```

**stdio** — for Claude Desktop and similar clients:

```bash
make venv
make mcp-stdio      # cd api && .venv/bin/python -m app.mcp.server
```

## Local development (API without Docker)

```bash
docker compose up -d db
make venv
cd api && .venv/bin/alembic upgrade head
cd api && .venv/bin/uvicorn app.main:app --reload
make test
make lint
```

## Web (Qwik)

```bash
cd web && npm install && npm run dev     # without Docker
```

The browser calls the API via `PUBLIC_API_BASE_URL`; SSR uses the server-only
`API_BASE_URL` (set to `http://api:8000/api/v1` inside compose). Details in `web/README.md`.

## Migrations

```bash
make revision m="add users table"
make migrate
```
