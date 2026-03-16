from enum import Enum


class ApplicationStatus(str, Enum):
    DRAFT = "DRAFT"
    READY_TO_SEND = "READY_TO_SEND"
    SENT = "SENT"
    FOLLOW_UP_DUE = "FOLLOW_UP_DUE"
    INTERVIEW = "INTERVIEW"
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"
    ARCHIVED = "ARCHIVED"
