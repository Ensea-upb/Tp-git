from fastapi import APIRouter

from app.api.v1 import health, offers

api_router = APIRouter(prefix="/v1")

api_router.include_router(health.router)
api_router.include_router(offers.router, prefix="/offers", tags=["offers"])
