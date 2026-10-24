"""Ollama agent: the model answers by calling tools on the MCP server.

Loop:
  1. Fetch the tool list from the MCP server and convert it to Ollama format
  2. Call Ollama chat(messages, tools)
  3. If the model returns tool_calls, execute each via MCP and append role="tool" messages
  4. Repeat until there are no tool_calls (or max_steps is reached)
"""

import json
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings
from app.services.mcp_client import (
    agent_visible_tools,
    make_mcp_client,
    mcp_tools_to_ollama,
    normalize_tool_args,
    tool_result_to_text,
)
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
        visible = agent_visible_tools(await mcp.list_tools())
        allowed = {t.name for t in visible}
        tools = mcp_tools_to_ollama(visible)

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
                args = normalize_tool_args(call.function.arguments)
                try:
                    if name not in allowed:
                        raise ValueError(f"Tool {name!r} is not available to the agent")
                    result = await mcp.call_tool(name, args)
                    text = tool_result_to_text(result)
                    error = False
                except Exception as exc:  # return the error to the model so it can recover
                    text = json.dumps({"error": str(exc)}, ensure_ascii=False)
                    error = True
                trace.append(ToolCallTrace(step, name, args, text, error))
                history.append({"role": "tool", "tool_name": name, "content": text})

    # max_steps exhausted: ask the model for a final answer without tools
    resp = await ollama.chat(model=model, messages=history, stream=False)
    history.append(resp.message.model_dump(exclude_none=True))
    return AgentResult(
        model=model,
        content=resp.message.content or "",
        steps=max_steps,
        tool_calls=trace,
        messages=history,
    )
