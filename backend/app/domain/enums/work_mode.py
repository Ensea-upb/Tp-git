import enum


class WorkMode(str, enum.Enum):
    """Mode de travail d'une offre."""

    ONSITE = "ONSITE"
    HYBRID = "HYBRID"
    REMOTE = "REMOTE"
