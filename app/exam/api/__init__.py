from fastapi import APIRouter

from .routes import router

exam_router = APIRouter()
exam_router.include_router(router, tags=["答题模块"])

__all__ = ["exam_router"]
