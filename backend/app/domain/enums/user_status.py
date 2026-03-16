from enum import StrEnum


class UserStatus(StrEnum):
    FAVORITE = "FAVORITE"
    SHORTLISTED = "SHORTLISTED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
