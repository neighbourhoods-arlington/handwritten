"""Ollama агент: модель MCP серверийн tool-уудыг дуудаж асуултад хариулна.

Loop:
  1. MCP серверээс tool жагсаалт авч Ollama формат руу хөрвүүлнэ
  2. Ollama chat(messages, tools) дуудна
  3. Модель tool_calls буцаавал тус бүрийг MCP-ээр гүйцэтгэж, role="tool" мессеж болгон нэмнэ
  4. tool_calls байхгүй болтол (эсвэл max_steps хүртэл) давтана
"""

import json
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings
from app.services.mcp_client import make_mcp_client, mcp_tools_to_ollama, tool_result_to_text
from app.services.ollama_client import get_ollama


@dataclass
class ToolCallTrace:
    step: int
    name: str
    arguments: dict[str, Any]
    result: str
    error: bool = False


@dataclass
class AgentResult:
    model: str
    content: str
    steps: int
    tool_calls: list[ToolCallTrace] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)


async def run_agent(
    messages: list[dict[str, Any]],
    model: str | None = None,
    system: str | None = None,
    max_steps: int | None = None,
) -> AgentResult:
    s = get_settings()
    model = model or s.ollama_model
    max_steps = max_steps or s.agent_max_steps

    history: list[dict[str, Any]] = [{"role": "system", "content": system or s.agent_system_prompt}]
    history.extend(messages)
    trace: list[ToolCallTrace] = []
    ollama = get_ollama()

    async with make_mcp_client() as mcp:
        tools = mcp_tools_to_ollama(await mcp.list_tools())

        for step in range(1, max_steps + 1):
            resp = await ollama.chat(model=model, messages=history, tools=tools, stream=False)
            msg = resp.message
            history.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                return AgentResult(
                    model=model,
                    content=msg.content or "",
                    steps=step,
                    tool_calls=trace,
                    messages=history,
                )

            for call in msg.tool_calls:
                name = call.function.name
                args = dict(call.function.arguments or {})
                try:
                    result = await mcp.call_tool(name, args)
                    text = tool_result_to_text(result)
                    error = False
                except Exception as exc:  # моделид алдааг буцааж өөрөө засах боломж өгнө
                    text = json.dumps({"error": str(exc)}, ensure_ascii=False)
                    error = True
                trace.append(ToolCallTrace(step, name, args, text, error))
                history.append({"role": "tool", "tool_name": name, "content": text})

    # max_steps дууссан: моделиос tool-гүй эцсийн хариу авна
    resp = await ollama.chat(model=model, messages=history, stream=False)
    history.append(resp.message.model_dump(exclude_none=True))
    return AgentResult(
        model=model,
        content=resp.message.content or "",
        steps=max_steps,
        tool_calls=trace,
        messages=history,
    )
