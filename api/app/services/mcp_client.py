"""MCP client — the agent uses it to call tools on the MCP server."""

import json
from typing import Any

from fastmcp import Client
from mcp.types import Tool as MCPTool

from app.core.config import get_settings
from app.mcp.tools.common import STAFF


def make_mcp_client() -> Client:
    """Connect over HTTP if MCP_CLIENT_URL is set, otherwise to this app's own server in-process."""
    s = get_settings()
    if s.mcp_client_url:
        return Client(s.mcp_client_url)
    from app.mcp.server import mcp  # noqa: PLC0415 — avoid circular import

    return Client(mcp)


def tool_tags(tool: MCPTool) -> set[str]:
    return set(((tool.meta or {}).get("fastmcp") or {}).get("tags") or [])


def agent_visible_tools(tools: list[MCPTool]) -> list[MCPTool]:
    """Drop tools tagged "staff" (approve/send notes, imports): they need a human."""
    return [t for t in tools if STAFF not in tool_tags(t)]


def mcp_tools_to_ollama(tools: list[MCPTool]) -> list[dict[str, Any]]:
    """Convert MCP tool definitions to Ollama's function-calling format."""
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


def normalize_tool_args(arguments: dict[str, Any] | None) -> dict[str, Any]:
    """Drop null-valued arguments so the server-side defaults apply.

    Small models (e.g. llama3.2) often emit ``{"limit": null}`` for optional
    parameters, which fails schema validation on the MCP server.
    """
    return {k: v for k, v in (arguments or {}).items() if v is not None}


def tool_result_to_text(result: Any) -> str:
    """Render a CallToolResult as text to feed back to the model."""
    if getattr(result, "structured_content", None):
        return json.dumps(result.structured_content, ensure_ascii=False)
    parts = [c.text for c in getattr(result, "content", []) if getattr(c, "text", None)]
    return "\n".join(parts) if parts else json.dumps(getattr(result, "data", None), default=str)
