"""MCP server (FastMCP).

Exposes domain tools over the MCP protocol. Tools live in app/mcp/tools/, one
sub-server per domain, mounted here without a namespace so tool names stay flat.
Full reference: docs/mcp-tools.md

Clients that call it:
  - the Ollama agent (app/services/agent.py) — in-process or over HTTP;
    it does not see tools tagged "staff"
  - Claude Code / Claude Desktop — HTTP (/mcp) or stdio; sees every tool

Runs in two modes:
  1. Mounted inside FastAPI with the HTTP transport  →  http://localhost:8000/mcp
  2. Standalone stdio:  python -m app.mcp.server
"""

from fastmcp import FastMCP

from app.core.config import get_settings
from app.mcp.tools import documents, donors, gifts, imports, letter_context, notes

settings = get_settings()

mcp = FastMCP(
    settings.mcp_server_name,
    instructions=(
        "MCP server for the Handwritten project (Phoenix Bikes). Helps staff send "
        "handwritten thank-you notes to small, infrequent donors: find eligible gifts, "
        "look up donors, draft notes for staff approval, and search transcribed documents."
    ),
)

for sub in (documents, donors, gifts, letter_context, notes, imports):
    mcp.mount(sub)


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


@mcp.prompt
def thank_you_note_prompt(
    first_name: str, amount: str, fund: str = "", receipt_note: str = ""
) -> str:
    """Prompt for drafting a short handwritten thank-you note for one gift."""
    details = f"Donor first name: {first_name}\nGift amount: ${amount}\n"
    if fund:
        details += f"Fund: {fund}\n"
    if receipt_note:
        details += f"Donor's note with the gift: {receipt_note}\n"
    return (
        "Write a warm, personal thank-you note from Phoenix Bikes staff, to be copied by "
        "hand onto a card. 3-5 sentences, under 80 words, no subject line, sign off as "
        '"The Phoenix Bikes team". Mention what the gift supports if the fund says so. '
        "If the donor's note mentions a memorial or honoree, acknowledge it gently. "
        "Do not invent facts.\n\n" + details
    )


if __name__ == "__main__":
    mcp.run()  # stdio
