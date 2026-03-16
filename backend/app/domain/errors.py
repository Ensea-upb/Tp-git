"""Domain exceptions — séparation claire entre 404 et 400."""


class NotFoundError(Exception):
    """Ressource introuvable → 404."""


class BusinessRuleError(Exception):
    """Violation d'une règle métier → 400."""
