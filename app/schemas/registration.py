import uuid
from datetime import datetime
from typing import Literal
from app.schemas.waitlist import WaitlistOut
from pydantic import BaseModel, ConfigDict
from app.enums import RegistrationStatus


class RegistrationCreate(BaseModel):
    event_id: uuid.UUID


class RegistrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    user_id: uuid.UUID
    status: RegistrationStatus
    confirmation_expires_at: datetime | None
    registered_at: datetime
    

class RegistrationResult(BaseModel):
    status: Literal["registered", "waitlisted"]
    message: str
    registration: RegistrationOut | None = None
    waitlist_entry: WaitlistOut | None = None