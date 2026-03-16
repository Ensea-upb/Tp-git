import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums.user_status import UserStatus


class OfferUserStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    offer_id: uuid.UUID
    status: UserStatus
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
