import uuid
from dataclasses import dataclass
from typing import Literal


@dataclass
class DeduplicationDecision:
    """
    Résultat de l'analyse de déduplication pour une offre.

    decision:
        "create"    → offre nouvelle, à insérer
        "update"    → offre existante détectée sur une nouvelle source, à enrichir
        "duplicate" → doublon exact, à ignorer
    """

    decision: Literal["create", "update", "duplicate"]
    reason: str
    confidence: float = 1.0           # 0.0–1.0
    matched_offer_id: uuid.UUID | None = None
