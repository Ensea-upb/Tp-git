from fastapi import APIRouter

from app.api.v1 import health, ingestion, offer_actions, offers, preferences, sources

api_router = APIRouter(prefix="/v1")

api_router.include_router(health.router)
api_router.include_router(offers.router, prefix="/offers", tags=["offers"])
api_router.include_router(offer_actions.router, prefix="/offers", tags=["offer-actions"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(preferences.router, prefix="/preferences", tags=["preferences"])
