from fastapi import APIRouter

from app.api.v1 import health, ingestion, offers, sources

api_router = APIRouter(prefix="/v1")

api_router.include_router(health.router)
api_router.include_router(offers.router, prefix="/offers", tags=["offers"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
