from enum import StrEnum


class StrategyActionType(StrEnum):
    APPLY_NOW = "APPLY_NOW"
    SEND_FOLLOWUP = "SEND_FOLLOWUP"
    PREPARE_INTERVIEW = "PREPARE_INTERVIEW"
    ARCHIVE_STALE = "ARCHIVE_STALE"
