from fastapi import APIRouter, HTTPException
from ollama import ResponseError

from app.schemas.agent import AgentRequest, AgentResponse, AgentToolOut, ToolCallOut
from app.services.agent import run_agent
from app.services.mcp_client import make_mcp_client, mcp_tools_to_ollama

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/tools", response_model=list[AgentToolOut])
async def tools() -> list[AgentToolOut]:
    """Агентад харагдах MCP tool-ууд (Ollama формат)."""
    async with make_mcp_client() as mcp:
        return [AgentToolOut(**t["function"]) for t in mcp_tools_to_ollama(await mcp.list_tools())]


@router.post("/chat", response_model=AgentResponse)
async def chat(req: AgentRequest) -> AgentResponse:
    """Ollama модель MCP tool-уудыг ашиглан хариулна."""
    if req.messages:
        messages = [m.model_dump() for m in req.messages]
    elif req.prompt:
        messages = [{"role": "user", "content": req.prompt}]
    else:
        raise HTTPException(status_code=422, detail="prompt эсвэл messages өгнө үү")

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
