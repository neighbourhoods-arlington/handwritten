from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str | None = None
    system: str | None = None


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    model: str | None = None


class LLMResponse(BaseModel):
    model: str
    content: str


class InstalledModel(BaseModel):
    name: str
    size_gb: float
    family: str | None = None
    parameters: str | None = None
    quantization: str | None = None


class RunningModel(BaseModel):
    name: str
    size_gb: float
    size_vram_gb: float
    context_length: int | None = None
    expires_at: str | None = None
    processor: str


class OllamaStatus(BaseModel):
    """What the Ollama server is doing right now (for the dashboard / demo)."""

    available: bool
    base_url: str
    version: str | None
    letter_model: str
    vision_model: str
    installed: list[InstalledModel]
    running: list[RunningModel]
    error: str | None = None
