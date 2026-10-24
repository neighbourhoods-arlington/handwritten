from fastapi import APIRouter, HTTPException
from ollama import ResponseError

from app.schemas.agent import AgentRequest, AgentResponse, AgentToolOut, ToolCallOut
from app.services.agent import run_agent
from app.services.mcp_client import agent_visible_tools, make_mcp_client, mcp_tools_to_ollama

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/tools", response_model=list[AgentToolOut])
async def tools() -> list[AgentToolOut]:
    """MCP tools visible to the agent (Ollama format)."""
    async with make_mcp_client() as mcp:
        tools = agent_visible_tools(await mcp.list_tools())
        return [AgentToolOut(**t["function"]) for t in mcp_tools_to_ollama(tools)]


@router.post("/chat", response_model=AgentResponse)
async def chat(req: AgentRequest) -> AgentResponse:
    """Answer using the Ollama model with MCP tools."""
    if req.messages:
        messages = [m.model_dump() for m in req.messages]
    elif req.prompt:
        messages = [{"role": "user", "content": req.prompt}]
    else:
        raise HTTPException(status_code=422, detail="Provide either prompt or messages")

    try:
        result = await run_agent(
            messages, model=req.model, system=req.system, max_steps=req.max_steps
        )
    except ResponseError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.error) from exc

    return AgentResponse(
        model=result.model,
        content=result.content,
        steps=result.steps,
        tool_calls=[ToolCallOut(**vars(t)) for t in result.tool_calls],
    )
