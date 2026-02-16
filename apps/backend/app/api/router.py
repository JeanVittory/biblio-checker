from fastapi import APIRouter

from app.api.routes.references.router import api_router as references_router

api_router = APIRouter(prefix="/api")
api_router.include_router(references_router, tags=["references"])
