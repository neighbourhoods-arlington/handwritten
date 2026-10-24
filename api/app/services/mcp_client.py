"""MCP клиент — агент энэ клиентээр MCP серверийн tool-уудыг дуудна."""

import json
from typing import Any

from fastmcp import Client
from mcp.types import Tool as MCPTool

from app.core.config import get_settings


def make_mcp_client() -> Client:
    """MCP_CLIENT_URL байвал тэр серверт HTTP-ээр, үгүй бол өөрийн серверт in-process холбогдоно."""
    s = get_settings()
    if s.mcp_client_url:
        return Client(s.mcp_client_url)
    from app.mcp.server import mcp  # noqa: PLC0415 — circular import-оос зайлсхийх

    return Client(mcp)


def mcp_tools_to_ollama(tools: list[MCPTool]) -> list[dict[str, Any]]:
    """MCP tool тодорхойлолтыг Ollama-ийн function-calling формат руу хөрвүүлэх."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.input_schema or {"type": "object", "properties": {}},
            },
        }
        for t in tools
    ]


def tool_result_to_text(result: Any) -> str:
    """CallToolResult-ийг моделид буцаах текст болгох."""
    if getattr(result, "structured_content", None):
        return json.dumps(result.structured_content, ensure_ascii=False)
    parts = [c.text for c in getattr(result, "content", []) if getattr(c, "text", None)]
    return "\n".join(parts) if parts else json.dumps(getattr(result, "data", None), default=str)
