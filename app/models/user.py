import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.enums import UserRole

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.registration import Registration
    from app.models.waitlist import WaitlistEntry
    from app.models.refresh_token import RefreshToken



class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role"), nullable=False, default=UserRole.ATTENDEE
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    events: Mapped[list["Event"]] = relationship(back_populates="organizer")
    registrations: Mapped[list["Registration"]] = relationship(back_populates="user")
    waitlist_entries: Mapped[list["WaitlistEntry"]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")