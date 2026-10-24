from fastapi import APIRouter

from app.api.routes import agent, documents, donors, health, imports, letters, llm

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(donors.router)
api_router.include_router(letters.router)
api_router.include_router(llm.router)
api_router.include_router(agent.router)
api_router.include_router(imports.router)
