from fastapi import APIRouter

from app.api.routes.analysis.router import api_router as analysis_router

api_router = APIRouter(prefix="/api")
api_router.include_router(analysis_router, tags=["analysis"])
