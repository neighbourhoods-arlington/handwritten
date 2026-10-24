from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.db import engine
from app.mcp.server import mcp
from app.pages import upload

settings = get_settings()

# FastMCP ASGI app. Its internal path is /mcp and it is mounted at the root,
# so http://host/mcp works without a redirect.
mcp_app = mcp.http_app(path=settings.mcp_mount_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The MCP session manager's lifespan must run alongside the app's
    async with mcp_app.lifespan(app):
        yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(upload.router)


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "api": "/api/v1",
        "mcp": settings.mcp_mount_path,
    }


# Mounted last: only requests that match no FastAPI route end up here
app.mount("/", mcp_app)
