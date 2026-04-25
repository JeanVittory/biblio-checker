from fastapi import APIRouter

from app.api.controllers.analysis import share, shared, start, status

api_router = APIRouter(prefix="/analysis")
api_router.include_router(start.router, tags=["analysis"])
api_router.include_router(status.router, tags=["analysis"])
api_router.include_router(share.router, tags=["analysis"])
api_router.include_router(shared.router, tags=["analysis"])
