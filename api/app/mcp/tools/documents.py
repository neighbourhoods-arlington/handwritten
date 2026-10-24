"""Document tools: handwriting transcriptions."""

import uuid

from fastmcp import FastMCP
from sqlalchemy import select

from app.core.db import SessionLocal
from app.mcp.tools.common import READ_ONLY
from app.models import Document

documents = FastMCP("documents")


@documents.tool(annotations=READ_ONLY)
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


@documents.tool(annotations=READ_ONLY)
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


@documents.tool
async def create_document(title: str, content: str = "", source_path: str | None = None) -> dict:
    """Create a new document."""
    async with SessionLocal() as session:
        doc = Document(title=title, content=content, source_path=source_path)
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return {"id": str(doc.id), "title": doc.title}


@documents.tool(annotations=READ_ONLY)
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
