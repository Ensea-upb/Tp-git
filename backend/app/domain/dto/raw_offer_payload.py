from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawOfferPayload:
    """
    Représentation d'une offre telle que retournée par un connecteur.
    Indépendante de tout modèle ORM ou schéma Pydantic.
    """

    source_name: str
    source_type: str
    raw_title: str
    raw_content: str

    external_offer_id: str | None = None
    offer_url: str | None = None
    raw_location: str | None = None
    raw_company_name: str | None = None
    published_at_detected: datetime | None = None
    metadata: dict = field(default_factory=dict)
