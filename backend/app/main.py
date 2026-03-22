import logging
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations Alembic appliquées")
    except Exception as exc:
        logger.warning("Migrations ignorées (déjà à jour ou erreur) : %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _run_migrations()
    logger.info("Backend démarré — env=%s", settings.app_env)
    yield
    logger.info("Backend arrêté")


app = FastAPI(
    title="Agent Personnel de Recherche de Stage",
    description="API backend — Sprint 10",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(api_router)
