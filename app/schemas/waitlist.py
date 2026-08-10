import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import WaitlistStatus


class WaitlistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    user_id: uuid.UUID
    status: WaitlistStatus
    position: int | None
    promoted_at: datetime | None
    expires_at: datetime | None
    created_at: datetime