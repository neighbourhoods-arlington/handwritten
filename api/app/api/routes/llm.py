from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from ollama import ResponseError

from app.core.config import get_settings
from app.schemas.llm import ChatRequest, GenerateRequest, LLMResponse
from app.services import ollama_client

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/models")
async def models() -> dict:
    try:
        return {"models": await ollama_client.list_models()}
    except Exception as exc:  # Ollama is probably down
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {exc}") from exc


@router.post("/generate", response_model=LLMResponse)
async def generate(req: GenerateRequest) -> LLMResponse:
    s = get_settings()
    try:
        text = await ollama_client.generate(req.prompt, model=req.model, system=req.system)
    except ResponseError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.error) from exc
    return LLMResponse(model=req.model or s.ollama_model, content=text)


@router.post("/chat", response_model=LLMResponse)
async def chat(req: ChatRequest) -> LLMResponse:
    s = get_settings()
    try:
        text = await ollama_client.chat([m.model_dump() for m in req.messages], model=req.model)
    except ResponseError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.error) from exc
    return LLMResponse(model=req.model or s.ollama_model, content=text)


@router.post("/ocr", response_model=LLMResponse)
async def ocr(
    image: UploadFile = File(...),
    prompt: str = Form("Transcribe the handwritten text in this image exactly."),
    model: str | None = Form(None),
) -> LLMResponse:
    """Transcribe a handwriting image to text with a vision model."""
    s = get_settings()
    data = await image.read()
    try:
        text = await ollama_client.describe_image(data, prompt, model=model)
    except ResponseError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.error) from exc
    return LLMResponse(model=model or s.ollama_vision_model, content=text)
