import uuid
from dataclasses import dataclass, field


@dataclass
class IngestionResult:
    """Bilan d'un cycle d'ingestion pour une source."""

    source_name: str
    total_fetched: int = 0
    new_offers: int = 0
    updated_offers: int = 0
    duplicates: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    error_details: list[str] = field(default_factory=list)
    # Identifiant du run persisté en base (disponible après commit)
    run_id: uuid.UUID | None = None
