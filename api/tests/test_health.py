from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_root_lists_mcp_mount():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/")
    assert r.status_code == 200
    assert r.json()["mcp"] == "/mcp"


async def test_mcp_tools_registered():
    from app.mcp.server import mcp

    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert {"list_documents", "get_document", "create_document", "search_documents"} <= names


async def test_mcp_tools_convert_to_ollama_format():
    from app.services.mcp_client import make_mcp_client, mcp_tools_to_ollama

    async with make_mcp_client() as client:
        tools = mcp_tools_to_ollama(await client.list_tools())
    assert tools and all(t["type"] == "function" for t in tools)
    by_name = {t["function"]["name"]: t["function"] for t in tools}
    assert by_name["search_documents"]["parameters"]["type"] == "object"
    assert "query" in by_name["search_documents"]["parameters"]["properties"]
