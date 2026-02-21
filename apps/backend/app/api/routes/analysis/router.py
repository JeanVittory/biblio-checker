from fastapi import APIRouter

from app.api.controllers.analysis import start

api_router = APIRouter(prefix="/analysis")
api_router.include_router(start.router, tags=["analysis"])
