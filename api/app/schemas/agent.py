from typing import Any

from pydantic import BaseModel, Field

from app.schemas.llm import ChatMessage


class AgentRequest(BaseModel):
    prompt: str | None = Field(default=None, min_length=1)
    messages: list[ChatMessage] | None = None
    model: str | None = None
    system: str | None = None
    max_steps: int | None = Field(default=None, ge=1, le=50)


class ToolCallOut(BaseModel):
    step: int
    name: str
    arguments: dict[str, Any]
    result: str
    error: bool


class AgentResponse(BaseModel):
    model: str
    content: str
    steps: int
    tool_calls: list[ToolCallOut]


class AgentToolOut(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]
