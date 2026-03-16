from enum import StrEnum


class IngestionStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"   # au moins une erreur mais des offres créées
    FAILED = "FAILED"     # aucune offre créée ou erreur fatale
