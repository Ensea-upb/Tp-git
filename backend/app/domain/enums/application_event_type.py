"""Enum des types d'événements de la timeline d'une candidature."""
from enum import StrEnum


class ApplicationEventType(StrEnum):
    APPLICATION_CREATED = "APPLICATION_CREATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    FOLLOWUP_SCHEDULED = "FOLLOWUP_SCHEDULED"
    RECRUITER_REPLIED = "RECRUITER_REPLIED"
    DRAFTS_READY = "DRAFTS_READY"
