"""MCP server (FastMCP).

Exposes domain tools (search, read, create documents) over the MCP protocol.
Clients that call it:
  - the Ollama agent (app/services/agent.py) — in-process or over HTTP
  - Claude Code / Claude Desktop — HTTP (/mcp) or stdio

Runs in two modes:
  1. Mounted inside FastAPI with the HTTP transport  →  http://localhost:8000/mcp
  2. Standalone stdio:  python -m app.mcp.server
"""

import uuid

from fastmcp import FastMCP
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models import Document

settings = get_settings()

mcp = FastMCP(
    settings.mcp_server_name,
    instructions=(
        "MCP server for the Handwritten project. Search, read and create "
        "documents transcribed from handwriting."
    ),
)


@mcp.tool
async def list_documents(limit: int = 20) -> list[dict]:
    """List the most recent documents (id, title, created_at)."""
    async with SessionLocal() as session:
        result = await session.execute(
            select(Document).order_by(Document.created_at.desc()).limit(limit)
        )
        return [
            {"id": str(d.id), "title": d.title, "created_at": d.created_at.isoformat()}
            for d in result.scalars()
        ]


@mcp.tool
async def get_document(doc_id: str) -> dict:
    """Get a single document by id, including its content."""
    async with SessionLocal() as session:
        doc = await session.get(Document, uuid.UUID(doc_id))
        if doc is None:
            raise ValueError(f"Document {doc_id} not found")
        return {
            "id": str(doc.id),
            "title": doc.title,
            "content": doc.content,
            "source_path": doc.source_path,
            "created_at": doc.created_at.isoformat(),
        }


@mcp.tool
async def create_document(title: str, content: str = "", source_path: str | None = None) -> dict:
    """Create a new document."""
    async with SessionLocal() as session:
        doc = Document(title=title, content=content, source_path=source_path)
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return {"id": str(doc.id), "title": doc.title}


@mcp.tool
async def search_documents(query: str, limit: int = 10) -> list[dict]:
    """Search title and content for text (case-insensitive)."""
    async with SessionLocal() as session:
        pattern = f"%{query}%"
        result = await session.execute(
            select(Document)
            .where(Document.title.ilike(pattern) | Document.content.ilike(pattern))
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        return [{"id": str(d.id), "title": d.title} for d in result.scalars()]


@mcp.resource("handwritten://config")
def server_config() -> dict:
    """Active server configuration (no secrets)."""
    return {
        "app_env": settings.app_env,
        "ollama_base_url": settings.ollama_base_url,
        "ollama_model": settings.ollama_model,
        "ollama_vision_model": settings.ollama_vision_model,
    }


@mcp.prompt
def transcribe_prompt(language: str = "English") -> str:
    """Prompt for transcribing handwriting."""
    return (
        f"You are an expert at reading {language} handwriting. "
        "Transcribe the text exactly, preserving line breaks. "
        "If a word is illegible, write [illegible]."
    )


if __name__ == "__main__":
    mcp.run()  # stdio
