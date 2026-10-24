"""Shared helpers for MCP tools."""

from typing import Any

from pydantic import BaseModel

# Tools tagged STAFF are hidden from the Ollama agent: they need a human
# (approving/sending notes, importing exports). Claude and other clients see them.
STAFF = "staff"

READ_ONLY = {"readOnlyHint": True}


def dump(schema: type[BaseModel], obj: Any) -> dict:
    """ORM object → JSON-safe dict through a Pydantic read schema."""
    return schema.model_validate(obj).model_dump(mode="json")
