import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Enum as SqlEnum, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.enums import EventStatus

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.registration import Registration
    from app.models.waitlist import WaitlistEntry


class Event(Base):
    __tablename__ = "events"
    
    __table_args__ = (
        CheckConstraint("capacity > 0", name="capacity_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    organizer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        SqlEnum(EventStatus, name="event_status"), nullable=False, default=EventStatus.DRAFT
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    organizer: Mapped["User"] = relationship(back_populates="events")
    registrations: Mapped[list["Registration"]] = relationship(back_populates="event")
    waitlist_entries: Mapped[list["WaitlistEntry"]] = relationship(back_populates="event")