import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.event import Event
from app.models.registration import Registration
from app.models.waitlist import WaitlistEntry
from app.enums import EventStatus, RegistrationStatus, WaitlistStatus
from app.config import get_settings

settings = get_settings()

OCCUPYING_STATUSES = (RegistrationStatus.PENDING_CONFIRMATION, RegistrationStatus.CONFIRMED)


async def register_for_event(db: AsyncSession, event_id: uuid.UUID, user_id: uuid.UUID):
    
    result = await db.execute(select(Event).where(Event.id == event_id).with_for_update())
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eveniment inexistent")
    if event.status != EventStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Evenimentul nu este deschis pentru înscrieri")

    existing_reg = await db.execute(
        select(Registration).where(
            Registration.event_id == event_id,
            Registration.user_id == user_id,
            Registration.status.in_(OCCUPYING_STATUSES),
        )
    )
    if existing_reg.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ești deja înscris la acest eveniment")

    existing_wait = await db.execute(
        select(WaitlistEntry).where(
            WaitlistEntry.event_id == event_id,
            WaitlistEntry.user_id == user_id,
            WaitlistEntry.status.in_((WaitlistStatus.WAITING, WaitlistStatus.PROMOTED)),
        )
    )
    if existing_wait.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ești deja pe lista de așteptare")

    count_result = await db.execute(
        select(func.count()).select_from(Registration).where(
            Registration.event_id == event_id,
            Registration.status.in_(OCCUPYING_STATUSES),
        )
    )
    occupied = count_result.scalar_one()

    if occupied < event.capacity:
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.REGISTRATION_CONFIRMATION_WINDOW_MINUTES
        )
        registration = Registration(
            user_id=user_id,
            event_id=event_id,
            status=RegistrationStatus.PENDING_CONFIRMATION,
            confirmation_expires_at=expires_at,
        )
        db.add(registration)
        await db.commit()
        await db.refresh(registration)
        return "registered", registration

    position_result = await db.execute(
        select(func.count()).select_from(WaitlistEntry).where(
            WaitlistEntry.event_id == event_id,
            WaitlistEntry.status == WaitlistStatus.WAITING,
        )
    )
    next_position = position_result.scalar_one() + 1

    waitlist_entry = WaitlistEntry(
        user_id=user_id, event_id=event_id, status=WaitlistStatus.WAITING, position=next_position
    )
    db.add(waitlist_entry)
    await db.commit()
    await db.refresh(waitlist_entry)
    return "waitlisted", waitlist_entry


async def confirm_registration(db: AsyncSession, registration: Registration) -> Registration:
    if registration.status != RegistrationStatus.PENDING_CONFIRMATION:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nu poate fi confirmată în starea curentă")
    if registration.confirmation_expires_at and registration.confirmation_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fereastra de confirmare a expirat")

    registration.status = RegistrationStatus.CONFIRMED
    registration.confirmation_expires_at = None
    await db.commit()
    return registration


async def cancel_registration(db: AsyncSession, registration: Registration) -> Registration:
    if registration.status not in OCCUPYING_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Înregistrarea nu poate fi anulată")

    registration.status = RegistrationStatus.CANCELLED
    await db.commit()

    from app.services.waitlist_service import promote_next_from_waitlist
    await promote_next_from_waitlist(db, registration.event_id)

    return registration