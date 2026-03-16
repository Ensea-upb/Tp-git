from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["system"])
def health_check() -> dict:
    """Endpoint de santé — public, sans authentification."""
    return {"status": "ok", "version": "1.0.0"}
