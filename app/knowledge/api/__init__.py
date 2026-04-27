from fastapi import APIRouter

from .routes import router

knowledge_router = APIRouter()
knowledge_router.include_router(router, tags=["知识库模块"])

__all__ = ["knowledge_router"]
