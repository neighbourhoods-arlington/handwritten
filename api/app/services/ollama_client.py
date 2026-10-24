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


async def status() -> dict:
    """Live view of the Ollama server for the dashboard: version, configured models,
    what is installed and what is loaded in memory right now."""
    s = get_settings()
    out: dict = {
        "available": False,
        "base_url": s.ollama_base_url,
        "version": None,
        "letter_model": s.ollama_model,
        "vision_model": s.ollama_vision_model,
        "installed": [],
        "running": [],
    }
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{s.ollama_base_url}/api/version")
            out["version"] = r.json().get("version")
        client = get_ollama()
        installed = await client.list()
        out["installed"] = [
            {
                "name": m.model,
                "size_gb": round((m.size or 0) / 1e9, 1),
                "family": (m.details.family if m.details else None),
                "parameters": (m.details.parameter_size if m.details else None),
                "quantization": (m.details.quantization_level if m.details else None),
            }
            for m in installed.models
            if m.model
        ]
        running = await client.ps()
        out["running"] = [
            {
                "name": m.model,
                "size_vram_gb": round((m.size_vram or 0) / 1e9, 1),
                "size_gb": round((m.size or 0) / 1e9, 1),
                "context_length": m.context_length,
                "expires_at": m.expires_at.isoformat() if m.expires_at else None,
                "processor": "GPU"
                if (m.size_vram or 0) >= (m.size or 1)
                else ("CPU" if not m.size_vram else "CPU/GPU"),
            }
            for m in running.models
            if m.model
        ]
        out["available"] = True
    except Exception as exc:  # Ollama down or unreachable: report, don't fail the page
        out["error"] = str(exc)
    return out
