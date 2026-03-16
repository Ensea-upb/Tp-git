from dataclasses import dataclass, field


@dataclass
class IngestionReport:
    """
    Bilan d'un cycle de collecte pour un connecteur.

    Produit et loggé par BaseConnector.fetch() après chaque appel.
    Ne dépend pas de OfferIngestionService.
    """

    source: str
    fetched: int = 0
    inserted: int = 0       # renseigné par OfferIngestionService si disponible
    duplicates: int = 0     # renseigné par OfferIngestionService si disponible
    errors: int = 0
    duration_seconds: float = 0.0
    error_details: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"[{self.source}] fetched={self.fetched} inserted={self.inserted} "
            f"duplicates={self.duplicates} errors={self.errors} "
            f"duration={self.duration_seconds:.2f}s"
        )
