from fastapi import APIRouter

from app.api.controllers.references import verify_authenticity

api_router = APIRouter(prefix="/references")
api_router.include_router(verify_authenticity.router, tags=["references"])

