from dataclasses import dataclass

from app.domain.enums.work_mode import WorkMode


@dataclass
class NormalizedOfferPayload:
    """
    Offre après normalisation déterministe.
    Produite par OfferNormalizer, consommée par OfferDeduplicator et OfferIngestionService.
    """

    normalized_title: str
    normalized_description: str
    company_name: str
    checksum: str  # SHA-256 déterministe

    contract_type: str | None = None
    duration_months: int | None = None
    location_text: str | None = None
    work_mode: WorkMode | None = None
    education_level: str | None = None
