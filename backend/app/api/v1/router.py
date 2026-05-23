from fastapi import APIRouter

from app.api.v1.trends import router as trends_router
from app.api.v1.videos import router as videos_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(trends_router)
api_router.include_router(videos_router)
