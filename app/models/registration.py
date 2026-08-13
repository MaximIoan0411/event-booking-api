import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Enum as SqlEnum, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.enums import RegistrationStatus

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.event import Event


class Registration(Base):
    __tablename__ = "registrations"
    
    __table_args__ = (
        Index(
            "uq_registration_active",
            "user_id", "event_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING_CONFIRMATION', 'CONFIRMED')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    status: Mapped[RegistrationStatus] = mapped_column(
        SqlEnum(RegistrationStatus, name="registration_status"),
        nullable=False,
        default=RegistrationStatus.PENDING_CONFIRMATION,
    )
    confirmation_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="registrations")
    event: Mapped["Event"] = relationship(back_populates="registrations")