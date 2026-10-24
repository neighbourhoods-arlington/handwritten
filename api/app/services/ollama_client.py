"""Async wrapper around the Ollama client."""

from functools import lru_cache

import httpx
from ollama import AsyncClient

from app.core.config import get_settings


@lru_cache
def get_ollama() -> AsyncClient:
    s = get_settings()
    return AsyncClient(host=s.ollama_base_url, timeout=s.ollama_timeout_seconds)


async def is_available() -> bool:
    """Whether the Ollama server is reachable."""
    s = get_settings()
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{s.ollama_base_url}/api/tags")
            return r.status_code == 200
    except httpx.HTTPError:
        return False


async def list_models() -> list[str]:
    resp = await get_ollama().list()
    return [m.model for m in resp.models if m.model]


async def generate(prompt: str, model: str | None = None, system: str | None = None) -> str:
    s = get_settings()
    resp = await get_ollama().generate(
        model=model or s.ollama_model,
        prompt=prompt,
        system=system,
        stream=False,
    )
    return resp.response


async def chat(messages: list[dict[str, str]], model: str | None = None) -> str:
    s = get_settings()
    resp = await get_ollama().chat(model=model or s.ollama_model, messages=messages, stream=False)
    return resp.message.content or ""


async def describe_image(image_bytes: bytes, prompt: str, model: str | None = None) -> str:
    """Read an image (e.g. handwriting) with a vision model."""
    s = get_settings()
    resp = await get_ollama().chat(
        model=model or s.ollama_vision_model,
        messages=[{"role": "user", "content": prompt, "images": [image_bytes]}],
        stream=False,
    )
    return resp.message.content or ""
