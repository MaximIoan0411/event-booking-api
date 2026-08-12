import uuid
from datetime import datetime, timezone, timedelta
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.enums import EventStatus
from app.schemas.user import UserPublic


class EventBase(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    capacity: int = Field(gt=0)
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def check_dates(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time trebuie să fie după start_time")
        min_start = datetime.now(timezone.utc) + timedelta(days=2)
        if self.start_time < min_start:
            raise ValueError("start_time trebuie să fie cu cel puțin 2 zile în avans")
        return self


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    capacity: int | None = Field(default=None, gt=0)
    start_time: datetime | None = None
    end_time: datetime | None = None


class EventApproval(BaseModel):
    action: Literal["approve", "reject"]


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    capacity: int
    start_time: datetime
    end_time: datetime
    status: EventStatus
    organizer: UserPublic
    created_at: datetime
    available_spots: int | None = None